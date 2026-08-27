"""
Monitoreo del fallback compartido de Groq — corre adentro de la propia app.

No depende de ningún cron externo ni de que la notebook esté prendida. Al
apretar "Activar" en el panel, arranca un thread propio de background
(`ensure_scheduler_running`/`_scheduler_loop`) que corre una prueba cada
`interval_minutes` de verdad, mientras la ventana esté activa. La conexión
con `material.views.health_check` (que UptimeRobot ya pinguea regularmente
para evitar que Render duerma el free tier) es solo una red de resguardo por
si el proceso se reinicia (deploy, crash) con una ventana todavía activa: ese
chequeo de resurrección está throttleado a 1 vez cada
HEALTH_PING_THROTTLE_SECONDS (~4 veces/día) — antes de ese throttle, CADA
ping (cada ~5 min) consultaba Postgres para ver si correspondía correr, lo
que le pisaba el autosuspend de 5 min a Neon: el compute nunca quedaba
inactivo el tiempo suficiente para bajar a cero y se consumían ~24h/día de
CU-hours aunque los monitoreos estuvieran apagados (encontrado 2026-08-14,
con la cuota gratis de Neon casi agotada a mitad de mes). El thread de
`_scheduler_loop`, en cambio, solo toca Postgres una vez por intervalo (para
leer la config vigente y sincronizar el buffer) — muy por debajo de la
frecuencia de esos pings, así que subir `interval_minutes` (más corridas/día)
no reintroduce ese problema.

Además, las corridas automáticas (a diferencia de los botones manuales
"Probar ahora"/"Probar visión" del panel, que siguen escribiendo directo a
Postgres para feedback inmediato) NO escriben en Postgres una por una: cada
resultado se apila primero en un archivo local (`BUFFER_PATH`, JSON Lines —
"una tabla en la app", no en la DB) y ese archivo se sincroniza a Postgres
al final de cada corrida (ver `sync_buffer_to_db`) — su valor es la
resiliencia: si el bulk_create falla por un problema transitorio de Neon, el
archivo NO se borra y esas filas se reintentan en la próxima corrida en vez
de perderse.

El test replica el camino real de generación (mismo backend, mismo chunking,
mismo tope duro de cantidad) pero llamando directo a las funciones internas
en vez de pegarle a la app por HTTP — no hace falta login, sesión, ni subir
un archivo real: usa el mismo texto de prueba fijo.
"""
import base64
import json
import logging
import threading
import time
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)

TEST_USERNAME = getattr(settings, 'GROQ_MONITOR_TEST_USERNAME', 'groq_test_bot')
FIXTURES_DIR = Path(__file__).resolve().parent.parent / 'scripts' / 'fixtures'

# Candidatos a probar como modelo de visión, por proveedor. No hay garantía
# de que todos existan/estén activos en un momento dado — el test reporta el
# error tal cual lo devuelve la API (ej. "model not found") para cada uno,
# así se decide con datos reales cuál usar en vez de asumir.
#
# Groq probado 2026-08-04 con la API key de GlobalAIConfig: NINGUNO de los 4
# candidatos históricos funcionó (`llama-3.2-*-vision-preview` decommissioned,
# `llama-4-scout`/`llama-4-maverick` no existen para esta key — GET
# /v1/models de esta cuenta hoy no devuelve NINGÚN modelo con visión). Por
# eso se sacó Groq de esta lista/UI — ver [[project_ai_image_support_evaluation]]
# para el detalle y re-agregarlo si Groq habilita algo en el futuro.
#
# Gemini probado 2026-08-04: `gemini-2.5-flash-lite` da 404 ("no longer
# available to new users"), `gemini-2.5-flash` funciona y responde
# correctamente incluso preguntas que requieren leer datos de la imagen
# (ver VISION_TEST_PROMPT/VISION_EXPECTED_SUBSTRINGS más abajo).
VISION_TEST_MODELS = {
    'gemini': [
        'gemini-2.5-flash',
        'gemini-2.5-flash-lite',
        'gemini-2.0-flash',
    ],
}
DEFAULT_VISION_MODEL = 'gemini-2.5-flash'
DEFAULT_VISION_PROVIDER = 'gemini'

# Gráfico de barras generado a propósito (ver scripts/generate_vision_test_chart.py
# si hace falta regenerarlo) — a diferencia de un ícono, exige que el modelo
# realmente "lea" valores de la imagen en vez de solo describir formas
# genéricas. VISION_EXPECTED_SUBSTRINGS se busca (case-insensitive) en la
# respuesta para marcar automáticamente si el modelo contestó bien.
VISION_TEST_IMAGE = Path(__file__).resolve().parent.parent / 'static' / 'test_images' / 'vision_test_chart.png'
VISION_TEST_PROMPT = '¿Cuál trimestre tuvo el valor más alto en el gráfico, y cuál fue aproximadamente ese valor?'
VISION_EXPECTED_SUBSTRINGS = ['T4', '77']
# 'easy': prosa lineal, ~2000 tokens, se parte en pocos fragmentos grandes.
# 'hard': mismo orden de tokens pero con listas, sub-ítems y jerga técnica
# densa (sistemas distribuidos/consenso) — se parte en más fragmentos más
# chicos, para estresar más veces seguidas el rate limit y ver cómo responde
# el modelo con contenido estructuralmente más difícil de resumir en JSON.
FIXTURES = {
    'easy': {'path': FIXTURES_DIR / 'groq_test_content.txt', 'split_max_tokens': 700},
    'hard': {'path': FIXTURES_DIR / 'groq_test_content_hard.txt', 'split_max_tokens': 400},
}
TARGET_QUESTIONS = 30

# Candidatos a modelo de TEXTO para el monitoreo de carga — deliberadamente
# fijos acá, NO tomados de GlobalAIConfig.model: el objetivo de esta corrida es
# comparar candidatos entre sí con datos reales, no probar "el modelo activo
# de producción" (ese sigue siendo GlobalAIConfig.model, editable desde Django
# Admin — ver ai_router.py, que ya no tiene ningún modelo hardcodeado como
# fallback). Sí se usa la API key ya cargada en GlobalAIConfig(provider='groq')
# — no hace falta una key separada para probar.
#
# Contexto (2026-08-22): Groq deprecó llama-3.1-8b-instant y
# llama-3.3-70b-versatile el 16/08/2026 para cuentas free/dev — los dos
# modelos que este proyecto usaba. Su propia guía de migración:
#   llama-3.1-8b-instant   → openai/gpt-oss-20b
#   llama-3.3-70b-versatile → openai/gpt-oss-120b  (o qwen/qwen3.6-27b)
# Los tres reemplazos son modelos de razonamiento (chain-of-thought) — a
# diferencia de los Llama que reemplazan, los tokens de "pensar" salen del
# mismo presupuesto que la respuesta final, así que cada candidato lleva acá
# el fix que le corresponde (generate_kwargs → ver OpenAICompatibleBackend.
# generate() en ai_router.py y el colchón de tokens en
# views_document_processor._generate_questions_for_chunk):
#   - gpt-oss-20b/120b: reasoning_effort="low" (Groq: valores low/medium/high,
#     default medium) para no gastar de más en razonamiento que no hace falta
#     para esta tarea.
#   - qwen3.6-27b: reasoning_effort="none" — este modelo soporta desactivar el
#     razonamiento por completo (a diferencia de gpt-oss, que siempre razona
#     algo), lo que de raíz evita el problema de truncamiento.
# response_format=json_object (json_mode) se pide siempre, para los tres —
# ver _generate_questions_for_chunk.
TEXT_TEST_MODELS = [
    {
        'model': 'openai/gpt-oss-20b',
        'generate_kwargs': {'reasoning_effort': 'low'},
    },
    {
        'model': 'openai/gpt-oss-120b',
        'generate_kwargs': {'reasoning_effort': 'low'},
    },
    {
        'model': 'qwen/qwen3.6-27b',
        'generate_kwargs': {'reasoning_effort': 'none'},
    },
]
# Techo externo de tokens de salida para este test — más alto que el default
# de producción (4096) para darle aire al colchón de razonamiento de arriba;
# ver el min() en _generate_questions_for_chunk, que igual no deja pedir más
# de lo que hace falta para la cantidad de preguntas pedidas.
TEXT_TEST_OUTPUT_CEILING = 6144

_run_lock = threading.Lock()
_vision_run_lock = threading.Lock()

# --- Buffer local ("tabla en la app") para las corridas automáticas --------
# JSON Lines en vez de un modelo Django/SQLite aparte: no necesita migración
# ni conexión propia, y alcanza para lo que es (unas pocas filas efímeras
# entre un tick y el siguiente).
BUFFER_PATH = Path(settings.BASE_DIR) / 'var' / 'groq_monitor_buffer.jsonl'
_buffer_lock = threading.Lock()


def _buffer_append(kind, fields):
    """Agrega una fila al buffer local. No toca Postgres."""
    record = dict(fields)
    record['kind'] = kind
    record.setdefault('created_at', timezone.now().isoformat())
    line = json.dumps(record, default=str)
    with _buffer_lock:
        BUFFER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(BUFFER_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')


def sync_buffer_to_db():
    """Sube todo lo acumulado en el buffer local a Postgres (bulk_create) y
    recién ahí lo borra del archivo — si el bulk_create falla, el archivo se
    conserva tal cual para reintentar en el próximo tick en vez de perder
    esas filas."""
    from .models import GroqMonitorRun, GroqVisionTestRun

    with _buffer_lock:
        if not BUFFER_PATH.exists():
            return 0
        raw = BUFFER_PATH.read_text(encoding='utf-8')
        records = [json.loads(line) for line in raw.splitlines() if line.strip()]
        if not records:
            BUFFER_PATH.unlink()
            return 0

        text_objs, vision_objs = [], []
        for r in records:
            r = dict(r)
            kind = r.pop('kind', 'text')
            created_at = parse_datetime(r.pop('created_at', '') or '') or timezone.now()
            if kind == 'vision':
                vision_objs.append(GroqVisionTestRun(created_at=created_at, **r))
            else:
                text_objs.append(GroqMonitorRun(created_at=created_at, **r))

        try:
            if text_objs:
                GroqMonitorRun.objects.bulk_create(text_objs)
            if vision_objs:
                GroqVisionTestRun.objects.bulk_create(vision_objs)
        except Exception:
            logger.exception(
                'Error sincronizando el buffer local de monitoreo a Postgres — '
                'se conserva el archivo para reintentar en el próximo tick.'
            )
            return 0

        BUFFER_PATH.unlink()
        return len(records)


_last_health_ping_check = 0.0
_health_ping_lock = threading.Lock()
# ~4 veces/día (24h / 6h). Ya NO marca la cadencia real de las corridas —
# eso lo hace el thread propio de _scheduler_loop, despierto a intervalo real
# de `interval_minutes`. Esto solo limita cada cuánto se chequea, vía el ping
# de UptimeRobot a /health/ (~cada 5 min), si hace falta RESUCITAR ese thread
# (ej. si el proceso de Render se reinició con una ventana todavía activa) —
# ver ensure_scheduler_running(). En el camino normal (el thread arrancó al
# instante desde el botón "Activar") este chequeo no hace nada.
HEALTH_PING_THROTTLE_SECONDS = 6 * 3600

_scheduler_lock = threading.Lock()
_scheduler_state = {'text': None, 'vision': None}  # kind -> {'thread', 'stop_event'}


def maybe_trigger_from_health_ping():
    """Único punto llamado desde material.views.health_check."""
    global _last_health_ping_check
    now = time.monotonic()
    with _health_ping_lock:
        if now - _last_health_ping_check < HEALTH_PING_THROTTLE_SECONDS:
            return
        _last_health_ping_check = now
    ensure_scheduler_running('text')
    ensure_scheduler_running('vision')


def _scheduler_alive(kind):
    state = _scheduler_state.get(kind)
    return bool(state) and state['thread'].is_alive()


def ensure_scheduler_running(kind):
    """Arranca (si no está corriendo ya) el thread de background que corre
    las pruebas de `kind` ('text'/'vision') al ritmo real de
    `interval_minutes`, en vez de quedar atado al throttle de ~6h pensado
    solo para no pisarle el autosuspend a Neon (ver HEALTH_PING_THROTTLE_
    SECONDS). El thread solo toca Postgres una vez por intervalo — para leer
    la config vigente y sincronizar el buffer — muy por debajo de la
    frecuencia de los pings de UptimeRobot que la generación anterior de
    este monitoreo usaba como reloj.

    Llamarla de más es gratis: no hace nada si ya hay un thread vivo para
    ese `kind`, y el thread mismo corta solo si el monitoreo no está
    activo."""
    with _scheduler_lock:
        if _scheduler_alive(kind):
            return
        stop_event = threading.Event()
        thread = threading.Thread(target=_scheduler_loop, args=(kind, stop_event), daemon=True)
        _scheduler_state[kind] = {'thread': thread, 'stop_event': stop_event}
        thread.start()


def stop_scheduler(kind):
    """Señala al thread de `kind` que corte apenas termine la corrida en
    curso (si hay una en curso), en vez de esperar dormido hasta el próximo
    intervalo. Llamada desde el botón "Detener" del panel."""
    state = _scheduler_state.get(kind)
    if state:
        state['stop_event'].set()


def _scheduler_loop(kind, stop_event):
    """Bucle real del monitoreo automático: una corrida por
    `interval_minutes`, releyendo la config de la DB en cada vuelta (así
    toma en caliente un cambio de intervalo o un "Detener" hecho desde el
    panel) hasta que la ventana venza o se pida frenar."""
    from .models import GroqMonitorSchedule, VisionMonitorSchedule
    model = GroqMonitorSchedule if kind == 'text' else VisionMonitorSchedule

    while not stop_event.is_set():
        cfg = model.objects.filter(enabled=True).first()
        if cfg is None:
            break

        now = timezone.now()
        if cfg.ends_at and now >= cfg.ends_at:
            model.objects.filter(pk=cfg.pk).update(enabled=False)
            logger.info(f'Monitoreo de {kind}: ventana vencida, se desactiva.')
            break

        if kind == 'text':
            _run_safely(persist='buffer')
        else:
            _run_vision_safely(cfg.provider, cfg.model, persist='buffer')
        model.objects.filter(pk=cfg.pk).update(last_run_at=timezone.now())

        interval_seconds = max(60, cfg.interval_minutes * 60)
        if stop_event.wait(timeout=interval_seconds):
            break


def _run_safely(persist='db'):
    if not _run_lock.acquire(blocking=False):
        return  # ya hay una corrida en curso, no superponer
    try:
        run_test(persist=persist)
        if persist == 'buffer':
            sync_buffer_to_db()
    except Exception:
        logger.exception('Corrida de monitoreo de Groq terminó con excepción no manejada')
    finally:
        _run_lock.release()


def _pick_fixture():
    """Alterna easy/hard según la cantidad de corridas ya guardadas, para ir
    juntando datos comparables de ambos documentos a lo largo de la ventana."""
    from .models import GroqMonitorRun
    count = GroqMonitorRun.objects.count()
    key = 'hard' if count % 2 == 1 else 'easy'
    return key, FIXTURES[key]


def _pick_text_model():
    """Rota entre TEXT_TEST_MODELS según la cantidad de corridas ya guardadas
    — con un módulo distinto al de _pick_fixture (2), así documento y modelo
    no quedan pegados siempre a la misma combinación (con 3 candidatos, el
    ciclo completo doc×modelo se cubre cada 6 corridas)."""
    from .models import GroqMonitorRun
    count = GroqMonitorRun.objects.count()
    return TEXT_TEST_MODELS[count % len(TEXT_TEST_MODELS)]


def run_test(fixture_key=None, persist='db'):
    """Ejecuta una corrida. Se puede llamar también manualmente (botón
    "Probar ahora" en la página de monitoreo, con persist='db' por default).

    fixture_key: 'easy' o 'hard' para forzar un documento puntual; si se omite,
    alterna automáticamente entre ambos (ver `_pick_fixture`).
    persist: 'db' escribe directo en GroqMonitorRun; 'buffer' apila en el
    archivo local (ver sync_buffer_to_db).

    El modelo de texto NO se lee de GlobalAIConfig.model — rota automáticamente
    entre TEXT_TEST_MODELS (ver comentario ahí) usando solo la API key ya
    cargada en GlobalAIConfig(provider='groq'). Así se compara a los tres
    candidatos con datos reales sin tocar cuál es el modelo activo en
    producción."""
    from django.contrib.auth.models import User
    from .models import GroqMonitorRun, GlobalAIConfig
    from .ai_router import _build_external_backend
    from .views_document_processor import _generate_questions_for_chunk, _split_into_chunks

    t0 = time.time()

    if fixture_key and fixture_key in FIXTURES:
        fixture = FIXTURES[fixture_key]
    else:
        fixture_key, fixture = _pick_fixture()

    candidate = _pick_text_model()
    model_name = candidate['model']
    generate_kwargs = candidate.get('generate_kwargs') or {}

    def save(**kwargs):
        elapsed = round(time.time() - t0, 1)
        payload = dict(elapsed_seconds=elapsed, fixture=fixture_key, model_name=model_name, **kwargs)
        if persist == 'buffer':
            _buffer_append('text', payload)
        else:
            GroqMonitorRun.objects.create(**payload)

    test_user = User.objects.filter(username=TEST_USERNAME).first()
    if test_user is None:
        save(success=False, reason='missing_test_user', detail=f'No existe el usuario "{TEST_USERNAME}".')
        return

    fixture_path = fixture['path']
    if not fixture_path.exists():
        save(success=False, reason='missing_fixture', detail=str(fixture_path))
        return

    cfg = GlobalAIConfig.objects.filter(provider='groq').exclude(api_key_encrypted='').order_by('-id').first()
    if cfg is None:
        save(success=False, reason='missing_api_key', detail="No hay ninguna GlobalAIConfig con proveedor 'groq' y API key cargada.")
        return

    try:
        backend = _build_external_backend(provider='groq', api_key=cfg.api_key, model=model_name, base_url=None)
        status = backend.get_status()
    except Exception as e:
        save(success=False, reason='backend_error', detail=str(e))
        return

    if not status.get('connected'):
        save(success=False, reason='backend_not_connected', detail=str(status))
        return

    text = fixture_path.read_text(encoding='utf-8')
    chunks = _split_into_chunks(text, max_tokens=fixture['split_max_tokens'])
    total_chunks = max(1, len(chunks))
    # Mismo techo de 12 preguntas/fragmento que usan las vistas reales — pedir
    # más excede el max_tokens de salida y Groq puede rechazar la request.
    # Redondeo hacia arriba (no //) para no quedar sistemáticamente por debajo
    # del objetivo — el tope duro más abajo se encarga de no pasarse.
    per_chunk = max(1, min(12, -(-TARGET_QUESTIONS // total_chunks)))
    chapter_title = (
        'Sistemas Distribuidos (monitor Groq — difícil)' if fixture_key == 'hard'
        else 'Bases de Datos (monitor Groq)'
    )

    questions = []
    failed_chunks = 0
    last_chunk_error = ''
    for i, chunk in enumerate(chunks):
        if len(questions) >= TARGET_QUESTIONS:
            break
        if i > 0:
            time.sleep(2)
        try:
            raw = _generate_questions_for_chunk(
                chunk, chapter_title, per_chunk, i, total_chunks,
                backend=backend, output_tokens_ceiling=TEXT_TEST_OUTPUT_CEILING,
                generate_kwargs=generate_kwargs,
            )
        except Exception as e:
            failed_chunks += 1
            last_chunk_error = f'{type(e).__name__}: {e}'
            logger.warning(f'Monitor Groq: fragmento {i + 1}/{total_chunks} falló ({model_name}): {last_chunk_error}')
            continue
        remaining = max(0, TARGET_QUESTIONS - len(questions))
        questions.extend((raw or [])[:remaining])

    texts = [(q.get('pregunta') or '').strip() for q in questions]
    empty_count = sum(1 for t in texts if not t)
    non_empty = [t for t in texts if t]
    duplicate_count = len(non_empty) - len(set(non_empty))

    # Cupo del candidato puntual que se acaba de probar (no el de
    # GlobalAIConfig — cada modelo de Groq tiene su propio bucket de RPD/TPM,
    # así que el cupo "global" no representaría a este candidato). Llamada
    # mínima (1 token de salida) solo para leer los headers de la respuesta.
    quota = {}
    try:
        quota_result = backend.generate(prompt='.', max_tokens=1, temperature=0)
        quota = quota_result.get('rate_limit') or {}
    except Exception as e:
        logger.warning(f'No se pudo leer cupo de {model_name} al final de la corrida: {e}')

    save(
        success=True,
        target_questions=TARGET_QUESTIONS,
        total_generated=len(questions),
        met_target=len(questions) >= TARGET_QUESTIONS and empty_count == 0,
        empty_questions=empty_count,
        duplicate_questions=duplicate_count,
        failed_chunks=failed_chunks,
        detail=(f'Último fragmento fallido: {last_chunk_error}' if failed_chunks else ''),
        quota_remaining_requests=quota.get('remaining_requests'),
        quota_limit_requests=quota.get('limit_requests'),
        quota_remaining_tokens=quota.get('remaining_tokens'),
        quota_limit_tokens=quota.get('limit_tokens'),
    )


def run_vision_test(model_name, provider=DEFAULT_VISION_PROVIDER, persist='db'):
    """
    Prueba puntual de un modelo con la imagen de prueba (gráfico con datos
    reales a leer, ver VISION_TEST_PROMPT). Usa la API key guardada en
    GlobalAIConfig para ese `provider` (busca por proveedor, no exige
    is_active=True — así se puede probar sin tocar cuál está activo como
    fallback real) y construye el backend con `_build_external_backend`,
    la MISMA función que usa la app en producción — así se prueba
    literalmente la misma clase (ej. GeminiBackend nativo para 'gemini',
    no el endpoint OpenAI-compatible), no una aproximación.

    persist: 'db' (default, botones manuales) o 'buffer' (tick automático).
    """
    from .models import GlobalAIConfig, GroqVisionTestRun
    from .ai_router import _build_external_backend

    t0 = time.time()

    def save(**kwargs):
        elapsed = round(time.time() - t0, 1)
        payload = dict(model_name=f'[{provider}] {model_name}', elapsed_seconds=elapsed, **kwargs)
        if persist == 'buffer':
            _buffer_append('vision', payload)
        else:
            GroqVisionTestRun.objects.create(**payload)

    cfg = GlobalAIConfig.objects.filter(provider=provider).exclude(api_key_encrypted='').order_by('-id').first()
    if cfg is None:
        save(success=False, error=f'No hay ninguna GlobalAIConfig con proveedor "{provider}" y API key cargada.')
        return

    if not VISION_TEST_IMAGE.exists():
        save(success=False, error=f'No se encontró la imagen de prueba: {VISION_TEST_IMAGE}')
        return

    try:
        image_b64 = base64.b64encode(VISION_TEST_IMAGE.read_bytes()).decode('utf-8')
        data_uri = f'data:image/png;base64,{image_b64}'
    except Exception as e:
        save(success=False, error=f'No se pudo leer/codificar la imagen de prueba: {e}')
        return

    try:
        backend = _build_external_backend(provider=provider, api_key=cfg.api_key, model=model_name, base_url=None)
        result = backend.generate(
            prompt=VISION_TEST_PROMPT,
            max_tokens=200,
            temperature=0.1,
            images=[data_uri],
        )
    except Exception as e:
        save(success=False, error=f'{type(e).__name__}: {e}')
        return

    rate_limit = result.get('rate_limit') or {}
    if not result.get('success'):
        save(success=False, error=result.get('error', 'Error desconocido'),
             quota_remaining_requests=rate_limit.get('remaining_requests'),
             quota_limit_requests=rate_limit.get('limit_requests'),
             quota_remaining_tokens=rate_limit.get('remaining_tokens'),
             quota_limit_tokens=rate_limit.get('limit_tokens'))
        return

    text = (result.get('text') or '').strip()
    content_ok = all(s.lower() in text.lower() for s in VISION_EXPECTED_SUBSTRINGS)
    save(success=True, response_text=text[:2000], content_check_passed=content_ok,
         quota_remaining_requests=rate_limit.get('remaining_requests'),
         quota_limit_requests=rate_limit.get('limit_requests'),
         quota_remaining_tokens=rate_limit.get('remaining_tokens'),
         quota_limit_tokens=rate_limit.get('limit_tokens'))


def run_vision_load_test(count, provider=DEFAULT_VISION_PROVIDER, model=DEFAULT_VISION_MODEL, delay_seconds=1):
    """
    Ráfaga de `count` llamadas de visión seguidas, para encontrar en la
    práctica el límite real de un modelo (RPM/RPD) en vez de asumirlo — cada
    llamada queda registrada como una GroqVisionTestRun normal (persist='db',
    no pasa por el buffer: es una acción manual, se quiere ver el resultado
    ya), así que después se puede leer con analyze_vision_quota_cycles()
    cuántas llamadas exitosas hubo antes de cortar y cuánto tardó en
    recuperarse.

    Ojo: cada llamada individual (run_vision_test → backend.generate) ya
    reintenta sola hasta 2 veces ante un 429 antes de darse por vencida (ver
    GeminiBackend/OpenAICompatibleBackend) — un "success=False, 429" acá
    representa 3 intentos reales contra la API, no 1. Es el mismo
    comportamiento que tiene la generación real de preguntas, así que el
    resultado es representativo de lo que vería un usuario, pero el consumo
    de cupo real es mayor al número de filas que se crean.
    """
    from django.db.models import Max
    from .models import GroqVisionTestRun

    created_ids = []
    for i in range(max(1, count)):
        if i > 0 and delay_seconds > 0:
            time.sleep(delay_seconds)
        before_max_id = GroqVisionTestRun.objects.aggregate(m=Max('id'))['m'] or 0
        run_vision_test(model, provider=provider)
        new_run = GroqVisionTestRun.objects.filter(id__gt=before_max_id).order_by('-id').first()
        if new_run:
            created_ids.append(new_run.id)
    return list(GroqVisionTestRun.objects.filter(id__in=created_ids).order_by('id'))


def _run_vision_safely(provider, model, persist='db'):
    if not _vision_run_lock.acquire(blocking=False):
        return
    try:
        run_vision_test(model, provider=provider, persist=persist)
        if persist == 'buffer':
            sync_buffer_to_db()
    except Exception:
        logger.exception('Corrida cíclica de monitoreo de visión terminó con excepción no manejada')
    finally:
        _vision_run_lock.release()


def analyze_vision_quota_cycles(limit=20):
    """
    Gemini no manda headers de cupo (a diferencia de Groq) — la única señal
    real es el error 429 cuando se corta. Esta función reconstruye, a partir
    del historial de GroqVisionTestRun, cada corte por cupo: cuántas llamadas
    exitosas hubo antes de cortar, y cuánto tardó en volver a andar (si es
    que ya volvió) — para ir viendo empíricamente el ritmo real de reset
    (¿por minuto? ¿por hora? ¿por día?) en vez de asumirlo.

    Devuelve una lista de dicts (más reciente primero):
        {blocked_at, model_name, successes_before, recovered_at, recovery_delta}
    `recovered_at`/`recovery_delta` quedan en None si todavía no hubo ninguna
    corrida exitosa después de ese 429.
    """
    from .models import GroqVisionTestRun

    runs = list(GroqVisionTestRun.objects.all().order_by('created_at'))
    cycles = []
    successes_since_reset = 0
    pending = None

    for run in runs:
        is_429 = (not run.success) and run.error and '429' in run.error
        if run.success:
            successes_since_reset += 1
            if pending is not None:
                pending['recovered_at'] = run.created_at
                pending['recovery_delta'] = run.created_at - pending['blocked_at']
                cycles.append(pending)
                pending = None
        elif is_429:
            if pending is None:
                pending = {
                    'blocked_at': run.created_at,
                    'model_name': run.model_name,
                    'successes_before': successes_since_reset,
                    'recovered_at': None,
                    'recovery_delta': None,
                }
            successes_since_reset = 0
        # errores que no son 429 (ej. modelo inválido) no cortan ni reinician
        # el conteo — no son evidencia de cupo agotado.

    if pending is not None:
        cycles.append(pending)

    cycles.reverse()
    return cycles[:limit]

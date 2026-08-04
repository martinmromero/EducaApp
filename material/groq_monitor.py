"""
Monitoreo del fallback compartido de Groq — corre adentro de la propia app.

No depende de ningún cron externo ni de que la notebook esté prendida: se
dispara desde `material.views.health_check` (que UptimeRobot ya pinguea
regularmente para evitar que Render duerma el free tier). Cada ping revisa si
pasó `interval_minutes` desde la última corrida y, si corresponde, lanza un
test en un thread de background sin bloquear la respuesta del health check.

El test replica el camino real de generación (mismo backend, mismo chunking,
mismo tope duro de cantidad) pero llamando directo a las funciones internas
en vez de pegarle a la app por HTTP — no hace falta login, sesión, ni subir
un archivo real: usa el mismo texto de prueba fijo.
"""
import base64
import logging
import threading
import time
from pathlib import Path

from django.conf import settings
from django.utils import timezone

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

_run_lock = threading.Lock()


def maybe_trigger():
    """Llamado en cada request a /health/. No bloquea: si corresponde disparar
    una corrida, la lanza en un thread aparte y vuelve enseguida."""
    try:
        from .models import GroqMonitorSchedule
        cfg = GroqMonitorSchedule.objects.filter(enabled=True).first()
        if cfg is None:
            return

        now = timezone.now()
        if cfg.ends_at and now >= cfg.ends_at:
            GroqMonitorSchedule.objects.filter(pk=cfg.pk).update(enabled=False)
            logger.info('Monitoreo de Groq: ventana de 48h vencida, se desactiva.')
            return

        if cfg.last_run_at and (now - cfg.last_run_at).total_seconds() < cfg.interval_minutes * 60:
            return

        # Reclamo atómico: solo un thread gana la carrera si dos requests caen
        # casi al mismo tiempo (poco probable con 1 worker, pero es gratis).
        claimed = GroqMonitorSchedule.objects.filter(
            pk=cfg.pk, last_run_at=cfg.last_run_at
        ).update(last_run_at=now)
        if not claimed:
            return

        threading.Thread(target=_run_safely, daemon=True).start()
    except Exception:
        logger.exception('Error chequeando si corresponde disparar el monitoreo de Groq')


def _run_safely():
    if not _run_lock.acquire(blocking=False):
        return  # ya hay una corrida en curso, no superponer
    try:
        run_test()
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


def run_test(fixture_key=None):
    """Ejecuta una corrida y la guarda en GroqMonitorRun. Se puede llamar
    también manualmente (botón "Probar ahora" en la página de monitoreo).

    fixture_key: 'easy' o 'hard' para forzar un documento puntual; si se omite,
    alterna automáticamente entre ambos (ver `_pick_fixture`)."""
    from django.contrib.auth.models import User
    from .models import GroqMonitorRun
    from .ai_router import get_backend_for_user, get_global_demo_quota, ensure_fresh_demo_quota
    from .views_document_processor import _generate_questions_for_chunk, _split_into_chunks

    t0 = time.time()

    if fixture_key and fixture_key in FIXTURES:
        fixture = FIXTURES[fixture_key]
    else:
        fixture_key, fixture = _pick_fixture()

    def save(**kwargs):
        elapsed = round(time.time() - t0, 1)
        GroqMonitorRun.objects.create(elapsed_seconds=elapsed, fixture=fixture_key, **kwargs)

    test_user = User.objects.filter(username=TEST_USERNAME).first()
    if test_user is None:
        save(success=False, reason='missing_test_user', detail=f'No existe el usuario "{TEST_USERNAME}".')
        return

    fixture_path = fixture['path']
    if not fixture_path.exists():
        save(success=False, reason='missing_fixture', detail=str(fixture_path))
        return

    try:
        backend = get_backend_for_user(test_user)
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
                backend=backend,
            )
        except Exception as e:
            failed_chunks += 1
            last_chunk_error = f'{type(e).__name__}: {e}'
            logger.warning(f'Monitor Groq: fragmento {i + 1}/{total_chunks} falló: {last_chunk_error}')
            continue
        remaining = max(0, TARGET_QUESTIONS - len(questions))
        questions.extend((raw or [])[:remaining])

    texts = [(q.get('pregunta') or '').strip() for q in questions]
    empty_count = sum(1 for t in texts if not t)
    non_empty = [t for t in texts if t]
    duplicate_count = len(non_empty) - len(set(non_empty))

    try:
        ensure_fresh_demo_quota()
        quota = get_global_demo_quota() or {}
    except Exception:
        quota = {}

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


def run_vision_test(model_name, provider=DEFAULT_VISION_PROVIDER):
    """
    Prueba puntual de un modelo con la imagen de prueba (gráfico con datos
    reales a leer, ver VISION_TEST_PROMPT). Usa la API key guardada en
    GlobalAIConfig para ese `provider` (busca por proveedor, no exige
    is_active=True — así se puede probar sin tocar cuál está activo como
    fallback real) y construye el backend con `_build_external_backend`,
    la MISMA función que usa la app en producción — así se prueba
    literalmente la misma clase (ej. GeminiBackend nativo para 'gemini',
    no el endpoint OpenAI-compatible), no una aproximación.
    """
    from .models import GlobalAIConfig, GroqVisionTestRun
    from .ai_router import _build_external_backend

    t0 = time.time()

    def save(**kwargs):
        elapsed = round(time.time() - t0, 1)
        GroqVisionTestRun.objects.create(
            model_name=f'[{provider}] {model_name}', elapsed_seconds=elapsed, **kwargs
        )

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


def maybe_trigger_vision():
    """Igual que maybe_trigger() pero para la corrida cíclica del modelo de
    visión ya elegido — mide cupo y cadencia de renovación en el tiempo,
    llamado desde el mismo pulso de /health/."""
    try:
        from .models import VisionMonitorSchedule
        cfg = VisionMonitorSchedule.objects.filter(enabled=True).first()
        if cfg is None:
            return

        now = timezone.now()
        if cfg.ends_at and now >= cfg.ends_at:
            VisionMonitorSchedule.objects.filter(pk=cfg.pk).update(enabled=False)
            logger.info('Monitoreo de visión: ventana vencida, se desactiva.')
            return

        if cfg.last_run_at and (now - cfg.last_run_at).total_seconds() < cfg.interval_minutes * 60:
            return

        claimed = VisionMonitorSchedule.objects.filter(
            pk=cfg.pk, last_run_at=cfg.last_run_at
        ).update(last_run_at=now)
        if not claimed:
            return

        threading.Thread(
            target=_run_vision_safely, args=(cfg.provider, cfg.model), daemon=True
        ).start()
    except Exception:
        logger.exception('Error chequeando si corresponde disparar el monitoreo de visión')


_vision_run_lock = threading.Lock()


def _run_vision_safely(provider, model):
    if not _vision_run_lock.acquire(blocking=False):
        return
    try:
        run_vision_test(model, provider=provider)
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

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
import logging
import threading
import time
from pathlib import Path

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

TEST_USERNAME = getattr(settings, 'GROQ_MONITOR_TEST_USERNAME', 'groq_test_bot')
FIXTURES_DIR = Path(__file__).resolve().parent.parent / 'scripts' / 'fixtures'
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

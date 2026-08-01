#!/usr/bin/env python3
"""
Test de carga/monitoreo del fallback compartido de Groq contra producción.

Replica el flujo real de la app (login -> subir documento -> pedir generación
de preguntas en modo streaming -> leer el SSE hasta el final) para detectar
si Groq deja de devolver una cantidad razonable de preguntas por tanda, sin
depender de abrir el navegador ni de que la notebook esté prendida.

Uso:
    EDUCAAPP_TEST_USER=groq_test_bot \
    EDUCAAPP_TEST_PASS=... \
    python scripts/groq_load_test.py

Variables de entorno:
    EDUCAAPP_BASE_URL      default: https://educaapp.onrender.com
    EDUCAAPP_TEST_USER     usuario de prueba dedicado (obligatorio)
    EDUCAAPP_TEST_PASS     contraseña de ese usuario (obligatorio)
    GROQ_TEST_TARGET_QTY   preguntas a pedir por tanda (default: 30)

Imprime un único JSON por línea (stdout) con el resultado de la corrida, para
que quien invoque el script (un cron, un agente) lo pueda loguear tal cual.
No hace ningún commit ni push — eso es responsabilidad de quien lo invoca.
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = os.environ.get('EDUCAAPP_BASE_URL', 'https://educaapp.onrender.com').rstrip('/')
USERNAME = os.environ.get('EDUCAAPP_TEST_USER')
PASSWORD = os.environ.get('EDUCAAPP_TEST_PASS')
TARGET_QTY = int(os.environ.get('GROQ_TEST_TARGET_QTY', '30'))
FIXTURE_PATH = Path(__file__).parent / 'fixtures' / 'groq_test_content.txt'

TIMEOUT = 30
STREAM_TIMEOUT = 300  # la generación de 30 preguntas puede tardar varios minutos


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def fail(reason, **extra):
    result = {
        'timestamp': now_iso(),
        'success': False,
        'reason': reason,
        **extra,
    }
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(1)


def main():
    if not USERNAME or not PASSWORD:
        fail('missing_credentials', detail='Faltan EDUCAAPP_TEST_USER / EDUCAAPP_TEST_PASS en el entorno.')

    if not FIXTURE_PATH.exists():
        fail('missing_fixture', detail=f'No se encontró {FIXTURE_PATH}')

    session = requests.Session()
    session.headers['User-Agent'] = 'EducaApp-GroqLoadTest/1.0'
    t0 = time.time()

    # ---- 1) Login ----
    login_url = f'{BASE_URL}/accounts/login/'
    try:
        r = session.get(login_url, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.RequestException as e:
        fail('login_page_unreachable', detail=str(e))

    csrf_token = session.cookies.get('csrftoken')
    if not csrf_token:
        match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r.text)
        csrf_token = match.group(1) if match else None
    if not csrf_token:
        fail('no_csrf_token_on_login_page')

    r = session.post(
        login_url,
        data={'username': USERNAME, 'password': PASSWORD, 'csrfmiddlewaretoken': csrf_token},
        headers={'Referer': login_url},
        timeout=TIMEOUT,
    )
    if 'accounts/login' in r.url and r.status_code == 200:
        fail('login_failed', detail='La respuesta volvió a la página de login — credenciales inválidas o CSRF rechazado.')

    csrf_token = session.cookies.get('csrftoken', csrf_token)

    # ---- 2) Subir documento de prueba ----
    upload_url = f'{BASE_URL}/doc-processor/upload/'
    try:
        with open(FIXTURE_PATH, 'rb') as fh:
            r = session.post(
                upload_url,
                data={'contenido_title': 'Groq load test — Bases de Datos', 'csrfmiddlewaretoken': csrf_token},
                files={'documento': ('groq_test_content.txt', fh, 'text/plain')},
                headers={'X-CSRFToken': csrf_token, 'Referer': f'{BASE_URL}/doc-processor/'},
                timeout=TIMEOUT,
            )
        r.raise_for_status()
        upload_data = r.json()
    except (requests.RequestException, ValueError) as e:
        fail('upload_failed', detail=str(e))

    if not upload_data.get('success'):
        fail('upload_rejected', detail=upload_data.get('error'))

    chapters = upload_data.get('chapters') or []
    if not chapters:
        fail('no_chapters_detected', upload_response=upload_data)

    # ---- 3) Iniciar generación en modo streaming ----
    gen_url = f'{BASE_URL}/doc-processor/generate-questions/'
    payload = {
        'chapter_indices': list(range(len(chapters))),
        'chapters': chapters,
        'doc_id': upload_data.get('doc_id'),
        'filename': upload_data.get('filename'),
        'stream_mode': True,
        'question_types': [],
        'total_questions': TARGET_QTY,
        'questions_per_block': 0,
        'contenido_id': upload_data.get('contenido_id'),
    }
    try:
        r = session.post(
            gen_url,
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': csrf_token,
                'Referer': f'{BASE_URL}/doc-processor/',
            },
            timeout=TIMEOUT,
        )
        try:
            job_data = r.json()
        except ValueError:
            job_data = None
        if r.status_code >= 400:
            fail(
                'generate_job_http_error',
                status_code=r.status_code,
                detail=(job_data or {}).get('error') if job_data else r.text[:500],
            )
    except requests.RequestException as e:
        fail('generate_job_request_failed', detail=str(e))

    if not job_data.get('success'):
        fail('generate_job_rejected', detail=job_data.get('error'))

    job_id = job_data.get('job_id')
    if not job_id:
        fail('no_job_id', response=job_data)

    # ---- 4) Leer el stream SSE hasta 'done' ----
    stream_url = f'{BASE_URL}/doc-processor/generate-questions/stream/{job_id}/'
    questions = []
    failed_chunks = []
    total_reported = None
    stream_error = None

    try:
        with session.get(stream_url, stream=True, timeout=STREAM_TIMEOUT) as resp:
            resp.raise_for_status()
            buffer = ''
            for raw_line in resp.iter_lines(decode_unicode=True):
                if raw_line is None:
                    continue
                if raw_line == '':
                    continue
                if not raw_line.startswith('data:'):
                    continue
                buffer = raw_line[len('data:'):].strip()
                try:
                    event = json.loads(buffer)
                except json.JSONDecodeError:
                    continue

                evt_type = event.get('type')
                if evt_type == 'questions':
                    questions.extend(event.get('questions') or [])
                elif evt_type == 'chunk_failed':
                    failed_chunks.append(event)
                elif evt_type == 'error':
                    stream_error = event.get('message') or 'error desconocido'
                    break
                elif evt_type == 'done':
                    total_reported = event.get('total')
                    break
    except requests.RequestException as e:
        fail('stream_request_failed', detail=str(e), questions_collected_so_far=len(questions))

    elapsed = round(time.time() - t0, 1)

    if stream_error:
        fail('stream_reported_error', detail=stream_error, questions_collected=len(questions), elapsed_seconds=elapsed)

    # ---- 5) Chequeos de calidad ----
    total_generated = len(questions)
    texts = [q.get('pregunta', '').strip() for q in questions]
    empty_count = sum(1 for t in texts if not t)
    duplicate_count = len(texts) - len(set(t for t in texts if t))

    # ---- 6) Cupo restante ----
    quota = None
    try:
        r = session.get(f'{BASE_URL}/configuracion-ia/status/', timeout=TIMEOUT)
        r.raise_for_status()
        status_data = r.json()
        quota = {
            'using_shared_fallback': status_data.get('using_shared_fallback'),
            'backend': status_data.get('backend'),
            'demo_quota': status_data.get('demo_quota'),
        }
    except (requests.RequestException, ValueError) as e:
        quota = {'error': str(e)}

    result = {
        'timestamp': now_iso(),
        'success': True,
        'elapsed_seconds': elapsed,
        'target_questions': TARGET_QTY,
        'total_generated': total_generated,
        'total_reported_by_server': total_reported,
        'met_target': total_generated >= TARGET_QTY,
        'empty_questions': empty_count,
        'duplicate_questions': duplicate_count,
        'failed_chunks': len(failed_chunks),
        'quota': quota,
    }
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result['met_target'] and empty_count == 0 else 2)


if __name__ == '__main__':
    main()

"""
Vistas para Document Processing en EducaApp
============================================
Endpoints para procesar documentos, contar tokens y preparar contenido para IA.
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import os
import uuid
import shutil
import tempfile
import threading
import time
import logging
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# In-memory job store for SSE streaming jobs (job_id → params)
_jobs = {}
_jobs_lock = threading.Lock()

from material.ia_processor import (
    extract_text_advanced,
    count_tokens,
    count_tokens_file,
    split_text_by_tokens,
    optimize_text_for_ai
)
from material.local_ai_client import local_ai

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def upload_and_process_document(request):
    """
    Vista para subir y procesar un documento (PDF, DOCX, PPTX).
    Retorna estructura completa con capítulos, tokens, metadata.
    También guarda el archivo como Contenido en la base de datos.
    
    POST params:
        - documento: archivo subido
        - contenido_title: título para Mis Contenidos (opcional)
        - remove_headers: bool (opcional, default True)
        - remove_footers: bool (opcional, default True)
    
    Returns:
        JSON con estructura procesada del documento
    """
    from material.models import Contenido

    if 'documento' not in request.FILES:
        return JsonResponse({
            'success': False,
            'error': 'No se envió ningún archivo'
        }, status=400)
    
    archivo = request.FILES['documento']
    remove_headers = request.POST.get('remove_headers', 'true').lower() == 'true'
    remove_footers = request.POST.get('remove_footers', 'true').lower() == 'true'
    contenido_title = request.POST.get('contenido_title', '').strip()
    
    # Validar extensión
    nombre = archivo.name
    ext = os.path.splitext(nombre)[1].lower()
    if ext not in ['.pdf', '.docx', '.pptx', '.txt']:
        return JsonResponse({
            'success': False,
            'error': f'Formato no soportado: {ext}'
        }, status=400)

    if not contenido_title:
        contenido_title = os.path.splitext(nombre)[0].replace('_', ' ').replace('-', ' ')

    try:
        # Guardar el archivo definitivamente en contenidos/ (también sirve para sesión)
        saved_relative = default_storage.save(f'contenidos/{nombre}', ContentFile(archivo.read()))
        file_path = os.path.join(settings.MEDIA_ROOT, saved_relative)

        # Procesar con DocumentProcessor
        result = extract_text_advanced(
            file_path,
            remove_headers=remove_headers,
            remove_footers=remove_footers
        )

        # Crear entrada en Contenido (Mis Contenidos)
        contenido = Contenido(
            title=contenido_title,
            uploaded_by=request.user,
        )
        contenido.file = saved_relative
        contenido.save()
        contenido_id = contenido.id

        # --- Actualizar sesión ---
        # Eliminar archivo previo de session temporal si era una sesión de doc_sessions
        prev_session = request.session.get('doc_processor', {})
        prev_path = prev_session.get('file_path', '')
        sessions_dir = os.path.join(settings.MEDIA_ROOT, 'doc_sessions')
        if prev_path and prev_path.startswith(str(sessions_dir)) and os.path.exists(prev_path):
            try:
                os.unlink(prev_path)
            except OSError:
                pass

        doc_id = str(uuid.uuid4())
        request.session['doc_processor'] = {
            'doc_id': doc_id,
            'file_path': file_path,
            'filename': nombre,
            'remove_headers': remove_headers,
            'remove_footers': remove_footers,
        }
        request.session.modified = True
        # ---------------------------------------------------
        
        # Formatear respuesta (content_preview solo para mostrar en UI)
        response_data = {
            'success': True,
            'doc_id': doc_id,
            'filename': nombre,
            'contenido_id': contenido_id,
            'metadata': result.get('metadata', {}),
            'stats': result.get('stats', {}),
            'chapters': [
                {
                    'title': ch.get('title', ''),
                    'tokens': ch.get('tokens', 0),
                    'content_preview': ch.get('content', '')[:6000],
                    'pages': ch.get('pages', [])
                }
                for ch in result.get('chapters', [])
            ],
            'toc': result.get('toc', [])
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        # Limpiar en caso de error
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except OSError:
                pass
        
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def count_document_tokens(request):
    """
    Vista rápida para solo contar tokens de un documento.
    Útil para estimar costos antes de procesar.
    
    POST params:
        - documento: archivo subido
    
    Returns:
        JSON con total de tokens
    """
    if 'documento' not in request.FILES:
        return JsonResponse({
            'success': False,
            'error': 'No se envió ningún archivo'
        }, status=400)
    
    archivo = request.FILES['documento']
    ext = os.path.splitext(archivo.name)[1].lower()
    
    if ext not in ['.pdf', '.docx', '.pptx', '.txt']:
        return JsonResponse({
            'success': False,
            'error': f'Formato no soportado: {ext}'
        }, status=400)
    
    try:
        # Guardar temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
            for chunk in archivo.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name
        
        # Contar tokens
        total_tokens = count_tokens_file(tmp_path)
        
        # Limpiar
        os.unlink(tmp_path)
        
        # Calcular costo estimado (GPT-4 pricing ejemplo)
        COST_PER_1K_TOKENS = 0.03  # USD (ajustar según modelo)
        estimated_cost = (total_tokens / 1000) * COST_PER_1K_TOKENS
        
        return JsonResponse({
            'success': True,
            'filename': archivo.name,
            'total_tokens': total_tokens,
            'estimated_cost_usd': round(estimated_cost, 4),
            'model_reference': 'GPT-4 (input tokens)'
        })
        
    except Exception as e:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def split_text_chunks(request):
    """
    Divide un texto en chunks según límite de tokens.
    
    POST params:
        - text: texto a dividir
        - max_tokens: límite por chunk (default: 4000)
    
    Returns:
        JSON con chunks
    """
    text = request.POST.get('text', '')
    max_tokens = int(request.POST.get('max_tokens', 4000))
    
    if not text:
        return JsonResponse({
            'success': False,
            'error': 'No se proporcionó texto'
        }, status=400)
    
    try:
        chunks = split_text_by_tokens(text, max_tokens=max_tokens)
        
        return JsonResponse({
            'success': True,
            'total_chunks': len(chunks),
            'max_tokens_per_chunk': max_tokens,
            'chunks': [
                {
                    'chunk_number': i + 1,
                    'tokens': count_tokens(chunk),
                    'preview': chunk[:100] + '...' if len(chunk) > 100 else chunk
                }
                for i, chunk in enumerate(chunks)
            ]
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def document_processor_dashboard(request):
    """
    Vista HTML para el dashboard de procesamiento de documentos.
    """
    from material.models import Subject
    # Verificar estado del servidor local de IA
    local_ai_status = local_ai.get_status()
    
    context = {
        'page_title': 'Procesador de Documentos',
        'supported_formats': ['.pdf', '.docx', '.pptx', '.txt'],
        'max_file_size_mb': 10,
        'local_ai_connected': local_ai_status['connected'],
        'local_ai_url': local_ai_status['url'],
        'selected_model': local_ai_status.get('selected_model', 'llama3.1:8b'),
        'default_model': local_ai_status.get('default_model', 'llama3.1:8b'),
        'subjects': Subject.objects.all().order_by('name'),
        'preselected_contenido_id': request.GET.get('contenido_id', ''),
    }
    
    return render(request, 'material/document_processor_dashboard.html', context)


@login_required
def process_contenido_by_id(request, contenido_id):
    """
    Procesa un Contenido ya guardado en el servidor y devuelve el mismo
    formato JSON que upload_and_process_document, para preseleccionarlo
    en el dashboard del doc-processor.
    """
    from material.models import Contenido
    from django.http import JsonResponse

    contenido = get_object_or_404(Contenido, id=contenido_id, uploaded_by=request.user)

    file_path = contenido.file.path
    ext = os.path.splitext(file_path)[1].lower()

    if ext not in ['.pdf', '.docx', '.pptx', '.txt']:
        return JsonResponse({'success': False, 'error': f'Formato no soportado: {ext}'}, status=400)

    try:
        result = extract_text_advanced(file_path, remove_headers=True, remove_footers=True)

        # Limpiar sesion previa
        prev_session = request.session.get('doc_processor', {})
        prev_path = prev_session.get('file_path')
        if prev_path and os.path.exists(prev_path) and not prev_path.startswith(str(settings.MEDIA_ROOT).rstrip('/') + '/contenidos'):
            try:
                os.unlink(prev_path)
            except OSError:
                pass

        doc_id = str(uuid.uuid4())
        request.session['doc_processor'] = {
            'doc_id': doc_id,
            'file_path': file_path,
            'filename': contenido.file.name.split('/')[-1],
            'remove_headers': True,
            'remove_footers': True,
        }
        request.session.modified = True

        nombre = contenido.file.name.split('/')[-1]
        return JsonResponse({
            'success': True,
            'doc_id': doc_id,
            'filename': nombre,
            'metadata': result.get('metadata', {}),
            'stats': result.get('stats', {}),
            'chapters': [
                {
                    'title': ch.get('title', ''),
                    'tokens': ch.get('tokens', 0),
                    'content_preview': ch.get('content', '')[:6000],
                    'pages': ch.get('pages', [])
                }
                for ch in result.get('chapters', [])
            ],
            'toc': result.get('toc', [])
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================
# Vistas para Servidor Local de IA
# ============================================

@login_required
@require_http_methods(["GET"])
def check_local_ai_status(request):
    """
    Verifica el estado de conexión al servidor local de IA.
    
    Returns:
        JSON con estado de conexión y modelos disponibles
    """
    try:
        status = local_ai.get_status()
        return JsonResponse({
            'success': True,
            **status
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'connected': False
        }, status=500)


@login_required
@require_http_methods(["GET"])
def list_local_ai_models(request):
    """
    Lista todos los modelos disponibles en el servidor local.
    
    Returns:
        JSON con lista de modelos
    """
    try:
        models = local_ai.get_models()
        current_model = local_ai.get_current_model()
        
        return JsonResponse({
            'success': True,
            'connected': local_ai.is_available(),
            'models': models,
            'count': len(models),
            'selected_model': current_model,
            'default_model': local_ai.default_model
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'models': []
        }, status=500)


@login_required
@require_http_methods(["POST"])
def set_local_ai_model(request):
    """
    Cambia el modelo activo del servidor local.
    
    POST params:
        - model: nombre del modelo a activar
    
    Returns:
        JSON con resultado de la operación
    """
    try:
        model_name = request.POST.get('model')
        
        if not model_name:
            return JsonResponse({
                'success': False,
                'error': 'Nombre de modelo no proporcionado'
            }, status=400)
        
        # Intentar cambiar el modelo
        success = local_ai.set_model(model_name)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': f'Modelo cambiado a {model_name}',
                'selected_model': model_name
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Modelo no disponible o servidor no conectado'
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def generate_questions_from_chapters(request):
    """
    Genera preguntas automáticamente usando IA desde capítulos seleccionados.

    Lee el documento completo persistido en sesión y aplica chunking para
    procesar capítulos de cualquier longitud sin truncar el contenido.

    POST JSON:
        - chapter_indices: lista de índices de capítulos (preferido)
        - chapters: lista de capítulos con título (fallback si no hay sesión)
        - filename: nombre del archivo fuente
        - doc_id: ID de documento (opcional, para validación)

    Returns:
        JSON con preguntas generadas
    """
    import json as json_module

    try:
        data = json_module.loads(request.body)
        chapter_indices = data.get('chapter_indices', [])
        chapters_from_request = data.get('chapters', [])
        filename = data.get('filename', 'Documento')
        stream_mode = data.get('stream_mode', False)

        if not chapter_indices and not chapters_from_request:
            return JsonResponse({
                'success': False,
                'error': 'No se proporcionaron capítulos'
            }, status=400)

        # Verificar servidor IA
        if not local_ai.check_connection():
            return JsonResponse({
                'success': False,
                'error': 'Servidor local de IA no disponible. Verifica la conexión VPN (192.168.12.236:11434).'
            }, status=503)

        # question_types enviados por el cliente (lista de strings)
        question_types = data.get('question_types') or []

        # Modo streaming: guardar job y retornar job_id al cliente
        if stream_mode:
            job_id = _store_streaming_job(request, chapter_indices, chapters_from_request, filename, question_types)
            return JsonResponse({
                'success': True,
                'job_id': job_id,
                'stream': True,
            })

        # --------------------------------------------------------
        # Obtener contenido completo desde el archivo en sesión
        # --------------------------------------------------------
        doc_session = request.session.get('doc_processor', {})
        session_file = doc_session.get('file_path')
        chapters_to_process = []

        if session_file and os.path.exists(session_file):
            # Re-procesar el archivo original para obtener contenido completo
            try:
                full_result = extract_text_advanced(
                    session_file,
                    remove_headers=doc_session.get('remove_headers', True),
                    remove_footers=doc_session.get('remove_footers', True)
                )
                all_session_chapters = full_result.get('chapters', [])

                if chapter_indices:
                    chapters_to_process = [
                        all_session_chapters[i]
                        for i in chapter_indices
                        if i < len(all_session_chapters)
                    ]
                else:
                    # Hacer match por título con los capítulos del request
                    request_titles = {ch.get('title', '') for ch in chapters_from_request}
                    chapters_to_process = [
                        ch for ch in all_session_chapters
                        if ch.get('title', '') in request_titles
                    ]
            except Exception as e:
                logger.warning(f"No se pudo re-procesar el archivo de sesión: {e}")
                # Caer en modo fallback

        # Fallback: usar el contenido preview que vino en el request
        if not chapters_to_process:
            logger.info("Usando contenido del request como fallback (sin sesión de archivo)")
            chapters_to_process = chapters_from_request

        if not chapters_to_process:
            return JsonResponse({
                'success': False,
                'error': 'No se pudo obtener el contenido de los capítulos'
            }, status=400)

        # --------------------------------------------------------
        # Generar preguntas por capítulo usando chunking
        # --------------------------------------------------------
        all_questions = []
        chapter_info = []

        for chapter in chapters_to_process:
            title = chapter.get('title', 'Capítulo')
            content = chapter.get('content', chapter.get('content_preview', ''))
            chapter_info.append({'title': title, 'pages': chapter.get('pages', [])})

            logger.info(f"Procesando capítulo '{title}' ({len(content)} caracteres)")

            # Dividir en chunks de ≤ 3000 tokens
            chunks = _split_into_chunks(content, max_tokens=3000)
            logger.info(f"  → {len(chunks)} chunk(s)")

            # Preguntas por chunk: entre 4 y 8, proporcional a número de chunks
            questions_per_chunk = max(4, min(8, 20 // max(len(chunks), 1)))

            for chunk_idx, chunk in enumerate(chunks):
                chunk_questions = _generate_questions_for_chunk(
                    chunk, title, questions_per_chunk, chunk_idx, len(chunks),
                    question_types=question_types
                )
                all_questions.extend(chunk_questions)
                logger.info(f"  chunk {chunk_idx + 1}/{len(chunks)}: {len(chunk_questions)} preguntas")

        # Deduplicar y agregar metadata
        all_questions = _deduplicate_questions(all_questions)
        for q in all_questions:
            q['source_chapters'] = chapter_info
            q['source_file'] = filename

        logger.info(f"Total preguntas generadas (dedup): {len(all_questions)}")

        return JsonResponse({
            'success': True,
            'questions': all_questions,
            'count': len(all_questions),
        })

    except Exception as e:
        logger.exception("Error en generate_questions_from_chapters")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def _store_streaming_job(request, chapter_indices, chapters_from_request, filename, question_types=None):
    """Guarda los parámetros del job en memoria y retorna el job_id."""
    job_id = str(uuid.uuid4())
    with _jobs_lock:
        # Limpiar jobs viejos (> 10 min) para no acumular basura
        now = time.time()
        stale = [jid for jid, j in _jobs.items() if now - j.get('created_at', 0) > 600]
        for jid in stale:
            _jobs.pop(jid, None)

        _jobs[job_id] = {
            'chapter_indices': chapter_indices,
            'chapters_from_request': chapters_from_request,
            'filename': filename,
            'question_types': question_types or [],
            'doc_session': dict(request.session.get('doc_processor', {})),
            'user_id': request.user.id,
            'created_at': now,
        }
    return job_id


# ============================================
# Helpers para generación por chunks
# ============================================

def _split_into_chunks(content, max_tokens=3000):
    """Divide el contenido en fragmentos de ≤ max_tokens tokens."""
    total_tokens = count_tokens(content)
    if total_tokens <= max_tokens:
        return [content]

    # Dividir por párrafos y agrupar hasta el límite
    paragraphs = content.split('\n\n')
    chunks = []
    current_parts = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = count_tokens(para)
        # Si un párrafo solo ya supera el límite, cortarlo por líneas
        if para_tokens > max_tokens:
            if current_parts:
                chunks.append('\n\n'.join(current_parts))
                current_parts = []
                current_tokens = 0
            lines = para.split('\n')
            for line in lines:
                line_tokens = count_tokens(line)
                if current_tokens + line_tokens > max_tokens and current_parts:
                    chunks.append('\n'.join(current_parts))
                    current_parts = [line]
                    current_tokens = line_tokens
                else:
                    current_parts.append(line)
                    current_tokens += line_tokens
        elif current_tokens + para_tokens > max_tokens and current_parts:
            chunks.append('\n\n'.join(current_parts))
            current_parts = [para]
            current_tokens = para_tokens
        else:
            current_parts.append(para)
            current_tokens += para_tokens

    if current_parts:
        chunks.append('\n\n'.join(current_parts))

    return chunks if chunks else [content]


def _generate_questions_for_chunk(content, chapter_title, num_questions, chunk_idx, total_chunks, question_types=None):
    """Genera preguntas para un fragmento de capítulo usando la IA local.

    Args:
        content: Texto del fragmento a procesar.
        chapter_title: Título del capítulo.
        num_questions: Número total de preguntas a generar.
        chunk_idx: Índice del fragmento actual (0-based).
        total_chunks: Total de fragmentos del capítulo.
        question_types: Lista de tipos habilitados, e.g. ['opcion_multiple', 'verdadero_falso'].
                        Si es None o vacío, usa todos los tipos.
    """
    import json as json_module

    # Tipos disponibles y sus descripciones para el prompt
    ALL_TYPES = {
        'opcion_multiple': 'Opción múltiple (4 opciones A/B/C/D, una correcta)',
        'verdadero_falso': 'Verdadero/Falso (afirmación clara)',
        'completar_blank': 'Completar el espacio (usa [___] en la pregunta para el espacio en blanco)',
        'desarrollo': 'Desarrollo (pregunta abierta con respuesta de referencia para el docente)',
    }

    if not question_types:
        question_types = list(ALL_TYPES.keys())

    enabled_descriptions = '\n'.join(
        f'  - "{t}": {ALL_TYPES[t]}'
        for t in question_types
        if t in ALL_TYPES
    )

    context_note = f"(parte {chunk_idx + 1} de {total_chunks})" if total_chunks > 1 else ""

    # Niveles de Bloom para el prompt
    bloom_desc = (
        "bloom_nivel: nivel cognitivo de Bloom (1=Recordar, 2=Comprender, 3=Aplicar, "
        "4=Analizar, 5=Evaluar, 6=Crear)"
    )

    prompt = f"""Analizá el siguiente texto educativo del capítulo "{chapter_title}" {context_note} y generá exactamente {num_questions} preguntas variadas.

TEXTO:
{content}

TIPOS DE PREGUNTAS HABILITADOS:
{enabled_descriptions}

REGLAS:
- Generá exactamente {num_questions} preguntas basándote ÚNICAMENTE en el texto anterior.
- Distribuí los tipos de manera relativamente pareja entre los tipos habilitados.
- Variá la dificultad: dificultad 1-2 (fácil), 3 (media), 4-5 (difícil).
- Para "opcion_multiple": siempre 4 opciones con prefijo A), B), C), D).
- Para "completar_blank": escribí la pregunta con [___] donde va la respuesta.
- Para "verdadero_falso": la respuesta debe ser exactamente "Verdadero" o "Falso".
- Para "desarrollo": la respuesta es la respuesta de referencia del docente (no del alumno).
- No incluyas referencias a páginas, títulos de sección ni numeración.
- Respondé SOLO con JSON válido, sin bloques de código markdown.

Formato JSON requerido:
{{
  "preguntas": [
    {{
      "pregunta": "texto de la pregunta",
      "tipo": "opcion_multiple",
      "opciones": ["A) opción 1", "B) opción 2", "C) opción 3", "D) opción 4"],
      "respuesta_correcta_index": 0,
      "respuesta": "A) texto de la opción correcta",
      "explicacion": "breve explicación de por qué es correcta",
      "dificultad": 2,
      "bloom_nivel": 1
    }},
    {{
      "pregunta": "Afirmación concreta. ¿Verdadero o Falso?",
      "tipo": "verdadero_falso",
      "respuesta": "Verdadero",
      "explicacion": "...",
      "dificultad": 1,
      "bloom_nivel": 1
    }},
    {{
      "pregunta": "El proceso por el cual las plantas obtienen energía se llama [___].",
      "tipo": "completar_blank",
      "respuesta": "fotosíntesis",
      "explicacion": "...",
      "dificultad": 2,
      "bloom_nivel": 1
    }},
    {{
      "pregunta": "Explicá cómo ocurre el proceso X.",
      "tipo": "desarrollo",
      "respuesta": "Respuesta de referencia: El proceso X ocurre cuando...",
      "explicacion": "Evalúa comprensión profunda del proceso.",
      "dificultad": 4,
      "bloom_nivel": 3
    }}
  ]
}}

Nota sobre bloom_nivel: {bloom_desc}"""

    result = local_ai.generate(prompt=prompt, temperature=0.4, max_tokens=4000)

    if not result['success']:
        logger.warning(f"IA falló para chunk {chunk_idx + 1}: {result.get('error', '')}")
        return []

    try:
        ai_response = result['text'].strip()
        # Eliminar bloques de código markdown si existen
        if ai_response.startswith('```'):
            lines = ai_response.split('\n')
            ai_response = '\n'.join(line for line in lines if not line.startswith('```'))
        # Intentar extraer el JSON si viene con texto alrededor
        start = ai_response.find('{')
        end = ai_response.rfind('}')
        if start != -1 and end != -1 and end > start:
            ai_response = ai_response[start:end + 1]
        questions_data = json_module.loads(ai_response)
        questions = questions_data.get('preguntas', [])
        # Filtrar solo los tipos habilitados (la IA puede equivocarse)
        questions = [q for q in questions if q.get('tipo', 'opcion_multiple') in question_types]
        return questions
    except Exception as e:
        logger.warning(f"No se pudo parsear JSON del chunk {chunk_idx + 1}: {e}")
        return []


def _deduplicate_questions(questions):
    """Elimina preguntas duplicadas comparando los primeros 80 caracteres (case-insensitive)."""
    seen = set()
    unique = []
    for q in questions:
        key = q.get('pregunta', '').lower().strip()[:80]
        if key and key not in seen:
            seen.add(key)
            unique.append(q)
    return unique


@login_required
@require_http_methods(["GET"])
def stream_questions(request, job_id):
    """
    SSE endpoint: transmite preguntas a medida que se generan por chunks.
    El cliente abre un EventSource hacia esta URL tras recibir job_id del
    endpoint POST /generate-questions/ con stream_mode=true.
    """
    import json as json_module

    def event_stream(job, user_id):
        # Verificar usuario antes de procesar
        if job.get('user_id') != user_id:
            yield f'data: {json_module.dumps({"type": "error", "message": "No autorizado"})}\n\n'
            return

        chapter_indices = job['chapter_indices']
        chapters_from_request = job['chapters_from_request']
        filename = job['filename']
        doc_session = job['doc_session']
        question_types = job.get('question_types') or []

        # Obtener contenido completo (misma lógica que generate_questions_from_chapters)
        chapters_to_process = []
        session_file = doc_session.get('file_path')
        if session_file and os.path.exists(session_file):
            try:
                full_result = extract_text_advanced(
                    session_file,
                    remove_headers=doc_session.get('remove_headers', True),
                    remove_footers=doc_session.get('remove_footers', True)
                )
                all_session_chapters = full_result.get('chapters', [])
                if chapter_indices:
                    chapters_to_process = [
                        all_session_chapters[i]
                        for i in chapter_indices
                        if i < len(all_session_chapters)
                    ]
                else:
                    req_titles = {ch.get('title', '') for ch in chapters_from_request}
                    chapters_to_process = [
                        ch for ch in all_session_chapters
                        if ch.get('title', '') in req_titles
                    ]
            except Exception as exc:
                logger.warning(f"SSE: no se pudo re-procesar sesion: {exc}")

        if not chapters_to_process:
            chapters_to_process = chapters_from_request

        if not chapters_to_process:
            yield f'data: {json_module.dumps({"type": "error", "message": "No se pudo obtener el contenido de los capítulos"})}\n\n'
            return

        # Pre-calcular total de chunks para progress
        chapter_splits = []
        total_chunks_all = 0
        for chapter in chapters_to_process:
            content = chapter.get('content', chapter.get('content_preview', ''))
            chunks = _split_into_chunks(content, max_tokens=3000)
            chapter_splits.append(chunks)
            total_chunks_all += len(chunks)

        yield f'data: {json_module.dumps({"type": "start", "total_chunks": total_chunks_all, "filename": filename})}\n\n'

        seen_keys = set()
        total_generated = 0
        chunk_idx_global = 0

        for chapter, chunks in zip(chapters_to_process, chapter_splits):
            title = chapter.get('title', 'Capítulo')
            pages = chapter.get('pages', [])
            questions_per_chunk = max(4, min(8, 20 // max(len(chunks), 1)))

            for i, chunk in enumerate(chunks):
                chunk_idx_global += 1
                try:
                    raw_questions = _generate_questions_for_chunk(
                        chunk, title, questions_per_chunk, i, len(chunks),
                        question_types=question_types
                    )
                    new_qs = []
                    for q in raw_questions:
                        key = q.get('pregunta', '').lower().strip()[:80]
                        if key and key not in seen_keys:
                            seen_keys.add(key)
                            q['source_chapters'] = [{'title': title, 'pages': pages}]
                            q['source_file'] = filename
                            new_qs.append(q)

                    total_generated += len(new_qs)
                    event = {
                        'type': 'questions',
                        'questions': new_qs,
                        'chunk': chunk_idx_global,
                        'total_chunks': total_chunks_all,
                        'chapter_title': title,
                    }
                    yield f'data: {json_module.dumps(event)}\n\n'

                except GeneratorExit:
                    return
                except Exception as exc:
                    logger.warning(f"SSE chunk {chunk_idx_global} error: {exc}")
                    yield f'data: {json_module.dumps({"type": "chunk_error", "chunk": chunk_idx_global, "message": str(exc)})}\n\n'

        yield f'data: {json_module.dumps({"type": "done", "total": total_generated})}\n\n'

    with _jobs_lock:
        job = _jobs.pop(job_id, None)

    if not job:
        def _not_found():
            import json as j
            yield f'data: {j.dumps({"type": "error", "message": "Job no encontrado o expirado"})}\n\n'
        response = StreamingHttpResponse(_not_found(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        return response

    response = StreamingHttpResponse(
        event_stream(job, request.user.id),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@login_required
@require_http_methods(["GET"])
def document_page_preview(request):
    """
    Devuelve metadata del documento en sesión para el visor de páginas:
    - Para PDF: número total de páginas y URL para servirlo en PDF.js
    - Para DOCX: bloques de texto por sección (para docx-preview + checkboxes)
    - Para PPTX: texto de cada slide (tarjeta por slide con checkbox)

    GET params: ninguno (usa la sesión doc_processor)

    Returns JSON:
        {
          "success": true,
          "file_type": "pdf"|"docx"|"pptx"|"txt",
          "filename": "...",
          "total_pages": N,          # PDF
          "file_url": "/media/...",  # PDF — para PDF.js
          "slides": [...],           # PPTX
          "sections": [...],         # DOCX/TXT
        }
    """
    doc_session = request.session.get('doc_processor', {})
    file_path = doc_session.get('file_path', '')
    filename = doc_session.get('filename', '')

    if not file_path or not os.path.exists(file_path):
        return JsonResponse({'success': False, 'error': 'No hay documento en sesión. Sube o selecciona uno primero.'}, status=400)

    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == '.pdf':
            doc = fitz.open(file_path)
            total_pages = doc.page_count
            doc.close()
            # Construir URL relativa a MEDIA_ROOT
            rel = os.path.relpath(file_path, settings.MEDIA_ROOT).replace('\\', '/')
            from django.conf import settings as _s
            file_url = _s.MEDIA_URL + rel
            return JsonResponse({
                'success': True,
                'file_type': 'pdf',
                'filename': filename,
                'total_pages': total_pages,
                'file_url': file_url,
            })

        elif ext == '.pptx':
            from pptx import Presentation as _Prs
            prs = _Prs(file_path)
            slides = []
            for i, slide in enumerate(prs.slides, 1):
                texts = []
                for shape in slide.shapes:
                    if hasattr(shape, 'text') and shape.text.strip():
                        texts.append(shape.text.strip())
                slides.append({
                    'slide_number': i,
                    'text': '\n'.join(texts) or f'(Slide {i} sin texto)',
                    'char_count': sum(len(t) for t in texts),
                })
            return JsonResponse({
                'success': True,
                'file_type': 'pptx',
                'filename': filename,
                'total_pages': len(slides),
                'slides': slides,
            })

        elif ext == '.docx':
            from docx import Document as _Doc
            doc = _Doc(file_path)
            # Agrupar párrafos en "secciones" de ~800 chars para que sean manejables
            sections = []
            current_text = []
            current_chars = 0
            section_idx = 1
            heading_title = 'Inicio'

            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                # Detectar headings como separadores de sección
                if para.style.name.startswith('Heading'):
                    if current_text:
                        sections.append({
                            'section_number': section_idx,
                            'title': heading_title,
                            'text': '\n'.join(current_text),
                            'char_count': current_chars,
                        })
                        section_idx += 1
                        current_text = []
                        current_chars = 0
                    heading_title = text
                else:
                    current_text.append(text)
                    current_chars += len(text)
                    # También dividir si el bloque es muy largo
                    if current_chars > 1200:
                        sections.append({
                            'section_number': section_idx,
                            'title': heading_title,
                            'text': '\n'.join(current_text),
                            'char_count': current_chars,
                        })
                        section_idx += 1
                        current_text = []
                        current_chars = 0
            if current_text:
                sections.append({
                    'section_number': section_idx,
                    'title': heading_title,
                    'text': '\n'.join(current_text),
                    'char_count': current_chars,
                })
            # URL del archivo para docx-preview.js
            rel = os.path.relpath(file_path, settings.MEDIA_ROOT).replace('\\', '/')
            from django.conf import settings as _s
            file_url = _s.MEDIA_URL + rel
            return JsonResponse({
                'success': True,
                'file_type': 'docx',
                'filename': filename,
                'total_pages': len(sections),
                'file_url': file_url,
                'sections': sections,
            })

        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            # Dividir en bloques de ~50 líneas
            block_size = 50
            sections = []
            for i in range(0, len(lines), block_size):
                block = ''.join(lines[i:i + block_size]).strip()
                sections.append({
                    'section_number': i // block_size + 1,
                    'title': f'Líneas {i+1}–{min(i+block_size, len(lines))}',
                    'text': block,
                    'char_count': len(block),
                })
            return JsonResponse({
                'success': True,
                'file_type': 'txt',
                'filename': filename,
                'total_pages': len(sections),
                'sections': sections,
            })

        else:
            return JsonResponse({'success': False, 'error': f'Formato no soportado para preview: {ext}'}, status=400)

    except Exception as e:
        logger.exception("Error en document_page_preview")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def get_pages_text(request):
    """
    Dado un conjunto de números de página/slide/sección seleccionados por el usuario,
    extrae el texto de esas unidades del documento en sesión.
    Devuelve el mismo formato de "chapters" que usa generate_questions_from_chapters.

    POST JSON:
        {
          "pages": [1, 3, 5],        # para PDF: números de página (1-based)
          "slides": [2, 4],          # para PPTX: números de slide (1-based)
          "sections": [1, 2],        # para DOCX/TXT: números de sección (1-based)
        }
    Returns JSON:
        {
          "success": true,
          "chapters": [{"title": "...", "content": "...", "tokens": N, "pages": [...]}]
        }
    """
    import json as json_module
    try:
        data = json_module.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)

    doc_session = request.session.get('doc_processor', {})
    file_path = doc_session.get('file_path', '')
    filename = doc_session.get('filename', '')

    if not file_path or not os.path.exists(file_path):
        return JsonResponse({'success': False, 'error': 'No hay documento en sesión.'}, status=400)

    ext = os.path.splitext(file_path)[1].lower()

    try:
        chapters = []

        if ext == '.pdf':
            selected_pages = [int(p) for p in data.get('pages', [])]
            if not selected_pages:
                return JsonResponse({'success': False, 'error': 'No se enviaron páginas.'}, status=400)
            doc = fitz.open(file_path)
            for page_num in sorted(selected_pages):
                if 1 <= page_num <= doc.page_count:
                    page = doc[page_num - 1]
                    text = page.get_text().strip()
                    if text:
                        chapters.append({
                            'title': f'Página {page_num}',
                            'content': text,
                            'tokens': count_tokens(text),
                            'pages': [page_num],
                        })
            doc.close()

        elif ext == '.pptx':
            from pptx import Presentation as _Prs
            selected = set(int(s) for s in data.get('slides', []))
            if not selected:
                return JsonResponse({'success': False, 'error': 'No se enviaron slides.'}, status=400)
            prs = _Prs(file_path)
            for i, slide in enumerate(prs.slides, 1):
                if i in selected:
                    texts = []
                    for shape in slide.shapes:
                        if hasattr(shape, 'text') and shape.text.strip():
                            texts.append(shape.text.strip())
                    text = '\n'.join(texts)
                    if text:
                        chapters.append({
                            'title': f'Slide {i}',
                            'content': text,
                            'tokens': count_tokens(text),
                            'pages': [i],
                        })

        elif ext in ('.docx', '.txt'):
            selected = set(int(s) for s in data.get('sections', []))
            if not selected:
                return JsonResponse({'success': False, 'error': 'No se enviaron secciones.'}, status=400)
            # Re-usar la misma lógica de document_page_preview para extraer secciones
            if ext == '.docx':
                from docx import Document as _Doc
                doc = _Doc(file_path)
                sections_all = []
                current_text = []
                current_chars = 0
                section_idx = 1
                heading_title = 'Inicio'
                for para in doc.paragraphs:
                    text = para.text.strip()
                    if not text:
                        continue
                    if para.style.name.startswith('Heading'):
                        if current_text:
                            sections_all.append((section_idx, heading_title, '\n'.join(current_text)))
                            section_idx += 1
                            current_text = []
                            current_chars = 0
                        heading_title = text
                    else:
                        current_text.append(text)
                        current_chars += len(text)
                        if current_chars > 1200:
                            sections_all.append((section_idx, heading_title, '\n'.join(current_text)))
                            section_idx += 1
                            current_text = []
                            current_chars = 0
                if current_text:
                    sections_all.append((section_idx, heading_title, '\n'.join(current_text)))
            else:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                block_size = 50
                sections_all = []
                for i in range(0, len(lines), block_size):
                    block = ''.join(lines[i:i + block_size]).strip()
                    idx = i // block_size + 1
                    sections_all.append((idx, f'Líneas {i+1}–{min(i+block_size, len(lines))}', block))

            for sec_num, title, text in sections_all:
                if sec_num in selected and text:
                    chapters.append({
                        'title': title,
                        'content': text,
                        'tokens': count_tokens(text),
                        'pages': [sec_num],
                    })

        if not chapters:
            return JsonResponse({'success': False, 'error': 'No se pudo extraer texto de las unidades seleccionadas.'}, status=400)

        return JsonResponse({
            'success': True,
            'filename': filename,
            'chapters': chapters,
            'total_tokens': sum(ch['tokens'] for ch in chapters),
        })

    except Exception as e:
        logger.exception("Error en get_pages_text")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def save_generated_questions(request):
    """
    Guarda preguntas generadas por IA en la base de datos.
    
    POST JSON:
        - approved: lista de preguntas aprobadas
        - rejected: lista de preguntas rechazadas
        - filename: nombre del archivo fuente
    
    Returns:
        JSON con resultado de la operación
    """
    import json as json_module
    from material.models import Question, Subject, Topic
    
    try:
        data = json_module.loads(request.body)
        approved = data.get('approved', [])
        rejected = data.get('rejected', [])
        filename = data.get('filename', 'Documento')
        subject_ids = data.get('subject_ids', [])
        
        saved_count = 0
        
        # Resolver materias seleccionadas por el usuario
        selected_subjects = list(Subject.objects.filter(id__in=subject_ids)) if subject_ids else []
        if not selected_subjects:
            # Fallback: primera materia disponible
            fallback = Subject.objects.first()
            if not fallback:
                return JsonResponse({
                    'success': False,
                    'error': 'No hay materias configuradas en el sistema'
                }, status=400)
            selected_subjects = [fallback]
        
        # Usar la primera materia seleccionada para anclar el tema
        default_subject = selected_subjects[0]
        
        # Obtener o crear tema por defecto
        default_topic = Topic.objects.filter(subject=default_subject).first()
        if not default_topic:
            default_topic = Topic.objects.create(
                name=f"Preguntas de {filename}",
                subject=default_subject
            )
        
        # Guardar preguntas aprobadas
        for q_data in approved:
            question = Question(
                topic=default_topic,
                question_type=q_data.get('tipo', 'opcion_multiple'),
                question_text=q_data.get('pregunta', ''),
                answer_text=q_data.get('respuesta', ''),
                difficulty=q_data.get('dificultad', 3),
                bloom_level=q_data.get('bloom_nivel') or None,
                user=request.user,
                generated_by_ai=True,
                ai_approved=True
            )
            
            # Guardar opciones si existen
            if 'opciones' in q_data:
                question.options = q_data['opciones']
            
            # Guardar información de capítulos fuente
            if 'source_chapters' in q_data:
                question.source_chapters = q_data['source_chapters']
            
            question.save()
            question.subjects.set(selected_subjects)
            saved_count += 1
        
        # Guardar preguntas rechazadas (para registro)
        for q_data in rejected:
            question = Question(
                topic=default_topic,
                question_type=q_data.get('tipo', 'opcion_multiple'),
                question_text=q_data.get('pregunta', ''),
                answer_text=q_data.get('respuesta', ''),
                difficulty=q_data.get('dificultad', 3),
                bloom_level=q_data.get('bloom_nivel') or None,
                user=request.user,
                generated_by_ai=True,
                ai_approved=False
            )
            
            if 'opciones' in q_data:
                question.options = q_data['opciones']
            
            if 'source_chapters' in q_data:
                question.source_chapters = q_data['source_chapters']
            
            question.save()
            question.subjects.set(selected_subjects)
        
        return JsonResponse({
            'success': True,
            'saved_count': saved_count,
            'approved_count': len(approved),
            'rejected_count': len(rejected),
            'total_count': len(approved) + len(rejected)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


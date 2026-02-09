"""
Vistas para Document Processing en EducaApp
============================================
Endpoints para procesar documentos, contar tokens y preparar contenido para IA.
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import tempfile
import logging

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
    
    POST params:
        - documento: archivo subido
        - remove_headers: bool (opcional, default True)
        - remove_footers: bool (opcional, default True)
    
    Returns:
        JSON con estructura procesada del documento
    """
    if 'documento' not in request.FILES:
        return JsonResponse({
            'success': False,
            'error': 'No se envió ningún archivo'
        }, status=400)
    
    archivo = request.FILES['documento']
    remove_headers = request.POST.get('remove_headers', 'true').lower() == 'true'
    remove_footers = request.POST.get('remove_footers', 'true').lower() == 'true'
    
    # Validar extensión
    nombre = archivo.name
    ext = os.path.splitext(nombre)[1].lower()
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
        
        # Procesar con DocumentProcessor
        result = extract_text_advanced(
            tmp_path,
            remove_headers=remove_headers,
            remove_footers=remove_footers
        )
        
        # Limpiar archivo temporal
        os.unlink(tmp_path)
        
        # Formatear respuesta
        response_data = {
            'success': True,
            'filename': nombre,
            'metadata': result.get('metadata', {}),
            'stats': result.get('stats', {}),
            'chapters': [
                {
                    'title': ch.get('title', ''),
                    'tokens': ch.get('tokens', 0),
                    'content_preview': ch.get('content', '')[:200] + '...' if len(ch.get('content', '')) > 200 else ch.get('content', ''),
                    'pages': ch.get('pages', [])
                }
                for ch in result.get('chapters', [])
            ],
            'toc': result.get('toc', [])
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        # Limpiar en caso de error
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        
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
    # Verificar estado del servidor local de IA
    local_ai_status = local_ai.get_status()
    
    context = {
        'page_title': 'Procesador de Documentos',
        'supported_formats': ['.pdf', '.docx', '.pptx', '.txt'],
        'max_file_size_mb': 10,
        'local_ai_connected': local_ai_status['connected'],
        'local_ai_url': local_ai_status['url'],
        'selected_model': local_ai_status.get('selected_model', 'llama3.1:8b'),
        'default_model': local_ai_status.get('default_model', 'llama3.1:8b')
    }
    
    return render(request, 'material/document_processor_dashboard.html', context)


@login_required
@require_http_methods(["POST"])
def optimize_text_view(request):
    """
    Optimiza texto para reducir tokens sin perder información.
    
    POST params:
        - text: texto a optimizar
        - remove_whitespace: bool (default: true)
    
    Returns:
        JSON con texto optimizado y stats
    """
    text = request.POST.get('text', '')
    remove_whitespace = request.POST.get('remove_whitespace', 'true').lower() == 'true'
    
    if not text:
        return JsonResponse({
            'success': False,
            'error': 'No se proporcionó texto'
        }, status=400)
    
    try:
        # Contar tokens antes
        tokens_before = count_tokens(text)
        
        # Optimizar
        optimized_text = optimize_text_for_ai(
            text,
            remove_extra_whitespace=remove_whitespace
        )
        
        # Contar tokens después
        tokens_after = count_tokens(optimized_text)
        
        # Calcular ahorro
        tokens_saved = tokens_before - tokens_after
        percentage_saved = (tokens_saved / tokens_before * 100) if tokens_before > 0 else 0
        
        return JsonResponse({
            'success': True,
            'original_tokens': tokens_before,
            'optimized_tokens': tokens_after,
            'tokens_saved': tokens_saved,
            'percentage_saved': round(percentage_saved, 2),
            'optimized_text': optimized_text
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


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
    
    POST JSON:
        - chapters: lista de capítulos con título y contenido
        - filename: nombre del archivo fuente
    
    Returns:
        JSON con preguntas generadas
    """
    import json as json_module
    
    try:
        data = json_module.loads(request.body)
        chapters = data.get('chapters', [])
        filename = data.get('filename', 'Documento')
        
        if not chapters:
            return JsonResponse({
                'success': False,
                'error': 'No se proporcionaron capítulos'
            }, status=400)
        
        # Verificar que el servidor local esté disponible
        # Forzar verificación en tiempo real (no cache)
        if not local_ai.check_connection():
            return JsonResponse({
                'success': False,
                'error': 'Servidor local de IA no disponible. Verifica que estés conectado a la VPN de la intranet (192.168.12.236:11434).'
            }, status=503)
        
        # Combinar contenido de todos los capítulos seleccionados
        combined_content = ""
        chapter_info = []
        
        for chapter in chapters:
            combined_content += f"\n\n=== {chapter.get('title', 'Capítulo')} ===\n"
            # Usar el preview si existe, sino buscar content
            content = chapter.get('content_preview', chapter.get('content', ''))
            combined_content += content
            chapter_info.append({
                'title': chapter.get('title'),
                'pages': chapter.get('pages', [])
            })
        
        # Construir prompt para generar preguntas
        prompt = f"""Analiza el siguiente texto educativo y genera exactamente 6 preguntas de opción múltiple variadas.

TEXTO:
{combined_content[:5000]}  

IMPORTANTE:
- Genera preguntas que cubran diferentes partes del texto
- Varía la dificultad (2 fáciles, 2 medias, 2 difíciles)
- No incluyas información de páginas, títulos de secciones ni numeración del libro
- Enfócate solo en el CONTENIDO educativo
- Responde SOLO con JSON válido, sin formato markdown ni explicaciones

Formato JSON requerido:
{{
  "preguntas": [
    {{
      "pregunta": "texto de la pregunta",
      "opciones": ["A) opción 1", "B) opción 2", "C) opción 3", "D) opción 4"],
      "respuesta_correcta_index": 0,
      "respuesta": "A) texto de la opción correcta",
      "explicacion": "por qué es correcta esta respuesta",
      "dificultad": 2,
      "tipo": "opcion_multiple"
    }}
  ]
}}"""
        
        # Generar con IA (con validación adicional)
        logger.info(f"Generando preguntas para {len(chapters)} capítulos")
        logger.info(f"Longitud del contenido combinado: {len(combined_content)} caracteres")
        
        result = local_ai.generate(
            prompt=prompt,
            temperature=0.4,  # Balanceado para creatividad pero precisión
            max_tokens=1500
        )
        
        logger.info(f"Resultado de generación: éxito={result['success']}")
        
        if not result['success']:
            return JsonResponse({
                'success': False,
                'error': f"Error de IA: {result.get('error', 'Error desconocido')}"
            }, status=500)
        
        # Intentar parsear el JSON de la respuesta
        ai_response = result['text'].strip()
        
        # Limpiar posibles marcadores de código markdown
        if ai_response.startswith('```'):
            lines = ai_response.split('\n')
            ai_response = '\n'.join([line for line in lines if not line.startswith('```')])
        
        try:
            questions_data = json_module.loads(ai_response)
            questions = questions_data.get('preguntas', [])
            
            if not questions:
                raise ValueError("No se encontraron preguntas en la respuesta")
            
            # Agregar información de capítulos fuente a cada pregunta
            for q in questions:
                q['source_chapters'] = chapter_info
                q['source_file'] = filename
            
            return JsonResponse({
                'success': True,
                'questions': questions,
                'count': len(questions),
                'tokens_used': result.get('tokens', 0),
                'duration_ms': result.get('duration_ms', 0)
            })
            
        except json_module.JSONDecodeError as e:
            # Si falla el parseo, intentar extraer preguntas de forma más flexible
            return JsonResponse({
                'success': False,
                'error': f'La IA no generó un JSON válido. Por favor intenta de nuevo.',
                'debug_response': ai_response[:500]
            }, status=500)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


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
        
        saved_count = 0
        
        # Obtener o crear materia por defecto
        default_subject = Subject.objects.first()
        if not default_subject:
            return JsonResponse({
                'success': False,
                'error': 'No hay materias configuradas en el sistema'
            }, status=400)
        
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
                subject=default_subject,
                topic=default_topic,
                question_type='opcion_multiple',
                question_text=q_data.get('pregunta', ''),
                answer_text=q_data.get('respuesta', ''),
                difficulty=q_data.get('dificultad', 3),
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
            saved_count += 1
        
        # Guardar preguntas rechazadas (para registro)
        for q_data in rejected:
            question = Question(
                subject=default_subject,
                topic=default_topic,
                question_type='opcion_multiple',
                question_text=q_data.get('pregunta', ''),
                answer_text=q_data.get('respuesta', ''),
                difficulty=q_data.get('dificultad', 3),
                user=request.user,
                generated_by_ai=True,
                ai_approved=False
            )
            
            if 'opciones' in q_data:
                question.options = q_data['opciones']
            
            if 'source_chapters' in q_data:
                question.source_chapters = q_data['source_chapters']
            
            question.save()
        
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


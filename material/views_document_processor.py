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

from material.ia_processor import (
    extract_text_advanced,
    count_tokens,
    count_tokens_file,
    split_text_by_tokens,
    optimize_text_for_ai
)


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
    context = {
        'page_title': 'Procesador de Documentos',
        'supported_formats': ['.pdf', '.docx', '.pptx', '.txt'],
        'max_file_size_mb': 10
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

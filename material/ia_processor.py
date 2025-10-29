"""
IA Processor para EducaApp
===========================
Módulo actualizado con PyMuPDF y DocumentProcessor para procesamiento avanzado.
Mantiene retrocompatibilidad con funciones existentes.
"""

# from transformers import pipeline
import fitz  # PyMuPDF (reemplaza a PyPDF2)
from docx import Document
from pptx import Presentation
import os
import re
import sys

# Importar el DocumentProcessor del módulo nuevo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from document_processor import DocumentProcessor


# Instancia global del procesador para reutilizar
_processor = DocumentProcessor()


def extract_text_from_file(file_path):
    """
    Extrae texto de archivos PDF, DOCX, PPTX, TXT.
    ACTUALIZADO: Usa PyMuPDF en vez de PyPDF2 para PDFs.
    
    Args:
        file_path: Ruta al archivo
    
    Returns:
        Texto extraído del documento
    """
    _, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower()
    text = ""

    if file_extension == '.pdf':
        # Usar PyMuPDF (fitz) en vez de PyPDF2
        doc = fitz.open(file_path)
        for i, page in enumerate(doc):
            page_text = page.get_text()
            if page_text:
                text += f"\n[Página {i+1}]\n" + page_text
        doc.close()
        
    elif file_extension == '.docx':
        doc = Document(file_path)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
            
    elif file_extension == '.pptx':
        ppt = Presentation(file_path)
        for i, slide in enumerate(ppt.slides, 1):
            text += f"\n[Slide {i}]\n"
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
                    
    elif file_extension == '.txt':
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
            
    else:
        raise ValueError(f"Formato de archivo no soportado: {file_extension}")
    
    return text.strip()


def extract_text_advanced(file_path, remove_headers=True, remove_footers=True):
    """
    NUEVA FUNCIÓN: Extracción avanzada con limpieza de headers/footers.
    Usa el DocumentProcessor completo.
    
    Args:
        file_path: Ruta al archivo
        remove_headers: Eliminar headers repetitivos (PDFs)
        remove_footers: Eliminar footers repetitivos (PDFs)
    
    Returns:
        Dict con estructura completa del documento
    """
    _, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower()
    
    if file_extension == '.pdf':
        return _processor.process_pdf(
            file_path,
            remove_headers=remove_headers,
            remove_footers=remove_footers,
            extract_toc=True
        )
    elif file_extension == '.docx':
        return _processor.process_docx(file_path)
    elif file_extension == '.pptx':
        return _processor.process_pptx(file_path)
    else:
        # Fallback para otros formatos
        text = extract_text_from_file(file_path)
        return {
            'metadata': {'title': os.path.basename(file_path)},
            'chapters': [{
                'title': 'Documento completo',
                'content': text,
                'tokens': _processor.count_tokens(text)
            }],
            'stats': {'total_tokens': _processor.count_tokens(text)}
        }


def count_tokens(text):
    """
    NUEVA FUNCIÓN: Cuenta tokens exactos usando tiktoken (GPT-4).
    
    Args:
        text: Texto a contar
    
    Returns:
        Número de tokens
    """
    return _processor.count_tokens(text)


def count_tokens_file(file_path):
    """
    NUEVA FUNCIÓN: Cuenta tokens de un archivo completo.
    
    Args:
        file_path: Ruta al archivo
    
    Returns:
        Número total de tokens
    """
    result = extract_text_advanced(file_path)
    return result['stats'].get('total_tokens', 0)


def split_text_by_tokens(text, max_tokens=4000):
    """
    NUEVA FUNCIÓN: Divide texto en chunks que no excedan límite de tokens.
    
    Args:
        text: Texto a dividir
        max_tokens: Límite de tokens por chunk
    
    Returns:
        Lista de chunks de texto
    """
    return _processor.split_by_token_limit(text, max_tokens=max_tokens)


def optimize_text_for_ai(text, remove_extra_whitespace=True):
    """
    NUEVA FUNCIÓN: Optimiza texto para reducir tokens sin perder información.
    
    Args:
        text: Texto a optimizar
        remove_extra_whitespace: Elimina espacios/saltos extras
    
    Returns:
        Texto optimizado
    """
    return _processor.optimize_for_ai(
        text,
        remove_extra_whitespace=remove_extra_whitespace,
        remove_urls=False,  # Por defecto no quitar URLs en documentos académicos
        remove_emails=False
    )


def split_text_into_chapters(text):
    """
    Divide el texto en capítulos basados en títulos detectados.
    NOTA: Para mejor detección, usar extract_text_advanced() que usa TOC.
    """
    chapters = re.split(r'(?i)(cap[ií]tulo \d+|secci[oó]n \d+)', text)
    return [c.strip() for c in chapters if c.strip()]


def generate_questions_from_text(text, num_questions):
    """
    Genera preguntas a partir del texto usando IA.
    NOTA: Requiere transformers instalado (comentado por defecto).
    
    Args:
        text: Texto a analizar
        num_questions: Número de preguntas a generar
    
    Returns:
        String con preguntas generadas
    """
    if not text.strip():
        return "No se encontró texto para analizar."
    
    # NOTA: Esta función requiere transformers que es pesado (>500MB)
    # Descomentar si se necesita:
    # from transformers import pipeline
    # generator = pipeline("summarization", model="facebook/bart-large-cnn")
    # chapters = split_text_into_chapters(text)
    # 
    # questions_output = []
    # for i, chapter in enumerate(chapters):
    #     summary = generator(chapter[:1024], max_length=150, min_length=30, truncation=True)[0]['summary_text']
    #     question = f"¿De qué trata este capítulo?\nRespuesta: {summary}\nReferencia: Capítulo {i+1}"
    #     questions_output.append(question)
    # 
    # return "\n\n".join(questions_output)
    
    # Por ahora, retornar mensaje informativo
    return (
        "Generación de preguntas con IA requiere instalar transformers.\n"
        "Para habilitarlo: pip install transformers torch\n"
        f"Texto recibido: {len(text)} caracteres, ~{count_tokens(text)} tokens"
    )

"""
Document Processor Module
==========================
Módulo para procesar documentos (PDF, DOCX, PPTX, TXT) con foco en:
- Extracción de estructura jerárquica (capítulos, secciones)
- Limpieza de texto repetitivo (headers, footers, números de página)
- Optimización de tokens para envío a IA (GPT-4, Claude, etc.)

Autor: EducaApp
Fecha: 29 octubre 2025
"""

import fitz  # PyMuPDF
import pdfplumber
import tiktoken
from markdownify import markdownify as md
from docx import Document
from pptx import Presentation
from typing import Dict, List, Tuple, Optional
import re
from collections import Counter
import json


class DocumentProcessor:
    """
    Procesador universal de documentos con detección de estructura
    y optimización para envío a IA.
    """
    
    def __init__(self, encoding_name: str = "cl100k_base"):
        """
        Inicializa el procesador.
        
        Args:
            encoding_name: Nombre del encoding de tiktoken (ej: "cl100k_base" para GPT-4)
        """
        self.encoding = tiktoken.get_encoding(encoding_name)
        self.stats = {
            'total_pages': 0,
            'total_tokens': 0,
            'chapters': [],
            'removed_headers': 0,
            'removed_footers': 0
        }
    
    # ========================================================================
    # PDF PROCESSING (PyMuPDF + pdfplumber)
    # ========================================================================
    
    def process_pdf(self, file_path: str, 
                   remove_headers: bool = True,
                   remove_footers: bool = True,
                   extract_toc: bool = True) -> Dict:
        """
        Procesa un PDF completo y extrae estructura + contenido limpio.
        
        Args:
            file_path: Ruta al archivo PDF
            remove_headers: Si True, detecta y elimina headers repetitivos
            remove_footers: Si True, detecta y elimina footers repetitivos
            extract_toc: Si True, extrae tabla de contenidos si existe
        
        Returns:
            Diccionario con estructura:
            {
                'metadata': {...},
                'toc': [...],
                'chapters': [{'title': str, 'content': str, 'tokens': int, 'pages': [int]}],
                'stats': {...}
            }
        """
        result = {
            'metadata': {},
            'toc': [],
            'chapters': [],
            'full_text': '',
            'stats': {}
        }
        
        # Abrir PDF con PyMuPDF
        doc = fitz.open(file_path)
        
        # Extraer metadata
        result['metadata'] = {
            'title': doc.metadata.get('title', ''),
            'author': doc.metadata.get('author', ''),
            'subject': doc.metadata.get('subject', ''),
            'total_pages': doc.page_count,
            'format': doc.metadata.get('format', 'PDF')
        }
        
        self.stats['total_pages'] = doc.page_count
        
        # Extraer TOC (tabla de contenidos) si existe
        if extract_toc:
            toc = doc.get_toc()
            result['toc'] = [
                {'level': level, 'title': title, 'page': page}
                for level, title, page in toc
            ]
        
        # Detectar headers/footers repetitivos con pdfplumber
        headers_to_remove = []
        footers_to_remove = []
        
        if remove_headers or remove_footers:
            headers_to_remove, footers_to_remove = self._detect_repetitive_text(file_path)
        
        # Extraer texto por capítulo si hay TOC, sino por páginas
        if result['toc'] and len(result['toc']) > 0:
            result['chapters'] = self._extract_chapters_from_toc(
                doc, result['toc'], headers_to_remove, footers_to_remove
            )
        else:
            # Sin TOC: extraer texto completo limpio
            full_text = self._extract_clean_text(
                doc, headers_to_remove, footers_to_remove
            )
            result['full_text'] = full_text
            result['chapters'] = [{
                'title': 'Documento completo',
                'content': full_text,
                'tokens': self.count_tokens(full_text),
                'pages': list(range(1, doc.page_count + 1))
            }]
        
        # Calcular stats finales
        result['stats'] = {
            'total_pages': doc.page_count,
            'total_chapters': len(result['chapters']),
            'total_tokens': sum(ch['tokens'] for ch in result['chapters']),
            'removed_headers': self.stats['removed_headers'],
            'removed_footers': self.stats['removed_footers']
        }
        
        doc.close()
        return result
    
    def _detect_repetitive_text(self, file_path: str, 
                                threshold: float = 0.7) -> Tuple[List[str], List[str]]:
        """
        Detecta headers y footers repetitivos usando pdfplumber.
        
        Args:
            file_path: Ruta al PDF
            threshold: Porcentaje de páginas donde debe aparecer para considerarse repetitivo (0-1)
        
        Returns:
            Tupla (headers, footers) con listas de textos a eliminar
        """
        headers = []
        footers = []
        
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            if total_pages == 0:
                return [], []
            
            # Recolectar primeras/últimas líneas de cada página
            top_lines = []
            bottom_lines = []
            
            for page in pdf.pages[:min(10, total_pages)]:  # Samplear primeras 10 páginas
                text = page.extract_text()
                if not text:
                    continue
                
                lines = text.strip().split('\n')
                if len(lines) > 0:
                    top_lines.append(lines[0].strip())
                if len(lines) > 1:
                    bottom_lines.append(lines[-1].strip())
            
            # Contar frecuencias
            top_counter = Counter(top_lines)
            bottom_counter = Counter(bottom_lines)
            
            # Identificar repetitivos (aparecen en >threshold% de páginas)
            min_occurrences = int(len(top_lines) * threshold)
            
            for text, count in top_counter.items():
                if count >= min_occurrences and len(text) > 5:  # Mín 5 chars
                    headers.append(text)
                    self.stats['removed_headers'] += count
            
            for text, count in bottom_counter.items():
                if count >= min_occurrences and len(text) > 3:
                    # Ignorar números de página simples
                    if not re.match(r'^\d+$', text):
                        footers.append(text)
                        self.stats['removed_footers'] += count
        
        return headers, footers
    
    def _extract_clean_text(self, doc: fitz.Document, 
                           headers: List[str], 
                           footers: List[str]) -> str:
        """
        Extrae texto limpio de todo el documento, removiendo headers/footers.
        """
        clean_text = []
        
        for page in doc:
            text = page.get_text()
            
            # Limpiar headers/footers
            text = self._remove_repetitive_patterns(text, headers, footers)
            
            clean_text.append(text.strip())
        
        return '\n\n'.join(clean_text)
    
    def _extract_chapters_from_toc(self, doc: fitz.Document, 
                                   toc: List[Dict],
                                   headers: List[str],
                                   footers: List[str]) -> List[Dict]:
        """
        Extrae contenido organizado por capítulos según TOC.
        """
        chapters = []
        
        # Filtrar solo capítulos de nivel 1 (principales)
        main_chapters = [item for item in toc if item['level'] == 1]
        
        for i, chapter in enumerate(main_chapters):
            start_page = chapter['page'] - 1  # PyMuPDF usa índice 0
            
            # Determinar página final (hasta siguiente capítulo o fin del documento)
            if i < len(main_chapters) - 1:
                end_page = main_chapters[i + 1]['page'] - 1
            else:
                end_page = doc.page_count
            
            # Extraer texto de páginas del capítulo
            chapter_text = []
            for page_num in range(start_page, end_page):
                if page_num < doc.page_count:
                    text = doc[page_num].get_text()
                    text = self._remove_repetitive_patterns(text, headers, footers)
                    chapter_text.append(text.strip())
            
            content = '\n\n'.join(chapter_text)
            
            chapters.append({
                'title': chapter['title'],
                'content': content,
                'tokens': self.count_tokens(content),
                'pages': list(range(start_page + 1, end_page + 1))
            })
        
        return chapters
    
    def _remove_repetitive_patterns(self, text: str, 
                                    headers: List[str], 
                                    footers: List[str]) -> str:
        """
        Elimina patrones repetitivos del texto.
        """
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Saltar headers
            if any(line_stripped.startswith(h) or line_stripped == h for h in headers):
                continue
            
            # Saltar footers
            if any(line_stripped.endswith(f) or line_stripped == f for f in footers):
                continue
            
            # Saltar números de página solitarios
            if re.match(r'^\d+$', line_stripped):
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    # ========================================================================
    # DOCX PROCESSING
    # ========================================================================
    
    def process_docx(self, file_path: str) -> Dict:
        """
        Procesa un archivo DOCX y extrae estructura por estilos (Heading 1, 2, etc.).
        
        Returns:
            Diccionario similar a process_pdf con capítulos organizados
        """
        result = {
            'metadata': {},
            'chapters': [],
            'full_text': '',
            'stats': {}
        }
        
        doc = Document(file_path)
        
        # Extraer metadata
        core_props = doc.core_properties
        result['metadata'] = {
            'title': core_props.title or '',
            'author': core_props.author or '',
            'subject': core_props.subject or '',
            'total_paragraphs': len(doc.paragraphs)
        }
        
        # Organizar por headings
        current_chapter = None
        chapters_list = []
        
        for para in doc.paragraphs:
            # Detectar si es un título (Heading 1)
            if para.style.name.startswith('Heading 1'):
                # Guardar capítulo anterior si existe
                if current_chapter:
                    chapters_list.append(current_chapter)
                
                # Iniciar nuevo capítulo
                current_chapter = {
                    'title': para.text,
                    'content': '',
                    'tokens': 0
                }
            elif current_chapter:
                # Añadir contenido al capítulo actual
                current_chapter['content'] += para.text + '\n\n'
        
        # Guardar último capítulo
        if current_chapter:
            chapters_list.append(current_chapter)
        
        # Si no hay capítulos, considerar todo el documento
        if not chapters_list:
            full_text = '\n\n'.join([p.text for p in doc.paragraphs])
            chapters_list.append({
                'title': 'Documento completo',
                'content': full_text,
                'tokens': self.count_tokens(full_text)
            })
        else:
            # Calcular tokens
            for chapter in chapters_list:
                chapter['tokens'] = self.count_tokens(chapter['content'])
        
        result['chapters'] = chapters_list
        result['full_text'] = '\n\n'.join([ch['content'] for ch in chapters_list])
        result['stats'] = {
            'total_chapters': len(chapters_list),
            'total_tokens': sum(ch['tokens'] for ch in chapters_list)
        }
        
        return result
    
    # ========================================================================
    # PPTX PROCESSING
    # ========================================================================
    
    def process_pptx(self, file_path: str) -> Dict:
        """
        Procesa un archivo PowerPoint y extrae texto slide por slide.
        
        Returns:
            Diccionario con estructura por slides
        """
        result = {
            'metadata': {},
            'slides': [],
            'full_text': '',
            'stats': {}
        }
        
        prs = Presentation(file_path)
        
        result['metadata'] = {
            'title': prs.core_properties.title or '',
            'author': prs.core_properties.author or '',
            'total_slides': len(prs.slides)
        }
        
        slides_list = []
        
        for i, slide in enumerate(prs.slides, 1):
            slide_text = []
            slide_title = ''
            
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    # Primera shape con texto suele ser el título
                    if not slide_title and shape.text.strip():
                        slide_title = shape.text.strip()
                    else:
                        slide_text.append(shape.text)
            
            content = '\n'.join(slide_text)
            
            slides_list.append({
                'slide_number': i,
                'title': slide_title or f'Slide {i}',
                'content': content,
                'tokens': self.count_tokens(content)
            })
        
        result['slides'] = slides_list
        result['full_text'] = '\n\n'.join([s['content'] for s in slides_list])
        result['stats'] = {
            'total_slides': len(slides_list),
            'total_tokens': sum(s['tokens'] for s in slides_list)
        }
        
        return result
    
    # ========================================================================
    # TOKEN COUNTING & OPTIMIZATION
    # ========================================================================
    
    def count_tokens(self, text: str) -> int:
        """
        Cuenta tokens exactos usando tiktoken (GPT-4 encoding).
        
        Args:
            text: Texto a contar
        
        Returns:
            Número de tokens
        """
        return len(self.encoding.encode(text))
    
    def split_by_token_limit(self, text: str, max_tokens: int = 4000) -> List[str]:
        """
        Divide texto en chunks que no excedan el límite de tokens.
        Útil para enviar a IA con ventana de contexto limitada.
        
        Args:
            text: Texto a dividir
            max_tokens: Límite de tokens por chunk
        
        Returns:
            Lista de chunks de texto
        """
        # Tokenizar
        tokens = self.encoding.encode(text)
        
        # Dividir en chunks
        chunks = []
        current_chunk = []
        
        for token in tokens:
            current_chunk.append(token)
            
            if len(current_chunk) >= max_tokens:
                # Decodificar chunk actual
                chunk_text = self.encoding.decode(current_chunk)
                chunks.append(chunk_text)
                current_chunk = []
        
        # Añadir último chunk si quedó algo
        if current_chunk:
            chunks.append(self.encoding.decode(current_chunk))
        
        return chunks
    
    def optimize_for_ai(self, text: str, 
                       remove_extra_whitespace: bool = True,
                       remove_urls: bool = False,
                       remove_emails: bool = False) -> str:
        """
        Optimiza texto para reducir tokens sin perder información relevante.
        
        Args:
            text: Texto a optimizar
            remove_extra_whitespace: Elimina espacios/saltos de línea extras
            remove_urls: Elimina URLs
            remove_emails: Elimina emails
        
        Returns:
            Texto optimizado
        """
        optimized = text
        
        if remove_extra_whitespace:
            # Eliminar múltiples espacios
            optimized = re.sub(r' +', ' ', optimized)
            # Eliminar múltiples saltos de línea (dejar máximo 2)
            optimized = re.sub(r'\n{3,}', '\n\n', optimized)
        
        if remove_urls:
            optimized = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', optimized)
        
        if remove_emails:
            optimized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', optimized)
        
        return optimized.strip()
    
    # ========================================================================
    # EXPORT TO JSON
    # ========================================================================
    
    def export_to_json(self, result: Dict, output_file: str):
        """
        Exporta el resultado procesado a JSON.
        
        Args:
            result: Diccionario resultado de process_pdf/docx/pptx
            output_file: Ruta del archivo JSON de salida
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    
    def get_stats_summary(self, result: Dict) -> str:
        """
        Genera un resumen legible de las estadísticas del documento.
        
        Returns:
            String con resumen formateado
        """
        stats = result.get('stats', {})
        metadata = result.get('metadata', {})
        
        summary = []
        summary.append("=" * 60)
        summary.append("RESUMEN DEL DOCUMENTO")
        summary.append("=" * 60)
        
        if metadata.get('title'):
            summary.append(f"Título: {metadata['title']}")
        if metadata.get('author'):
            summary.append(f"Autor: {metadata['author']}")
        
        summary.append("")
        summary.append(f"Total de páginas/slides: {stats.get('total_pages', stats.get('total_slides', 'N/A'))}")
        summary.append(f"Total de capítulos/secciones: {stats.get('total_chapters', len(result.get('chapters', [])))}")
        summary.append(f"Total de tokens (GPT-4): {stats.get('total_tokens', 0):,}")
        
        if stats.get('removed_headers', 0) > 0:
            summary.append(f"Headers eliminados: {stats['removed_headers']}")
        if stats.get('removed_footers', 0) > 0:
            summary.append(f"Footers eliminados: {stats['removed_footers']}")
        
        summary.append("=" * 60)
        
        return '\n'.join(summary)


# ============================================================================
# FUNCIONES DE CONVENIENCIA
# ============================================================================

def process_document(file_path: str, **kwargs) -> Dict:
    """
    Función de conveniencia que detecta el tipo de archivo y procesa automáticamente.
    
    Args:
        file_path: Ruta al archivo (PDF, DOCX, PPTX)
        **kwargs: Argumentos adicionales pasados al procesador específico
    
    Returns:
        Diccionario con estructura procesada
    """
    processor = DocumentProcessor()
    
    if file_path.lower().endswith('.pdf'):
        return processor.process_pdf(file_path, **kwargs)
    elif file_path.lower().endswith('.docx'):
        return processor.process_docx(file_path, **kwargs)
    elif file_path.lower().endswith('.pptx'):
        return processor.process_pptx(file_path, **kwargs)
    else:
        raise ValueError(f"Formato no soportado: {file_path}")


def quick_token_count(file_path: str) -> int:
    """
    Cuenta rápidamente tokens de un documento sin procesamiento completo.
    
    Args:
        file_path: Ruta al archivo
    
    Returns:
        Número total de tokens
    """
    result = process_document(file_path)
    return result['stats'].get('total_tokens', 0)


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    # Ejemplo de uso básico
    processor = DocumentProcessor()
    
    # Procesar un PDF
    # result = processor.process_pdf("documento.pdf", remove_headers=True, remove_footers=True)
    
    # Ver resumen
    # print(processor.get_stats_summary(result))
    
    # Exportar a JSON
    # processor.export_to_json(result, "documento_procesado.json")
    
    # Contar tokens de un capítulo específico
    # capitulo1 = result['chapters'][0]
    # print(f"Capítulo: {capitulo1['title']}")
    # print(f"Tokens: {capitulo1['tokens']}")
    
    # Dividir por límite de tokens
    # chunks = processor.split_by_token_limit(capitulo1['content'], max_tokens=2000)
    # print(f"Dividido en {len(chunks)} chunks de máx 2000 tokens")
    
    print("Document Processor cargado correctamente.")
    print("Importa con: from document_processor import DocumentProcessor, process_document")

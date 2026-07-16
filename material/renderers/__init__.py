"""Renderers de documentos para exportación."""

from .pdf_renderer import render_exam_payload_to_pdf
from .docx_renderer import render_exam_payload_to_docx
from .pdf_renderer import render_exam_batch_payloads_to_pdf
from .docx_renderer import render_exam_batch_payloads_to_docx

__all__ = [
    'render_exam_payload_to_pdf',
    'render_exam_payload_to_docx',
    'render_exam_batch_payloads_to_pdf',
    'render_exam_batch_payloads_to_docx',
]

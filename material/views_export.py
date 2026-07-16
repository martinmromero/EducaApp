"""
views_export.py
Exportación de exámenes a DOCX y PDF mediante builder + renderers unificados.

Todas las respuestas se sirven como descarga HTTP; no se escribe a disco.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from .document_builder import build_document_payload
from .models import Exam, ExamVersionBatch
from .print_format_utils import get_print_style_context, resolve_print_format_for_exam
from .renderers import (
    render_exam_batch_payloads_to_docx,
    render_exam_batch_payloads_to_pdf,
    render_exam_payload_to_docx,
    render_exam_payload_to_pdf,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers internos
# ──────────────────────────────────────────────────────────────────────────────

_TIPO_EXAMEN_LABELS = {
    'final': 'Final',
    'parcial': 'Parcial',
    '1er_parcial': '1er Parcial',
    '2do_parcial': '2do Parcial',
    '3er_parcial': '3er Parcial',
    'recuperatorio': 'Recuperatorio',
    'practico': 'Práctico',
}

_TIPO_MODALIDAD_LABELS = {'individual': 'Individual', 'grupal': 'Grupal'}


def _as_bool_param(raw_value, default=False):
    if raw_value is None:
        return default
    return str(raw_value).strip().lower() in {'1', 'true', 'yes', 'si', 'on'}

def _build_export_context(examen, con_respuestas=False):
    """
    Construye el contexto de exportación con exactamente las mismas claves que
    ver_examen() pasa a su template, más la variable `con_respuestas`.
    Esto garantiza que PDF, DOCX y la vista browser usen la misma estructura.
    """
    questions_texts = []
    for q in examen.questions.order_by('pk').all():
        questions_texts.append({
            'text': q.question_text,
            'type': q.question_type,
            'options': q.options or [],
            'question_image_b64': q.question_image_b64 or '',
            'answer_text': q.answer_text or '',
            'answer_image_b64': q.answer_image_b64 or '',
        })

    outcomes_texts = [o.description for o in examen.learning_outcomes.all()]
    if not outcomes_texts and examen.outcomes_snapshot:
        outcomes_texts = list(examen.outcomes_snapshot)

    topics_texts = [t.name for t in examen.topics.all()]
    if not topics_texts and examen.topics_snapshot:
        topics_texts = list(examen.topics_snapshot)

    if examen.professor:
        professor_name = examen.professor.get_full_name() or examen.professor.username
    else:
        professor_name = '-'

    modalidad_list = [m.strip() for m in (examen.resolution_time or '').split(',') if m.strip()]

    formato = resolve_print_format_for_exam(examen)

    return {
        # ── mismo formato que ver_examen() ──
        'exam': examen,
        'institution': {'name': examen.institution_name or '-'},
        'faculty':     {'name': examen.faculty_name or '-'},
        'career':      {'name': examen.career_name or '-'},
        'subject':     {'name': examen.subject.name if examen.subject else '-'},
        'professor':   {'get_full_name': professor_name},
        'current_date': examen.date_str or '-',
        'exam_type':  _TIPO_EXAMEN_LABELS.get(examen.exam_type or '', examen.exam_type or '-'),
        'exam_mode':  _TIPO_MODALIDAD_LABELS.get(examen.exam_group or '', examen.exam_group or '-'),
        'resolution_time': examen.duration_minutes,
        'modalidad_resolucion': modalidad_list,
        'instructions': examen.instructions or '',
        'notes_and_recommendations': examen.notes_and_recommendations or '',
        'questions_texts': questions_texts,
        'outcomes_texts': outcomes_texts,
        'topics_texts': topics_texts,
        'print_style': get_print_style_context(formato),
        # ── extra solo para exportación ──
        'con_respuestas': con_respuestas,
    }


def _safe_filename(title, suffix=''):
    """Genera un nombre de archivo seguro a partir del título del examen."""
    safe = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in title)
    safe = safe.strip().replace(' ', '_')[:60]
    return f"{safe}{suffix}"


# ──────────────────────────────────────────────────────────────────────────────
# Exportar a DOCX
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def exportar_examen_docx(request, pk):
    """
    Genera y descarga el examen como archivo .docx (Office Open XML).
    El orden de secciones es idéntico al de base_exam_preview.html:
      encabezado → info (2 cols) → outcomes → instrucciones → temas → preguntas

    Query params:
      ?con_respuestas=1   incluye la clave de respuestas de cada pregunta.
    """
    examen = get_object_or_404(Exam, pk=pk, created_by=request.user)
    con_respuestas = _as_bool_param(request.GET.get('con_respuestas'), default=False)
    include_rubrics = _as_bool_param(request.GET.get('include_rubrics'), default=True)
    formato = resolve_print_format_for_exam(examen)
    payload = build_document_payload(
        examen,
        kind='exam',
        include_answers=con_respuestas,
        include_rubrics=include_rubrics,
    )
    content = render_exam_payload_to_docx(payload, formato)

    suffix = '_con_respuestas' if con_respuestas else ''
    filename = _safe_filename(examen.title or 'Examen', suffix) + '.docx'

    response = HttpResponse(
        content,
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ──────────────────────────────────────────────────────────────────────────────
# Exportar a PDF
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def exportar_examen_pdf(request, pk):
    """
    Genera y descarga el examen como archivo .pdf.

    Usa renderer PDF unificado (payload neutral + ReportLab Platypus).
    Toma el formato asignado/snapshot del examen para tipografia, color y
    margenes.

    Query params:
      ?con_respuestas=1   incluye la clave de respuestas de cada pregunta.
    """
    examen = get_object_or_404(Exam, pk=pk, created_by=request.user)
    con_respuestas = _as_bool_param(request.GET.get('con_respuestas'), default=False)
    include_rubrics = _as_bool_param(request.GET.get('include_rubrics'), default=True)
    try:
        formato = resolve_print_format_for_exam(examen)
        payload = build_document_payload(
            examen,
            kind='exam',
            include_answers=con_respuestas,
            include_rubrics=include_rubrics,
        )
        content = render_exam_payload_to_pdf(payload, formato)
    except Exception as render_error:
        return HttpResponse(
            f'Error al generar PDF con renderer unificado: {render_error}',
            status=500,
            content_type='text/plain; charset=utf-8',
        )

    suffix = '_con_respuestas' if con_respuestas else ''
    filename = _safe_filename(examen.title or 'Examen', suffix) + '.pdf'

    response = HttpResponse(content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def exportar_lote_docx(request, batch_id):
    batch = get_object_or_404(ExamVersionBatch, pk=batch_id, created_by=request.user)
    con_respuestas = _as_bool_param(request.GET.get('con_respuestas'), default=False)
    include_rubrics = _as_bool_param(request.GET.get('include_rubrics'), default=True)
    versions = batch.versions.all().order_by('version_number', 'id')

    exam_documents = []
    for idx, examen in enumerate(versions, start=1):
        exam_documents.append({
            'payload': build_document_payload(
                examen,
                kind='exam',
                include_answers=con_respuestas,
                include_rubrics=include_rubrics,
            ),
            'formato': resolve_print_format_for_exam(examen),
            'label': f"Version {examen.version_number or idx}",
        })

    content = render_exam_batch_payloads_to_docx(exam_documents)
    suffix = '_con_respuestas' if con_respuestas else ''
    filename = _safe_filename(batch.name or 'Lote', suffix) + '.docx'
    response = HttpResponse(
        content,
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def exportar_lote_pdf(request, batch_id):
    batch = get_object_or_404(ExamVersionBatch, pk=batch_id, created_by=request.user)
    con_respuestas = _as_bool_param(request.GET.get('con_respuestas'), default=False)
    include_rubrics = _as_bool_param(request.GET.get('include_rubrics'), default=True)
    versions = batch.versions.all().order_by('version_number', 'id')

    exam_documents = []
    for idx, examen in enumerate(versions, start=1):
        exam_documents.append({
            'payload': build_document_payload(
                examen,
                kind='exam',
                include_answers=con_respuestas,
                include_rubrics=include_rubrics,
            ),
            'formato': resolve_print_format_for_exam(examen),
            'label': f"Version {examen.version_number or idx}",
        })

    try:
        content = render_exam_batch_payloads_to_pdf(exam_documents)
    except Exception as render_error:
        return HttpResponse(
            f'Error al generar PDF del lote con renderer unificado: {render_error}',
            status=500,
            content_type='text/plain; charset=utf-8',
        )

    suffix = '_con_respuestas' if con_respuestas else ''
    filename = _safe_filename(batch.name or 'Lote', suffix) + '.pdf'
    response = HttpResponse(content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

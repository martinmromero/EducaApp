"""
views_export.py
Exportación de exámenes a DOCX y PDF mediante builder + renderers unificados.

Todas las respuestas se sirven como descarga HTTP; no se escribe a disco.
"""

import logging

from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.utils import DatabaseError, OperationalError, ProgrammingError
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404
from django.http import HttpResponse

from .document_builder import build_document_payload
from .exam_labels import get_exam_mode_label, get_exam_type_label
from .models import Exam, ExamVersionBatch
from .print_format_utils import get_print_style_context, resolve_print_format_for_exam
from .renderers import (
    render_exam_batch_payloads_to_docx,
    render_exam_batch_payloads_to_pdf,
    render_exam_payload_to_docx,
    render_exam_payload_to_pdf,
)


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers internos
# ──────────────────────────────────────────────────────────────────────────────

def _as_bool_param(raw_value, default=False):
    if raw_value is None:
        return default
    return str(raw_value).strip().lower() in {'1', 'true', 'yes', 'si', 'on'}


def _get_table_columns(table_name):
    try:
        with connection.cursor() as cursor:
            return {
                col.name for col in connection.introspection.get_table_description(cursor, table_name)
            }
    except Exception:
        return set()


def _get_compatible_exam_queryset():
    qs = Exam.objects.select_related('subject', 'professor')
    exam_columns = _get_table_columns(Exam._meta.db_table)
    if exam_columns and not {'version_batch_id', 'version_number'}.issubset(exam_columns):
        qs = qs.defer('version_batch', 'version_number')
    return qs


def _get_compatible_exam_or_404(user, pk):
    try:
        return get_object_or_404(_get_compatible_exam_queryset(), pk=pk, created_by=user)
    except (OperationalError, ProgrammingError, DatabaseError):
        logger.warning('Esquema de examenes desfasado en produccion; degradando export del examen %s.', pk)
        fallback_qs = Exam.objects.select_related('subject', 'professor').defer('version_batch', 'version_number')
        return get_object_or_404(fallback_qs, pk=pk, created_by=user)


def _resolve_print_format_safe(examen):
    try:
        return resolve_print_format_for_exam(examen)
    except (OperationalError, ProgrammingError, DatabaseError):
        logger.warning('No se pudo resolver el formato de impresion para el examen %s; usando defaults.', examen.pk)
        return None


def _build_payload_safe(examen, *, con_respuestas=False, include_rubrics=True):
    try:
        return build_document_payload(
            examen,
            kind='exam',
            include_answers=con_respuestas,
            include_rubrics=include_rubrics,
        )
    except (OperationalError, ProgrammingError, DatabaseError):
        if include_rubrics:
            logger.warning('No se pudieron cargar rubricas del examen %s; exportando sin rubricas.', examen.pk)
            return build_document_payload(
                examen,
                kind='exam',
                include_answers=con_respuestas,
                include_rubrics=False,
            )
        raise


def _clone_exam_without_assigned_format(examen):
    field_names = [field.name for field in Exam._meta.concrete_fields if field.name != 'id']
    cloned = Exam(**model_to_dict(examen, fields=field_names))
    cloned.pk = examen.pk
    cloned._state.adding = False
    cloned._state.db = examen._state.db
    for attr_name in ('subject', 'professor', 'created_by'):
        if hasattr(examen, attr_name):
            setattr(cloned, attr_name, getattr(examen, attr_name))
    for relation_name in ('questions', 'topics', 'learning_outcomes'):
        if hasattr(examen, relation_name):
            setattr(cloned, relation_name, getattr(examen, relation_name))
    return cloned


def _prepare_export_payload_and_format(examen, *, con_respuestas=False, include_rubrics=True):
    formato = _resolve_print_format_safe(examen)
    payload_exam = examen if formato is not None else _clone_exam_without_assigned_format(examen)
    payload = _build_payload_safe(
        payload_exam,
        con_respuestas=con_respuestas,
        include_rubrics=include_rubrics,
    )
    return payload, formato

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
        'exam_type': get_exam_type_label(examen.exam_type) or '-',
        'exam_mode': get_exam_mode_label(examen.exam_group) or '-',
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
    examen = _get_compatible_exam_or_404(request.user, pk)
    con_respuestas = _as_bool_param(request.GET.get('con_respuestas'), default=False)
    include_rubrics = _as_bool_param(request.GET.get('include_rubrics'), default=True)
    payload, formato = _prepare_export_payload_and_format(
        examen,
        con_respuestas=con_respuestas,
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
    examen = _get_compatible_exam_or_404(request.user, pk)
    con_respuestas = _as_bool_param(request.GET.get('con_respuestas'), default=False)
    include_rubrics = _as_bool_param(request.GET.get('include_rubrics'), default=True)
    try:
        payload, formato = _prepare_export_payload_and_format(
            examen,
            con_respuestas=con_respuestas,
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
        payload, formato = _prepare_export_payload_and_format(
            examen,
            con_respuestas=con_respuestas,
            include_rubrics=include_rubrics,
        )
        exam_documents.append({
            'payload': payload,
            'formato': formato,
            'label': f"Version {examen.__dict__.get('version_number') or idx}",
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
        payload, formato = _prepare_export_payload_and_format(
            examen,
            con_respuestas=con_respuestas,
            include_rubrics=include_rubrics,
        )
        exam_documents.append({
            'payload': payload,
            'formato': formato,
            'label': f"Version {examen.__dict__.get('version_number') or idx}",
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

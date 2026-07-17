"""Document builder neutral para exportación e impresión."""

from typing import Any


def _resolve_institution_logo_data(exam: Any) -> dict:
    """Resuelve logo institucional desde InstitutionV2 por nombre de institución."""
    institution_name = (getattr(exam, 'institution_name', '') or '').strip()
    if not institution_name:
        return {'logo_url': None, 'logo_b64': '', 'logo_path': ''}

    try:
        from .models import InstitutionV2

        institution = InstitutionV2.objects.filter(name__iexact=institution_name).first()
        if not institution:
            return {'logo_url': None, 'logo_b64': '', 'logo_path': ''}

        logo_b64 = getattr(institution, 'logo_b64', '') or ''
        logo_path = ''
        try:
            logo_path = institution.logo.path if institution.logo else ''
        except Exception:
            logo_path = ''

        logo_url = logo_b64 or getattr(institution, 'logo_src', '') or None
        return {
            'logo_url': logo_url,
            'logo_b64': logo_b64,
            'logo_path': logo_path,
        }
    except Exception:
        return {'logo_url': None, 'logo_b64': '', 'logo_path': ''}


def build_document_payload(obj: Any, *, kind: str = 'exam', include_answers: bool = False, include_rubrics: bool = True) -> list[dict]:
    """Construye una estructura intermedia neutral para renderers PDF/DOCX/HTML."""
    if kind != 'exam':
        raise ValueError(f"Unsupported document kind: {kind}")

    return build_exam_document_payload(
        obj,
        include_answers=include_answers,
        include_rubrics=include_rubrics,
    )


def build_exam_document_payload(exam: Any, *, include_answers: bool = False, include_rubrics: bool = True) -> list[dict]:
    """Builder inicial para exámenes escritos.

    Retorna bloques neutrales; los renderers traducen estos bloques a PDF/DOCX.
    """
    logo_data = _resolve_institution_logo_data(exam)
    exam_type = getattr(exam, 'exam_type', '') or ''
    exam_year = getattr(exam, 'year', None)
    date_str = getattr(exam, 'date_str', '') or ''
    if not exam_year and date_str and len(date_str) >= 4:
        maybe_year = ''.join(ch for ch in date_str if ch.isdigit())
        exam_year = maybe_year[-4:] if len(maybe_year) >= 4 else ''

    blocks = [
        {
            'tipo': 'letterhead',
            'logo_url': logo_data.get('logo_url') or None,
            'logo_b64': logo_data.get('logo_b64') or '',
            'logo_path': logo_data.get('logo_path') or '',
            'institucion': getattr(exam, 'institution_name', '') or '',
            'facultad': getattr(exam, 'faculty_name', '') or '',
            'carrera': getattr(exam, 'career_name', '') or '',
            'materia': getattr(getattr(exam, 'subject', None), 'name', '') or getattr(exam, 'subject_name', ''),
            'profesor': getattr(getattr(exam, 'professor', None), 'get_full_name', lambda: '')() if getattr(exam, 'professor', None) else '',
            'fecha': getattr(exam, 'date_str', '') or '',
            'tipo_examen': exam_type,
            'modalidad': getattr(exam, 'exam_group', '') or '',
            'anio': exam_year or '',
            'duracion_minutos': getattr(exam, 'duration_minutes', None),
        },
        {
            'tipo': 'datos_alumno',
            'fecha': date_str,
            'tipo_examen': exam_type,
        },
        {
            'tipo': 'titulo',
            'texto': getattr(exam, 'title', '') or '',
        },
    ]

    instructions = getattr(exam, 'instructions', '') or ''
    if instructions:
        blocks.append({'tipo': 'instrucciones_generales', 'texto': instructions})

    outcomes = [o.description for o in exam.learning_outcomes.all()] if hasattr(exam, 'learning_outcomes') else []
    if not outcomes:
        outcomes = list(getattr(exam, 'outcomes_snapshot', None) or [])
    if outcomes:
        blocks.append({'tipo': 'resultados_aprendizaje', 'items': outcomes})

    requirements_text = ''
    for field_name in ['requisitos_aprobar', 'requirements_to_pass', 'approval_requirements']:
        value = getattr(exam, field_name, '') or ''
        if value:
            requirements_text = value
            break
    if requirements_text:
        blocks.append({'tipo': 'requisitos_aprobar', 'texto': requirements_text})

    time_text = (getattr(exam, 'resolution_time', '') or '').strip()
    if not time_text and getattr(exam, 'duration_minutes', None):
        time_text = f"{getattr(exam, 'duration_minutes')} minutos"
    if time_text:
        blocks.append({'tipo': 'tiempo', 'texto': time_text})

    topics = [t.name for t in exam.topics.all()] if hasattr(exam, 'topics') else []
    if not topics:
        topics = list(getattr(exam, 'topics_snapshot', None) or [])
    if topics:
        blocks.append({'tipo': 'lista_temas', 'items': topics})

    questions_qs = getattr(exam, 'questions', None)
    questions = questions_qs.order_by('pk').all() if hasattr(questions_qs, 'all') else []
    for idx, question in enumerate(questions, start=1):
        options = getattr(question, 'options', None) or []
        block = {
            'tipo': 'pregunta',
            'numero': idx,
            'texto': getattr(question, 'question_text', '') or '',
            'subtipo': getattr(question, 'question_type', '') or '',
            'opciones': options,
            'dificultad': getattr(question, 'difficulty', None),
            'imagen_pregunta_b64': getattr(question, 'question_image_b64', '') or '',
            'imagen_respuesta_b64': getattr(question, 'answer_image_b64', '') or '',
        }
        if include_answers:
            block['respuesta'] = getattr(question, 'answer_text', '') or ''
        blocks.append(block)

    if include_rubrics and hasattr(exam, 'exam_rubrics'):
        rubric_links = exam.exam_rubrics.filter(show_in_exam=True).select_related('rubric').order_by('position', 'id')
        for exam_rubric in rubric_links:
            rubric = exam_rubric.rubric
            level_objs = list(rubric.levels.order_by('order', 'id'))
            levels = [lvl.label for lvl in level_objs]
            criteria = list(rubric.criteria.order_by('order', 'id'))
            rows = []
            for criterion in criteria:
                cells = {c.level_id: c.description for c in criterion.cells.select_related('level')}
                rows.append({
                    'criterio': criterion.name,
                    'celdas': [cells.get(level.id, '') for level in level_objs],
                })
            blocks.append({
                'tipo': 'tabla_rubrica',
                'titulo': rubric.title,
                'columnas': levels,
                'filas': rows,
            })

    return blocks
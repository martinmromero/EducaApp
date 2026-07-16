"""Document builder neutral para exportación e impresión."""

from typing import Any


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
    blocks = [
        {
            'tipo': 'encabezado',
            'institucion': getattr(exam, 'institution_name', '') or '',
            'facultad': getattr(exam, 'faculty_name', '') or '',
            'carrera': getattr(exam, 'career_name', '') or '',
            'materia': getattr(getattr(exam, 'subject', None), 'name', '') or getattr(exam, 'subject_name', ''),
            'profesor': getattr(getattr(exam, 'professor', None), 'get_full_name', lambda: '')() if getattr(exam, 'professor', None) else '',
            'fecha': getattr(exam, 'date_str', '') or '',
            'tipo_examen': getattr(exam, 'exam_type', '') or '',
            'modalidad': getattr(exam, 'exam_group', '') or '',
            'duracion_minutos': getattr(exam, 'duration_minutes', None),
        },
        {
            'tipo': 'titulo',
            'texto': getattr(exam, 'title', '') or '',
        },
    ]

    instructions = getattr(exam, 'instructions', '') or ''
    if instructions:
        blocks.append({'tipo': 'instrucciones', 'texto': instructions})

    outcomes = [o.description for o in exam.learning_outcomes.all()] if hasattr(exam, 'learning_outcomes') else []
    if not outcomes:
        outcomes = list(getattr(exam, 'outcomes_snapshot', None) or [])
    if outcomes:
        blocks.append({'tipo': 'lista_outcomes', 'items': outcomes})

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
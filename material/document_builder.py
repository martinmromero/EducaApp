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
            'materia': getattr(getattr(exam, 'subject', None), 'name', '') or getattr(exam, 'subject_name', ''),
            'profesor': getattr(getattr(exam, 'professor', None), 'get_full_name', lambda: '')() if getattr(exam, 'professor', None) else '',
            'fecha': getattr(exam, 'date_str', '') or '',
        },
        {
            'tipo': 'titulo',
            'texto': getattr(exam, 'title', '') or '',
        },
    ]

    instructions = getattr(exam, 'instructions', '') or ''
    if instructions:
        blocks.append({'tipo': 'instrucciones', 'texto': instructions})

    for idx, question in enumerate(getattr(exam, 'questions', []).all() if hasattr(getattr(exam, 'questions', None), 'all') else [], start=1):
        block = {
            'tipo': 'pregunta',
            'numero': idx,
            'texto': getattr(question, 'question_text', '') or '',
            'subtipo': getattr(question, 'question_type', '') or '',
            'opciones': json.loads(question.options_json) if getattr(question, 'options_json', None) else [],
            'puntaje': getattr(question, 'difficulty', None),
        }
        if include_answers:
            block['respuesta'] = getattr(question, 'answer_text', '') or ''
        blocks.append(block)

    if include_rubrics and hasattr(exam, 'exam_rubrics'):
        for exam_rubric in exam.exam_rubrics.filter(show_in_exam=True).select_related('rubric'):
            blocks.append({
                'tipo': 'tabla_rubrica',
                'titulo': exam_rubric.rubric.title,
                'rubric_id': exam_rubric.rubric_id,
            })

    return blocks
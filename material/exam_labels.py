"""Shared label helpers for exam-related display strings."""

EXAM_TYPE_LABELS = {
    'final': 'Final',
    'parcial': 'Parcial',
    '1er_parcial': '1er Parcial',
    '2do_parcial': '2do Parcial',
    '3er_parcial': '3er Parcial',
    'recuperatorio': 'Recuperatorio',
    'practico': 'Práctico',
}


EXAM_MODE_LABELS = {
    'individual': 'Individual',
    'grupal': 'Grupal',
}


def get_exam_type_label(raw_exam_type):
    value = (raw_exam_type or '').strip()
    if not value:
        return ''
    return EXAM_TYPE_LABELS.get(value.lower(), value.replace('_', ' '))


def get_exam_mode_label(raw_exam_mode):
    value = (raw_exam_mode or '').strip()
    if not value:
        return ''
    return EXAM_MODE_LABELS.get(value.lower(), value)

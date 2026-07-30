"""
Punto único para decidir qué preguntas puede ver/usar un usuario más allá de
las que él mismo cargó. Hoy solo suma el contenido semilla del sistema
(`settings.SEED_CONTENT_USERNAME`); si en el futuro se retoma "materias
compartibles" (ver memoria del proyecto), se extiende acá agregando otra
condición al OR en vez de duplicar esta lógica en cada vista.
"""
from django.conf import settings
from django.db.models import Q

from .models import Question


def get_visible_questions(user, subject=None, include_seed=False):
    """Preguntas propias del usuario, más las semilla del sistema si `include_seed`.

    `subject` (opcional) restringe a una única Subject exacta — nunca se
    mezclan preguntas de materias distintas al sumar contenido semilla.
    """
    visibility = Q(user=user)
    if include_seed:
        visibility |= Q(user__username=settings.SEED_CONTENT_USERNAME)

    qs = Question.objects.filter(visibility)
    if subject is not None:
        qs = qs.filter(subjects=subject)
    return qs.distinct()

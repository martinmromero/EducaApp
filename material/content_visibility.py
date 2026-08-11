"""
Punto único para decidir qué preguntas puede ver/usar un usuario más allá de
las que él mismo cargó: contenido semilla del sistema
(`settings.SEED_CONTENT_USERNAME`, opt-in por request vía `include_seed`) y
preguntas compartidas por otros usuarios a través de un `SharingGroup` del que
el usuario es miembro aceptado (siempre activo, no es opt-in por request: es
una relación permanente que el propio usuario configuró en "Mis grupos").
"""
from django.conf import settings
from django.db.models import Q

from .models import Question, Subject, SubjectShare


def get_visible_subjects(user):
    """Materias propias del usuario, más las compartidas con él por otros
    usuarios a través de un `SharingGroup` del que es miembro aceptado.

    Antes /materias/ (y el picker de materia del wizard) mostraban
    Subject.objects.filter(is_seed_demo=False) a secas: todas las materias
    reales del sistema, de cualquier docente, a cualquier usuario. Ver
    [[project_subject_topic_global_sharing_bug]].
    """
    return Subject.objects.filter(is_seed_demo=False).filter(
        Q(created_by=user) |
        Q(
            group_shares__is_active=True,
            group_shares__group__memberships__user=user,
            group_shares__group__memberships__status='accepted',
        )
    ).distinct()


def get_visible_questions(user, subject=None, include_seed=False):
    """Preguntas propias del usuario, más semilla/compartidas según corresponda.

    `subject` (opcional) restringe a una única Subject exacta — nunca se
    mezclan preguntas de materias distintas al sumar contenido semilla o
    compartido.
    """
    visibility = Q(user=user)
    if include_seed:
        visibility |= Q(user__username=settings.SEED_CONTENT_USERNAME)

    shared_pairs = SubjectShare.objects.filter(
        is_active=True,
        group__memberships__user=user,
        group__memberships__status='accepted',
    ).exclude(shared_by=user)
    if subject is not None:
        shared_pairs = shared_pairs.filter(subject=subject)
    for owner_id, subject_id in shared_pairs.values_list('shared_by_id', 'subject_id').distinct():
        visibility |= Q(user_id=owner_id, subjects__id=subject_id)

    qs = Question.objects.filter(visibility)
    if subject is not None:
        qs = qs.filter(subjects=subject)
    return qs.distinct()


# "Elegible para armar examen": una pregunta generada por IA necesita haber
# sido aprobada explícitamente (ai_approved=True); una pregunta cargada a mano
# o por CSV/TXT (generated_by_ai=False) no pasa por ningún paso de aprobación
# — QuestionForm no expone ese campo — así que `ai_approved` le queda en NULL
# para siempre. Filtrar por `ai_approved=True` a secas (como hacía el código
# viejo) excluye para siempre todo el contenido cargado a mano del armado de
# examen. Usar esta condición en vez de `ai_approved=True` donde se arme el
# pool de preguntas utilizables.
EXAM_ELIGIBLE_Q = Q(generated_by_ai=False) | Q(ai_approved=True)

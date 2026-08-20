"""
Punto único para decidir qué preguntas puede ver/usar un usuario más allá de
las que él mismo cargó: contenido semilla del sistema
(`settings.SEED_CONTENT_USERNAME`, opt-in por request vía `include_seed`) y
preguntas compartidas por otros usuarios a través de un `SharingGroup` del que
el usuario es miembro aceptado (siempre activo, no es opt-in por request: es
una relación permanente que el propio usuario configuró en "Mis grupos").
"""
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from .models import (
    Career, ContentShare, ExamTemplate, FacultyV2, FormatoImpresion,
    InstitutionV2, Question, Rubric, Subject,
)


# Institución/Facultad/Carrera/Materia: catálogo institucional (curado por
# admin, visible para todos) MÁS el "espacio personal" del propio usuario —
# lo que él mismo creó y todavía no fue sumado al catálogo institucional
# (ver informe de rediseño / acuerdo de "personal space"). Nadie ve el
# espacio personal de otro usuario acá; eso es visibilidad, no lo confundir
# con la bandeja de administración, que sí ve todo para poder revisarlo.
def get_visible_institutions(user):
    return InstitutionV2.objects.filter(is_seed_demo=False).filter(
        Q(es_catalogo_institucional=True) | Q(created_by=user)
    )


def get_visible_faculties(user):
    return FacultyV2.objects.filter(is_active=True).filter(
        Q(es_catalogo_institucional=True) | Q(created_by=user)
    )


def get_visible_careers(user):
    return Career.objects.filter(is_seed_demo=False).filter(
        Q(es_catalogo_institucional=True) | Q(created_by=user)
    )


def get_visible_subjects(user):
    """Materias del catálogo institucional (curado por admin, visible para
    todos) más el espacio personal del propio usuario — lo que él mismo
    creó y todavía no fue sumado al catálogo institucional (ver informe de
    rediseño). El CONTENIDO de cada materia (Temas/Unidades/Preguntas)
    sigue siendo privado por separado, con su propio criterio.
    """
    return Subject.objects.filter(is_seed_demo=False).filter(
        Q(es_catalogo_institucional=True) | Q(created_by=user)
    )


def get_visible_questions(user, subject=None, include_seed=False):
    """Preguntas propias del usuario, más semilla/compartidas según corresponda.

    `subject` (opcional) restringe a una única Subject exacta — nunca se
    mezclan preguntas de materias distintas al sumar contenido semilla o
    compartido.
    """
    visibility = Q(user=user)
    if include_seed:
        visibility |= Q(user__username=settings.SEED_CONTENT_USERNAME)

    shared_pairs = ContentShare.objects.filter(
        kind='materia',
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


def _get_visible_via_content_share(model, kind, user, owner_field):
    """Objetos propios (por `owner_field`) más los compartidos con el usuario
    vía ContentShare(kind=kind) — mismo criterio para Rubric/ExamTemplate/
    FormatoImpresion, cada uno apuntado por GenericForeignKey (no hay
    accessor inverso directo, se resuelve juntando IDs compartidos primero).
    """
    shared_ids = ContentShare.objects.filter(
        kind=kind,
        is_active=True,
        content_type=ContentType.objects.get_for_model(model),
        group__memberships__user=user,
        group__memberships__status='accepted',
    ).exclude(shared_by=user).values_list('object_id', flat=True)

    return model.objects.filter(
        Q(**{owner_field: user}) | Q(id__in=list(shared_ids))
    ).distinct()


def get_visible_rubrics(user):
    """Rúbricas propias del usuario, más las compartidas con él por otros
    usuarios a través de un `SharingGroup` del que es miembro aceptado."""
    return _get_visible_via_content_share(Rubric, 'rubrica', user, 'created_by')


def get_visible_templates(user):
    """Plantillas de examen propias, más las compartidas por el grupo."""
    return _get_visible_via_content_share(ExamTemplate, 'plantilla', user, 'created_by')


def get_visible_formats(user):
    """Formatos de impresión propios, más los compartidos por el grupo."""
    return _get_visible_via_content_share(FormatoImpresion, 'formato', user, 'user')


# "Elegible para armar examen": una pregunta generada por IA necesita haber
# sido aprobada explícitamente (ai_approved=True); una pregunta cargada a mano
# o por CSV/TXT (generated_by_ai=False) no pasa por ningún paso de aprobación
# — QuestionForm no expone ese campo — así que `ai_approved` le queda en NULL
# para siempre. Filtrar por `ai_approved=True` a secas (como hacía el código
# viejo) excluye para siempre todo el contenido cargado a mano del armado de
# examen. Usar esta condición en vez de `ai_approved=True` donde se arme el
# pool de preguntas utilizables.
EXAM_ELIGIBLE_Q = Q(generated_by_ai=False) | Q(ai_approved=True)

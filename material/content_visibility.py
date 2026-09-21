"""
Punto único para decidir qué preguntas puede ver/usar un usuario más allá de
las que él mismo cargó: contenido semilla del sistema
(`settings.SEED_CONTENT_USERNAME`, opt-in por request vía `include_seed`) y
preguntas compartidas por otros usuarios a través de un `SharingGroup` del que
el usuario es miembro aceptado (siempre activo, no es opt-in por request: es
una relación permanente que el propio usuario configuró en "Mis grupos").
"""
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Exists, OuterRef, Q

from .models import (
    Career, ContentShare, ExamTemplate, Favorite, FacultyV2, FormatoImpresion,
    InstitutionV2, Profile, Question, Rubric, Subject,
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


def order_subjects_by_relevance(user, subjects_qs):
    """Reordena una queryset de Subject para que lo más relevante para ESTE
    usuario aparezca primero — favoritas, después las que ya tiene con
    preguntas propias cargadas, y recién después el resto por orden
    alfabético. Pensado para checklists largos de materias (editar
    pregunta, cargar pregunta a mano — reportado en Modo Testing: "mostrar
    cientos de materias posibles no sirve") donde poder buscar por texto no
    alcanza si además no se sabe por dónde arrancar. Reusable en cualquier
    pantalla con el mismo problema: no asume nada del widget (checklist,
    dropdown, lo que sea), solo reordena la queryset — el HTML sigue
    saliendo en ese mismo orden porque los widgets de selección iteran la
    queryset tal cual."""
    subject_ct = ContentType.objects.get_for_model(Subject)
    is_favorite = Exists(
        Favorite.objects.filter(user=user, content_type=subject_ct, object_id=OuterRef('pk'))
    )
    has_content = Exists(
        Question.objects.filter(user=user, subjects=OuterRef('pk'))
    )
    return subjects_qs.annotate(
        _is_favorite=is_favorite, _has_content=has_content,
    ).order_by('-_is_favorite', '-_has_content', 'name')


def count_relevant_subjects(user, subjects_qs):
    """Cuántas de `subjects_qs` son "de este usuario" en el mismo sentido
    que `order_subjects_by_relevance` (favoritas o con preguntas propias
    cargadas) — pensado para que el frontend sepa dónde termina de verdad
    lo relevante, en vez de cortar en una posición fija arbitraria (mostrar
    siempre top-8 aunque solo 2 sean relevantes de verdad no es mejor que
    mostrar todo)."""
    subject_ct = ContentType.objects.get_for_model(Subject)
    is_favorite = Exists(
        Favorite.objects.filter(user=user, content_type=subject_ct, object_id=OuterRef('pk'))
    )
    has_content = Exists(
        Question.objects.filter(user=user, subjects=OuterRef('pk'))
    )
    return subjects_qs.annotate(
        _is_favorite=is_favorite, _has_content=has_content,
    ).filter(Q(_is_favorite=True) | Q(_has_content=True)).count()


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


def get_visible_professors(user):
    """Candidatos a "Docente" de un examen/plantilla.

    Un admin (o superuser) arma exámenes/plantillas en nombre de cualquier
    docente real del sistema — mismo criterio de "admin" que
    `views.is_admin` (is_superuser OR Profile.role == 'admin'; no se puede
    importar esa función acá por el import circular views→content_visibility,
    así que se repite la condición). Un usuario común solo puede quedar
    como su propio profesor: antes esto era
    `User.objects.filter(profile__role__in=[...])` sin distinción de rol, que
    en los hechos listaba TODAS las cuentas del sistema (incluidas las de
    prueba/QA de otros usuarios) para cualquiera que abriera el formulario.
    """
    is_admin_user = user.is_superuser
    if not is_admin_user:
        try:
            is_admin_user = user.profile.role == 'admin'
        except Profile.DoesNotExist:
            is_admin_user = False

    base = User.objects.filter(is_active=True).exclude(profile__is_training_account=True)
    if is_admin_user:
        return base
    return base.filter(id=user.id)


# "Elegible para armar examen": una pregunta generada por IA necesita haber
# sido aprobada explícitamente (ai_approved=True); una pregunta cargada a mano
# o por CSV/TXT (generated_by_ai=False) no pasa por ningún paso de aprobación
# — QuestionForm no expone ese campo — así que `ai_approved` le queda en NULL
# para siempre. Filtrar por `ai_approved=True` a secas (como hacía el código
# viejo) excluye para siempre todo el contenido cargado a mano del armado de
# examen. Usar esta condición en vez de `ai_approved=True` donde se arme el
# pool de preguntas utilizables.
EXAM_ELIGIBLE_Q = Q(generated_by_ai=False) | Q(ai_approved=True)

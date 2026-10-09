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
    CareerSubject, InstitutionV2, LearningOutcome, Profile, Question, Rubric, Subject,
    Subtopic, Topic,
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


def get_visible_learning_outcomes(user):
    """Mismo mecanismo de espacio personal que institución/facultad/carrera/
    materia (ver get_visible_subjects) — un Resultado de Aprendizaje
    institucional (curado por admin) es visible para todos; uno personal
    solo para quien lo cargó, hasta que un admin lo sume al catálogo o lo
    fusione con uno existente. No hace falta excluir contenido semilla acá
    aparte: los RA semilla cuelgan de una Subject con is_seed_demo=True, que
    ya queda afuera de get_visible_subjects — cualquier caller que combine
    esto con `career_subject__subject__in=get_visible_subjects(user)` (o
    equivalente) los excluye de forma transitiva."""
    return LearningOutcome.objects.filter(
        Q(es_catalogo_institucional=True) | Q(created_by=user)
    )


def _is_admin_user(user):
    """Misma condición que `views.is_admin` (no se puede importar por el import
    circular views→content_visibility)."""
    if user.is_superuser:
        return True
    try:
        return user.profile.role == 'admin'
    except Profile.DoesNotExist:
        return False


def get_visible_topics(user, subject=None, career_subject=None):
    """Tópicos que este usuario puede ver/usar.

    Mismo criterio de espacio personal vs. catálogo que el resto del catálogo
    (ver get_visible_learning_outcomes): uno del catálogo institucional
    (unificado, lo administra un admin) lo ven todos; uno personal solo quien
    lo creó — más los de un docente que compartió con él esa materia por un
    grupo de confianza (si no, las preguntas compartidas llegarían con un
    tópico que el destinatario no puede ver ni elegir).

    `career_subject` (una CareerSubject o su pk) acota a esa carrera-materia:
    los de esa carrera más los que no tienen carrera asignada. Sin ese dato
    (flujos que todavía no saben la carrera) se devuelven todos los visibles
    de la materia, como antes de existir el campo.
    """
    visibility = Q(es_catalogo_institucional=True) | Q(created_by=user)
    shared_pairs = ContentShare.objects.filter(
        kind='materia',
        is_active=True,
        group__memberships__user=user,
        group__memberships__status='accepted',
    ).exclude(shared_by=user)
    if subject is not None:
        shared_pairs = shared_pairs.filter(subject=subject)
    for owner_id, subject_id in shared_pairs.values_list('shared_by_id', 'subject_id').distinct():
        visibility |= Q(created_by_id=owner_id, subject_id=subject_id)

    qs = Topic.objects.filter(visibility)
    if subject is not None:
        qs = qs.filter(subject=subject)
    if career_subject is not None:
        qs = qs.filter(Q(career_subject=career_subject) | Q(career_subject__isnull=True))
    return qs.distinct()


def get_visible_subtopics(user, topic=None):
    """Sub-tópicos que el usuario puede ver: los de tópicos que ve (ver
    get_visible_topics) y que son del catálogo, propios o de un docente que le
    compartió la materia por un grupo de confianza."""
    shared_owner_ids = ContentShare.objects.filter(
        kind='materia', is_active=True,
        group__memberships__user=user, group__memberships__status='accepted',
    ).exclude(shared_by=user).values_list('shared_by_id', flat=True)
    qs = Subtopic.objects.filter(topic__in=get_visible_topics(user)).filter(
        Q(es_catalogo_institucional=True) | Q(created_by=user) | Q(created_by_id__in=list(shared_owner_ids))
    )
    if topic is not None:
        qs = qs.filter(topic=topic)
    return qs.distinct()


def subtopic_creation_scope(user, topic):
    """(es_catalogo_institucional, created_by) para un sub-tópico NUEVO de
    `topic`: del catálogo solo si lo crea un admin sobre un tópico del
    catálogo; personal en cualquier otro caso."""
    return (bool(_is_admin_user(user) and topic.es_catalogo_institucional), user)


def get_or_create_subtopic(user, topic, name):
    """El sub-tópico `name` que `user` ya ve en `topic`, o uno nuevo según su
    alcance. Reemplaza a `Subtopic.objects.get_or_create(name=..., topic=...)`.
    Devuelve (sub-tópico, creado)."""
    existente = get_visible_subtopics(user, topic=topic).filter(name__iexact=name).order_by('-es_catalogo_institucional', 'id').first()
    if existente is not None:
        return existente, False
    es_catalogo, creador = subtopic_creation_scope(user, topic)
    return Subtopic.objects.create(
        name=name, topic=topic, es_catalogo_institucional=es_catalogo, created_by=creador,
    ), True


def topic_creation_scope(user, subject):
    """(es_catalogo_institucional, created_by) para un tópico NUEVO de `subject`.

    Un admin sobre una materia del catálogo crea tópicos del catálogo; en
    cualquier otro caso (un docente sobre una materia del catálogo, o el
    dueño de una materia personal) el tópico es personal: lo ve solo quien lo
    crea y puede proponerlo al catálogo. Mismo criterio que los resultados de
    aprendizaje."""
    return (bool(_is_admin_user(user) and subject.es_catalogo_institucional), user)


def resolve_career_subject(subject, career_id=None):
    """La CareerSubject de `subject` para la carrera `career_id`.

    Sin carrera indicada: si la materia está en UNA sola carrera, esa es la
    única posible y se usa; si está en varias (o en ninguna), None — el
    llamador no sabe a cuál se refiere y se queda con "todas". Con una carrera
    en la que la materia no está, también None."""
    if career_id and str(career_id).isdigit():
        return CareerSubject.objects.filter(subject=subject, career_id=int(career_id)).first()
    unicas = list(CareerSubject.objects.filter(subject=subject)[:2])
    return unicas[0] if len(unicas) == 1 else None


def get_or_create_topic(user, subject, name, career_subject=None, importance=3):
    """El tópico de nombre `name` visible para `user` en `subject` (y en la
    carrera indicada, si se indicó), o uno nuevo creado según su alcance.

    Reemplaza a `Topic.objects.get_or_create(name=..., subject=...)`: ese
    atajo reutilizaba el tópico de CUALQUIER docente con el mismo nombre y,
    si no existía, lo creaba sin dueño ni alcance. Devuelve (tópico, creado)."""
    existente = get_visible_topics(user, subject=subject, career_subject=career_subject).filter(
        name__iexact=name,
    ).order_by('-es_catalogo_institucional', 'id').first()
    if existente is not None:
        return existente, False
    es_catalogo, creador = topic_creation_scope(user, subject)
    topic = Topic.objects.create(
        name=name, subject=subject, career_subject=career_subject, importance=importance,
        es_catalogo_institucional=es_catalogo, created_by=creador,
    )
    return topic, True


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


def get_oral_questions(user, subject):
    """Preguntas que un cuestionario oral de `subject` puede usar: las propias
    del docente más las que le compartieron por un grupo de confianza, y solo
    las elegibles (aprobadas), igual que el examen escrito.

    Antes el oral solo tomaba las propias (`user=...`) y cualquiera, aprobada o
    no: el módulo es anterior al sistema de compartir (content_visibility) y
    nunca se actualizó. Sus tópicos y subtópicos llegan con las preguntas
    (ver get_visible_topics)."""
    return get_visible_questions(user, subject=subject).filter(EXAM_ELIGIBLE_Q)


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

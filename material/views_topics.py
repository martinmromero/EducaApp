"""ABM de tópicos y sub-tópicos, dentro de la ficha de la materia.

Un tópico pertenece a la asociación carrera-materia (Topic.career_subject) y
sigue el mismo criterio de espacio personal vs. catálogo que el resto del
catálogo (ver content_visibility.get_visible_topics):

- Materia personal: los tópicos son del dueño.
- Materia del catálogo: los tópicos del catálogo los administra un admin; un
  docente que necesita otro crea uno personal (solo lo ve él) y puede
  proponerlo al catálogo. Un admin lo aprueba, lo rechaza o lo fusiona con uno
  existente desde la bandeja de solicitudes.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from .content_visibility import (
    get_visible_subjects, get_visible_subtopics, get_visible_topics,
    subtopic_creation_scope, topic_creation_scope,
)
from .models import CareerSubject, CatalogRequest, Question, Subtopic, Topic
from .views import is_admin

TAG = 'materias'


def _volver(subject):
    return redirect(reverse('material:subject_detail', kwargs={'pk': subject.pk}) + '#topicos')


def puede_editar_topico(user, topic):
    """Admin, o el dueño de un tópico personal. Los del catálogo son del admin."""
    return is_admin(user) or (topic.created_by_id == user.id and not topic.es_catalogo_institucional)


def puede_editar_subtopico(user, subtopic):
    return is_admin(user) or (subtopic.created_by_id == user.id and not subtopic.es_catalogo_institucional)


def _career_subject_from_post(request, subject):
    """La carrera-materia elegida en el formulario (debe ser de esta materia),
    o None si no se eligió ninguna."""
    raw = (request.POST.get('career_subject_id') or '').strip()
    if not raw.isdigit():
        return None
    return CareerSubject.objects.filter(pk=int(raw), subject=subject).first()


def _topico_visible_o_404(request, pk):
    return get_object_or_404(get_visible_topics(request.user), pk=pk)


@login_required
@require_POST
def topic_create(request, subject_id):
    subject = get_object_or_404(get_visible_subjects(request.user), pk=subject_id)
    name = (request.POST.get('name') or '').strip()
    if not name:
        messages.error(request, 'El nombre del tópico no puede estar vacío.', extra_tags=TAG)
        return _volver(subject)

    career_subject = _career_subject_from_post(request, subject)
    if get_visible_topics(request.user, subject=subject, career_subject=career_subject).filter(
        name__iexact=name,
    ).exists():
        messages.error(request, f'Ya existe un tópico "{name}" en esta materia.', extra_tags=TAG)
        return _volver(subject)

    es_catalogo, creador = topic_creation_scope(request.user, subject)
    try:
        Topic.objects.create(
            name=name, subject=subject, career_subject=career_subject, importance=3,
            es_catalogo_institucional=es_catalogo, created_by=creador,
        )
    except IntegrityError:
        messages.error(request, f'Ya existe un tópico "{name}" en esta materia.', extra_tags=TAG)
        return _volver(subject)

    if es_catalogo:
        messages.success(request, f'Tópico "{name}" agregado al catálogo.', extra_tags=TAG)
    else:
        messages.success(
            request,
            f'Tópico "{name}" agregado al espacio personal. Si sirve para todos, se puede proponer al catálogo.',
            extra_tags=TAG,
        )
    return _volver(subject)


@login_required
@require_POST
def topic_update(request, pk):
    topic = _topico_visible_o_404(request, pk)
    if not puede_editar_topico(request.user, topic):
        messages.error(request, 'Este tópico es del catálogo: lo administra un administrador.', extra_tags=TAG)
        return _volver(topic.subject)

    name = (request.POST.get('name') or '').strip()
    if not name:
        messages.error(request, 'El nombre del tópico no puede estar vacío.', extra_tags=TAG)
        return _volver(topic.subject)
    career_subject = _career_subject_from_post(request, topic.subject)

    repetido = get_visible_topics(request.user, subject=topic.subject, career_subject=career_subject).filter(
        name__iexact=name,
    ).exclude(pk=topic.pk).exists()
    if repetido:
        messages.error(request, f'Ya existe un tópico "{name}" en esta materia.', extra_tags=TAG)
        return _volver(topic.subject)

    topic.name = name
    topic.career_subject = career_subject
    try:
        topic.save(update_fields=['name', 'career_subject'])
    except IntegrityError:
        messages.error(request, f'Ya existe un tópico "{name}" en esta materia.', extra_tags=TAG)
        return _volver(topic.subject)
    messages.success(request, 'Tópico actualizado.', extra_tags=TAG)
    return _volver(topic.subject)


@login_required
@require_POST
def topic_delete(request, pk):
    topic = _topico_visible_o_404(request, pk)
    subject = topic.subject
    if not puede_editar_topico(request.user, topic):
        messages.error(request, 'Este tópico es del catálogo: lo administra un administrador.', extra_tags=TAG)
        return _volver(subject)

    preguntas = Question.objects.filter(topic=topic).count()
    nombre = topic.name
    topic.delete()
    if preguntas == 0:
        aviso = ''
    elif preguntas == 1:
        aviso = ' 1 pregunta quedó sin tópico.'
    else:
        aviso = f' {preguntas} preguntas quedaron sin tópico.'
    messages.success(request, f'Tópico "{nombre}" eliminado.{aviso}', extra_tags=TAG)
    return _volver(subject)


@login_required
@require_POST
def topic_propose(request, pk):
    """Propone al catálogo un tópico personal propio."""
    topic = _topico_visible_o_404(request, pk)
    subject = topic.subject
    if topic.es_catalogo_institucional or topic.created_by_id != request.user.id:
        messages.error(request, 'Solo se puede proponer un tópico personal propio.', extra_tags=TAG)
        return _volver(subject)
    if not subject.es_catalogo_institucional:
        messages.error(
            request,
            'La materia todavía es personal: primero hay que proponer la materia al catálogo.',
            extra_tags=TAG,
        )
        return _volver(subject)
    if CatalogRequest.objects.filter(tipo='topico', topico=topic, estado='pendiente').exists():
        messages.info(request, 'Este tópico ya está propuesto: falta la respuesta de un administrador.', extra_tags=TAG)
        return _volver(subject)

    cs = topic.career_subject
    CatalogRequest.objects.create(
        tipo='topico', nombre_propuesto=topic.name, topico=topic, materia=subject,
        carrera=cs.career if cs else None,
        justificacion=(request.POST.get('justificacion') or '').strip(),
        solicitado_por=request.user,
    )
    messages.success(
        request,
        f'Tópico "{topic.name}" propuesto al catálogo. Se sigue usando mientras tanto; el resultado se ve en "Mis agregados".',
        extra_tags=TAG,
    )
    return _volver(subject)


@login_required
@require_POST
def subtopic_create(request, topic_id):
    topic = _topico_visible_o_404(request, topic_id)
    name = (request.POST.get('name') or '').strip()
    if not name:
        messages.error(request, 'El nombre del sub-tópico no puede estar vacío.', extra_tags=TAG)
        return _volver(topic.subject)
    if get_visible_subtopics(request.user, topic=topic).filter(name__iexact=name).exists():
        messages.error(request, f'Ya existe un sub-tópico "{name}" en este tópico.', extra_tags=TAG)
        return _volver(topic.subject)
    es_catalogo, creador = subtopic_creation_scope(request.user, topic)
    Subtopic.objects.create(name=name, topic=topic, es_catalogo_institucional=es_catalogo, created_by=creador)
    messages.success(request, f'Sub-tópico "{name}" agregado.', extra_tags=TAG)
    return _volver(topic.subject)


@login_required
@require_POST
def subtopic_update(request, pk):
    subtopic = get_object_or_404(get_visible_subtopics(request.user), pk=pk)
    subject = subtopic.topic.subject
    if not puede_editar_subtopico(request.user, subtopic):
        messages.error(request, 'Este sub-tópico es del catálogo: lo administra un administrador.', extra_tags=TAG)
        return _volver(subject)
    name = (request.POST.get('name') or '').strip()
    if not name:
        messages.error(request, 'El nombre del sub-tópico no puede estar vacío.', extra_tags=TAG)
        return _volver(subject)
    if get_visible_subtopics(request.user, topic=subtopic.topic).filter(name__iexact=name).exclude(pk=subtopic.pk).exists():
        messages.error(request, f'Ya existe un sub-tópico "{name}" en este tópico.', extra_tags=TAG)
        return _volver(subject)
    subtopic.name = name
    subtopic.save(update_fields=['name'])
    messages.success(request, 'Sub-tópico actualizado.', extra_tags=TAG)
    return _volver(subject)


@login_required
@require_POST
def subtopic_delete(request, pk):
    subtopic = get_object_or_404(get_visible_subtopics(request.user), pk=pk)
    subject = subtopic.topic.subject
    if not puede_editar_subtopico(request.user, subtopic):
        messages.error(request, 'Este sub-tópico es del catálogo: lo administra un administrador.', extra_tags=TAG)
        return _volver(subject)
    nombre = subtopic.name
    subtopic.delete()
    messages.success(request, f'Sub-tópico "{nombre}" eliminado.', extra_tags=TAG)
    return _volver(subject)


def topicos_para_ficha(user, subject, career_subjects):
    """Arma, para la ficha de la materia, los tópicos que `user` ve agrupados
    por carrera-materia, más los que no tienen carrera asignada.

    Cada tópico trae sus sub-tópicos visibles y qué puede hacer `user` con él
    (editar, proponerlo) para que la plantilla no tenga que decidirlo."""
    topics = list(get_visible_topics(user, subject=subject).order_by('name'))
    subtopics = {}
    for sub in get_visible_subtopics(user).filter(topic__in=topics).order_by('name'):
        sub.puede_editar = puede_editar_subtopico(user, sub)
        subtopics.setdefault(sub.topic_id, []).append(sub)
    pendientes = set(CatalogRequest.objects.filter(
        tipo='topico', estado='pendiente', topico__in=topics,
    ).values_list('topico_id', flat=True))
    for topic in topics:
        topic.subs = subtopics.get(topic.pk, [])
        topic.puede_editar = puede_editar_topico(user, topic)
        topic.propuesto = topic.pk in pendientes
        topic.puede_proponer = (
            not topic.es_catalogo_institucional and topic.created_by_id == user.id
            and subject.es_catalogo_institucional and not topic.propuesto
        )
    por_carrera = [
        {'career_subject': cs, 'topics': [t for t in topics if t.career_subject_id == cs.pk]}
        for cs in career_subjects
    ]
    sin_carrera = [t for t in topics if t.career_subject_id is None]
    return por_carrera, sin_carrera

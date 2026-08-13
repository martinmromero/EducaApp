"""
Área de Pruebas — cuenta espejo por docente.

Punto único para crear, poblar, vaciar y resetear la cuenta de práctica
emparejada con cada usuario real (ver TrainingAccountLink en models.py).
"Entrar" al Área de Pruebas es un login() real como la cuenta espejo (ver
material/training_views.py), no un flag de sesión que cambie el dueño de
cada consulta — por eso este módulo nunca toca request/session, solo
maneja los objetos de dominio.

Se llama SOLO desde una acción explícita del usuario (o de un admin
reseteando una cuenta ya existente) — nunca especulativamente ni en lote,
para no inflar la base de datos con cuentas que nadie pidió.
"""
import datetime
import logging
import threading
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import IntegrityError, connection
from django.utils import timezone

logger = logging.getLogger(__name__)

# "Siempre una copia de Área de Pruebas lista sin asignar" (ver
# ensure_spare_pool): cuántos repuestos completamente clonados se
# mantienen en el pool en todo momento. En 1 alcanza para que
# entrar/resetear sea instantáneo para el caso común (un solo docente
# haciéndolo a la vez) — subir esto es tan simple como cambiar el número,
# no hay nada más codificado contra "1" en particular.
SPARE_POOL_TARGET_SIZE = 1

from .models import (
    CampusV2,
    Career,
    Contenido,
    Exam,
    ExamRubric,
    ExamTemplate,
    ExamVersionBatch,
    FacultyV2,
    Favorite,
    FormatoImpresion,
    InstitutionSubject,
    InstitutionV2,
    LearningOutcome,
    OralExamSet,
    Question,
    Rubric,
    RubricCell,
    RubricCriterion,
    RubricLevel,
    Subject,
    Topic,
    TrainingAccountLink,
    UserInstitution,
)

# Campos de Exam que se copian tal cual del examen semilla al clon — todo lo
# que no depende de qué Subject/Topic/Question puntual se haya clonado.
_EXAM_COPY_FIELDS = [
    'instructions', 'duration_minutes', 'year', 'exam_mode', 'exam_group', 'shift',
    'resolution_time', 'topics_to_evaluate',
    'institution_name', 'faculty_name', 'campus_name', 'career_name',
    'topics_snapshot', 'outcomes_snapshot', 'date_str', 'is_published',
]


def _seed_user():
    username = getattr(settings, 'SEED_CONTENT_USERNAME', 'educaapp_demo')
    return User.objects.get(username=username)


def get_or_create_training_account(real_user):
    """Devuelve la cuenta del Área de Pruebas de este docente. Si es la
    primera vez, toma un repuesto ya clonado del pool (instantáneo) — si
    no hay ninguno disponible en este momento, cae al camino sincrónico de
    siempre (clonar de cero acá mismo). Cualquiera de los dos casos
    dispara una reposición del pool en background."""
    link = TrainingAccountLink.objects.filter(real_user=real_user).select_related('training_user').first()
    if link:
        return link.training_user

    spare = _find_spare_training_account()
    if spare is not None:
        try:
            TrainingAccountLink.objects.create(real_user=real_user, training_user=spare)
            training_user = spare
        except IntegrityError:
            # Otro request en simultáneo se llevó este mismo repuesto justo
            # antes — no hay repuesto libre después de todo, cae al camino
            # sincrónico.
            training_user = _provision_and_link(real_user)
    else:
        training_user = _provision_and_link(real_user)

    _apply_real_user_preferences(training_user, real_user)
    _replenish_pool_async()
    return training_user


def _provision_and_link(real_user):
    training_user = _provision_training_account(f'training__{real_user.pk}')
    TrainingAccountLink.objects.create(real_user=real_user, training_user=training_user)
    return training_user


def _provision_training_account(username):
    """Crea una cuenta de Área de Pruebas completa y autocontenida (User +
    Profile + clon del contenido semilla) sin emparejarla con nadie
    todavía — el llamador decide si queda como repuesto en el pool o se
    empareja de una con un docente real."""
    training_user = User.objects.create(username=username, is_active=True)
    training_user.set_unusable_password()
    training_user.save()

    profile = training_user.profile  # ya existe por la señal post_save de User
    profile.role = 'user'
    profile.is_training_account = True
    profile.onboarding_completed = True
    profile.save(update_fields=['role', 'is_training_account', 'onboarding_completed'])

    clone_seed_content_into(training_user)
    return training_user


def _apply_real_user_preferences(training_user, real_user):
    """El tema visual se copia recién al asignar (no al provisionar el
    repuesto): un repuesto en el pool todavía no sabe qué docente real lo
    va a reclamar."""
    try:
        training_user.profile.visual_theme = real_user.profile.visual_theme
        training_user.profile.save(update_fields=['visual_theme'])
    except Exception:
        pass


def _find_spare_training_account():
    """Una cuenta de Área de Pruebas ya clonada pero todavía sin
    emparejar con ningún docente (no tiene fila en TrainingAccountLink),
    o None si el pool está vacío en este momento."""
    return User.objects.filter(
        profile__is_training_account=True,
    ).exclude(
        id__in=TrainingAccountLink.objects.values('training_user_id'),
    ).order_by('id').first()


def _spare_pool_size():
    return User.objects.filter(
        profile__is_training_account=True,
    ).exclude(
        id__in=TrainingAccountLink.objects.values('training_user_id'),
    ).count()


def ensure_spare_pool(target_size=SPARE_POOL_TARGET_SIZE):
    """Repone el pool de repuestos hasta `target_size`. Sincrónico a
    propósito — pensado para llamarse desde un comando de management (deploy)
    o encolado en un thread aparte para no bloquear un request (ver
    `_replenish_pool_async`). Devuelve cuántos repuestos nuevos creó."""
    missing = target_size - _spare_pool_size()
    created = 0
    for _ in range(max(missing, 0)):
        _provision_training_account(f'training_spare__{uuid.uuid4().hex[:12]}')
        created += 1
    return created


def _replenish_pool_async():
    """Fire-and-forget: si el pool quedó corto, arranca un thread aparte
    para reponerlo sin demorar la respuesta al usuario. Si el thread no
    llega a terminar (reciclado del worker, excepción, etc.) no pasa nada
    grave — es una optimización, no una dependencia dura: la próxima vez
    que alguien entre/resetee y no encuentre repuesto, cae sola al camino
    sincrónico de siempre (ver get_or_create_training_account/
    reset_training_account)."""
    def _worker():
        try:
            ensure_spare_pool()
        except Exception:
            logger.exception('No se pudo reponer en background el pool del Área de Pruebas.')
        finally:
            connection.close()  # el thread no comparte la conexión del request
    threading.Thread(target=_worker, daemon=True).start()


def _delete_training_account_async(training_user_id):
    """Fire-and-forget: borra en background una cuenta de Área de Pruebas
    que ya quedó desvinculada (ver reset_training_account) — se le pasa
    el ID, no el objeto, porque un objeto obtenido con la conexión del
    request no es seguro de reusar desde otro thread."""
    def _worker():
        try:
            training_user = User.objects.filter(pk=training_user_id).first()
            if training_user is not None:
                delete_all_content_for_training_user(training_user)
                training_user.delete()
        except Exception:
            logger.exception('No se pudo borrar en background la cuenta vieja del Área de Pruebas.')
        finally:
            connection.close()
    threading.Thread(target=_worker, daemon=True).start()


def clone_seed_content_into(training_user):
    """Clona el contenido semilla (rúbricas, contenidos, exámenes,
    cuestionarios orales, plantillas incluidos) en propiedad de
    training_user. Cada materia semilla se clona en una fila de Subject
    aparte (created_by=training_user) — nunca se reutiliza ni se apunta a
    la fila semilla original."""
    seed_user = _seed_user()

    # Las instituciones en sí son públicas/compartidas por diseño (no se
    # clonan), pero la lista "mis instituciones" SÍ es personal por usuario
    # (UserInstitution) — sin esto, /instituciones-v2/ le queda vacía a la
    # cuenta de práctica aunque sus plantillas de examen ya referencien
    # estas mismas instituciones semilla. Idempotente (unique_together),
    # seguro de llamar de nuevo en cada reset.
    for institution in InstitutionV2.objects.filter(is_seed_demo=True):
        UserInstitution.objects.get_or_create(user=training_user, institution=institution)

    for seed_subject in Subject.objects.filter(is_seed_demo=True):
        subject = Subject.objects.create(
            name=seed_subject.name, is_seed_demo=False, created_by=training_user,
        )

        topic_map = {}
        for topic in Topic.objects.filter(subject=seed_subject):
            topic_map[topic.id] = Topic.objects.create(
                subject=subject, name=topic.name, importance=topic.importance,
            )
        topics_list = list(topic_map.values())

        for outcome in LearningOutcome.objects.filter(subject=seed_subject):
            LearningOutcome.objects.create(subject=subject, description=outcome.description)

        question_map = {}
        for question in Question.objects.filter(subjects=seed_subject, user=seed_user):
            new_question = Question.objects.create(
                user=training_user,
                topic=topic_map.get(question.topic_id),
                question_type=question.question_type,
                question_text=question.question_text,
                answer_text=question.answer_text,
                options_json=question.options_json,
                difficulty=question.difficulty,
                bloom_level=question.bloom_level,
                ai_approved=True,
            )
            new_question.subjects.add(subject)
            question_map[question.id] = new_question

        self_contenido = Contenido.objects.filter(subjects=seed_subject, uploaded_by=seed_user).first()
        if self_contenido:
            contenido = Contenido.objects.create(
                title=self_contenido.title,
                uploaded_by=training_user,
                author=self_contenido.author,
                publisher=self_contenido.publisher,
                year=self_contenido.year,
                edition=self_contenido.edition,
                pages=self_contenido.pages,
                isbn=self_contenido.isbn,
                chapter=self_contenido.chapter,
                file_deleted_at=timezone.now() - datetime.timedelta(days=30),
            )
            contenido.subjects.add(subject)
            if question_map:
                Question.objects.filter(pk__in=[q.pk for q in question_map.values()]).update(contenido=contenido)

        rubric = _clone_rubric(seed_subject, seed_user, training_user)
        individual_exam = _clone_individual_exam(seed_subject, seed_user, subject, training_user, topics_list, question_map)
        if individual_exam and rubric:
            ExamRubric.objects.create(exam=individual_exam, rubric=rubric, show_in_exam=True, position=0)
        _clone_batch_exam(seed_subject, seed_user, subject, training_user, topics_list, question_map)
        _clone_oral_exam(seed_subject, seed_user, subject, training_user, topics_list)
        _clone_exam_template(seed_subject, subject, training_user)


def _clone_rubric(seed_subject, seed_user, training_user):
    title = f'Rúbrica de evaluación — {seed_subject.name}'
    seed_rubric = Rubric.objects.filter(title=title, created_by=seed_user).first()
    if not seed_rubric:
        return None

    rubric = Rubric.objects.create(title=title, created_by=training_user)
    level_map = {}
    for level in seed_rubric.levels.all():
        level_map[level.id] = RubricLevel.objects.create(rubric=rubric, label=level.label, order=level.order)
    for criterion in seed_rubric.criteria.all():
        new_criterion = RubricCriterion.objects.create(rubric=rubric, name=criterion.name, order=criterion.order)
        for cell in criterion.cells.all():
            RubricCell.objects.create(
                criterion=new_criterion, level=level_map[cell.level_id], description=cell.description,
            )
    return rubric


def _exam_field_copy(seed_exam):
    return {field: getattr(seed_exam, field) for field in _EXAM_COPY_FIELDS}


def _clone_individual_exam(seed_subject, seed_user, subject, training_user, topics_list, question_map):
    seed_exam = Exam.objects.filter(
        subject=seed_subject, created_by=seed_user, version_batch__isnull=True, exam_type='final',
    ).first()
    if not seed_exam:
        return None

    exam = Exam.objects.create(
        title=seed_exam.title,
        exam_type=seed_exam.exam_type,
        professor=training_user,
        created_by=training_user,
        subject=subject,
        subject_name=subject.name,
        **_exam_field_copy(seed_exam),
    )
    exam.topics.set(topics_list)
    mapped = [question_map[q.id] for q in seed_exam.questions.all() if q.id in question_map]
    exam.questions.set(mapped)
    return exam


def _clone_batch_exam(seed_subject, seed_user, subject, training_user, topics_list, question_map):
    seed_batch = ExamVersionBatch.objects.filter(subject=seed_subject, created_by=seed_user).first()
    if not seed_batch:
        return

    batch = ExamVersionBatch.objects.create(
        name=seed_batch.name,
        created_by=training_user,
        subject=subject,
        institution_name=seed_batch.institution_name,
        exam_type=seed_batch.exam_type,
        semester=seed_batch.semester,
        year=seed_batch.year,
        version_count=seed_batch.version_count,
        questions_per_version=seed_batch.questions_per_version,
    )
    for seed_version in Exam.objects.filter(version_batch=seed_batch).order_by('version_number'):
        version = Exam.objects.create(
            title=seed_version.title,
            exam_type=seed_version.exam_type,
            partial_number=seed_version.partial_number,
            version_batch=batch,
            version_number=seed_version.version_number,
            professor=training_user,
            created_by=training_user,
            subject=subject,
            subject_name=subject.name,
            **_exam_field_copy(seed_version),
        )
        version.topics.set(topics_list)
        mapped = [question_map[q.id] for q in seed_version.questions.all() if q.id in question_map]
        version.questions.set(mapped)


def _clone_oral_exam(seed_subject, seed_user, subject, training_user, topics_list):
    seed_oral = OralExamSet.objects.filter(subject=seed_subject, user=seed_user).first()
    if not seed_oral:
        return

    oral_exam = OralExamSet.objects.create(
        name=seed_oral.name,
        subject=subject,
        user=training_user,
        num_groups=seed_oral.num_groups,
        students_per_group=seed_oral.students_per_group,
        questions_per_student=seed_oral.questions_per_student,
        total_students=seed_oral.total_students,
    )
    oral_exam.topics.set(topics_list)
    # Reusa el generador real (mismo algoritmo que create_oral_exam() para un
    # cuestionario de verdad) — al filtrar por user=training_user y
    # topic__in=<tópicos clonados>, arma la asignación solo con las
    # preguntas ya clonadas de esta materia.
    from .views import generate_oral_exam_questions
    try:
        generate_oral_exam_questions(oral_exam)
    except ValueError:
        pass


def _clone_exam_template(seed_subject, subject, training_user):
    inst_subject = InstitutionSubject.objects.filter(subject=seed_subject).select_related('institution').first()
    if not inst_subject:
        return
    institution = inst_subject.institution
    faculty = FacultyV2.objects.filter(institution=institution).first()
    campus = CampusV2.objects.filter(institution=institution).first()
    career = Career.objects.filter(subjects=seed_subject).first()
    if not faculty or not career:
        return

    outcomes_snapshot = list(LearningOutcome.objects.filter(subject=subject).values_list('description', flat=True))

    template = ExamTemplate.objects.create(
        institution=institution,
        faculty=faculty,
        career=career,
        campus=campus,
        subject=subject,
        professor=training_user,
        year=timezone.now().year,
        exam_type='final',
        exam_mode='presencial',
        shift='manana',
        notes_and_recommendations='Revisar los conceptos fundamentales de la materia antes del examen.',
        created_by=training_user,
        institution_name_snapshot=institution.name,
        faculty_name_snapshot=faculty.name,
        campus_name_snapshot=campus.name if campus else '',
        career_name_snapshot=career.name,
        subject_name_snapshot=subject.name,
        outcomes_snapshot=outcomes_snapshot,
    )
    template.learning_outcomes.set(LearningOutcome.objects.filter(subject=subject))


def delete_all_content_for_training_user(training_user):
    """Borra todo lo que la cuenta de práctica haya generado — nunca toca
    nada de la cuenta real emparejada ni de la cuenta semilla, ambas
    identificadas por un User distinto."""
    Exam.objects.filter(created_by=training_user).delete()
    ExamVersionBatch.objects.filter(created_by=training_user).delete()
    ExamTemplate.objects.filter(created_by=training_user).delete()
    Rubric.objects.filter(created_by=training_user).delete()
    OralExamSet.objects.filter(user=training_user).delete()
    FormatoImpresion.objects.filter(user=training_user).delete()
    Contenido.objects.filter(uploaded_by=training_user).delete()
    Question.objects.filter(user=training_user).delete()
    Subject.objects.filter(created_by=training_user).delete()
    Favorite.objects.filter(user=training_user).delete()


def reset_training_account(training_user):
    """Resetea el Área de Pruebas del docente dueño de `training_user`. Se
    llama SOLO desde una acción explícita (propia o de un admin) — nunca
    automáticamente.

    Si hay un repuesto ya listo en el pool, hace un swap instantáneo: el
    vínculo pasa a apuntar al repuesto (ya clonado) y la cuenta vieja se
    borra en background. Si no hay repuesto disponible, cae al camino de
    siempre: vaciar y reclonar la misma cuenta en el lugar (más lento,
    pero funciona igual). En ambos casos repone el pool en background.

    Devuelve la cuenta de práctica vigente después del reset — puede ser
    una cuenta distinta (User) a la que se pasó como argumento, así que
    el llamador que dependa de la sesión (ver training_views.py) tiene
    que revisar si cambió y volver a loguearse como corresponde.
    """
    link = TrainingAccountLink.objects.select_related('training_user').get(training_user=training_user)
    old_training_user = link.training_user

    spare = _find_spare_training_account()
    if spare is None:
        delete_all_content_for_training_user(old_training_user)
        clone_seed_content_into(old_training_user)
        _replenish_pool_async()
        return old_training_user

    _apply_real_user_preferences(spare, link.real_user)
    link.training_user = spare
    link.save(update_fields=['training_user'])

    _delete_training_account_async(old_training_user.id)
    _replenish_pool_async()
    return spare

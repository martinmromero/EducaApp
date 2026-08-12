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

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

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
)

# Campos de Exam que se copian tal cual del examen semilla al clon — todo lo
# que no depende de qué Subject/Topic/Question puntual se haya clonado.
_EXAM_COPY_FIELDS = [
    'instructions', 'duration_minutes', 'year', 'exam_mode', 'exam_group', 'shift',
    'resolution_time', 'topics_to_evaluate', 'notes_and_recommendations',
    'institution_name', 'faculty_name', 'campus_name', 'career_name',
    'topics_snapshot', 'outcomes_snapshot', 'date_str', 'is_published',
]


def _seed_user():
    username = getattr(settings, 'SEED_CONTENT_USERNAME', 'educaapp_demo')
    return User.objects.get(username=username)


def get_or_create_training_account(real_user):
    """Devuelve la cuenta del Área de Pruebas de este docente, creándola
    (y poblándola con una copia del contenido semilla) si es la primera vez."""
    link = TrainingAccountLink.objects.filter(real_user=real_user).select_related('training_user').first()
    if link:
        return link.training_user

    training_user = User.objects.create(username=f'training__{real_user.pk}', is_active=True)
    training_user.set_unusable_password()
    training_user.save()

    profile = training_user.profile  # ya existe por la señal post_save de User
    profile.role = 'user'
    profile.is_training_account = True
    profile.onboarding_completed = True
    try:
        profile.visual_theme = real_user.profile.visual_theme
    except Exception:
        pass
    profile.save(update_fields=['role', 'is_training_account', 'onboarding_completed', 'visual_theme'])

    TrainingAccountLink.objects.create(real_user=real_user, training_user=training_user)

    clone_seed_content_into(training_user)
    return training_user


def clone_seed_content_into(training_user):
    """Clona el contenido semilla (rúbricas, contenidos, exámenes,
    cuestionarios orales, plantillas incluidos) en propiedad de
    training_user. Cada materia semilla se clona en una fila de Subject
    aparte (created_by=training_user) — nunca se reutiliza ni se apunta a
    la fila semilla original."""
    seed_user = _seed_user()

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

    topics_snapshot = list(Topic.objects.filter(subject=subject).values_list('name', flat=True))
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
        resolution_time='90 minutos',
        topics_to_evaluate='\n'.join(topics_snapshot),
        notes_and_recommendations='Revisar los conceptos fundamentales de la materia antes del examen.',
        created_by=training_user,
        institution_name_snapshot=institution.name,
        faculty_name_snapshot=faculty.name,
        campus_name_snapshot=campus.name if campus else '',
        career_name_snapshot=career.name,
        subject_name_snapshot=subject.name,
        topics_snapshot=topics_snapshot,
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
    """Vacía y repuebla la cuenta de práctica. Se llama SOLO desde una
    acción explícita (propia o de un admin) — nunca automáticamente."""
    delete_all_content_for_training_user(training_user)
    clone_seed_content_into(training_user)

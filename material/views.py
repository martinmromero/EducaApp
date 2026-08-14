import functools

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Q
from .column_filters import (
    ColumnFilterField,
    apply_column_filters,
    get_active_filter_count,
    get_filter_options,
    get_filter_querystring,
    get_filter_querystring_excluding,
    get_selected_filters,
    _apply_field_filter,
    NONE_VALUE,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helper: distribución de niveles de Bloom para un queryset de preguntas
# ──────────────────────────────────────────────────────────────────────────────
def _compute_bloom_display(question_qs):
    """
    Recibe un QuerySet de Question y retorna una lista de 6 dicts
    ordenada de nivel 6 (Crear) a nivel 1 (Recordar), lista para
                    form.save_m2m()  # Save many-to-many relationships
    """
    from django.db.models import Count

    raw = {
        item['bloom_level']: item['n']
        for item in question_qs.values('bloom_level').annotate(n=Count('id'))
        if item['bloom_level'] is not None
    }
    max_count = max(raw.values()) if raw else 1

    BLOOM_META = [
        (6, 'Crear',      '#9b59b6', 'diseñar, construir, planificar, producir'),
        (5, 'Evaluar',    '#3498db', 'juzgar, criticar, valorar, argumentar'),
        (4, 'Analizar',   '#27ae60', 'diferenciar, comparar, organizar, atribuir'),
        (3, 'Aplicar',    '#f39c12', 'ejecutar, implementar, usar, resolver'),
        (2, 'Comprender', '#e67e22', 'interpretar, ejemplificar, resumir, inferir'),
        (1, 'Recordar',   '#e74c3c', 'reconocer, listar, identificar, nombrar'),
    ]

    return [
        {
            'level': lvl,
            'name': name,
            'color': color,
            'verbs': verbs,
            'count': raw.get(lvl, 0),
            'pct': round(raw.get(lvl, 0) / max_count * 100) if max_count else 0,
        }
        for lvl, name, color, verbs in BLOOM_META
    ]


@login_required
def bloom_taxonomy(request):
    """Página de referencia de la Taxonomía de Bloom con estadísticas del usuario."""
    from .models import Question

    qs = Question.objects.filter(user=request.user)
    bloom_display = _compute_bloom_display(qs)
    total_bloom_questions = sum(item['count'] for item in bloom_display)

    context = {
        'bloom_display': bloom_display,
        'total_bloom_questions': total_bloom_questions,
        'total_questions': qs.count(),
    }
    if request.GET.get('popup'):
        return render(request, 'material/bloom_taxonomy_popup.html', context)
    return render(request, 'material/bloom_taxonomy.html', context)


@login_required
def preview_exam(request):
    raw_exam = request.session.get('preview_exam')
    if not raw_exam:
        messages.error(request, 'No hay datos para mostrar el preview.', extra_tags='general')
        return redirect('material:create_exam')

    exam = dict(raw_exam)
    from .models import Subject, InstitutionV2, FacultyV2, Career, CampusV2, User, Question, Topic, LearningOutcome

    subject_obj = None
    if exam.get('subject') and str(exam.get('subject')).isdigit():
        subject_obj = Subject.objects.filter(pk=int(exam['subject'])).first()

    institution_obj = None
    if exam.get('institucion'):
        if str(exam['institucion']).isdigit():
            institucion = InstitutionV2.objects.filter(pk=exam['institucion']).first()
            institution_obj = institucion
            exam['institucion'] = institucion.name if institucion else exam['institucion']
        elif exam['institucion'] == 'otro':
            exam['institucion'] = exam.get('institucion_text') or 'Otro'
    if institution_obj is None and exam.get('institucion'):
        institution_obj = InstitutionV2.objects.filter(name__iexact=exam.get('institucion')).first()

    institution_payload = {
        'name': exam.get('institucion', 'Institución'),
        'logo_b64': getattr(institution_obj, 'logo_b64', '') if institution_obj else '',
        'logo_url': (institution_obj.logo.url if institution_obj and getattr(institution_obj, 'logo', None) else ''),
    }
    if exam.get('facultad'):
        if str(exam['facultad']).isdigit():
            facultad = FacultyV2.objects.filter(pk=exam['facultad']).first()
            exam['facultad'] = facultad.name if facultad else exam['facultad']
        elif exam['facultad'] == 'otro':
            exam['facultad'] = exam.get('facultad_text') or 'Otro'
    if exam.get('carrera'):
        if str(exam['carrera']).isdigit():
            carrera = Career.objects.filter(pk=exam['carrera']).first()
            exam['carrera'] = carrera.name if carrera else exam['carrera']
        elif exam['carrera'] == 'otro':
            exam['carrera'] = exam.get('carrera_text') or 'Otro'
    if exam.get('sede'):
        if str(exam['sede']).isdigit():
            sede = CampusV2.objects.filter(pk=exam['sede']).first()
            exam['sede'] = sede.name if sede else exam['sede']
        elif exam['sede'] == 'otro':
            exam['sede'] = exam.get('sede_text') or 'Otro'
    if exam.get('profesor') and str(exam.get('profesor')).isdigit():
        profesor = User.objects.filter(pk=exam['profesor']).first()
        exam['profesor'] = profesor.get_full_name() if profesor else exam['profesor']

    exam['subject'] = subject_obj.name if subject_obj else exam.get('subject')

    raw_topics = exam.get('topics', [])
    topic_ids = [int(t) for t in raw_topics if str(t).isdigit()]
    outcome_ids = [int(o) for o in exam.get('learning_outcomes', []) if str(o).isdigit()]
    manual_question_ids = [int(q) for q in exam.get('questions', []) if str(q).isdigit()]

    # 'all' es un sentinel explícito, no "no se eligió nada": lo manda a propósito
    # onboarding_v2_demo_scheme para el examen de ejemplo del asistente ("usar
    # todos los tópicos de la materia"). Si topic_ids viene vacío por CUALQUIER
    # otra razón (nadie tocó el checkbox, o el fetch que puebla los checkboxes
    # falló) NO hay que armar el examen igual con todos los tópicos — eso arma
    # un examen con preguntas que el usuario nunca eligió, sin avisarle.
    topics_is_all_sentinel = 'all' in raw_topics
    if topics_is_all_sentinel:
        selected_topics = Topic.objects.filter(subject=subject_obj) if subject_obj else Topic.objects.none()
    elif topic_ids:
        selected_topics = Topic.objects.filter(pk__in=topic_ids)
    else:
        selected_topics = Topic.objects.none()
    topics_texts = list(selected_topics.values_list('name', flat=True))

    outcomes_texts = list(LearningOutcome.objects.filter(pk__in=outcome_ids).values_list('description', flat=True)) if outcome_ids else []

    versions_count = 1
    try:
        versions_count = max(1, int(exam.get('num_versions') or 1))
    except (TypeError, ValueError):
        versions_count = 1

    questions_per_version = 0
    try:
        questions_per_version = int(exam.get('questions_per_version') or 0)
    except (TypeError, ValueError):
        questions_per_version = 0

    if questions_per_version <= 0:
        questions_per_version = len(manual_question_ids) if manual_question_ids else max(1, selected_topics.count())

    from .content_visibility import get_visible_questions, EXAM_ELIGIBLE_Q
    include_seed = bool(exam.get('include_seed'))

    generated_versions = []
    if manual_question_ids and subject_obj:
        if versions_count == 1:
            generated_versions = [list(get_visible_questions(
                request.user, subject=subject_obj, include_seed=include_seed
            ).filter(
                EXAM_ELIGIBLE_Q,
                pk__in=manual_question_ids,
            ).distinct())]
        else:
            balance_by_topic = str(exam.get('balance_by_topic', '1')) == '1'
            generated_versions = _pick_questions_for_versions(
                subject=subject_obj,
                selected_topics=selected_topics,
                user=request.user,
                versions_count=versions_count,
                questions_per_version=questions_per_version,
                balance_by_topic=balance_by_topic,
                allowed_question_ids=manual_question_ids,
                include_seed=include_seed,
            )
    elif subject_obj:
        balance_by_topic = str(exam.get('balance_by_topic', '1')) == '1'
        generated_versions = _pick_questions_for_versions(
            subject=subject_obj,
            selected_topics=selected_topics,
            user=request.user,
            versions_count=versions_count,
            questions_per_version=questions_per_version,
            balance_by_topic=balance_by_topic,
            include_seed=include_seed,
        )

    versions_preview = []
    preview_ids = []
    for idx, q_list in enumerate(generated_versions, start=1):
        version_ids = [q.id for q in q_list]
        preview_ids.append(version_ids)
        versions_preview.append({
            'number': idx,
            'question_ids': version_ids,
            'questions_texts': [
                {
                    'id': q.id,
                    'text': q.question_text,
                    'type': q.question_type,
                    'options': q.options or [],
                    'question_image_b64': q.question_image_b64 or '',
                    'answer_text': q.answer_text or '',
                    'answer_image_b64': q.answer_image_b64 or '',
                    'bibliographic_reference': q.bibliographic_reference or '',
                }
                for q in q_list
            ]
        })

    request.session['preview_generated_versions_ids'] = preview_ids

    # Si no se armó ninguna pregunta en ninguna versión, no tiene sentido
    # mostrar un preview vacío como si el examen se hubiera generado bien —
    # sobre todo porque puede pasar en silencio (ej. no se eligió ningún
    # tópico). Mejor volver a Crear Examen con un aviso claro.
    total_questions_all_versions = sum(len(ids) for ids in preview_ids)
    if total_questions_all_versions == 0:
        if not selected_topics.exists() and not manual_question_ids:
            reason = 'No se seleccionó ningún tópico ni pregunta para armar el examen.'
        else:
            reason = 'No se encontraron preguntas disponibles para los tópicos/preguntas seleccionados.'
        messages.warning(
            request,
            f'{reason} Elegir al menos un tópico (o preguntas puntuales) antes de generar el examen.',
            extra_tags='general',
        )
        return redirect('material:create_exam')

    is_multiversion = len(versions_preview) > 1
    print_preview = request.GET.get('print') == '1'
    questions_texts = [] if is_multiversion else (versions_preview[0]['questions_texts'] if versions_preview else [])

    bloom_display = []
    total_exam_questions = len(questions_texts)
    if preview_ids and preview_ids[0]:
        bloom_display = _compute_bloom_display(Question.objects.filter(pk__in=preview_ids[0]))

    _TIPO_EXAMEN_LABELS = {
        '1er_parcial': '1er Parcial', '2do_parcial': '2do Parcial',
        '3er_parcial': '3er Parcial', 'final': 'Final',
        'recuperatorio': 'Recuperatorio', 'practico': 'Práctico',
    }
    _TIPO_MODALIDAD_LABELS = {'individual': 'Individual', 'grupal': 'Grupal'}

    suggested_batch_name = ''
    if is_multiversion:
        raw_year = exam.get('year')
        preview_year = int(raw_year) if raw_year and str(raw_year).strip().isdigit() else None
        if not preview_year and exam.get('fecha'):
            try:
                preview_year = int(str(exam.get('fecha')).split('-')[0])
            except (ValueError, IndexError):
                preview_year = None
        suggested_batch_name = (exam.get('batch_name') or '').strip() or _suggest_batch_name(
            subject_obj, exam, exam.get('institucion', ''), len(versions_preview), preview_year
        )

    context = {
        'exam': exam,
        'questions_texts': questions_texts,
        'versions_preview': versions_preview,
        'outcomes_texts': outcomes_texts,
        'topics_texts': topics_texts,
        'institution': institution_payload,
        'faculty': {'name': exam.get('facultad', 'Facultad')},
        'career': {'name': exam.get('carrera', 'Carrera')},
        'subject': {'name': exam.get('subject', 'Materia')},
        'professor': {'get_full_name': exam.get('profesor', '-')},
        'current_date': format_fecha_ddmmaaaa(exam.get('fecha', '')) or '-',
        'exam_type': _TIPO_EXAMEN_LABELS.get(exam.get('tipo_examen', ''), exam.get('tipo_examen') or '-'),
        'exam_mode': _TIPO_MODALIDAD_LABELS.get(exam.get('tipo_modalidad', ''), exam.get('tipo_modalidad') or '-'),
        'duracion_minutos': exam.get('duration_minutes', ''),
        'modalidad_resolucion': exam.get('modalidad_resolucion', []),
        'instructions': exam.get('instructions', ''),
        'bloom_display': bloom_display,
        'total_exam_questions': total_exam_questions,
        'suggested_batch_name': suggested_batch_name,
        'print_style': get_print_style_context(
            resolve_print_format_for_context(
                user=request.user,
                institution_name=exam.get('institucion', '') or '',
            )
        ),
        'wizard_active': request.session.get('onb2_wizard_active', False),
        # "Ejemplo del asistente": el botón Guardar simula el guardado (no
        # persiste nada real) y lleva al listado de Mis Exámenes simulado —
        # ver onboarding_v2_demo_scheme y [[project_onboarding_reform_2026_08]].
        # Esta pantalla solo se ve UNA vez en el recorrido: desde el listado
        # simulado, "Ver examen" queda deshabilitado a propósito (no hay una
        # segunda visita con el examen ya "guardado" que mostrar).
        'is_demo': bool(request.session.get('onb2_demo_scheme_active')),
    }

    if is_multiversion and not print_preview:
        return render(request, 'material/exams/preview_exam_versions.html', context)
    return render(request, 'material/exams/preview_exam.html', context)
from django.http import JsonResponse, Http404
import os
# Endpoint para obtener el nombre de la carrera por ID
from .models import Career

def get_career_name(request, career_id):
    try:
        career = Career.objects.get(pk=career_id)
        return JsonResponse({'name': career.name})
    except Career.DoesNotExist:
        return JsonResponse({'name': 'Carrera no encontrada'}, status=404)
from django.views.decorators.http import require_GET
from .models import ExamTemplate, Subject, Question, LearningOutcome, Topic

# AJAX: obtener datos de plantilla de examen
@login_required
@require_GET
def get_exam_template(request, template_id):
    # Las plantillas son privadas de quien las crea (no existe ningún
    # mecanismo para compartirlas, a diferencia de materias/preguntas) — sin
    # este filtro, cualquier usuario autenticado podía traerse los datos de
    # la plantilla de otro con solo adivinar/incrementar el ID.
    try:
        template = ExamTemplate.objects.get(id=template_id, created_by=request.user)
    except ExamTemplate.DoesNotExist:
        return JsonResponse({'error': 'Plantilla no encontrada'}, status=404)

    data = {
        'subject_id': template.subject.id if template.subject else None,
        'title': getattr(template, 'title', None),
        'instructions': getattr(template, 'notes_and_recommendations', None),
        'questions': list(template.question_set.values_list('id', flat=True)) if hasattr(template, 'question_set') else [],
        'learning_outcomes': list(template.learning_outcomes.values_list('id', flat=True)),
        'rubric_ids': list(template.rubrics.values_list('id', flat=True)),
        'institution_id': template.institution.id if template.institution else None,
        'faculty_id': template.faculty.id if template.faculty else None,
        'career_id': template.career.id if template.career else None,
        'campus_id': template.campus.id if template.campus else None,
        'professor_id': template.professor.id if template.professor else None,
        'exam_type': template.exam_type,
        'exam_mode': template.exam_mode,
        'shift': template.shift,
    }
    return JsonResponse(data)
from django.views.decorators.http import require_GET
# AJAX: obtener preguntas por temas seleccionados
@login_required
@require_GET
def get_questions_by_topics(request):
    from .content_visibility import get_visible_questions, EXAM_ELIGIBLE_Q
    all_topics = request.GET.get('all', 'false') == 'true'
    subject_id = request.GET.get('subject_id')
    topics = request.GET.get('topics', '')
    topic_ids = [int(t) for t in topics.split(',') if t]
    subject_arg = int(subject_id) if subject_id and str(subject_id).isdigit() else None
    # Mismo include_seed que get_topics?for_exam=1: sin esto, el examen de
    # ejemplo del asistente (cuyas preguntas son todas del bot de contenido
    # semilla, no del usuario) siempre devolvía cero preguntas por tópico.
    include_seed = bool(request.session.get('onb2_include_seed'))
    base_qs = get_visible_questions(request.user, subject=subject_arg, include_seed=include_seed)
    review_filter = EXAM_ELIGIBLE_Q
    questions = Question.objects.none()
    if all_topics and subject_id:
        questions = base_qs.filter(review_filter)
    elif topic_ids:
        questions = base_qs.filter(topic_id__in=topic_ids).filter(review_filter)
    data = [
        # Texto completo (sin truncar): quien arma el examen necesita poder
        # distinguir preguntas parecidas, y el panel ya es una lista con
        # scroll propio pensada para texto de varias líneas.
        {'id': q.id, 'text': q.question_text, 'topic_id': q.topic_id}
        for q in questions
    ]
    return JsonResponse(data, safe=False)

# AJAX: obtener carreras por facultad seleccionada
@require_GET
def get_careers_by_faculty(request, faculty_id):
    from .models import Career, FacultyV2
    careers = Career.objects.filter(faculties__id=faculty_id, is_seed_demo=False).distinct()
    data = [{'id': c.id, 'name': c.name} for c in careers]
    return JsonResponse({'careers': data})
# Standard library imports
import csv
import json
import logging


from django.forms import formset_factory, modelformset_factory, inlineformset_factory


# Django core imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.views.generic import DetailView, UpdateView, CreateView, ListView, DeleteView
from django.urls import reverse_lazy
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods, require_POST
from django.core.paginator import Paginator
from django.db import models, transaction, connection
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404, reverse
from .models import (Exam, ExamTemplate, Contenido, Profile, Question, Subject, Topic, 
    Subtopic, LearningOutcome, Career, 
    OralExamSet, OralExamGroup, OralExamStudent, OralExamStudentQuestion,
    Rubric, ExamRubric, RubricLevel, RubricCriterion, RubricCell, ExamVersionBatch,
    FormatoImpresion)
from .models import (InstitutionV2, CampusV2, FacultyV2, UserInstitution, InstitutionLog, InstitutionCareer, InstitutionSubject)
from .models import Favorite
from .models import get_or_create_real_subject
from django.contrib.contenttypes.models import ContentType
from .forms import (
    CustomLoginForm, ExamForm, ExamTemplateForm, QuestionForm, 
    UserEditForm, UserCreateForm, UserSelfEditForm, ContenidoForm,
    LearningOutcomeForm, SubjectForm, ProfileForm, CareerForm,
    OralExamForm, FormatoImpresionForm
)
from .print_format_utils import (
    assign_print_format_to_exam,
    clear_existing_default_for_scope,
    get_print_style_context,
    get_visible_print_formats,
    propagate_print_format_to_exams,
    resolve_print_format_for_context,
    resolve_print_format_for_exam,
)
from .exam_labels import get_exam_mode_label, get_exam_type_label, format_fecha_ddmmaaaa
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.utils import OperationalError, ProgrammingError, DatabaseError
from django.db.models import Prefetch, F, Value, CharField, Case, When, Exists, OuterRef
from django.db.models.functions import Concat
from .ia_processor import extract_book_metadata
from django.utils import timezone 
from .forms import LearningOutcomeForm, ProfileForm


from .forms import InstitutionV2Form, CampusV2Form, FacultyV2Form

from django.db import transaction
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import ExamTemplate, LearningOutcome

from django.db import IntegrityError  # Agregar este import al inicio
from django.db.models import ProtectedError
from .delete_preview import get_delete_preview

# Logger configuration
logger = logging.getLogger(__name__)


LearningOutcomeFormSet = inlineformset_factory(
    Subject,
    LearningOutcome,
    form=LearningOutcomeForm,
    extra=1,
    fields=('description',),
    fk_name='subject'
)


def get_topics(request):
    """
    Materia y Tópico son globales por nombre (Subject/Topic no están
    scopeados por usuario) — cualquier docente que use el mismo nombre de
    materia comparte el mismo Subject, y ve los tópicos que OTROS docentes
    hayan creado ahí (ej. el nombre de un documento que subieron). Pero las
    Question sí son por usuario (ver content_visibility.get_visible_questions):
    solo se ven las propias, más semilla/compartidas si corresponde.

    Sin filtrar, un docente nuevo veía en "Crear Examen" tópicos de otros
    usuarios sin ninguna pregunta suya disponible ahí — los elegía, tildaba
    "Todo", y el examen le salía vacío para esos tópicos, sin ningún aviso.

    `for_exam=1` (usado por create_exam.js y oral_exams/create.html, donde
    el objetivo es "dame preguntas ya cargadas") filtra a solo los tópicos
    que tienen AL MENOS una pregunta visible para este usuario. Sin ese
    parámetro (usado por upload_questions.html, donde el objetivo es
    "categorizar contenido nuevo mío") se listan todos los tópicos de la
    materia sin filtrar — ahí sí tiene sentido reutilizar un tópico que hoy
    está "vacío" para este usuario, porque le está por sumar contenido.
    """
    subject_id = request.GET.get('subject_id')
    topics_qs = Topic.objects.filter(subject_id=subject_id).distinct()

    if request.GET.get('for_exam') == '1' and request.user.is_authenticated:
        from .content_visibility import get_visible_questions, EXAM_ELIGIBLE_Q
        subject_obj = Subject.objects.filter(pk=subject_id).first()
        if subject_obj:
            # Mismo include_seed que va a usar save_exam_from_session/preview_exam
            # al generar de verdad (ver _collect_exam_post_data) — si acá se
            # usara siempre True, un tópico que solo tiene preguntas semilla
            # aparecería como "disponible" aunque el usuario no haya activado
            # esa preferencia, y el examen le saldría vacío igual para ese caso.
            include_seed = bool(request.session.get('onb2_include_seed'))
            visible_topic_ids = get_visible_questions(
                request.user, subject=subject_obj, include_seed=include_seed
            ).filter(EXAM_ELIGIBLE_Q).values_list('topic_id', flat=True).distinct()
            topics_qs = topics_qs.filter(pk__in=visible_topic_ids)

    topics = topics_qs.values('id', 'name')
    return JsonResponse(list(topics), safe=False)

def get_subtopics(request):
    topic_id = request.GET.get('topic_id')
    subtopics = Subtopic.objects.filter(topic_id=topic_id).values('id', 'name')
    return JsonResponse(list(subtopics), safe=False)

def get_faculties(request):
    institution_id = request.GET.get('institution_id')
    faculties = FacultyV2.objects.filter(
        institution_id=institution_id,
        is_active=True,
        institution__is_seed_demo=False,
    ).values('id', 'name').order_by('name')
    return JsonResponse(list(faculties), safe=False)

def get_campus_by_institution(request):
    institution_id = request.GET.get('institution_id')
    campus = CampusV2.objects.filter(
        institution_id=institution_id,
        institution__is_seed_demo=False,
    ).values('id', 'name').order_by('name')
    return JsonResponse(list(campus), safe=False)

def is_admin(user):
    # Superuser siempre cuenta como admin de la app, aun si su Profile.role
    # quedó en 'user' por default (el signal de creación de perfil no sabe
    # de is_superuser). Este es el único criterio de "admin" a nivel app;
    # es independiente de User.is_staff, que solo controla el acceso al
    # panel /admin/ de Django (restringido a superusers, ver material/admin.py).
    if user.is_superuser:
        return True
    try:
        return user.profile.role == 'admin'
    except Profile.DoesNotExist:
        return False

def _is_last_active_admin(user):
    return not Profile.objects.filter(
        role='admin', user__is_active=True
    ).exclude(user_id=user.id).exists()


def _protected_error_message(exc):
    """Arma un mensaje legible a partir de un django.db.models.ProtectedError.

    ExamTemplate protege 7 modelos padre (institution, faculty, career,
    subject, campus, professor, created_by) — sin esto, borrar cualquiera
    de esos mientras exista una ExamTemplate asociada tira un 500 crudo.
    """
    from collections import Counter
    objetos = list(exc.protected_objects)
    conteo = Counter(o.__class__._meta.verbose_name_plural.title() for o in objetos)
    detalle = ', '.join(f'{cantidad} {etiqueta}' for etiqueta, cantidad in conteo.items())
    return (
        f'No se puede eliminar: está siendo usado por {detalle}. '
        'Eliminá o reasigná esos elementos primero.'
    )


class CustomLoginView(LoginView):
    form_class = CustomLoginForm
    template_name = 'registration/login.html'

    def form_invalid(self, form):
        """Maneja intentos fallidos de login"""
        messages.error(self.request, "Credenciales inválidas. Intente nuevamente.", extra_tags='general')
        return super().form_invalid(form)
    

@login_required
def index(request):
    # El primer login de un usuario nuevo cae acá y OnboardingGateMiddleware
    # lo redirige a /comenzar/ si todavía no completó (ni salió de) el asistente.
    try:
        contenidos_count = Contenido.objects.filter(uploaded_by=request.user).count()
    except Exception:
        contenidos_count = 0
    try:
        preguntas_count = Question.objects.filter(user=request.user).count()
    except Exception:
        preguntas_count = 0
    try:
        examenes_count = Exam.objects.filter(created_by=request.user).count()
    except Exception:
        examenes_count = 0
    try:
        ultimos_examenes = list(
            Exam.objects.filter(created_by=request.user).order_by('-created_at')[:5]
        )
    except Exception:
        ultimos_examenes = []
    try:
        favoritos_count = Favorite.objects.filter(user=request.user).count()
    except Exception:
        favoritos_count = 0

    context = {
        'is_admin': is_admin(request.user),
        'contenidos_count': contenidos_count,
        'preguntas_count': preguntas_count,
        'examenes_count': examenes_count,
        'favoritos_count': favoritos_count,
        'ultimos_examenes': ultimos_examenes,
    }
    return render(request, 'material/index.html', context)

@login_required
def upload_contenido(request):  # Antes upload_material
    if request.method == 'POST':
        form = ContenidoForm(request.POST, request.FILES)
        if form.is_valid():
            from .cleanup import compute_file_hash

            file_obj = request.FILES.get('file')
            file_hash = compute_file_hash(file_obj) if file_obj else None

            # --- Deduplicación ---
            existing = None
            if file_hash:
                existing = Contenido.objects.filter(
                    file_hash=file_hash, uploaded_by=request.user
                ).first()

            if existing and existing.file_available:
                messages.warning(
                    request,
                    f'Este documento ya existe en tus contenidos: "{existing.title}". '
                    f'No se creó un duplicado.',
                    extra_tags='contenidos'
                )
                return redirect('material:mis_contenidos')

            if existing and not existing.file_available:
                # El archivo había expirado — restaurarlo
                from django.core.files.storage import default_storage
                from django.core.files.base import ContentFile
                file_obj.seek(0)
                saved_relative = default_storage.save(
                    f'contenidos/{file_obj.name}', ContentFile(file_obj.read())
                )
                existing.file = saved_relative
                existing.file_deleted_at = None
                existing.save(update_fields=['file', 'file_deleted_at'])
                messages.success(
                    request,
                    f'El archivo de "{existing.title}" había expirado y fue restaurado correctamente.',
                    extra_tags='contenidos'
                )
                return redirect('material:mis_contenidos')

            # --- Nuevo documento ---
            contenido = form.save(commit=False)
            contenido.uploaded_by = request.user
            contenido.file_hash = file_hash
            contenido.save()
            form.save_m2m()
            messages.success(request, 'Los archivos se subieron correctamente.', extra_tags='contenidos')
            return redirect('material:mis_contenidos')
    else:
        form = ContenidoForm()
    return render(request, 'material/questions/upload.html', {
        'form': form,
        'max_upload_mb': settings.CONTENIDO_MAX_UPLOAD_MB,
    })

@login_required
def extract_metadata_from_upload(request):
    """
    Vista AJAX para extraer metadata de un archivo PDF subido.
    Retorna JSON con ISBN, título, autor, edición, editorial, año, páginas.
    """
    from django.http import JsonResponse
    import tempfile
    import os
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No se recibió ningún archivo'}, status=400)
    
    uploaded_file = request.FILES['file']
    
    # Validar que sea PDF
    if not uploaded_file.name.lower().endswith('.pdf'):
        return JsonResponse({
            'error': 'Solo se puede extraer metadata de archivos PDF',
            'metadata': {}
        })
    
    try:
        # Guardar temporalmente el archivo
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            for chunk in uploaded_file.chunks():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name
        
        # Extraer metadata
        metadata = extract_book_metadata(tmp_path)
        
        # Limpiar archivo temporal
        os.unlink(tmp_path)
        
        # Si no hay título, usar el nombre del archivo
        if not metadata.get('title'):
            metadata['title'] = os.path.splitext(uploaded_file.name)[0]
        
        return JsonResponse({
            'success': True,
            'metadata': metadata,
            'filename': uploaded_file.name
        })
        
    except Exception as e:
        return JsonResponse({
            'error': f'Error al procesar el archivo: {str(e)}',
            'metadata': {}
        }, status=500)


def _collect_exam_post_data(request, form):
    exam_data = {}
    multiple_fields = ['questions', 'topics', 'learning_outcomes']
    for field in form.fields:
        if field in multiple_fields:
            exam_data[field] = request.POST.getlist(field)
        else:
            exam_data[field] = request.POST.get(field)

    exam_data['institucion'] = request.POST.get('institucion_dropdown')
    exam_data['institucion_text'] = request.POST.get('institucion_text', '').strip()
    exam_data['facultad'] = request.POST.get('facultad_dropdown')
    exam_data['facultad_text'] = request.POST.get('facultad_text', '').strip()
    exam_data['carrera'] = request.POST.get('carrera_dropdown')
    exam_data['carrera_text'] = request.POST.get('carrera_text', '').strip()
    exam_data['sede'] = request.POST.get('sede_dropdown')
    exam_data['sede_text'] = request.POST.get('sede_text', '').strip()
    exam_data['curso'] = request.POST.get('curso')
    exam_data['turno'] = request.POST.get('turno_dropdown')
    exam_data['turno_text'] = request.POST.get('turno_text', '').strip()
    exam_data['profesor'] = request.POST.get('profesor_dropdown')
    exam_data['fecha'] = request.POST.get('fecha')
    exam_data['year'] = request.POST.get('year', '').strip()
    exam_data['tipo_examen'] = request.POST.get('tipo_examen')
    exam_data['tipo_modalidad'] = request.POST.get('tipo_modalidad')
    exam_data['modalidad_resolucion'] = request.POST.getlist('modalidad_resolucion')
    exam_data['alumno'] = request.POST.get('alumno')
    exam_data['batch_name'] = request.POST.get('batch_name', '').strip()
    exam_data['batch_semester'] = request.POST.get('batch_semester', '').strip()
    exam_data['num_versions'] = request.POST.get('num_versions', '1').strip() or '1'
    exam_data['questions_per_version'] = request.POST.get('questions_per_version', '').strip()
    exam_data['balance_by_topic'] = '1' if request.POST.get('balance_by_topic') else '0'
    exam_data['rubric_ids'] = request.POST.getlist('rubric_ids')
    # Preferencia de sumar contenido semilla, elegida en el wizard (paso 3 o 6,
    # ver onboarding_save_step step='seed_pref'). No se popea acá: si el
    # usuario reenvía el formulario (vuelve atrás y cambia algo), no debe
    # perder la preferencia. Se limpia al terminar/salir del wizard.
    exam_data['include_seed'] = bool(request.session.get('onb2_include_seed'))
    return exam_data


def _suggest_batch_name(subject, exam_data, institution_name, versions_count, year):
    tipo_map = {
        '1er_parcial': '1er parcial',
        '2do_parcial': '2do parcial',
        '3er_parcial': '3er parcial',
        'final': 'final',
        'recuperatorio': 'recuperatorio',
        'practico': 'practico',
    }
    tipo = tipo_map.get(exam_data.get('tipo_examen', ''), 'examen')
    materia = subject.name if subject else 'sin materia'
    institucion = institution_name or 'sin institucion'
    # "batch_semester" es el campo oculto que sincroniza el Período (número +
    # Bimestre/Trimestre/Cuatrimestre/Semestre) del Área 1 del formulario.
    periodo = exam_data.get('batch_semester') or 'sin periodo'
    curso = (exam_data.get('curso') or '').strip()
    year_str = str(year) if year else 'sin año'
    parts = [tipo, materia, institucion, periodo]
    if curso:
        parts.append(curso)
    parts += [year_str, f"{versions_count} opciones"]
    return " - ".join(parts)


def _arrange_questions_avoiding_same_topic_consecutive(question_list):
    from collections import defaultdict
    grouped = defaultdict(list)
    for q in question_list:
        grouped[q.topic_id].append(q)

    result = []
    last_topic = None
    while grouped:
        candidates = [
            (topic_id, items) for topic_id, items in grouped.items() if topic_id != last_topic and items
        ]
        if not candidates:
            candidates = [(topic_id, items) for topic_id, items in grouped.items() if items]
        candidates.sort(key=lambda item: len(item[1]), reverse=True)
        topic_id, items = candidates[0]
        result.append(items.pop())
        last_topic = topic_id
        if not items:
            grouped.pop(topic_id, None)
    return result


def _pick_questions_for_versions(subject, selected_topics, user, versions_count, questions_per_version, balance_by_topic=True, allowed_question_ids=None, include_seed=False):
    import random
    from collections import defaultdict

    from .content_visibility import get_visible_questions, EXAM_ELIGIBLE_Q

    pools = defaultdict(list)
    base_qs = get_visible_questions(user, subject=subject, include_seed=include_seed).filter(
        EXAM_ELIGIBLE_Q,
        topic__in=selected_topics,
    ).select_related('topic')
    if allowed_question_ids:
        base_qs = base_qs.filter(pk__in=allowed_question_ids)

    for q in base_qs:
        pools[q.topic_id].append(q)
    for topic_id in pools:
        random.shuffle(pools[topic_id])

    topic_ids = list(selected_topics.values_list('id', flat=True))
    if not topic_ids:
        return []

    if balance_by_topic:
        base = questions_per_version // len(topic_ids)
        remainder = questions_per_version % len(topic_ids)
        per_topic_required = {tid: base for tid in topic_ids}
        for tid in topic_ids[:remainder]:
            per_topic_required[tid] += 1
    else:
        per_topic_required = {tid: 0 for tid in topic_ids}

    globally_used = set()
    all_questions = list(base_qs)
    versions = []

    for _ in range(versions_count):
        version_questions = []
        used_in_version = set()

        for tid in topic_ids:
            needed = per_topic_required[tid]
            if needed <= 0:
                continue

            strict = [q for q in pools.get(tid, []) if q.id not in used_in_version and q.id not in globally_used]
            relaxed = [q for q in pools.get(tid, []) if q.id not in used_in_version]
            chosen = strict[:needed]
            if len(chosen) < needed:
                missing = needed - len(chosen)
                extra = [q for q in relaxed if q.id not in {x.id for x in chosen}][:missing]
                chosen.extend(extra)

            for q in chosen:
                if q.id not in used_in_version:
                    version_questions.append(q)
                    used_in_version.add(q.id)
                    globally_used.add(q.id)

        if len(version_questions) < questions_per_version:
            fallback = [q for q in all_questions if q.id not in used_in_version and q.id not in globally_used]
            if len(fallback) < (questions_per_version - len(version_questions)):
                fallback.extend([q for q in all_questions if q.id not in used_in_version and q not in fallback])

            for q in fallback:
                if len(version_questions) >= questions_per_version:
                    break
                if q.id in used_in_version:
                    continue
                version_questions.append(q)
                used_in_version.add(q.id)
                globally_used.add(q.id)

        versions.append(_arrange_questions_avoiding_same_topic_consecutive(version_questions))

    return versions


@functools.lru_cache(maxsize=8)
def _get_table_columns(table_name):
    try:
        table_names = set(connection.introspection.table_names())
        if table_name not in table_names:
            return set()
        with connection.cursor() as cursor:
            return {
                col.name for col in connection.introspection.get_table_description(cursor, table_name)
            }
    except Exception:
        return set()


@functools.lru_cache(maxsize=1)
def _get_exam_version_schema_state():
    # El esquema de la DB no cambia durante la vida del proceso, así que esto
    # se cachea: antes se volvía a introspeccionar la DB (2 queries) en cada
    # navegación a "Exámenes", siendo un costo fijo innecesario por request.
    exam_table = Exam._meta.db_table
    batch_table = ExamVersionBatch._meta.db_table
    has_exam_version_fields = False
    has_batch_table = False

    try:
        table_names = set(connection.introspection.table_names())
        has_batch_table = batch_table in table_names

        if exam_table in table_names:
            exam_columns = _get_table_columns(exam_table)
            has_exam_version_fields = {
                'version_batch_id',
                'version_number',
            }.issubset(exam_columns)
    except Exception:
        has_exam_version_fields = False
        has_batch_table = False

    return has_exam_version_fields, has_batch_table


def _get_compatible_exam_queryset():
    qs = Exam.objects.select_related('subject', 'professor')
    has_exam_version_fields, _ = _get_exam_version_schema_state()
    if not has_exam_version_fields:
        qs = qs.defer('version_batch', 'version_number')
    return qs


def _get_compatible_exam_or_404(user, pk):
    try:
        return get_object_or_404(_get_compatible_exam_queryset(), pk=pk, created_by=user)
    except (OperationalError, ProgrammingError, DatabaseError):
        logger.warning('Esquema de examenes desfasado en produccion; degradando carga de examen %s.', pk)
        fallback_qs = Exam.objects.select_related('subject', 'professor').defer('version_batch', 'version_number')
        return get_object_or_404(fallback_qs, pk=pk, created_by=user)


def _resolve_exam_print_format_safe(examen):
    try:
        return resolve_print_format_for_exam(examen)
    except (OperationalError, ProgrammingError, DatabaseError):
        logger.warning('No se pudo resolver el formato de impresion para el examen %s; usando defaults.', examen.pk)
        return None


def _build_preview_exam_payload_from_exam(examen):
    from .models import InstitutionV2, FacultyV2, Career, CampusV2

    def _resolve_dropdown_value(model_cls, name_value):
        if not name_value:
            return '', ''
        obj = model_cls.objects.filter(name__iexact=name_value).first()
        if obj:
            return str(obj.pk), ''
        return 'otro', name_value

    institucion, institucion_text = _resolve_dropdown_value(InstitutionV2, examen.institution_name)
    facultad, facultad_text = _resolve_dropdown_value(FacultyV2, examen.faculty_name)
    carrera, carrera_text = _resolve_dropdown_value(Career, examen.career_name)
    sede, sede_text = _resolve_dropdown_value(CampusV2, examen.campus_name)

    turno = ''
    turno_text = ''
    if examen.shift:
        if examen.shift in ['mañana', 'tarde', 'noche']:
            turno = examen.shift
        else:
            turno = 'otro'
            turno_text = examen.shift

    profesor = str(examen.professor_id) if examen.professor_id else ''
    modalidad_resolucion = [m.strip() for m in (examen.resolution_time or '').split(',') if m.strip()]

    return {
        'title': examen.title or '',
        'subject': str(examen.subject_id) if examen.subject_id else '',
        'topics': list(examen.topics.values_list('id', flat=True)),
        'questions': list(examen.questions.values_list('id', flat=True)),
        'learning_outcomes': list(examen.learning_outcomes.values_list('id', flat=True)),
        'rubric_ids': list(examen.exam_rubrics.values_list('rubric_id', flat=True)),
        'instructions': examen.instructions or '',
        'duration_minutes': examen.duration_minutes,
        'institucion': institucion,
        'institucion_text': institucion_text,
        'facultad': facultad,
        'facultad_text': facultad_text,
        'carrera': carrera,
        'carrera_text': carrera_text,
        'sede': sede,
        'sede_text': sede_text,
        'curso': examen.curso or '',
        'turno': turno,
        'turno_text': turno_text,
        'profesor': profesor,
        'fecha': examen.date_str or '',
        'year': str(examen.year) if examen.year else '',
        'tipo_examen': examen.exam_type or '',
        'tipo_modalidad': examen.exam_group or '',
        'modalidad_resolucion': modalidad_resolucion,
        'alumno': examen.alumno or '',
        'batch_name': '',
        'batch_semester': '',
        'num_versions': '1',
        'questions_per_version': '',
        'balance_by_topic': '1',
    }


def _ensure_exam_version_schema():
    has_exam_version_fields, has_batch_table = _get_exam_version_schema_state()
    if has_exam_version_fields and has_batch_table:
        return True

    try:
        with connection.schema_editor() as schema_editor:
            table_names = set(connection.introspection.table_names())

            if not has_batch_table and ExamVersionBatch._meta.db_table not in table_names:
                schema_editor.create_model(ExamVersionBatch)

            exam_columns = _get_table_columns(Exam._meta.db_table)
            if 'version_batch_id' not in exam_columns:
                schema_editor.add_field(Exam, Exam._meta.get_field('version_batch'))
                exam_columns.add('version_batch_id')
            if 'version_number' not in exam_columns:
                schema_editor.add_field(Exam, Exam._meta.get_field('version_number'))
    except Exception:
        logger.exception('No se pudo auto-crear el esquema de lotes de examenes en runtime.')
        return False

    has_exam_version_fields, has_batch_table = _get_exam_version_schema_state()
    return has_exam_version_fields and has_batch_table


def _create_exam_with_compatible_schema(exam_kwargs, selected_topics, selected_outcomes, version_questions):
    exam_table = Exam._meta.db_table
    existing_columns = _get_table_columns(exam_table)
    if not existing_columns:
        exam_obj = Exam.objects.create(**exam_kwargs)
        exam_obj.topics.set(selected_topics)
        if selected_outcomes.exists():
            exam_obj.learning_outcomes.set(selected_outcomes)
        exam_obj.questions.set(version_questions)
        return exam_obj

    exam_obj = Exam(**exam_kwargs)
    concrete_fields = []
    values = []

    for field in Exam._meta.local_concrete_fields:
        if field.primary_key or not field.column or field.column not in existing_columns:
            continue

        if getattr(field, 'auto_now_add', False) or getattr(field, 'auto_now', False):
            value = field.pre_save(exam_obj, add=True)
            setattr(exam_obj, field.attname, value)
        else:
            value = getattr(exam_obj, field.attname)

        value = field.get_db_prep_save(value, connection)

        concrete_fields.append(field)
        values.append(value)

    if not concrete_fields:
        raise DatabaseError('No hay columnas compatibles disponibles para insertar examenes.')

    quoted_table = connection.ops.quote_name(exam_table)
    column_sql = ', '.join(connection.ops.quote_name(field.column) for field in concrete_fields)
    placeholder_sql = ', '.join(['%s'] * len(concrete_fields))

    with connection.cursor() as cursor:
        if connection.vendor == 'postgresql':
            cursor.execute(
                f'INSERT INTO {quoted_table} ({column_sql}) VALUES ({placeholder_sql}) RETURNING id',
                values,
            )
            exam_id = cursor.fetchone()[0]
        else:
            cursor.execute(
                f'INSERT INTO {quoted_table} ({column_sql}) VALUES ({placeholder_sql})',
                values,
            )
            exam_id = cursor.lastrowid

    topic_ids = list(selected_topics.values_list('id', flat=True))
    if topic_ids:
        Exam.topics.through.objects.bulk_create([
            Exam.topics.through(exam_id=exam_id, topic_id=topic_id)
            for topic_id in topic_ids
        ])

    outcome_ids = list(selected_outcomes.values_list('id', flat=True))
    if outcome_ids:
        Exam.learning_outcomes.through.objects.bulk_create([
            Exam.learning_outcomes.through(exam_id=exam_id, learningoutcome_id=outcome_id)
            for outcome_id in outcome_ids
        ])

    question_ids = [question.id for question in version_questions]
    if question_ids:
        Exam.questions.through.objects.bulk_create([
            Exam.questions.through(exam_id=exam_id, question_id=question_id)
            for question_id in question_ids
        ])

    exam_obj.pk = exam_id
    return exam_obj


def _safe_assign_print_format(exam_obj):
    """Resuelve y asigna el formato de impresion en su propio savepoint.

    Si la tabla de formatos/asignaciones no existe todavia en Postgres (Neon
    desfasado), un DatabaseError sin savepoint deja la transaccion externa
    'aborted': cualquier INSERT posterior (el siguiente examen del lote, o el
    commit final) falla o se pierde en silencio. Por eso esto corre dentro de
    su propio transaction.atomic() y absorbe el error ahi mismo.
    """
    try:
        with transaction.atomic():
            if hasattr(exam_obj, 'formato_impresion_asignado'):
                return
            formato = resolve_print_format_for_exam(exam_obj)
            if formato:
                assign_print_format_to_exam(exam_obj, formato)
    except (OperationalError, ProgrammingError, DatabaseError):
        logger.warning(
            'No se pudo asignar formato de impresion al examen %s (tabla desactualizada); se omite.',
            getattr(exam_obj, 'pk', None),
        )


def _apply_rubrics_to_exam(exam_obj, rubrics):
    """Reemplaza las rúbricas asociadas al examen por la lista dada (mismo
    criterio 'set' que topics/questions/learning_outcomes: lo que se guarda
    en el wizard es la selección completa, no un delta)."""
    exam_obj.exam_rubrics.all().delete()
    if rubrics:
        ExamRubric.objects.bulk_create([
            ExamRubric(exam=exam_obj, rubric=r, position=i)
            for i, r in enumerate(rubrics)
        ])


@login_required
def create_exam(request):
    from .models import FacultyV2, Career, CampusV2, Subject, ExamTemplate, InstitutionV2
    from django.contrib.auth.models import User

    # ONBOARDING WIZARD V2: si venimos del asistente (?wizard=1), lo recordamos en
    # sesión para mostrar el banner de continuidad en todo este sub-flujo
    # (create_exam -> preview_exam -> save_exam_from_session). Si en cambio
    # llegamos por la navegación normal (sidebar "Exámenes"), sin el parámetro,
    # limpiamos cualquier flag viejo: si no lo hiciéramos, alguien que abandonó
    # el wizard a mitad de camino vería el banner "seguís en el asistente"
    # pegado semanas después, en un uso totalmente normal de la app.
    # ONBOARDING WIZARD V2 (ejemplo enlatado): ?demo_peek=1 muestra esta misma
    # pantalla real, con los datos del ejemplo ya cargados (por el mismo
    # mecanismo de prefill de más abajo), de solo lectura y sin tocar el
    # estado de sesión del ejemplo — es un vistazo de paso, entre el resumen
    # y la vista previa del examen, no un flujo nuevo a completar.
    is_demo_peek = request.GET.get('demo_peek') == '1' and bool(request.session.get('onb2_demo_scheme_active'))

    if request.GET.get('wizard') == '1':
        request.session['onb2_wizard_active'] = True
    elif not is_demo_peek:
        request.session.pop('onb2_wizard_active', None)
        # onb2_include_seed también se limpia acá, salvo en el vistazo demo:
        # en el wizard manual (?wizard=1) lo pudo haber activado el propio
        # usuario en el paso 3/6 (ver onboarding_save_step, step=seed_pref) y
        # todavía lo necesita más abajo, al guardar; en navegación normal
        # (sin wizard ni demo_peek) no debe quedar pegado de una vuelta
        # anterior.
        request.session.pop('onb2_include_seed', None)
    wizard_active = request.session.get('onb2_wizard_active', False)
    # Crear Examen es siempre un examen REAL — nunca el ejemplo enlatado del
    # asistente (ver onboarding_v2_demo_scheme), aunque venga con ?wizard=1
    # (wizard manual). Si esta marca quedó pegada de una vuelta anterior por
    # "esquema ya armado", se limpia acá para no simular el guardado de un
    # examen real — excepto en el vistazo de solo lectura de arriba, que
    # necesita que la marca siga viva para que preview_exam seguido de esto
    # siga tratándose como el ejemplo del asistente.
    if not is_demo_peek:
        request.session.pop('onb2_demo_scheme_active', None)

    # Institución/Carrera del contenido semilla (ver seed_demo_content) solo
    # deben aparecer seleccionables en el vistazo de solo lectura del
    # asistente (?demo_peek=1, donde el prefill necesita encontrarlas entre
    # las opciones) — nunca en el uso normal de Crear Examen.
    instituciones = InstitutionV2.objects.filter(is_active=True)
    facultades = FacultyV2.objects.filter(is_active=True)
    carreras = Career.objects.all()
    sedes = CampusV2.objects.filter(is_active=True)
    if not is_demo_peek:
        instituciones = instituciones.filter(is_seed_demo=False)
        carreras = carreras.filter(is_seed_demo=False)
    materias = Subject.objects.filter(is_seed_demo=False)
    profesores = (
        User.objects.filter(profile__role='admin') | User.objects.filter(profile__role='user')
    ).exclude(profile__is_training_account=True)
    # Las plantillas son privadas de quien las crea (no existe ningún
    # mecanismo para compartirlas) — mostrar las de otros usuarios era
    # además la puerta de entrada al problema de get_exam_template de más
    # arriba, no solo una opción confusa en el desplegable.
    templates = ExamTemplate.objects.filter(created_by=request.user)
    # ?plantilla_id= viene del botón "Crear examen con esta plantilla" (listado
    # de plantillas / preview). Se compara contra `templates`, que ya está
    # acotado a las del usuario, así que un ID ajeno simplemente no matchea
    # ningún <option> en el template y el desplegable queda en "Examen vacío".
    preselected_template_id = request.GET.get('plantilla_id')

    from .content_visibility import get_visible_rubrics
    visible_rubrics = get_visible_rubrics(request.user)

    if request.method == 'POST':
        form = ExamForm(request.POST)
        exam_data = _collect_exam_post_data(request, form)
        request.session['preview_exam'] = exam_data
        # Invalida el cache de versiones de una preview anterior: si no, un
        # envio del formulario con otra materia/temas/cantidad de versiones
        # podia reciclar preguntas de la preview vieja en save_exam_from_session
        # (p.ej. guardar directo despues de haber abandonado una preview previa).
        # preview_exam la vuelve a poblar mas abajo si el usuario pasa por ahi.
        request.session.pop('preview_generated_versions_ids', None)

        if 'save' in request.POST:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return save_exam_from_session(request)
            return redirect('material:save_exam_from_session')
        return redirect('material:preview_exam')

    if request.GET.get('limpiar') == '1':
        request.session.pop('preview_exam', None)
        request.session.pop('editing_exam_id', None)
        request.session.pop('preview_generated_versions_ids', None)
        return redirect('material:create_exam')

    form = ExamForm()
    # ExamForm.subject viene del FK del modelo (sin límite propio), a
    # diferencia de ContenidoForm/QuestionForm que sí filtran is_seed_demo —
    # sin esto, las materias semilla (solo pensadas para el esquema de
    # ejemplo del asistente) aparecían seleccionables en Crear Examen para
    # cualquier usuario real. En el vistazo de solo lectura (?demo_peek=1)
    # se necesita la materia semilla en las opciones para que el prefill la
    # muestre seleccionada.
    if is_demo_peek:
        form.fields['subject'].queryset = Subject.objects.all()
    else:
        # Subject es global por nombre (sin dueño) — mostrar TODAS las
        # materias no-semilla dejaba elegibles materias de otros docentes
        # sin ninguna pregunta visible para este usuario (propia o
        # compartida por grupo), con el panel de Tópicos/Preguntas vacío
        # como único indicio. Mismo criterio de visibilidad que ya usa
        # get_topics?for_exam=1: si no hay nada elegible para armar un
        # examen ahí, la materia no debería aparecer como opción.
        from .content_visibility import get_visible_questions, EXAM_ELIGIBLE_Q
        visible_subject_ids = get_visible_questions(request.user).filter(
            EXAM_ELIGIBLE_Q
        ).values_list('subjects__id', flat=True).distinct()
        form.fields['subject'].queryset = Subject.objects.filter(
            is_seed_demo=False, id__in=visible_subject_ids
        )

    import json as _json
    prefill_data = request.session.get('preview_exam') or {}

    edit_exam_id = request.GET.get('edit_exam_id', '')
    if str(edit_exam_id).isdigit():
        editing_exam = _get_compatible_exam_queryset().filter(
            pk=int(edit_exam_id),
            created_by=request.user,
        ).first()
        if editing_exam is not None:
            prefill_data = _build_preview_exam_payload_from_exam(editing_exam)
            request.session['editing_exam_id'] = editing_exam.pk
            request.session.pop('preview_generated_versions_ids', None)

    if not prefill_data:
        editing_exam_id = request.session.get('editing_exam_id')
        if str(editing_exam_id).isdigit():
            editing_exam = _get_compatible_exam_queryset().filter(
                pk=int(editing_exam_id),
                created_by=request.user,
            ).first()
            if editing_exam is not None:
                prefill_data = _build_preview_exam_payload_from_exam(editing_exam)

    # ONBOARDING WIZARD V2: si venimos del asistente y todavía no hay ningún
    # borrador de examen en curso, autocompletamos con lo que ya se cargó en
    # los pasos anteriores (institución del paso 2, materia del paso 3/4,
    # profesor = vos mismo, temas de las preguntas recién aprobadas en el
    # paso 5). wizard_prefill_fields le dice al template qué campos resaltar.
    wizard_prefill_fields = []
    if wizard_active and not prefill_data:
        from .models import Contenido, Question, UserInstitution

        wiz_built = {}
        wiz_contenido_id = request.GET.get('contenido_id', '')
        wiz_subject_id = request.GET.get('subject_id', '')

        subject_id_final = wiz_subject_id if wiz_subject_id.isdigit() else None
        if not subject_id_final and wiz_contenido_id.isdigit():
            contenido_obj = Contenido.objects.filter(
                pk=int(wiz_contenido_id), uploaded_by=request.user
            ).prefetch_related('subjects').first()
            if contenido_obj:
                first_subject = contenido_obj.subjects.first()
                if first_subject:
                    subject_id_final = str(first_subject.id)
        if subject_id_final:
            wiz_built['subject'] = subject_id_final
            wizard_prefill_fields.append('subject')

        user_institution = UserInstitution.objects.filter(
            user=request.user
        ).select_related('institution').first()
        if user_institution:
            wiz_built['institucion'] = str(user_institution.institution_id)
            wizard_prefill_fields.append('institucion')

        wiz_built['profesor'] = str(request.user.id)
        wizard_prefill_fields.append('profesor')

        if wiz_contenido_id.isdigit():
            topic_ids = list(
                Question.objects.filter(
                    contenido_id=int(wiz_contenido_id), user=request.user, ai_approved=True
                ).exclude(topic__isnull=True).values_list('topic_id', flat=True).distinct()
            )
            if topic_ids:
                wiz_built['topics'] = [str(t) for t in topic_ids]
                wizard_prefill_fields.append('topics')

        prefill_data = wiz_built

    prefill_data_json = _json.dumps(prefill_data)
    context = {
        'form': form,
        'instituciones': instituciones,
        'facultades': facultades,
        'carreras': carreras,
        'sedes': sedes,
        'materias': materias,
        'profesores': profesores,
        'templates': templates,
        'preselected_template_id': preselected_template_id,
        'visible_rubrics': visible_rubrics,
        'prefill_data_json': prefill_data_json,
        'wizard_active': wizard_active,
        'wizard_prefill_fields_json': _json.dumps(wizard_prefill_fields),
        'is_demo_peek': is_demo_peek,
    }
    return render(request, 'material/exams/create_exam.html', context)

@login_required
def save_exam_from_session(request):
    """Guarda examen/es desde sesión. Soporta lote de versiones para examen escrito."""
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    def _error(text):
        if is_ajax:
            return JsonResponse({'success': False, 'message': text})
        messages.error(request, text, extra_tags='general')
        return redirect('material:create_exam')

    exam_data = request.session.get('preview_exam')
    if not exam_data:
        return _error('No hay datos de examen para guardar.')

    from .models import Subject, Question, Topic, LearningOutcome, Exam as ExamModel
    from .models import InstitutionV2, FacultyV2, Career, CampusV2
    from django.contrib.auth.models import User

    # ── Subject ─────────────────────────────────────────────
    subject = None
    if exam_data.get('subject') and str(exam_data['subject']).isdigit():
        subject = Subject.objects.filter(pk=int(exam_data['subject'])).first()
    if not subject:
        return _error('No se pudo determinar la materia del examen.')

    # ── Title ────────────────────────────────────────────────
    tipo_map = {
        '1er_parcial': '1er Parcial', '2do_parcial': '2do Parcial',
        '3er_parcial': '3er Parcial', 'final': 'Final',
        'recuperatorio': 'Recuperatorio', 'practico': 'Práctico',
    }
    tipo = tipo_map.get(exam_data.get('tipo_examen', ''), exam_data.get('tipo_examen') or 'Examen')
    fecha = exam_data.get('fecha', '')
    title = (exam_data.get('title') or '').strip() or \
            f"{tipo} - {subject.name}" + (f" ({fecha})" if fecha else "")

    duration = 60
    try:
        duration = int(exam_data.get('duration_minutes') or 60)
    except (ValueError, TypeError):
        pass

    # ── Resolve text names from V2 PKs ───────────────────────
    def _resolve_name(model_cls, raw_val, text_fallback):
        if not raw_val:
            return text_fallback or ''
        if str(raw_val).isdigit():
            obj = model_cls.objects.filter(pk=int(raw_val)).first()
            return obj.name if obj else (text_fallback or '')
        if raw_val == 'otro':
            return text_fallback or 'Otro'
        return str(raw_val)

    institution_name = _resolve_name(
        InstitutionV2, exam_data.get('institucion'), exam_data.get('institucion_text'))
    faculty_name = _resolve_name(
        FacultyV2, exam_data.get('facultad'), exam_data.get('facultad_text'))
    campus_name = _resolve_name(
        CampusV2, exam_data.get('sede'), exam_data.get('sede_text'))

    # carrera: Career model name or text
    carrera_raw = exam_data.get('carrera', '')
    carrera_text = exam_data.get('carrera_text', '')
    if str(carrera_raw).isdigit():
        c_obj = Career.objects.filter(pk=int(carrera_raw)).first()
        career_name = c_obj.name if c_obj else carrera_text
    elif carrera_raw == 'otro':
        career_name = carrera_text or 'Otro'
    else:
        career_name = str(carrera_raw) if carrera_raw else carrera_text

    # professor FK
    professor = None
    prof_raw = exam_data.get('profesor', '')
    if str(prof_raw).isdigit():
        professor = User.objects.filter(pk=int(prof_raw)).first()

    # turno / shift
    shift_raw = exam_data.get('turno', '') or exam_data.get('turno_text', '')
    valid_shifts = ['mañana', 'tarde', 'noche']
    shift = shift_raw if shift_raw in valid_shifts else None

    # exam_type: se recorta al max_length real del campo como salvaguarda
    # (nunca deberia disparar con los valores actuales de EXAM_TYPE_CHOICES,
    # ver material/models.py:797 — max_length=20).
    exam_type = exam_data.get('tipo_examen') or None
    if exam_type:
        exam_type = exam_type[:Exam._meta.get_field('exam_type').max_length]

    # exam_group (individual / grupal) — this is tipo_modalidad from the form
    exam_group_raw = exam_data.get('tipo_modalidad', '')
    valid_groups = ['individual', 'grupal']
    exam_group = exam_group_raw if exam_group_raw in valid_groups else 'individual'

    # exam_mode (oral / escrito) — separate field, not used in the form currently
    exam_mode = None

    # resolution_time (modalidad_resolucion list or free text)
    mod_res = exam_data.get('modalidad_resolucion', '')
    if isinstance(mod_res, list):
        resolution_time = ', '.join(mod_res)
    else:
        resolution_time = str(mod_res) if mod_res else ''

    # year: explícito (campo "Año" del formulario) si se cargó; si no, se infiere de la fecha
    year = None
    raw_year = exam_data.get('year')
    if raw_year and str(raw_year).strip().isdigit():
        year = int(str(raw_year).strip())
    elif fecha:
        try:
            year = int(str(fecha).split('-')[0])
        except (ValueError, IndexError):
            pass

    # ── M2M relations helper ───────────────────────────────────
    def _ids(key):
        raw = exam_data.get(key, [])
        if isinstance(raw, list):
            return [int(v) for v in raw if str(v).isdigit()]
        return []

    t_ids = _ids('topics')
    if t_ids and 'all' not in [str(v) for v in exam_data.get('topics', [])]:
        selected_topics = Topic.objects.filter(pk__in=t_ids)
    else:
        selected_topics = Topic.objects.filter(subject=subject)

    o_ids = _ids('learning_outcomes')
    selected_outcomes = LearningOutcome.objects.filter(pk__in=o_ids) if o_ids else LearningOutcome.objects.none()

    # Rúbricas elegidas en el wizard: se filtran por get_visible_rubrics
    # (propias + compartidas por grupo) para que un rubric_id ajeno colado a
    # mano en el POST no se pueda adjuntar a un examen propio.
    from .content_visibility import get_visible_rubrics
    r_ids = _ids('rubric_ids')
    selected_rubrics = list(get_visible_rubrics(request.user).filter(pk__in=r_ids)) if r_ids else []

    versions_count = 1
    try:
        versions_count = max(1, int(exam_data.get('num_versions') or 1))
    except (ValueError, TypeError):
        versions_count = 1

    q_ids = _ids('questions')
    questions_per_version = None
    try:
        raw_qpv = int(exam_data.get('questions_per_version') or 0)
        if raw_qpv > 0:
            questions_per_version = raw_qpv
    except (ValueError, TypeError):
        pass

    if questions_per_version is None:
        questions_per_version = len(q_ids) if q_ids else max(1, selected_topics.count())

    if selected_topics.count() == 0:
        return _error('Debe seleccionar al menos un tópico para generar temas.')

    preview_version_ids = request.session.get('preview_generated_versions_ids') or []
    if versions_count > 1 or preview_version_ids:
        _ensure_exam_version_schema()

    has_exam_version_fields, has_batch_table = _get_exam_version_schema_state()
    supports_version_batches = has_exam_version_fields and has_batch_table
    exam_columns = _get_table_columns(Exam._meta.db_table)
    expected_exam_columns = {
        field.column for field in Exam._meta.local_concrete_fields
        if field.column and not field.primary_key
    }
    has_full_exam_write_schema = bool(exam_columns) and expected_exam_columns.issubset(exam_columns)

    from .content_visibility import get_visible_questions, EXAM_ELIGIBLE_Q
    include_seed = bool(exam_data.get('include_seed'))

    if preview_version_ids:
        chosen_versions = [
            list(get_visible_questions(request.user, include_seed=include_seed).filter(
                EXAM_ELIGIBLE_Q, pk__in=version_ids,
            ).distinct())
            for version_ids in preview_version_ids
            if version_ids
        ]
        versions_count = len(chosen_versions) if chosen_versions else versions_count
    elif q_ids:
        if versions_count == 1:
            chosen_versions = [list(get_visible_questions(
                request.user, include_seed=include_seed
            ).filter(
                EXAM_ELIGIBLE_Q,
                pk__in=q_ids,
            ).distinct())]
        else:
            balance_by_topic = str(exam_data.get('balance_by_topic', '1')) == '1'
            chosen_versions = _pick_questions_for_versions(
                subject=subject,
                selected_topics=selected_topics,
                user=request.user,
                versions_count=versions_count,
                questions_per_version=questions_per_version,
                balance_by_topic=balance_by_topic,
                allowed_question_ids=q_ids,
                include_seed=include_seed,
            )
    else:
        balance_by_topic = str(exam_data.get('balance_by_topic', '1')) == '1'
        chosen_versions = _pick_questions_for_versions(
            subject=subject,
            selected_topics=selected_topics,
            user=request.user,
            versions_count=versions_count,
            questions_per_version=questions_per_version,
            balance_by_topic=balance_by_topic,
            include_seed=include_seed,
        )
    if not chosen_versions or not chosen_versions[0]:
        return _error('No hay preguntas suficientes para generar el examen.')

    editing_exam_id = request.session.get('editing_exam_id')
    editing_exam = None
    if str(editing_exam_id).isdigit():
        editing_exam = _get_compatible_exam_queryset().filter(pk=int(editing_exam_id), created_by=request.user).first()

    try:
        with transaction.atomic():
            # El nombre puede venir editado desde la pantalla de validacion de
            # preguntas (preview_exam_versions.html), que lo manda en el POST
            # del guardado; si no, se usa lo que ya habia en el form original.
            batch_name = (request.POST.get('batch_name') or exam_data.get('batch_name') or '').strip()
            if not batch_name:
                batch_name = _suggest_batch_name(subject, exam_data, institution_name, versions_count, year)

            batch = None
            if supports_version_batches and editing_exam is None and versions_count > 1:
                batch = ExamVersionBatch.objects.create(
                    name=batch_name,
                    created_by=request.user,
                    subject=subject,
                    institution_name=institution_name,
                    exam_type=exam_type or '',
                    semester=exam_data.get('batch_semester') or '',
                    year=year,
                    version_count=versions_count,
                    questions_per_version=questions_per_version,
                )

            created_exams = []

            if editing_exam is not None:
                exam_kwargs = {
                    'title': title,
                    'subject': subject,
                    'duration_minutes': duration,
                    'instructions': exam_data.get('instructions') or '',
                    'institution_name': institution_name,
                    'faculty_name': faculty_name,
                    'campus_name': campus_name,
                    'career_name': career_name,
                    'professor': professor,
                    'exam_type': exam_type,
                    'exam_mode': exam_mode,
                    'exam_group': exam_group,
                    'shift': shift,
                    'year': year,
                    'date_str': fecha,
                    'resolution_time': resolution_time or None,
                    'alumno': exam_data.get('alumno') or '',
                    'curso': exam_data.get('curso') or '',
                    'topics_to_evaluate': exam_data.get('topics_to_evaluate') or None,
                }
                for field_name, field_value in exam_kwargs.items():
                    setattr(editing_exam, field_name, field_value)
                editing_exam.save()
                editing_exam.topics.set(selected_topics)
                editing_exam.learning_outcomes.set(selected_outcomes)
                editing_exam.questions.set(chosen_versions[0])
                _apply_rubrics_to_exam(editing_exam, selected_rubrics)
                _safe_assign_print_format(editing_exam)
                created_exams.append(editing_exam)

            for idx, version_questions in enumerate(chosen_versions, start=1):
                if editing_exam is not None:
                    break
                exam_kwargs = {
                    'title': f"{title} - Version {idx}",
                    'subject': subject,
                    'created_by': request.user,
                    'duration_minutes': duration,
                    'instructions': exam_data.get('instructions') or '',
                    'institution_name': institution_name,
                    'faculty_name': faculty_name,
                    'campus_name': campus_name,
                    'career_name': career_name,
                    'professor': professor,
                    'exam_type': exam_type,
                    'exam_mode': exam_mode,
                    'exam_group': exam_group,
                    'shift': shift,
                    'year': year,
                    'date_str': fecha,
                    'resolution_time': resolution_time or None,
                    'alumno': exam_data.get('alumno') or '',
                    'curso': exam_data.get('curso') or '',
                    'topics_to_evaluate': exam_data.get('topics_to_evaluate') or None,
                }
                if supports_version_batches and batch is not None:
                    exam_kwargs['version_batch'] = batch
                    exam_kwargs['version_number'] = idx

                if has_full_exam_write_schema:
                    exam_obj = ExamModel.objects.create(**exam_kwargs)
                    exam_obj.topics.set(selected_topics)
                    if selected_outcomes.exists():
                        exam_obj.learning_outcomes.set(selected_outcomes)
                    exam_obj.questions.set(version_questions)
                else:
                    exam_obj = _create_exam_with_compatible_schema(
                        exam_kwargs,
                        selected_topics,
                        selected_outcomes,
                        version_questions,
                    )
                _apply_rubrics_to_exam(exam_obj, selected_rubrics)
                _safe_assign_print_format(exam_obj)
                created_exams.append(exam_obj)
    except Exception:
        logger.exception('Error guardando examenes desde /save-exam/.')
        return _error('No se pudo guardar el examen. Intenta nuevamente en unos segundos.')

    del request.session['preview_exam']
    request.session.pop('preview_generated_versions_ids', None)
    request.session.pop('editing_exam_id', None)

    if batch is not None:
        success_message = f'Se guardo el lote "{batch.name}" con {len(created_exams)} versiones.'
        success_redirect = ('material:view_exam_batch', {'batch_id': batch.id})
    elif editing_exam is not None:
        success_message = 'Examen actualizado correctamente.'
        success_redirect = ('material:mis_examenes', {})
    elif versions_count > 1:
        # Se pidieron varias versiones pero el esquema de lotes no esta disponible todavia.
        success_message = (
            f'Se guardaron {len(created_exams)} examen(es) individuales. '
            'El agrupado por versiones quedara disponible cuando se apliquen las migraciones pendientes.'
        )
        success_redirect = ('material:mis_examenes', {})
    else:
        success_message = 'Examen guardado correctamente.'
        success_redirect = ('material:mis_examenes', {})

    # ONBOARDING WIZARD V2: si el examen se guardó estando en modo asistente,
    # cerramos el flujo llevando a la pantalla final del wizard en vez de a
    # "mis exámenes" directamente.
    wizard_finished = bool(request.session.pop('onb2_wizard_active', False))

    if is_ajax:
        return JsonResponse({
            'success': True,
            'message': success_message,
            'redirect_url': reverse('material:onboarding_v2_finish') if wizard_finished else reverse('material:mis_examenes'),
            'created_exam_ids': [e.pk for e in created_exams],
        })

    messages.success(request, success_message, extra_tags='examenes')
    if wizard_finished:
        return redirect('material:onboarding_v2_finish')
    return redirect(success_redirect[0], **success_redirect[1])

@login_required
def create_exam_template(request):
    from .content_visibility import get_visible_subjects

    # Obtener instituciones del usuario
    user_institutions = InstitutionV2.objects.filter(
        userinstitution__user=request.user,
        is_active=True
    )

    # Materias visibles del usuario (propias + compartidas vía grupos de
    # confianza). Antes se derivaban de compartir institución con otro
    # docente (subject_institutions__institution__in=user_institutions):
    # las instituciones son públicas a propósito (cualquiera puede unirse),
    # así que ese filtro dejaba ver las materias de cualquier otro docente
    # de la misma institución. Ver [[project_subject_topic_global_sharing_bug]].
    subjects = get_visible_subjects(request.user)

    if request.method == 'POST':
        form = ExamTemplateForm(
            request.POST, 
            request.FILES, 
            user=request.user
        )
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    exam_template = form.save(commit=False)
                    exam_template.created_by = request.user
                    exam_template.save()
                    form.save_m2m()

                    # ── Poblar snapshots ──
                    exam_template.institution_name_snapshot = exam_template.institution.name if exam_template.institution_id else ''
                    exam_template.faculty_name_snapshot     = exam_template.faculty.name     if exam_template.faculty_id     else ''
                    exam_template.campus_name_snapshot      = exam_template.campus.name      if exam_template.campus_id      else ''
                    exam_template.career_name_snapshot      = exam_template.career.name      if exam_template.career_id      else ''
                    exam_template.subject_name_snapshot     = exam_template.subject.name     if exam_template.subject_id     else ''
                    exam_template.outcomes_snapshot = list(
                        exam_template.learning_outcomes.values_list('description', flat=True)
                    )
                    exam_template.save(update_fields=[
                        'institution_name_snapshot', 'faculty_name_snapshot', 'campus_name_snapshot',
                        'career_name_snapshot', 'subject_name_snapshot', 'outcomes_snapshot',
                    ])

                    InstitutionLog.objects.create(
                        institution=exam_template.institution,
                        user=request.user,
                        action=f"Creó plantilla de examen: {exam_template}"
                    )
                    
                    messages.success(
                        request, 
                        'Plantilla creada correctamente',
                        extra_tags='plantillas'
                    )
                    return redirect('material:list_exam_templates')
                    
            except Exception as e:
                logger.error(f"Error creating exam template: {str(e)}")
                messages.error(
                    request,
                    'Error al guardar la plantilla. Detalles en logs.',
                    extra_tags='danger'
                )
    else:
        form = ExamTemplateForm(user=request.user)
    
    context = {
        'form': form,
        'subjects': subjects,
        'learning_outcomes': LearningOutcome.objects.filter(
            subject__in=subjects
        ).select_related('subject'),
        'current_institution': request.GET.get('institution_id'),
        'exam_modes': ExamTemplate.EXAM_MODE_CHOICES,
        'time_units': [
            {'value': 'minutes', 'label': 'Minutos'},
            {'value': 'hours', 'label': 'Horas'},
            {'value': 'days', 'label': 'Días'}
        ]
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        institution_id = request.GET.get('institution_id')
        if institution_id:
            # Se filtra dentro de las materias visibles del usuario, no de
            # todas las de la institución — antes esto devolvía outcomes de
            # cualquier institución con solo pasar su ID por querystring,
            # sin chequear que el usuario perteneciera a ella.
            institution_subjects = subjects.filter(
                subject_institutions__institution_id=institution_id
            )
            outcomes = LearningOutcome.objects.filter(
                subject__in=institution_subjects
            ).values('id', 'name', 'subject__name')
            return JsonResponse(list(outcomes), safe=False)
        return JsonResponse([], safe=False)
    
    return render(
        request,
        'material/exams/create_exam_template.html',
        context
    )


@require_POST
@login_required
def preview_exam_template(request):
    try:
        # Validación básica
        if not all(request.POST.get(field) for field in ['institution', 'faculty', 'career', 'subject']):
            return JsonResponse({'error': 'Faltan campos requeridos'}, status=400)

        # Procesar outcomes seleccionados
        selected_outcomes = request.POST.get('learning_outcomes', '').split(',')
        selected_outcomes = [oid.strip() for oid in selected_outcomes if oid.strip()]

        # Obtener datos para el preview
        institution = InstitutionV2.objects.get(id=request.POST['institution'])
        faculty = FacultyV2.objects.get(id=request.POST['faculty'])
        career = Career.objects.get(id=request.POST['career'])
        subject = Subject.objects.get(id=request.POST['subject'])
        professor = User.objects.get(id=request.POST.get('professor', request.user.id))

        # Si ya se eligió un formato de impresión en el form (antes de
        # guardar la plantilla), la vista previa lo respeta — mismo criterio
        # que view_exam_template una vez guardada.
        print_format_id = request.POST.get('print_format')
        chosen_print_format = get_visible_print_formats(request.user).filter(
            pk=print_format_id
        ).first() if print_format_id else None

        # Obtener los outcomes seleccionados del modelo LearningOutcome
        outcomes_to_display = []
        if selected_outcomes:
            outcomes = LearningOutcome.objects.filter(
                id__in=selected_outcomes,
                subject=subject
            )
            outcomes_to_display = [
                {
                    'description': outcome.description
                }
                for outcome in outcomes
            ]

        # Crear un objeto exam-like para compatibilidad con el template base.
        # 'instructions' vacío a propósito — mismo criterio que view_exam_template:
        # una plantilla solo tiene notes_and_recommendations, no un segundo
        # campo de texto libre.
        exam_data = {
            'title': '',  # Las plantillas no tienen título por defecto
            'instructions': '',
            'tipo_examen': request.POST.get('exam_type', ''),
            'tipo_modalidad': request.POST.get('exam_mode', ''),
            'modalidad_resolucion': [],  # No disponible en plantillas
            'alumno': '',  # Campo vacío para plantillas
            'fecha': '',  # Campo vacío para plantillas
            'year': '',  # Las plantillas no tienen año: se muestra en blanco
            'curso': '',  # No disponible en plantillas
            'turno': '',  # No disponible en plantillas
            'sede': ''   # No disponible en plantillas
        }

        context = {
            'exam': exam_data,  # Objeto exam para compatibilidad
            'institution': institution,
            'faculty': faculty,
            'career': career,
            'subject': subject,
            'professor': professor,
            'exam_mode': request.POST.get('exam_mode', ''),
            'exam_type': request.POST.get('exam_type', ''),
            'notes_and_recommendations': request.POST.get('notes_and_recommendations', ''),
            'learning_outcomes': outcomes_to_display,
            'current_date': '',  # Las plantillas no tienen fecha: se muestra en blanco
            'print_style': get_print_style_context(
                chosen_print_format or resolve_print_format_for_context(user=request.user, institution=institution)
            ),
            'back_url': reverse('material:list_exam_templates'),
        }

        return render(request, 'material/exams/preview_exam_template.html', context)

    except Exception as e:
        logger.error(f"Preview error: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def edit_exam_template(request, template_id):
    """Vista para editar una plantilla de examen existente"""
    try:
        template = ExamTemplate.objects.get(
            id=template_id,
            created_by=request.user
        )
    except ExamTemplate.DoesNotExist:
        messages.error(request, 'La plantilla no existe o no tienes permisos para editarla.', extra_tags='plantillas')
        return redirect('material:list_exam_templates')

    if request.method == 'POST':
        # Debug: Ver qué datos se están enviando
        print(f"DEBUG: Datos POST recibidos: {dict(request.POST)}")
        
        form = ExamTemplateForm(request.POST, instance=template, user=request.user)
        
        # Debug: Información del template original
        print(f"DEBUG: Template original ID: {template.id}")
        print(f"DEBUG: Template original created_by: {template.created_by}")
        print(f"DEBUG: Form instance ID antes de validar: {form.instance.id if hasattr(form, 'instance') else 'No instance'}")
        print(f"DEBUG: Form instance es el mismo objeto?: {form.instance is template}")
        
        if form.is_valid():
            try:
                # Verificar que el formulario mantenga la instancia correcta
                exam_template = form.save(commit=False)
                
                print(f"DEBUG: Después de form.save(commit=False):")
                print(f"  - ID: {exam_template.id}")
                print(f"  - PK: {exam_template.pk}")
                print(f"  - created_by: {exam_template.created_by}")
                print(f"  - Es el mismo objeto que el template original?: {exam_template is template}")
                
                # Verificar si hay algún campo que esté causando problemas
                print(f"DEBUG: Campos del formulario cambiados: {form.changed_data}")
                
                # Guardar
                exam_template.save()
                form.save_m2m()

                # ── Actualizar snapshots (el usuario editó conscientemente la plantilla) ──
                exam_template.institution_name_snapshot = exam_template.institution.name if exam_template.institution_id else ''
                exam_template.faculty_name_snapshot     = exam_template.faculty.name     if exam_template.faculty_id     else ''
                exam_template.campus_name_snapshot      = exam_template.campus.name      if exam_template.campus_id      else ''
                exam_template.career_name_snapshot      = exam_template.career.name      if exam_template.career_id      else ''
                exam_template.subject_name_snapshot     = exam_template.subject.name     if exam_template.subject_id     else ''
                exam_template.outcomes_snapshot = list(
                    exam_template.learning_outcomes.values_list('description', flat=True)
                )
                exam_template.save(update_fields=[
                    'institution_name_snapshot', 'faculty_name_snapshot', 'campus_name_snapshot',
                    'career_name_snapshot', 'subject_name_snapshot', 'outcomes_snapshot',
                ])
                
                print(f"DEBUG: Después de save():")
                print(f"  - ID final: {exam_template.id}")
                print(f"  - PK final: {exam_template.pk}")
                
                # Verificar en la base de datos
                updated_template = ExamTemplate.objects.get(id=template_id)
                print(f"DEBUG: Template desde DB - ID: {updated_template.id}, created_by: {updated_template.created_by}")
                
                messages.success(request, f'Plantilla con ID {exam_template.id} actualizada exitosamente.', extra_tags='plantillas')
                return redirect('material:list_exam_templates')
                
            except Exception as e:
                print(f"DEBUG: Error al guardar: {str(e)}")
                import traceback
                traceback.print_exc()
                messages.error(request, f'Error al actualizar la plantilla: {str(e)}', extra_tags='plantillas')
        else:
            print(f"DEBUG: Errores del formulario: {form.errors}")
            print(f"DEBUG: Non-field errors: {form.non_field_errors()}")
            messages.error(request, 'Por favor corrige los errores en el formulario.', extra_tags='plantillas')
    else:
        # GET request - crear formulario con la instancia existente
        form = ExamTemplateForm(instance=template, user=request.user)

    # Materias visibles del usuario (propias + compartidas). El fallback
    # anterior (request.user.profile.institutions, campo v1 ya muerto desde
    # el rediseño de instituciones) siempre resultaba en lista vacía, así
    # que en la práctica esto mostraba SIEMPRE todas las materias del
    # sistema sin excepción. Ver [[project_subject_topic_global_sharing_bug]].
    from .content_visibility import get_visible_subjects
    subjects = get_visible_subjects(request.user)

    context = {
        'form': form,
        'subjects': subjects,
        'learning_outcomes': LearningOutcome.objects.filter(
            subject__in=subjects
        ).select_related('subject'),
        'current_institution': template.institution.id if template.institution else None,
        'exam_modes': ExamTemplate.EXAM_MODE_CHOICES,
        'time_units': [
            {'value': 'minutes', 'label': 'Minutos'},
            {'value': 'hours', 'label': 'Horas'},
            {'value': 'days', 'label': 'Días'}
        ],
        'template': template,  # Para referencia adicional si es necesario
        'edit_mode': True,     # Indicar que estamos en modo edición
    }
    
    return render(request, 'material/exams/create_exam_template.html', context)

@login_required
def view_exam_template(request, template_id):
    """Vista específica para ver plantillas guardadas (GET)"""
    try:
        template = ExamTemplate.objects.get(
            id=template_id,
            created_by=request.user
        )
    except ExamTemplate.DoesNotExist:
        raise Http404("La plantilla no existe o no tienes permisos para verla")

    outcomes_to_display = [
        {'description': outcome.description}
        for outcome in template.learning_outcomes.all()
    ]

    # Crear un objeto exam-like para compatibilidad con el template base.
    # 'instructions' queda vacío a propósito: una plantilla solo tiene un
    # campo de texto libre (notes_and_recommendations, ver abajo) — antes
    # se repetía acá también y el preview mostraba el mismo párrafo dos
    # veces, como "Instrucciones generales" Y "Notas y recomendaciones".
    exam_data = {
        'title': getattr(template, 'title', ''),
        'instructions': '',
        'tipo_examen': template.get_exam_type_display(),
        'tipo_modalidad': template.get_exam_mode_display(),
        'curso': '',
        'turno': '',
        'sede': '',
        'alumno': '',
        'fecha': '',  # Las plantillas no tienen fecha: se muestra en blanco
        'year': '',  # Las plantillas no tienen año: se muestra en blanco
        'modalidad_resolucion': '',
    }

    context = {
        'exam': exam_data,
        'template_id': template.id,
        'template_name': str(template),
        'institution': template.institution,
        'faculty': template.faculty,
        'career': template.career,
        'subject': template.subject,
        'professor': template.professor,
        'exam_mode': template.get_exam_mode_display(),
        'exam_type': template.get_exam_type_display(),
        'notes_and_recommendations': template.notes_and_recommendations,
        'learning_outcomes': outcomes_to_display,
        'rubric_grids': [_prepare_rubric_grid(r) for r in template.rubrics.all()],
        'current_date': '',  # Las plantillas no tienen fecha: se muestra en blanco
        'is_preview': False,
        # El formato elegido en la plantilla es más específico que los
        # defaults de usuario/institución — se usa primero si está seteado,
        # y solo si no, se cae a la cadena de siempre.
        'print_style': get_print_style_context(
            template.print_format or resolve_print_format_for_context(user=request.user, institution=template.institution)
        ),
        'back_url': _safe_next_url(request, reverse('material:list_exam_templates')),
    }

    return render(request, 'material/exams/preview_exam_template.html', context)

@login_required
@transaction.atomic
def save_exam_template(request):
    if request.method == 'POST':
        try:
            # No pasa por ExamTemplateForm (este endpoint arma el dict a mano
            # desde POST) — el formato elegido se valida igual que en
            # toggle_favorite: solo uno visible para este usuario, nunca
            # confiando en el ID crudo del POST.
            print_format_id_raw = request.POST.get('print_format')
            print_format_obj = None
            if print_format_id_raw and print_format_id_raw.isdigit():
                print_format_obj = get_visible_print_formats(request.user).filter(pk=print_format_id_raw).first()

            # Campos de contenido — se aplican tanto al crear una plantilla
            # nueva como al actualizar una existente (save_mode='update').
            # created_by/year quedan afuera a propósito: son metadata de
            # creación, no algo que "editar" deba tocar.
            content_fields = {
                'name': request.POST.get('name', '').strip(),
                'institution_id': request.POST.get('institution'),
                'faculty_id': request.POST.get('faculty'),
                'career_id': request.POST.get('career'),
                'subject_id': request.POST.get('subject'),
                'exam_mode': request.POST.get('exam_mode'),
                'exam_type': request.POST.get('exam_type'),
                'campus_id': request.POST.get('campus'),
                'professor_id': request.POST.get('professor', request.user.id),
                'notes_and_recommendations': request.POST.get('notes_and_recommendations', ''),
                'print_format': print_format_obj,
            }

            # Validación mínima
            required_fields = ['institution_id', 'faculty_id', 'career_id', 'subject_id']
            if not all(content_fields[field] for field in required_fields):
                return JsonResponse({
                    'success': False,
                    'error': 'Institución, Facultad, Carrera y Materia son requeridos'
                }, status=400)

            # 'update' pisa la plantilla que se está editando en vez de crear
            # una nueva — antes esto NUNCA pasaba (no se leía template_id en
            # ningún lado), así que "Editar" en realidad siempre creaba una
            # copia sin que nadie lo pidiera. Ahora es una elección explícita
            # del usuario (botón "Guardar" vs "Guardar como copia"). Se
            # revalida el dueño acá — nunca alcanza con que el ID venga en
            # el POST.
            save_mode = request.POST.get('save_mode', 'copy')
            template_id = request.POST.get('template_id')
            if save_mode == 'update' and template_id and template_id.isdigit():
                exam_template = get_object_or_404(ExamTemplate, pk=template_id, created_by=request.user)
                for field, value in content_fields.items():
                    setattr(exam_template, field, value)
                exam_template.save(skip_validation=True)
                success_message = 'Plantilla actualizada correctamente'
            else:
                exam_template = ExamTemplate(
                    created_by=request.user,
                    year=timezone.now().year,
                    **content_fields,
                )
                exam_template.save(skip_validation=True)
                success_message = 'Plantilla guardada correctamente'

            # Manejar outcomes
            outcomes_ids = []
            if 'learning_outcomes[]' in request.POST:
                outcomes_ids = request.POST.getlist('learning_outcomes[]')
            elif 'learning_outcomes' in request.POST:
                outcomes_str = request.POST.get('learning_outcomes', '')
                outcomes_ids = [x for x in outcomes_str.split(',') if x]

            if outcomes_ids:
                outcomes = LearningOutcome.objects.filter(
                    id__in=outcomes_ids,
                    subject_id=content_fields['subject_id']
                )
                exam_template.learning_outcomes.set(outcomes)
            elif save_mode == 'update':
                # A diferencia de crear (donde "vacío" es el estado inicial
                # normal), en un update explícito vaciar la lista es una
                # elección real del usuario y hay que respetarla.
                exam_template.learning_outcomes.clear()

            # Manejar rúbricas — mismo patrón que outcomes arriba, filtradas
            # por get_visible_rubrics para que no se pueda colar por POST el
            # ID de una rúbrica ajena/no compartida.
            rubric_ids = []
            if 'rubrics[]' in request.POST:
                rubric_ids = request.POST.getlist('rubrics[]')
            elif 'rubrics' in request.POST:
                rubrics_str = request.POST.get('rubrics', '')
                rubric_ids = [x for x in rubrics_str.split(',') if x]

            if rubric_ids:
                from .content_visibility import get_visible_rubrics
                rubrics = get_visible_rubrics(request.user).filter(id__in=rubric_ids)
                exam_template.rubrics.set(rubrics)
            elif save_mode == 'update':
                exam_template.rubrics.clear()

            return JsonResponse({
                'success': True,
                'message': success_message,
                'template_id': exam_template.id
            })

        except Http404:
            return JsonResponse({
                'success': False,
                'error': 'La plantilla no existe o no te pertenece.'
            }, status=404)

        except IntegrityError as e:
            return JsonResponse({
                'success': False,
                'error': 'Error de integridad en la base de datos: ' + str(e)
            }, status=400)

        except Exception as e:
            logger.error(f"Error saving exam template: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'Error interno: ' + str(e)
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    }, status=405)

# Definicion de columnas filtrables de las plantillas de examen, usando el motor
# generico de material/column_filters.py (tambien usado por "Mis examenes").
EXAM_TEMPLATE_FILTER_FIELDS = [
    ColumnFilterField('institution', 'Institución', label_field='institution__name'),
    ColumnFilterField('faculty', 'Facultad', label_field='faculty__name'),
    ColumnFilterField('career', 'Carrera', label_field='career__name'),
    ColumnFilterField('subject', 'Materia', label_field='subject__name'),
    ColumnFilterField('professor', 'Profesor', label_fields=['professor__first_name', 'professor__last_name']),
    ColumnFilterField('year', 'Año'),
    ColumnFilterField('exam_type', 'Tipo', choices=ExamTemplate.EXAM_TYPE_CHOICES),
]

EXAM_TEMPLATE_FILTER_COLUMNS = [{'field': f.name, 'label': f.label} for f in EXAM_TEMPLATE_FILTER_FIELDS]

# Columnas filtrables de "Mis preguntas". 'subject' y 'ai_status' no pasan por
# el motor generico: 'subject' es M2M con fallback a topic__subject para
# preguntas viejas, y 'ai_status' combina generated_by_ai + ai_approved en un
# unico set de estados (ver _apply_subject_filter/_apply_ai_status_filter).
QUESTION_FILTER_FIELDS = [
    ColumnFilterField('topic', 'Tópico', label_field='topic__name'),
    ColumnFilterField('subtopic', 'Sub-tópico', label_field='subtopic__name'),
    ColumnFilterField('bloom_level', 'Bloom', choices=[
        (1, 'N1 — Recordar'), (2, 'N2 — Comprender'), (3, 'N3 — Aplicar'),
        (4, 'N4 — Analizar'), (5, 'N5 — Evaluar'), (6, 'N6 — Crear'),
    ]),
]
QUESTION_AI_STATUS_OPTIONS = [
    {'value': 'aprobada', 'label': '✅ Aprobada'},
    {'value': 'rechazada', 'label': '❌ Rechazada'},
    {'value': 'sin_revisar', 'label': '⏳ Sin revisar'},
]
QUESTION_FILTER_COLUMNS = [
    {'field': 'subject', 'label': 'Materia'},
    {'field': 'topic', 'label': 'Tópico'},
    {'field': 'subtopic', 'label': 'Sub-tópico'},
    {'field': 'bloom_level', 'label': 'Bloom'},
    {'field': 'ai_status', 'label': 'Estado IA'},
]


def _apply_subject_filter(qs, raw_values):
    ids = [v for v in raw_values if str(v).isdigit()]
    quiere_sin_materia = NONE_VALUE in raw_values
    if not ids and not quiere_sin_materia:
        return qs
    q = Q()
    if ids:
        q |= Q(subjects__id__in=ids) | Q(subjects__isnull=True, topic__subject_id__in=ids)
    if quiere_sin_materia:
        q |= Q(subjects__isnull=True) & (Q(topic__isnull=True) | Q(topic__subject__isnull=True))
    return qs.filter(q).distinct()


def _apply_ai_status_filter(qs, statuses):
    if not statuses:
        return qs
    q = Q()
    matched = False
    if 'aprobada' in statuses:
        q |= Q(generated_by_ai=True, ai_approved=True)
        matched = True
    if 'rechazada' in statuses:
        q |= Q(generated_by_ai=True, ai_approved=False)
        matched = True
    if 'sin_revisar' in statuses:
        q |= Q(generated_by_ai=True, ai_approved__isnull=True)
        matched = True
    return qs.filter(q) if matched else qs


def _apply_column_filters_from_params(qs, fields, params):
    """Como apply_column_filters de column_filters.py, pero recibe un
    QueryDict directamente (request.GET o request.POST) en vez de asumir
    siempre request.GET; lo necesitan bulk_eliminar_preguntas y
    exportar_preguntas, que reciben los filtros vigentes como inputs
    ocultos en un POST."""
    for f in fields:
        values = params.getlist(f.name)
        if values:
            qs = _apply_field_filter(qs, f, values)
    return qs


def _build_question_subject_options(qs):
    """Opciones de la columna Materia: union de materias asignadas por M2M
    y, para preguntas viejas sin M2M, la materia del tema (topic__subject)."""
    seen = {}
    m2m_rows = qs.exclude(subjects__isnull=True).values_list('subjects__id', 'subjects__name').distinct()
    legacy_rows = qs.filter(subjects__isnull=True, topic__subject__isnull=False) \
        .values_list('topic__subject__id', 'topic__subject__name').distinct()
    for sid, sname in list(m2m_rows) + list(legacy_rows):
        seen[str(sid)] = sname
    options = sorted(({'value': v, 'label': l} for v, l in seen.items()), key=lambda o: o['label'])
    sin_materia = qs.filter(subjects__isnull=True).filter(
        Q(topic__isnull=True) | Q(topic__subject__isnull=True)
    ).exists()
    if sin_materia:
        options = [{'value': NONE_VALUE, 'label': 'Sin Materia'}] + options
    return options


@login_required
def list_exam_templates(request):
    # Consulta optimizada con select_related y prefetch_related
    base_templates = ExamTemplate.objects.filter(
        created_by=request.user
    ).select_related(
        'institution',
        'faculty',
        'career',
        'subject',
        'professor'
    ).prefetch_related(
        'learning_outcomes'
    )

    selected_filters = get_selected_filters(request, EXAM_TEMPLATE_FILTER_FIELDS)
    filter_options = get_filter_options(base_templates, EXAM_TEMPLATE_FILTER_FIELDS, selected_filters)
    templates = apply_column_filters(request, base_templates, EXAM_TEMPLATE_FILTER_FIELDS).order_by('-created_at')

    favorite_ids = set(Favorite.objects.filter(
        user=request.user, content_type=ContentType.objects.get_for_model(ExamTemplate)
    ).values_list('object_id', flat=True))
    only_favorites = request.GET.get('favoritos') == '1'
    if only_favorites:
        templates = templates.filter(pk__in=favorite_ids)

    # Paginación
    paginator = Paginator(templates, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'exam_templates': page_obj,
        'filter_options': filter_options,
        'selected_filters': selected_filters,
        'active_filter_count': get_active_filter_count(selected_filters),
        'filter_querystring': get_filter_querystring(request),
        'filter_columns': [c for c in EXAM_TEMPLATE_FILTER_COLUMNS if c['field'] != 'exam_type'],
        'favorite_ids': favorite_ids,
        'only_favorites': only_favorites,
        'favorites_toggle_querystring': get_filter_querystring_excluding(request, 'favoritos'),
    }

    return render(request, 'material/exams/list_exam_templates.html', context)

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('material:index')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def mis_invitaciones(request):
    """Panel de administración: genera links de invitación de un solo uso
    para dar de alta cuentas nuevas (ver invitacion_aceptar)."""
    from .models import Invitation

    if not is_admin(request.user):
        messages.error(request, 'No hay permiso para acceder a esta sección.')
        return redirect('material:index')

    if request.method == 'POST':
        Invitation.objects.create(created_by=request.user)
        return redirect('material:mis_invitaciones')

    invitations = Invitation.objects.select_related('created_by', 'used_by')
    items = [
        {
            'invitation': inv,
            'link': settings.PUBLIC_BASE_URL.rstrip('/') + reverse(
                'material:invitacion_aceptar', args=[inv.token]
            ),
        }
        for inv in invitations
    ]
    return render(request, 'material/mis_invitaciones.html', {'items': items})


def invitacion_aceptar(request, token):
    """Formulario público (sin login) que reclama una Invitation: crea la
    cuenta con los datos cargados acá y loguea directo, dejando que
    OnboardingGateMiddleware lleve al wizard habitual porque la pregunta de
    seguridad ya queda seteada y onboarding_completed sigue en False."""
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError
    from .models import Invitation, Profile

    invitation = get_object_or_404(Invitation, token=token)
    if invitation.is_used():
        return render(request, 'registration/invitacion_aceptar.html', {'invitation_used': True})

    errors = []
    posted = {}
    if request.method == 'POST':
        posted = request.POST
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        p1 = request.POST.get('password1', '')
        p2 = request.POST.get('password2', '')
        security_question = request.POST.get('security_question', '')
        security_answer = request.POST.get('security_answer', '').strip()
        valid_questions = dict(Profile.SECURITY_QUESTION_CHOICES)

        if not first_name:
            errors.append('Completar el nombre.')
        if not last_name:
            errors.append('Completar el apellido.')
        if not username:
            errors.append('Completar el usuario.')
        elif User.objects.filter(username=username).exists():
            errors.append('Ese nombre de usuario ya está en uso.')
        if p1 != p2:
            errors.append('Las contraseñas no coinciden.')
        elif not p1:
            errors.append('Completar la contraseña.')
        else:
            try:
                validate_password(p1)
            except ValidationError as e:
                errors.extend(e.messages)
        if security_question not in valid_questions:
            errors.append('Elegir una pregunta de seguridad.')
        if not security_answer:
            errors.append('Completar la respuesta a la pregunta de seguridad.')

        if not errors:
            user = User.objects.create(
                username=username, first_name=first_name, last_name=last_name, email=email,
            )
            user.set_password(p1)
            user.save()
            profile = user.profile
            profile.security_question = security_question
            profile.security_answer = security_answer
            profile.save(update_fields=['security_question', 'security_answer'])

            invitation.used_at = timezone.now()
            invitation.used_by = user
            invitation.save(update_fields=['used_at', 'used_by'])

            login(request, user)
            return redirect('material:index')

    return render(request, 'registration/invitacion_aceptar.html', {
        'errors': errors,
        'posted': posted,
        'question_choices': Profile.SECURITY_QUESTION_CHOICES,
    })


@login_required
def security_question_setup(request):
    """
    Se pide una única vez, en el primer login (ver OnboardingGateMiddleware,
    que redirige acá desde '/' mientras el perfil no tenga pregunta
    configurada) — es lo que después habilita recuperar la contraseña sin
    depender de email en /accounts/recuperar/.
    """
    from .models import Profile
    profile = request.user.profile
    error = None
    if request.method == 'POST':
        question = request.POST.get('security_question', '')
        answer = request.POST.get('security_answer', '').strip()
        valid_keys = dict(Profile.SECURITY_QUESTION_CHOICES)
        if question in valid_keys and answer:
            profile.security_question = question
            profile.security_answer = answer
            profile.save(update_fields=['security_question', 'security_answer'])
            return redirect('material:index')
        error = 'Elegir una pregunta y completar una respuesta.'
    return render(request, 'material/security_question_setup.html', {
        'question_choices': Profile.SECURITY_QUESTION_CHOICES,
        'error': error,
    })


def password_reset_request(request):
    """Paso 1 de recuperación de contraseña: pide el usuario."""
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        user = User.objects.filter(username=username).first()
        has_question = bool(user and getattr(user, 'profile', None) and user.profile.security_question)
        if not has_question:
            error = 'No se encontró ese usuario, o todavía no tiene una pregunta de seguridad configurada. Contactar al administrador.'
        else:
            request.session['pwreset_username'] = username
            request.session['pwreset_attempts'] = 0
            return redirect('password_reset_question')
    return render(request, 'registration/password_reset_request.html', {'error': error})


def password_reset_question(request):
    """Paso 2: muestra la pregunta guardada del usuario y valida la respuesta."""
    from .models import Profile
    username = request.session.get('pwreset_username')
    if not username:
        return redirect('password_reset_request')
    user = User.objects.filter(username=username).first()
    if not user or not getattr(user, 'profile', None) or not user.profile.security_question:
        request.session.pop('pwreset_username', None)
        return redirect('password_reset_request')

    question_label = dict(Profile.SECURITY_QUESTION_CHOICES).get(user.profile.security_question, '')
    error = None
    if request.method == 'POST':
        answer = request.POST.get('answer', '').strip()
        saved = (user.profile.security_answer or '').strip()
        if answer and answer.lower() == saved.lower():
            request.session['pwreset_verified_username'] = username
            request.session.pop('pwreset_username', None)
            request.session.pop('pwreset_attempts', None)
            return redirect('password_reset_new')
        attempts = request.session.get('pwreset_attempts', 0) + 1
        request.session['pwreset_attempts'] = attempts
        if attempts >= 5:
            request.session.pop('pwreset_username', None)
            request.session.pop('pwreset_attempts', None)
            return render(request, 'registration/password_reset_request.html', {
                'error': 'Demasiados intentos. Volver a empezar.',
            })
        error = 'La respuesta no coincide. Intentar de nuevo.'
    return render(request, 'registration/password_reset_question.html', {
        'question_label': question_label,
        'error': error,
    })


def password_reset_new(request):
    """Paso 3: ya validada la identidad por la pregunta de seguridad, define la contraseña nueva."""
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    username = request.session.get('pwreset_verified_username')
    if not username:
        return redirect('password_reset_request')
    user = User.objects.filter(username=username).first()
    if not user:
        request.session.pop('pwreset_verified_username', None)
        return redirect('password_reset_request')

    errors = []
    if request.method == 'POST':
        p1 = request.POST.get('new_password1', '')
        p2 = request.POST.get('new_password2', '')
        if p1 != p2:
            errors.append('Las contraseñas no coinciden.')
        else:
            try:
                validate_password(p1, user=user)
            except ValidationError as e:
                errors = list(e.messages)
        if not errors:
            user.set_password(p1)
            user.save()
            request.session.pop('pwreset_verified_username', None)
            messages.success(request, 'Contraseña actualizada. Ya se puede iniciar sesión.', extra_tags='general')
            return redirect('login')
    return render(request, 'registration/password_reset_new.html', {'errors': errors})


@login_required
@user_passes_test(is_admin, login_url='/')
def user_list(request):
    # Las cuentas espejo del Área de Pruebas nunca aparecen como fila
    # propia (no son un docente) — su estado se muestra colgado de la fila
    # del docente real dueño, vía select_related('training_link__training_user').
    users = User.objects.exclude(profile__is_training_account=True).select_related('training_link__training_user')
    return render(request, 'material/user_list.html', {'users': users})

@login_required
@user_passes_test(is_admin, login_url='/')
def create_user(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario creado correctamente.', extra_tags='usuarios')
            return redirect('material:user_list')
    else:
        form = UserCreateForm()
    return render(request, 'material/create_user.html', {'form': form})

@login_required
@user_passes_test(is_admin, login_url='/')
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            was_admin = is_admin(user)
            demoting_or_deactivating = was_admin and (
                form.cleaned_data.get('role') != 'admin'
                or not form.cleaned_data.get('is_active')
            )
            if demoting_or_deactivating and user == request.user:
                messages.error(request, 'No se puede quitar el propio rol de administrador ni desactivar la propia cuenta.', extra_tags='usuarios')
                return redirect('material:edit_user', user_id=user.id)
            if demoting_or_deactivating and _is_last_active_admin(user):
                messages.error(request, 'No se puede quitar el rol de administrador ni desactivar al último administrador del sistema.', extra_tags='usuarios')
                return redirect('material:edit_user', user_id=user.id)
            form.save()
            messages.success(request, 'Usuario actualizado correctamente.', extra_tags='usuarios')
            return redirect('material:user_list')
    else:
        form = UserEditForm(instance=user)
    return render(request, 'material/edit_user.html', {'form': form, 'user': user})

@login_required
@user_passes_test(is_admin, login_url='/')
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        if user == request.user:
            messages.error(request, 'No se puede eliminar la propia cuenta.', extra_tags='usuarios')
            return redirect('material:user_list')
        if is_admin(user) and _is_last_active_admin(user):
            messages.error(request, 'No se puede eliminar al último administrador del sistema.', extra_tags='usuarios')
            return redirect('material:user_list')
        try:
            user.delete()
        except ProtectedError as e:
            messages.error(request, _protected_error_message(e), extra_tags='usuarios')
            return redirect('material:user_list')
        messages.success(request, 'Usuario eliminado correctamente.', extra_tags='usuarios')
        return redirect('material:user_list')
    return render(request, 'material/confirm_delete_user.html', {
        'user': user,
        'preview': get_delete_preview(user),
    })

@login_required
def mis_datos(request):
    # Usa UserSelfEditForm (no UserEditForm) a propósito: ese formulario no
    # expone 'role'/'is_active'/'institutions', así que un usuario no-admin
    # no puede auto-promoverse enviando esos campos por POST manual, sin
    # depender de que la plantilla los oculte.
    user = request.user
    if request.method == 'POST':
        form = UserSelfEditForm(request.POST, instance=user)
        if form.is_valid():
            if form.has_changed():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Sus cambios fueron guardados.')
            else:
                messages.info(request, 'No se realizaron cambios.')
            return redirect('material:mis_datos')
    else:
        form = UserSelfEditForm(instance=user)
    return render(request, 'material/mis_datos.html', {
        'form': form,
        'is_admin': is_admin(request.user)
    })

# Columnas filtrables de "Mis examenes". 'kind' (Individual/Lote) no es un
# campo real de DB -- es el discriminador entre Exam y ExamVersionBatch que
# se combinan en este listado -- por eso no pasa por el motor generico de
# material/column_filters.py y se resuelve a mano en la vista (ver mas abajo).
MIS_EXAMENES_FILTER_FIELDS = [
    ColumnFilterField('subject', 'Materia', label_field='subject__name'),
]
MIS_EXAMENES_KIND_OPTIONS = [
    {'value': 'exam', 'label': 'Individual'},
    {'value': 'batch', 'label': 'Lote'},
]
MIS_EXAMENES_FILTER_COLUMNS = [
    {'field': 'subject', 'label': 'Materia'},
    {'field': 'kind', 'label': 'Tipo'},
]


@login_required
def mis_examenes(request):
    has_exam_version_fields, has_batch_table = _get_exam_version_schema_state()

    try:
        examenes_qs = Exam.objects.filter(created_by=request.user).select_related('subject')

        if has_exam_version_fields:
            examenes_qs = examenes_qs.select_related('version_batch').filter(version_batch__isnull=True)
        else:
            # Evita SELECT de columnas nuevas cuando Neon no corrio las migraciones.
            examenes_qs = examenes_qs.defer('version_batch', 'version_number')

        if has_batch_table and has_exam_version_fields:
            batches_qs = ExamVersionBatch.objects.filter(created_by=request.user).select_related('subject')
        else:
            batches_qs = ExamVersionBatch.objects.none()
    except (OperationalError, ProgrammingError, DatabaseError):
        logger.warning('Esquema de examenes desfasado en produccion; degradando mis_examenes sin lotes.')
        examenes_qs = Exam.objects.filter(created_by=request.user).select_related('subject').defer('version_batch', 'version_number')
        batches_qs = ExamVersionBatch.objects.none()

    selected_filters = get_selected_filters(request, MIS_EXAMENES_FILTER_FIELDS)
    selected_kind = set(request.GET.getlist('kind'))
    selected_filters['kind'] = selected_kind

    include_exams = not selected_kind or 'exam' in selected_kind
    include_batches = not selected_kind or 'batch' in selected_kind

    option_querysets = []
    if include_exams:
        option_querysets.append(examenes_qs)
    if include_batches:
        option_querysets.append(batches_qs)
    if not option_querysets:
        option_querysets = [examenes_qs.none()]

    filter_options = get_filter_options(option_querysets, MIS_EXAMENES_FILTER_FIELDS, selected_filters)
    filter_options['kind'] = MIS_EXAMENES_KIND_OPTIONS

    examenes_qs = apply_column_filters(request, examenes_qs, MIS_EXAMENES_FILTER_FIELDS) if include_exams else examenes_qs.none()
    batches_qs = apply_column_filters(request, batches_qs, MIS_EXAMENES_FILTER_FIELDS) if include_batches else batches_qs.none()

    examenes = list(examenes_qs)
    batches = list(batches_qs)

    favorite_ids = set(Favorite.objects.filter(
        user=request.user, content_type=ContentType.objects.get_for_model(Exam)
    ).values_list('object_id', flat=True))
    batch_favorite_ids = set(Favorite.objects.filter(
        user=request.user, content_type=ContentType.objects.get_for_model(ExamVersionBatch)
    ).values_list('object_id', flat=True))
    only_favorites = request.GET.get('favoritos') == '1'
    if only_favorites:
        examenes = [e for e in examenes if e.id in favorite_ids]
        # El favorito de un lote marca el lote en sí, no cada examen que
        # contiene — no confundir con favorite_ids (Exam individual).
        batches = [b for b in batches if b.id in batch_favorite_ids]

    items = [
        {
            'kind': 'batch',
            'sort_key': batch.created_at,
            'batch': batch,
        }
        for batch in batches
    ] + [
        {
            'kind': 'exam',
            'sort_key': examen.created_at,
            'examen': examen,
        }
        for examen in examenes
    ]
    items.sort(key=lambda item: item['sort_key'], reverse=True)

    return render(request, 'material/exams/mis_examenes_new.html', {
        'items': items,
        'total_count': len(examenes) + len(batches),
        'filter_options': filter_options,
        'selected_filters': selected_filters,
        'active_filter_count': get_active_filter_count(selected_filters),
        'filter_querystring': get_filter_querystring(request),
        'filter_columns': MIS_EXAMENES_FILTER_COLUMNS,
        'favorite_ids': favorite_ids,
        'batch_favorite_ids': batch_favorite_ids,
        'only_favorites': only_favorites,
        'favorites_toggle_querystring': get_filter_querystring_excluding(request, 'favoritos'),
    })


@login_required
def view_exam_batch(request, batch_id):
    batch = get_object_or_404(ExamVersionBatch, id=batch_id, created_by=request.user)
    versions = batch.versions.all().prefetch_related('questions__topic').order_by('version_number', 'id')
    return render(request, 'material/exams/view_exam_batch.html', {
        'batch': batch,
        'versions': versions,
        'back_url': _safe_next_url(request, reverse('material:mis_examenes')),
    })


@login_required
@require_POST
def update_exam_batch_name(request, batch_id):
    batch = get_object_or_404(ExamVersionBatch, id=batch_id, created_by=request.user)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    new_name = request.POST.get('name', '').strip()

    if new_name:
        batch.name = new_name
        batch.save(update_fields=['name'])
        message = 'Nombre del lote actualizado.'
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': message,
                'redirect_url': reverse('material:mis_examenes'),
            })
        messages.success(request, message, extra_tags='examenes')
        return redirect('material:mis_examenes')

    message = 'El nombre del lote no puede estar vacio.'
    if is_ajax:
        return JsonResponse({'success': False, 'message': message})
    messages.error(request, message, extra_tags='examenes')
    return redirect('material:view_exam_batch', batch_id=batch.id)


@login_required
@require_POST
def eliminar_exam_batch(request, batch_id):
    batch = get_object_or_404(ExamVersionBatch, id=batch_id, created_by=request.user)
    with transaction.atomic():
        versions_qs = batch.versions.all()
        versions_count = versions_qs.count()
        versions_qs.delete()
        batch_name = batch.name
        batch.delete()

    messages.success(
        request,
        f'Se eliminó el lote "{batch_name}" con {versions_count} version(es).',
        extra_tags='examenes'
    )
    return redirect('material:mis_examenes')


@login_required
@require_POST
def bulk_eliminar_examenes(request):
    """Borrado multiple de 'Mis examenes': la lista mezcla Exam y
    ExamVersionBatch (dos modelos, dos endpoints de borrado individual), asi
    que cada checkbox viaja como '<kind>:<id>' (p.ej. 'exam:12', 'batch:5')
    para poder separarlos aca."""
    item_ids = request.POST.getlist('item_ids')
    exam_ids = [i.split(':', 1)[1] for i in item_ids if i.startswith('exam:')]
    batch_ids = [i.split(':', 1)[1] for i in item_ids if i.startswith('batch:')]
    exam_ids = [int(i) for i in exam_ids if i.isdigit()]
    batch_ids = [int(i) for i in batch_ids if i.isdigit()]

    if not exam_ids and not batch_ids:
        messages.error(request, 'No se seleccionó ningún examen para eliminar.', extra_tags='examenes')
        return redirect('material:mis_examenes')

    exams_count = 0
    batches_count = 0
    with transaction.atomic():
        if exam_ids:
            exams_qs = Exam.objects.filter(pk__in=exam_ids, created_by=request.user)
            exams_count = exams_qs.count()
            exams_qs.delete()
        if batch_ids:
            batches_qs = ExamVersionBatch.objects.filter(pk__in=batch_ids, created_by=request.user)
            for batch in batches_qs:
                batch.versions.all().delete()
                batch.delete()
                batches_count += 1

    parts = []
    if exams_count:
        parts.append(f'{exams_count} examen{"es" if exams_count != 1 else ""}')
    if batches_count:
        parts.append(f'{batches_count} lote{"s" if batches_count != 1 else ""}')
    messages.success(request, f'Se eliminaron {" y ".join(parts)}.', extra_tags='examenes')
    return redirect('material:mis_examenes')


@login_required
def exam_version_available_questions(request):
    exam_id = request.GET.get('exam_id')
    question_id = request.GET.get('question_id')
    if not (str(exam_id).isdigit() and str(question_id).isdigit()):
        return JsonResponse({'success': False, 'error': 'Parametros invalidos'}, status=400)

    from .content_visibility import get_visible_questions

    exam = get_object_or_404(Exam, id=int(exam_id), created_by=request.user)
    # Si el examen ya tiene alguna pregunta semilla (se sumaron con el "opt-in"
    # del wizard), el reemplazo también puede ofrecer candidatas semilla —
    # nunca al revés: un examen 100% propio nunca sugiere semilla sin que el
    # usuario lo haya elegido antes.
    include_seed = exam.questions.filter(user__username=settings.SEED_CONTENT_USERNAME).exists()
    current_question = get_object_or_404(
        get_visible_questions(request.user, include_seed=include_seed), id=int(question_id)
    )
    used_ids = set(exam.questions.values_list('id', flat=True))
    used_ids.discard(current_question.id)

    candidates = get_visible_questions(
        request.user, subject=exam.subject_id, include_seed=include_seed
    ).filter(
        topic_id=current_question.topic_id,
    ).exclude(id__in=used_ids)[:80]

    return JsonResponse({
        'success': True,
        'current_topic': current_question.topic.name if current_question.topic else '',
        'questions': [
            {'id': q.id, 'text': q.question_text, 'topic': q.topic.name if q.topic else ''}
            for q in candidates
        ]
    })


@login_required
@require_POST
def replace_exam_version_question(request):
    from .content_visibility import get_visible_questions

    exam_id = request.POST.get('exam_id')
    old_question_id = request.POST.get('old_question_id')
    new_question_id = request.POST.get('new_question_id')
    if not (str(exam_id).isdigit() and str(old_question_id).isdigit() and str(new_question_id).isdigit()):
        return JsonResponse({'success': False, 'error': 'Parametros invalidos'}, status=400)

    exam = get_object_or_404(Exam, id=int(exam_id), created_by=request.user)
    include_seed = exam.questions.filter(user__username=settings.SEED_CONTENT_USERNAME).exists()
    old_q = get_object_or_404(
        get_visible_questions(request.user, include_seed=include_seed), id=int(old_question_id)
    )
    replace_mode = request.POST.get('replace_mode', 'same_topic')

    if replace_mode == 'random_other':
        import random
        used_ids = set(exam.questions.values_list('id', flat=True))
        used_ids.discard(old_q.id)
        candidates = list(
            get_visible_questions(
                request.user, subject=exam.subject_id, include_seed=include_seed
            ).exclude(id__in=used_ids).exclude(topic_id=old_q.topic_id)
        )
        if not candidates:
            return JsonResponse({'success': False, 'error': 'No hay preguntas disponibles de otro tópico.'}, status=400)
        new_q = random.choice(candidates)
    else:
        new_q = get_object_or_404(
            get_visible_questions(request.user, include_seed=include_seed), id=int(new_question_id)
        )

    if replace_mode != 'random_other' and old_q.topic_id != new_q.topic_id:
        return JsonResponse({'success': False, 'error': 'La nueva pregunta debe ser del mismo tópico.'}, status=400)
    if exam.questions.filter(id=new_q.id).exists():
        return JsonResponse({'success': False, 'error': 'La pregunta ya esta en este tema.'}, status=400)

    exam.questions.remove(old_q)
    exam.questions.add(new_q)
    return JsonResponse({'success': True})


@login_required
def preview_exam_available_questions(request):
    version_number = request.GET.get('version_number')
    question_id = request.GET.get('question_id')
    subject_id = request.session.get('preview_exam', {}).get('subject')
    preview_versions = request.session.get('preview_generated_versions_ids') or []

    if not (str(version_number).isdigit() and str(question_id).isdigit() and str(subject_id).isdigit()):
        return JsonResponse({'success': False, 'error': 'Parametros invalidos'}, status=400)

    version_index = int(version_number) - 1
    if version_index < 0 or version_index >= len(preview_versions):
        return JsonResponse({'success': False, 'error': 'Version invalida'}, status=400)

    from .content_visibility import get_visible_questions
    include_seed = bool(request.session.get('preview_exam', {}).get('include_seed'))

    current_question = get_object_or_404(
        get_visible_questions(request.user, include_seed=include_seed), id=int(question_id)
    )
    used_ids = set(preview_versions[version_index])
    used_ids.discard(current_question.id)

    candidates = get_visible_questions(
        request.user, subject=int(subject_id), include_seed=include_seed
    ).filter(
        topic_id=current_question.topic_id,
    ).exclude(id__in=used_ids)[:80]

    return JsonResponse({
        'success': True,
        'current_topic': current_question.topic.name if current_question.topic else '',
        'questions': [
            {'id': q.id, 'text': q.question_text, 'topic': q.topic.name if q.topic else ''}
            for q in candidates
        ]
    })


@login_required
@require_POST
def preview_exam_replace_question(request):
    version_number = request.POST.get('version_number')
    old_question_id = request.POST.get('old_question_id')
    new_question_id = request.POST.get('new_question_id')
    preview_versions = request.session.get('preview_generated_versions_ids') or []

    if not (str(version_number).isdigit() and str(old_question_id).isdigit() and str(new_question_id).isdigit()):
        return JsonResponse({'success': False, 'error': 'Parametros invalidos'}, status=400)

    version_index = int(version_number) - 1
    if version_index < 0 or version_index >= len(preview_versions):
        return JsonResponse({'success': False, 'error': 'Version invalida'}, status=400)

    from .content_visibility import get_visible_questions
    include_seed = bool(request.session.get('preview_exam', {}).get('include_seed'))

    old_q = get_object_or_404(
        get_visible_questions(request.user, include_seed=include_seed), id=int(old_question_id)
    )
    replace_mode = request.POST.get('replace_mode', 'same_topic')

    if replace_mode == 'random_other':
        import random
        subject_id = request.session.get('preview_exam', {}).get('subject')
        used_ids = set(preview_versions[version_index])
        used_ids.discard(old_q.id)
        candidates = list(
            get_visible_questions(
                request.user, subject=int(subject_id), include_seed=include_seed
            ).exclude(id__in=used_ids).exclude(topic_id=old_q.topic_id)
        )
        if not candidates:
            return JsonResponse({'success': False, 'error': 'No hay preguntas disponibles de otro tópico.'}, status=400)
        new_q = random.choice(candidates)
    else:
        new_q = get_object_or_404(
            get_visible_questions(request.user, include_seed=include_seed), id=int(new_question_id)
        )

    if replace_mode != 'random_other' and old_q.topic_id != new_q.topic_id:
        return JsonResponse({'success': False, 'error': 'La nueva pregunta debe ser del mismo tópico.'}, status=400)
    if int(new_q.id) in preview_versions[version_index]:
        return JsonResponse({'success': False, 'error': 'La pregunta ya esta en este tema.'}, status=400)

    updated = list(preview_versions[version_index])
    try:
        replace_at = updated.index(int(old_question_id))
    except ValueError:
        return JsonResponse({'success': False, 'error': 'La pregunta original no esta en la version.'}, status=400)

    updated[replace_at] = int(new_q.id)
    preview_versions[version_index] = updated
    request.session['preview_generated_versions_ids'] = preview_versions
    request.session.modified = True
    return JsonResponse({'success': True})

@login_required
def ver_examen(request, pk):
    examen = _get_compatible_exam_or_404(request.user, pk)
    institution_obj = InstitutionV2.objects.filter(name__iexact=examen.institution_name).first() if examen.institution_name else None
    institution_payload = {
        'name': examen.institution_name or '-',
        'logo_b64': getattr(institution_obj, 'logo_b64', '') if institution_obj else '',
        'logo_url': (institution_obj.logo.url if institution_obj and getattr(institution_obj, 'logo', None) else ''),
    }
    questions_texts = []
    for q in examen.questions.all():
        questions_texts.append({
            'text': q.question_text,
            'type': q.question_type,
            'options': q.options or [],
            'question_image_b64': q.question_image_b64 or '',
            'answer_text': q.answer_text or '',
            'answer_image_b64': q.answer_image_b64 or '',
            'bibliographic_reference': q.bibliographic_reference or '',
        })
    outcomes_texts = [o.description for o in examen.learning_outcomes.all()]
    topics_texts = [t.name for t in examen.topics.all()]
    bloom_display = _compute_bloom_display(examen.questions.all())
    total_exam_questions = examen.questions.count()

    exam_type_display = get_exam_type_label(examen.exam_type) or '-'
    exam_mode_display = get_exam_mode_label(examen.exam_group) or '-'
    print_format = _resolve_exam_print_format_safe(examen)

    # Pass professor as dict (same shape as preview_exam) so template works identically
    if examen.professor:
        professor = {'get_full_name': examen.professor.get_full_name() or examen.professor.username}
    else:
        professor = {'get_full_name': '-'}

    # modalidad_resolucion list for template
    modalidad_list = [m.strip() for m in (examen.resolution_time or '').split(',') if m.strip()]

    try:
        rubric_grids = [
            _prepare_rubric_grid(er.rubric)
            for er in ExamRubric.objects.filter(exam=examen, show_in_exam=True)
                                        .select_related('rubric')
                                        .order_by('position', 'id')
        ]
    except (OperationalError, ProgrammingError, DatabaseError):
        logger.warning('No se pudieron cargar rubricas del examen %s; continuando sin rubricas.', examen.pk)
        rubric_grids = []

    return render(request, 'material/exams/ver_examen.html', {
        'exam': examen,
        'institution': institution_payload,
        'faculty': {'name': examen.faculty_name or '-'},
        'career': {'name': examen.career_name or '-'},
        'subject': {'name': examen.subject.name if examen.subject else '-'},
        'professor': professor,
        'current_date': format_fecha_ddmmaaaa(examen.date_str or '') or '-',
        'exam_type': exam_type_display,
        'exam_mode': exam_mode_display,
        'duracion_minutos': examen.duration_minutes,
        'modalidad_resolucion': modalidad_list,
        'instructions': examen.instructions or '',
        'questions_texts': questions_texts,
        'outcomes_texts': outcomes_texts,
        'topics_texts': topics_texts,
        'bloom_display': bloom_display,
        'total_exam_questions': total_exam_questions,
        'print_style': get_print_style_context(print_format),
        'rubric_grids': rubric_grids,
        'has_rubrics': bool(rubric_grids),
        'back_url': _safe_next_url(request, reverse('material:mis_examenes')),
    })


@login_required
def editar_examen(request, pk):
    examen = _get_compatible_exam_or_404(request.user, pk)
    request.session['preview_exam'] = _build_preview_exam_payload_from_exam(examen)
    request.session['editing_exam_id'] = examen.pk
    request.session.pop('preview_generated_versions_ids', None)

    messages.info(request, 'Puedes editar el examen y volver a previsualizar/guardar.', extra_tags='examenes')
    return redirect(f"{reverse('material:create_exam')}?edit_exam_id={examen.pk}")

@login_required
def eliminar_examen(request, pk):
    examen = get_object_or_404(Exam, pk=pk, created_by=request.user)
    if request.method == 'POST':
        examen.delete()
        messages.success(request, 'Examen eliminado correctamente.', extra_tags='examenes')
    return redirect('material:mis_examenes')

def _aplicar_filtros_preguntas(preguntas, params):
    """Aplica los filtros por columna (materia/tema/subtema/bloom/estado IA).

    `params` es un QueryDict (sirve tanto request.GET como request.POST),
    usado por lista_preguntas, bulk_eliminar_preguntas y exportar_preguntas
    para mantener el mismo criterio de filtrado en las tres vistas.
    """
    preguntas = _apply_column_filters_from_params(preguntas, QUESTION_FILTER_FIELDS, params)
    preguntas = _apply_subject_filter(preguntas, params.getlist('subject'))
    preguntas = _apply_ai_status_filter(preguntas, set(params.getlist('ai_status')))
    return preguntas


@login_required
def lista_preguntas(request):
    from .content_visibility import get_visible_questions
    base_preguntas = get_visible_questions(request.user).prefetch_related('subjects').select_related('topic', 'subtopic', 'contenido', 'user')

    selected_filters = get_selected_filters(request, QUESTION_FILTER_FIELDS)
    subject_selected = set(request.GET.getlist('subject'))
    ai_status_selected = set(request.GET.getlist('ai_status'))
    selected_filters['subject'] = subject_selected
    selected_filters['ai_status'] = ai_status_selected

    # Opciones de tema/subtema/bloom en cascada respecto a materia y estado IA.
    scoped_generic = _apply_subject_filter(base_preguntas, subject_selected)
    scoped_generic = _apply_ai_status_filter(scoped_generic, ai_status_selected)
    filter_options = get_filter_options(scoped_generic, QUESTION_FILTER_FIELDS, selected_filters)

    # Opciones de materia en cascada respecto a tema/subtema/bloom y estado IA
    # (nunca respecto a la propia materia, para no autoexcluirse).
    scoped_subject = _apply_column_filters_from_params(base_preguntas, QUESTION_FILTER_FIELDS, request.GET)
    scoped_subject = _apply_ai_status_filter(scoped_subject, ai_status_selected)
    filter_options['subject'] = _build_question_subject_options(scoped_subject)
    filter_options['ai_status'] = QUESTION_AI_STATUS_OPTIONS

    preguntas = _aplicar_filtros_preguntas(base_preguntas, request.GET)

    # Contadores dinámicos sobre el total filtrado (no solo la página actual)
    materias_count = preguntas.exclude(subjects__isnull=True).values('subjects').distinct().count()
    temas_count = preguntas.exclude(topic__isnull=True).values('topic').distinct().count()
    subtemas_count = preguntas.exclude(subtopic__isnull=True).values('subtopic').distinct().count()
    ia_generadas_count = preguntas.filter(generated_by_ai=True).count()
    ia_aprobadas_count = preguntas.filter(generated_by_ai=True, ai_approved=True).count()
    ia_rechazadas_count = preguntas.filter(generated_by_ai=True, ai_approved=False).count()
    ia_sin_revisar_count = preguntas.filter(generated_by_ai=True, ai_approved__isnull=True).count()

    paginator = Paginator(preguntas, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'preguntas': page_obj,
        'filter_options': filter_options,
        'selected_filters': selected_filters,
        'active_filter_count': get_active_filter_count(selected_filters),
        'filter_querystring': get_filter_querystring(request),
        'filter_columns': QUESTION_FILTER_COLUMNS,
        'materias_count': materias_count,
        'temas_count': temas_count,
        'subtemas_count': subtemas_count,
        'ia_generadas_count': ia_generadas_count,
        'ia_aprobadas_count': ia_aprobadas_count,
        'ia_rechazadas_count': ia_rechazadas_count,
        'ia_sin_revisar_count': ia_sin_revisar_count,
    }
    return render(request, 'material/questions/lista_preguntas.html', context)

@login_required
def ver_pregunta(request, pk):
    # include_seed=True a propósito acá (a diferencia del resto de la app,
    # que lo deja en False salvo que el usuario lo haya activado): esta
    # vista se usa también para el "Ver examen" del demo del asistente,
    # donde las preguntas mostradas SON de la materia semilla — sin esto,
    # clickear una pregunta del examen de ejemplo tiraría 404.
    from .content_visibility import get_visible_questions
    pregunta = get_object_or_404(get_visible_questions(request.user, include_seed=True), pk=pk)
    return render(request, 'material/questions/ver_pregunta.html', {'pregunta': pregunta})

@login_required
def editar_pregunta(request, pk):
    pregunta = get_object_or_404(Question, pk=pk, user=request.user)

    if request.method == 'POST':
        form = QuestionForm(request.POST, request.FILES, instance=pregunta, current_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pregunta actualizada correctamente', extra_tags='preguntas')
            return redirect('material:lista_preguntas')
    else:
        form = QuestionForm(instance=pregunta, current_user=request.user)
    
    return render(request, 'material/questions/editar_pregunta.html', {
        'form': form,
        'pregunta': pregunta
    })

@login_required
def eliminar_pregunta(request, pk):
    pregunta = get_object_or_404(Question, pk=pk, user=request.user)

    if request.method == 'POST':
        examenes_afectados = list(pregunta.exams.all())
        pregunta.delete()
        if examenes_afectados:
            nombres = ', '.join(e.title for e in examenes_afectados)
            messages.warning(
                request,
                f'Pregunta eliminada. Quedó usada en {len(examenes_afectados)} '
                f'examen(es) que ahora tienen una pregunta menos: {nombres}. '
                'Revisalos y reemplazala si hace falta.',
                extra_tags='preguntas'
            )
        else:
            messages.success(request, 'Pregunta eliminada correctamente', extra_tags='preguntas')
        return redirect('material:lista_preguntas')

    return render(request, 'material/questions/confirmar_eliminar.html', {
        'pregunta': pregunta,
        'examenes_afectados': pregunta.exams.all(),
    })

@login_required
@require_POST
def bulk_eliminar_preguntas(request):
    from urllib.parse import urlencode

    delete_all_filtered = request.POST.get('all_filtered_selected') == '1'

    if delete_all_filtered:
        preguntas = Question.objects.filter(user=request.user)
        preguntas = _aplicar_filtros_preguntas(preguntas, request.POST)
        count = preguntas.count()
        examenes_afectados = set(Exam.objects.filter(questions__in=preguntas))
        preguntas.delete()
    else:
        ids_raw = request.POST.getlist('pregunta_ids')
        ids = [int(i) for i in ids_raw if i.isdigit()]
        if not ids:
            messages.error(request, 'No se seleccionó ninguna pregunta para eliminar.', extra_tags='preguntas')
            return redirect('material:lista_preguntas')
        preguntas = Question.objects.filter(pk__in=ids, user=request.user)
        count = preguntas.count()
        examenes_afectados = set(Exam.objects.filter(questions__in=preguntas))
        preguntas.delete()

    if count == 1:
        messages.success(request, 'Se eliminó 1 pregunta correctamente.', extra_tags='preguntas')
    else:
        messages.success(request, f'Se eliminaron {count} preguntas correctamente.', extra_tags='preguntas')

    if examenes_afectados:
        nombres = ', '.join(e.title for e in examenes_afectados)
        messages.warning(
            request,
            f'{len(examenes_afectados)} examen(es) quedaron con una o más preguntas menos: '
            f'{nombres}. Revisalos y reemplazá las preguntas que hagan falta.',
            extra_tags='preguntas'
        )

    params = []
    for key in ['subject', 'topic', 'subtopic', 'bloom_level', 'ai_status']:
        params.extend((key, val) for val in request.POST.getlist(key))
    redirect_url = reverse('material:lista_preguntas')
    if params:
        redirect_url += '?' + urlencode(params)
    return redirect(redirect_url)


def _pregunta_materia_nombre(pregunta):
    if pregunta.topic_id and pregunta.topic.subject_id:
        return pregunta.topic.subject.name
    first_subject = pregunta.subjects.first()
    return first_subject.name if first_subject else ''


def _pregunta_opciones_export(pregunta):
    if pregunta.question_type != 'opcion_multiple' or not pregunta.options_json:
        return ''
    # Re-serializa sin \uXXXX: preguntas viejas se guardaron con json.dumps
    # ensure_ascii=True (default), lo que deja los acentos escapados.
    try:
        parsed = json.loads(pregunta.options_json)
        return json.dumps(parsed, ensure_ascii=False)
    except (TypeError, ValueError):
        return pregunta.options_json


def _export_preguntas_csv(preguntas):
    response = HttpResponse(content_type='text/csv')
    filename = f'preguntas_export_{timezone.now():%Y%m%d_%H%M%S}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('﻿')
    writer = csv.writer(response)
    writer.writerow(['materia', 'pregunta', 'respuesta', 'tema', 'subtema', 'pagina', 'tipo', 'opciones', 'dificultad', 'nivel_bloom'])
    for p in preguntas:
        writer.writerow([
            _pregunta_materia_nombre(p),
            p.question_text,
            p.answer_text,
            p.topic.name if p.topic else '',
            p.subtopic.name if p.subtopic else '',
            p.source_page if p.source_page is not None else '',
            p.question_type,
            _pregunta_opciones_export(p),
            p.difficulty,
            p.bloom_level if p.bloom_level is not None else '',
        ])
    return response


def _export_preguntas_txt(preguntas):
    bloques = []
    for p in preguntas:
        lineas = [
            f'materia: {_pregunta_materia_nombre(p)}',
            f'pregunta: {p.question_text}',
            f'respuesta: {p.answer_text}',
            f'tema: {p.topic.name if p.topic else ""}',
        ]
        if p.subtopic:
            lineas.append(f'subtema: {p.subtopic.name}')
        if p.source_page is not None:
            lineas.append(f'pagina: {p.source_page}')
        lineas.append(f'tipo: {p.question_type}')
        opciones = _pregunta_opciones_export(p)
        if opciones:
            lineas.append(f'opciones: {opciones}')
        lineas.append(f'dificultad: {p.difficulty}')
        if p.bloom_level is not None:
            lineas.append(f'nivel_bloom: {p.bloom_level}')
        bloques.append('\n'.join(lineas))

    content = '\n\n'.join(bloques) + '\n'
    filename = f'preguntas_export_{timezone.now():%Y%m%d_%H%M%S}.txt'
    response = HttpResponse(content, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_POST
def exportar_preguntas(request):
    formato = request.GET.get('formato', 'csv')

    if request.POST.get('all_filtered_selected') == '1':
        preguntas = Question.objects.filter(user=request.user)
        preguntas = _aplicar_filtros_preguntas(preguntas, request.POST)
    else:
        ids_raw = request.POST.getlist('pregunta_ids')
        ids = [int(i) for i in ids_raw if i.isdigit()]
        if not ids:
            messages.error(request, 'No se seleccionó ninguna pregunta para exportar.', extra_tags='preguntas')
            return redirect('material:lista_preguntas')
        preguntas = Question.objects.filter(pk__in=ids, user=request.user)

    preguntas = preguntas.select_related('topic__subject', 'subtopic').prefetch_related('subjects').order_by('topic__name', 'subtopic__name', 'id')

    if formato == 'txt':
        return _export_preguntas_txt(preguntas)
    return _export_preguntas_csv(preguntas)


@login_required
def mis_contenidos(request):
    from .cleanup import _delete_files_for_queryset

    base_qs = Contenido.objects.filter(uploaded_by=request.user).prefetch_related('subjects')

    vigentes_qs = base_qs.filter(file_deleted_at__isnull=True).order_by('-uploaded_at')
    vigentes_paginator = Paginator(vigentes_qs, 25)
    vigentes_page = vigentes_paginator.get_page(request.GET.get('vpage'))

    # El archivo puede haber desaparecido sin que file_deleted_at se haya
    # actualizado (la sesión sigue abierta pero el storage es efímero, hubo
    # un redeploy, etc.). Reconciliamos contra el storage real solo sobre la
    # página que se va a mostrar, no sobre todos los vigentes del usuario:
    # con muchos documentos, chequear el storage de todos en cada request
    # es I/O sincrónico innecesario en un worker único.
    stale_ids = [c.id for c in vigentes_page if not c.file_actually_exists()]
    if stale_ids:
        _delete_files_for_queryset(Contenido.objects.filter(id__in=stale_ids))
        vigentes_page = vigentes_paginator.get_page(request.GET.get('vpage'))

    borrados_qs = base_qs.filter(file_deleted_at__isnull=False)

    q = request.GET.get('q', '').strip()
    if q:
        borrados_qs = borrados_qs.filter(Q(title__icontains=q) | Q(isbn__icontains=q))

    materia_id = request.GET.get('materia', '').strip()
    if materia_id.isdigit():
        borrados_qs = borrados_qs.filter(subjects__id=materia_id)

    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()
    if fecha_desde:
        borrados_qs = borrados_qs.filter(uploaded_at__date__gte=fecha_desde)
    if fecha_hasta:
        borrados_qs = borrados_qs.filter(uploaded_at__date__lte=fecha_hasta)

    borrados_qs = borrados_qs.order_by('-uploaded_at').distinct()

    paginator = Paginator(borrados_qs, 25)
    borrados_page = paginator.get_page(request.GET.get('page'))

    materias = Subject.objects.filter(contenidos__uploaded_by=request.user).distinct().order_by('name')

    return render(request, 'material/questions/mis_contenidos.html', {
        'vigentes_page': vigentes_page,
        'borrados_page': borrados_page,
        'materias': materias,
        'q': q,
        'materia_id': materia_id,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    })

@login_required
def delete_contenido(request):
    if request.method == 'POST':
        from .cleanup import _delete_files_for_queryset
        contenido_ids = request.POST.getlist('contenido_ids')
        if not contenido_ids:
            messages.error(request, 'No se seleccionó ningún documento para borrar.', extra_tags='contenidos')
            return redirect('material:mis_contenidos')
        contenidos = Contenido.objects.filter(
            id__in=contenido_ids, uploaded_by=request.user, file_deleted_at__isnull=True
        ).exclude(file='')
        count = _delete_files_for_queryset(contenidos)
        if count == 1:
            messages.success(request, 'El archivo ha sido borrado correctamente. El documento y las preguntas que lo citan como fuente se conservan.', extra_tags='contenidos')
        elif count > 1:
            messages.success(request, f'Los archivos de {count} documentos han sido borrados correctamente. Los documentos y las preguntas que los citan como fuente se conservan.', extra_tags='contenidos')
        else:
            messages.info(request, 'Los documentos seleccionados ya no tenían archivo disponible.', extra_tags='contenidos')
    return redirect('material:mis_contenidos')

@login_required
def upload_questions(request):
    """
    Vista para subir preguntas, tanto individualmente como por lotes (CSV/TXT)
    """
    if request.method == 'POST':
        # Verificar si se está subiendo un archivo (procesamiento batch)
        if 'file' in request.FILES:
            try:
                file = request.FILES['file']
                file_extension = os.path.splitext(file.name)[1].lower()
                
                # Obtener contenido seleccionado si existe
                contenido_seleccionado = None
                contenido_id = request.POST.get('contenido')
                if contenido_id:
                    try:
                        contenido_seleccionado = Contenido.objects.get(id=contenido_id, uploaded_by=request.user)
                    except Contenido.DoesNotExist:
                        pass
                
                # Procesar archivo según extensión
                if file_extension == '.csv':
                    questions_created = process_csv_file(file, contenido_seleccionado, request.user)
                    messages.success(request, f'{questions_created} preguntas creadas desde archivo CSV.', extra_tags='preguntas')
                elif file_extension == '.txt':
                    questions_created = process_txt_file(file, contenido_seleccionado, request.user)
                    messages.success(request, f'{questions_created} preguntas creadas desde archivo TXT.', extra_tags='preguntas')
                else:
                    messages.error(request, 'Formato de archivo no soportado. Use CSV o TXT.', extra_tags='preguntas')
                    return redirect('material:upload_questions')
                
                return redirect('material:lista_preguntas')
                
            except Exception as e:
                logger.error(f"Error al procesar archivo: {str(e)}", exc_info=True)
                messages.error(request, f'Ocurrió un error al procesar el archivo: {str(e)}', extra_tags='preguntas')
                return redirect('material:upload_questions')
        
        # Procesamiento para pregunta individual
        else:
            form = QuestionForm(request.POST, request.FILES, current_user=request.user)
            
            if form.is_valid():
                try:
                    question = form.save(commit=False)
                    question.user = request.user
                    # Asignar contenido solo si se seleccionó
                    if form.cleaned_data['contenido']:
                        question.contenido = form.cleaned_data['contenido']
                    else:
                        question.contenido = None
                    question.save()
                    form.save_m2m()
                    messages.success(request, 'Pregunta guardada correctamente.', extra_tags='preguntas')
                    return redirect('material:lista_preguntas')
                
                except Exception as e:
                    logger.error(f"Error al guardar pregunta individual: {str(e)}", exc_info=True)
                    messages.error(request, f'Ocurrió un error: {str(e)}', extra_tags='preguntas')
                    return redirect('material:upload_questions')
            
            else:
                field_errors = []
                for field_name, errors in form.errors.items():
                    label = form.fields.get(field_name).label if field_name in form.fields else field_name
                    for err in errors:
                        field_errors.append(f"{label}: {err}")

                if field_errors:
                    messages.error(
                        request,
                        'Por favor corrija los errores en el formulario: ' + ' | '.join(field_errors),
                        extra_tags='preguntas'
                    )
                else:
                    messages.error(request, 'Por favor corrija los errores en el formulario.', extra_tags='preguntas')
    else:
        form = QuestionForm(current_user=request.user)
    
    context = {
        'form': form,
        'current_tab': request.session.get('upload_questions_tab', 'single')
    }
    
    return render(request, 'material/questions/upload_questions.html', context)

# Funciones auxiliares para procesamiento de archivos
def _normalize_question_type(raw_value):
    raw = (raw_value or '').strip().lower()
    mapping = {
        'desarrollo': 'desarrollo',
        'a_desarrollar': 'desarrollo',
        'a desarrollar': 'desarrollo',
        'opcion_multiple': 'opcion_multiple',
        'opción_múltiple': 'opcion_multiple',
        'opcion multiple': 'opcion_multiple',
        'multiple_choice': 'opcion_multiple',
        'multiple choice': 'opcion_multiple',
        'verdadero_falso': 'verdadero_falso',
        'verdadero/falso': 'verdadero_falso',
        'verdadero falso': 'verdadero_falso',
        'true_false': 'verdadero_falso',
        'completar_blank': 'completar_blank',
        'completar': 'completar_blank',
        'completar el espacio': 'completar_blank',
        'fill_blank': 'completar_blank',
    }
    return mapping.get(raw, 'desarrollo')


def _normalize_true_false_answer(raw_answer):
    val = (raw_answer or '').strip().lower()
    if val in ['verdadero', 'v', 'true', '1', 'si', 'sí']:
        return 'Verdadero'
    if val in ['falso', 'f', 'false', '0', 'no']:
        return 'Falso'
    return raw_answer or ''


def _normalize_difficulty(raw_value):
    val = (raw_value or '').strip()
    if not val.isdigit():
        return 1
    return max(1, min(5, int(val)))


def _normalize_bloom_level(raw_value):
    val = (raw_value or '').strip()
    if not val.isdigit():
        return None
    parsed = int(val)
    return parsed if 1 <= parsed <= 6 else None


def _parse_options_json(raw_options):
    text = (raw_options or '').strip()
    if not text:
        return ''

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return json.dumps([str(v) for v in parsed[:4]], ensure_ascii=False)
    except Exception:
        pass

    # Fallback: "A|B|C|D"
    parts = [p.strip() for p in text.split('|') if p.strip()]
    if parts:
        return json.dumps(parts[:4], ensure_ascii=False)
    return ''


def process_csv_file(file, contenido, user):
    from .models import Subject, Topic, Subtopic, Question
    
    # Intentar múltiples codificaciones
    encodings = ['utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1', 'utf-16']
    decoded_file = None
    
    for encoding in encodings:
        try:
            file.seek(0)  # Volver al inicio del archivo
            decoded_file = file.read().decode(encoding).splitlines()
            logger.info(f"Archivo CSV leído exitosamente con codificación: {encoding}")
            break
        except UnicodeDecodeError:
            continue
    
    if decoded_file is None:
        raise Exception("No se pudo leer el archivo. Formatos soportados: UTF-8, Latin1, Windows-1252, ISO-8859-1, UTF-16.")
    
    try:
        reader = csv.DictReader(decoded_file)
    except Exception as e:
        raise Exception(f"Error al procesar el CSV: {str(e)}")
    
    questions_created = 0
    errors = []
    row_number = 1  # Para seguimiento de filas

    for row in reader:
        row_number += 1
        try:
            # Validar campos requeridos
            missing_fields = []
            if not row.get('materia'):
                missing_fields.append('materia')
            if not row.get('pregunta'):
                missing_fields.append('pregunta')
            if not row.get('respuesta'):
                missing_fields.append('respuesta')
            if not row.get('tema'):
                missing_fields.append('tema')
                
            if missing_fields:
                error_msg = f"Fila {row_number}: faltan campos requeridos: {', '.join(missing_fields)}"
                errors.append(error_msg)
                logger.warning(error_msg)
                continue
                
            # Obtener o crear la materia (real, no mezcla con materias semilla)
            subject, _ = get_or_create_real_subject(row.get('materia', 'General'), user)

            # Obtener o crear el tema
            topic, _ = Topic.objects.get_or_create(
                name=row.get('tema', 'General'),
                subject=subject
            )
            
            # Obtener subtema solo si se proporciona
            subtopic = None
            if row.get('subtema') and row.get('subtema').strip():
                subtopic, _ = Subtopic.objects.get_or_create(
                    name=row.get('subtema'),
                    topic=topic
                )
            
            # Crear la pregunta solo con campos que existen en el modelo
            q_type = _normalize_question_type(row.get('tipo'))
            answer_text = row['respuesta']
            if q_type == 'verdadero_falso':
                answer_text = _normalize_true_false_answer(answer_text)

            q = Question.objects.create(
                contenido=contenido,
                question_text=row['pregunta'],
                answer_text=answer_text,
                topic=topic,
                subtopic=subtopic,
                question_type=q_type,
                options_json=_parse_options_json(row.get('opciones')) if q_type == 'opcion_multiple' else None,
                source_page=int(row['pagina']) if row.get('pagina') and row.get('pagina').strip().isdigit() else None,
                difficulty=_normalize_difficulty(row.get('dificultad')),
                bloom_level=_normalize_bloom_level(row.get('nivel_bloom')),
                user=user
            )
            q.subjects.add(subject)
            questions_created += 1
        except Exception as e:
            error_msg = f"Fila {row_number}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"Error creando pregunta desde CSV - {error_msg}")
            continue

    # Si hay errores, lanzar excepción con detalles
    if errors and questions_created == 0:
        raise Exception(f"No se pudo crear ninguna pregunta. Errores encontrados:\n" + "\n".join(errors[:5]))
    elif errors:
        logger.warning(f"Se crearon {questions_created} preguntas con {len(errors)} errores: {errors[:3]}")
    
    return questions_created

def process_txt_file(file, contenido, user):
    # Intentar múltiples codificaciones
    encodings = ['utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1', 'utf-16']
    lines = None
    
    for encoding in encodings:
        try:
            file.seek(0)  # Volver al inicio del archivo
            lines = file.read().decode(encoding).splitlines()
            logger.info(f"Archivo TXT leído exitosamente con codificación: {encoding}")
            break
        except UnicodeDecodeError:
            continue
    
    if lines is None:
        raise Exception("No se pudo leer el archivo. Formatos soportados: UTF-8, Latin1, Windows-1252, ISO-8859-1, UTF-16.")
    question_data = {}
    questions_created = 0

    for line in lines:
        if line.strip():
            if ':' in line:
                key, value = line.split(':', 1)
                question_data[key.strip().lower()] = value.strip()
        else:
            if question_data:
                create_question_from_dict(question_data, contenido, user)
                questions_created += 1
                question_data = {}

    if question_data:
        create_question_from_dict(question_data, contenido, user)
        questions_created += 1

    return questions_created

def create_question_from_dict(data, contenido, user):
    from .models import Subject, Topic, Subtopic, Question, get_or_create_real_subject
    # Obtener o crear Subject (real, no mezcla con materias semilla)
    subject, _ = get_or_create_real_subject(data.get('materia', 'General'), user)

    # Obtener o crear Topic
    topic, _ = Topic.objects.get_or_create(
        name=data.get('tema', 'General'),
        subject=subject
    )
    
    # Obtener subtopic solo si existe en los datos
    subtopic = None
    if data.get('subtema'):
        subtopic, _ = Subtopic.objects.get_or_create(
            name=data.get('subtema'),
            topic=topic
        )
    
    # Crear la pregunta solo con campos que existen en el modelo
    q_type = _normalize_question_type(data.get('tipo'))
    answer_text = data.get('respuesta', '')
    if q_type == 'verdadero_falso':
        answer_text = _normalize_true_false_answer(answer_text)

    q = Question.objects.create(
        contenido=contenido,
        question_text=data.get('pregunta', ''),
        answer_text=answer_text,
        topic=topic,
        subtopic=subtopic,
        question_type=q_type,
        options_json=_parse_options_json(data.get('opciones')) if q_type == 'opcion_multiple' else None,
        source_page=int(data.get('pagina')) if data.get('pagina') and str(data.get('pagina')).strip().isdigit() else None,
        difficulty=_normalize_difficulty(data.get('dificultad')),
        bloom_level=_normalize_bloom_level(data.get('nivel_bloom')),
        user=user
    )
    q.subjects.add(subject)


def download_template(request, format):
    if format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="template.csv"'
        writer = csv.writer(response)
        writer.writerow(['materia', 'pregunta', 'respuesta', 'tema', 'subtema', 'pagina', 'tipo', 'opciones', 'dificultad', 'nivel_bloom'])
        writer.writerow(['Matemáticas', '¿Cuál es la capital de Francia?', 'París', 'Geografía', 'Capitales', 1, 'desarrollo', '', 2, ''])
        writer.writerow(['Literatura', '¿Quién escribió "Cien años de soledad"?', 'Gabriel García Márquez', 'Literatura', 'Autores', 2, 'opcion_multiple', '["Gabriel García Márquez","Jorge Luis Borges","Julio Cortázar","Mario Vargas Llosa"]', 3, 1])
        return response
    elif format == 'json':
        data = [
            {
                "materia": "Matemáticas",
                "pregunta": "¿Cuál es la capital de Francia?",
                "respuesta": "París",
                "tema": "Geografía",
                "subtema": "Capitales",
                "pagina": 1,
                "tipo": "desarrollo",
                "opciones": "",
                "dificultad": 2,
                "nivel_bloom": ""
            },
            {
                "materia": "Literatura",
                "pregunta": "¿Quién escribió 'Cien años de soledad'?",
                "respuesta": "Gabriel García Márquez",
                "tema": "Literatura",
                "subtema": "Autores",
                "pagina": 2,
                "tipo": "opcion_multiple",
                "opciones": ["Gabriel García Márquez", "Jorge Luis Borges", "Julio Cortázar", "Mario Vargas Llosa"],
                "dificultad": 3,
                "nivel_bloom": 1
            }
        ]
        response = HttpResponse(json.dumps(data, indent=4, ensure_ascii=False), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="template.json"'
        return response
    elif format == 'txt':
        content = """materia: Matemáticas
pregunta: ¿Cuál es la capital de Francia?
respuesta: París
tema: Geografía
subtema: Capitales
pagina: 1
tipo: desarrollo
dificultad: 2

materia: Literatura
pregunta: ¿Quién escribió 'Cien años de soledad'?
respuesta: Gabriel García Márquez
tema: Literatura
subtema: Autores
pagina: 2
tipo: opcion_multiple
opciones: Gabriel García Márquez|Jorge Luis Borges|Julio Cortázar|Mario Vargas Llosa
dificultad: 3
nivel_bloom: 1"""
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="template.txt"'
        return response
    else:
        messages.error(request, 'Formato de plantilla no soportado.', extra_tags='plantillas')
        return redirect('material:upload_questions')

@login_required
def delete_exam_template(request):
    if request.method == 'POST':
        template_ids = request.POST.getlist('template_ids')
        ExamTemplate.objects.filter(id__in=template_ids, created_by=request.user).delete()
        messages.success(request, 'Las plantillas seleccionadas se han eliminado correctamente.', extra_tags='plantillas')
    return redirect('material:list_exam_templates')


# FUNCIÓN OBSOLETA: manage_learning_outcomes eliminada
# Los learning outcomes ahora se gestionan por materia individual
# usando LearningOutcomeCreateView y LearningOutcomeListView

@login_required
def get_learning_outcomes(request):
    subject_id = request.GET.get('subject_id')
    if not subject_id:
        return JsonResponse([], safe=False)
    
    try:
        subject = Subject.objects.get(id=subject_id)
        outcomes = list(LearningOutcome.objects.filter(subject=subject)
                      .values('id', 'description'))
        
        return JsonResponse(outcomes, safe=False)
    
    except Subject.DoesNotExist:
        return JsonResponse({'error': 'Materia no encontrada'}, status=404)
    except Exception as e:
        logger.error(f"Error en get_learning_outcomes: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

# CANDIDATO A BORRAR (auditoría 2026-08-03, ver memoria
# project_institution_v1_cleanup): edit_institution y delete_institution
# (modelo Institution v1, ya reemplazado por InstitutionV2) son código
# muerto e inalcanzable — no tienen ninguna ruta registrada en urls.py, ni
# ningún link en ningún template. Peor: si algo las invocara, romperían
# igual: usan `InstitutionForm`, una clase que no existe en forms.py (ni
# está importada acá), y `edit_institution.html`, un template que tampoco
# existe en el repo. Confirmado con NameError reproducido al analizar el
# código, no solo inferido.
@login_required
def edit_institution(request, pk):
    institution = get_object_or_404(Institution, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = InstitutionForm(request.POST, request.FILES, instance=institution)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Procesar logo
                    if 'logo-clear' in request.POST:
                        institution.logo.delete(save=False)
                    if 'logo' in request.FILES:
                        institution.logo = request.FILES['logo']
                    
                    institution = form.save()
                    
                    # Sincronizar sedes
                    existing_campuses = list(institution.campuses.all())
                    submitted_campuses = []
                    
                    for campus_name in request.POST.getlist('campuses'):
                        if campus_name.strip():
                            campus = next((c for c in existing_campuses if c.name == campus_name.strip()), None)
                            if not campus:
                                campus = Campus.objects.create(
                                    name=campus_name.strip(),
                                    institution=institution
                                )
                            submitted_campuses.append(campus.id)
                    
                    # Eliminar sedes no enviadas
                    Campus.objects.filter(
                        institution=institution
                    ).exclude(id__in=submitted_campuses).delete()
                    
                    # Sincronizar facultades
                    existing_faculties = list(institution.faculties.all())
                    submitted_faculties = []
                    
                    for name, code in zip(
                        request.POST.getlist('faculty_names'),
                        request.POST.getlist('faculty_codes')
                    ):
                        if name.strip():
                            faculty = next((f for f in existing_faculties if f.name == name.strip()), None)
                            if not faculty:
                                faculty = Faculty.objects.create(
                                    name=name.strip(),
                                    code=code.strip(),
                                    institution=institution
                                )
                            submitted_faculties.append(faculty.id)
                    
                    # Eliminar facultades no enviadas
                    Faculty.objects.filter(
                        institution=institution
                    ).exclude(id__in=submitted_faculties).delete()
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Cambios guardados correctamente'
                    })
            
            except Exception as e:
                logger.error(f"Error en edit_institution: {str(e)}", exc_info=True)
                return JsonResponse({
                    'success': False,
                    'error': 'Error al procesar los cambios'
                }, status=500)
        
        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)
    
    # GET request
    campuses = institution.campuses.all()
    faculties = institution.faculties.all()
    
    return render(request, 'material/edit_institution.html', {
        'institution': institution,
        'campuses': campuses,
        'faculties': faculties,
        'form': InstitutionForm(instance=institution)
    })

# CANDIDATO A BORRAR — ver nota arriba de edit_institution (misma auditoría).
@login_required
@require_http_methods(["POST"])
def delete_institution(request, pk):
    institution = get_object_or_404(Institution, pk=pk, owner=request.user)
    try:
        with transaction.atomic():
            # Eliminar relaciones primero para evitar problemas de integridad
            institution.campuses.all().delete()
            institution.faculties.all().delete()
            institution.delete()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            messages.success(request, 'Institución eliminada correctamente', extra_tags='instituciones')
            return redirect('material:manage_institutions')
            
    except Exception as e:
        logger.error(f"Error eliminando institución: {str(e)}", exc_info=True)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'Error al eliminar la institución'
            }, status=500)
        messages.error(request, 'Error al eliminar la institución')
        return redirect('material:manage_institutions')

# material/views.py - Agregar al final del archivo

# "Logo"/"Sedes"/"Facultades" no son campos reales: se anotan como 'yes'/'no'
# en la queryset (ver institution_v2_list) para poder ofrecerlos como filtros
# categoricos tipo Excel via el motor generico de material/column_filters.py.
# Nombre (busqueda libre) y Favoritos (toggle) se manejan aparte porque no son
# listas de valores discretos.
INSTITUTION_V2_FILTER_FIELDS = [
    ColumnFilterField('has_logo', 'Logo', choices=[('yes', 'Con logo'), ('no', 'Sin logo')]),
    ColumnFilterField('has_campus', 'Sedes', choices=[('yes', 'Con sedes'), ('no', 'Sin sedes')]),
    ColumnFilterField('has_faculty', 'Facultades', choices=[('yes', 'Con facultades'), ('no', 'Sin facultades')]),
]
INSTITUTION_V2_FILTER_COLUMNS = [{'field': f.name, 'label': f.label} for f in INSTITUTION_V2_FILTER_FIELDS]


@login_required
def institution_v2_list(request):
    name_query = request.GET.get('name', '')
    favorite_only = request.GET.get('favorites') == 'on'
    from django.db import DatabaseError

    def ensure_logo_b64_column():
        from django.db import connection
        table_name = 'material_institutionv2'
        column_name = 'logo_b64'
        with connection.cursor() as cursor:
            columns = [col.name for col in connection.introspection.get_table_description(cursor, table_name)]
            if column_name in columns:
                return
            if connection.vendor == 'postgresql':
                cursor.execute(f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "{column_name}" TEXT NULL')
            else:
                cursor.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" TEXT')

    try:
        ensure_logo_b64_column()

        # Filtrar solo instituciones activas (is_active=True), sin las
        # institución(es) semilla (si el usuario pasó por el esquema ya
        # armado del asistente, queda una UserInstitution apuntando ahí) —
        # excepto para la cuenta del Área de Pruebas, para la que las
        # instituciones semilla SÍ son "las suyas" a propósito (ver
        # training_accounts.py, que la vincula explícitamente a esas).
        institutions = InstitutionV2.objects.filter(
            userinstitution__user=request.user,
            is_active=True,  # Solo mostrar instituciones activas
        )
        if not getattr(request.user.profile, 'is_training_account', False):
            institutions = institutions.filter(is_seed_demo=False)

        if name_query:
            institutions = institutions.filter(name__icontains=name_query)

        if favorite_only:
            institutions = institutions.filter(
                userinstitution__user=request.user,
                userinstitution__is_favorite=True
            )

        institutions = institutions.annotate(
            has_campus_flag=Exists(CampusV2.objects.filter(institution=OuterRef('pk'))),
            has_faculty_flag=Exists(FacultyV2.objects.filter(institution=OuterRef('pk'))),
        ).annotate(
            has_logo=Case(
                When(Q(logo_b64__isnull=False) & ~Q(logo_b64=''), then=Value('yes')),
                When(Q(logo__isnull=False) & ~Q(logo=''), then=Value('yes')),
                default=Value('no'),
                output_field=CharField(),
            ),
            has_campus=Case(When(has_campus_flag=True, then=Value('yes')), default=Value('no'), output_field=CharField()),
            has_faculty=Case(When(has_faculty_flag=True, then=Value('yes')), default=Value('no'), output_field=CharField()),
        )

        selected_filters = get_selected_filters(request, INSTITUTION_V2_FILTER_FIELDS)
        filter_options = get_filter_options(institutions, INSTITUTION_V2_FILTER_FIELDS, selected_filters)
        institutions = apply_column_filters(request, institutions, INSTITUTION_V2_FILTER_FIELDS)

        institutions = institutions.prefetch_related(
            'campusv2_set',
            'facultyv2_set'
        ).distinct()

        favorite_count = UserInstitution.objects.filter(
            user=request.user,
            is_favorite=True,
            institution__is_active=True  # Contar solo favoritos activos
        ).count()

        paginator = Paginator(institutions, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        active_filter_count = (
            get_active_filter_count(selected_filters)
            + (1 if name_query else 0)
            + (1 if favorite_only else 0)
        )

    except DatabaseError as e:
        logger.error(f"Error DB en institution_v2_list: {str(e)}", exc_info=True)
        messages.error(request, 'Se detecto un problema temporal de base de datos en Instituciones. Reintenta en unos minutos.')
        page_obj = Paginator([], 10).get_page(1)
        favorite_count = 0
        selected_filters = get_selected_filters(request, INSTITUTION_V2_FILTER_FIELDS)
        filter_options = {f.name: [] for f in INSTITUTION_V2_FILTER_FIELDS}
        active_filter_count = 0

    return render(request, 'material/institutions_v2/list.html', {
        'institutions': page_obj,
        'name_query': name_query,
        'favorite_only': favorite_only,
        'favorite_count': favorite_count,
        'filter_options': filter_options,
        'selected_filters': selected_filters,
        'active_filter_count': active_filter_count,
        'filter_querystring': get_filter_querystring(request),
        'filter_columns': INSTITUTION_V2_FILTER_COLUMNS,
    })

@login_required
def create_institution_v2(request):
    CampusFormSet = formset_factory(CampusV2Form, extra=1)
    FacultyFormSet = formset_factory(FacultyV2Form, extra=1)

    if request.method == 'POST':
        form = InstitutionV2Form(request.POST, request.FILES)
        campus_formset = CampusFormSet(request.POST, prefix='campus')
        faculty_formset = FacultyFormSet(request.POST, prefix='faculty')

        if all([form.is_valid(), campus_formset.is_valid(), faculty_formset.is_valid()]):
            with transaction.atomic():
                institution = form.save()

                # Guardar logo en Base64 para producción (filesystem efímero)
                if institution.logo:
                    import base64
                    institution.logo.seek(0)
                    institution.logo_b64 = 'data:image/png;base64,' + base64.b64encode(institution.logo.read()).decode()
                    institution.save(update_fields=['logo_b64'])

                UserInstitution.objects.create(user=request.user, institution=institution)

                # Procesar sedes
                for campus_form in campus_formset:
                    if campus_form.cleaned_data.get('name'):
                        CampusV2.objects.create(
                            institution=institution,
                            name=campus_form.cleaned_data['name']
                        )

                # Procesar facultades
                for faculty_form in faculty_formset:
                    if faculty_form.cleaned_data.get('name'):
                        FacultyV2.objects.create(
                            institution=institution,
                            name=faculty_form.cleaned_data['name']
                        )

                messages.success(request, 'Institución creada con éxito.', extra_tags='instituciones')
                return redirect('material:institution_v2_detail', pk=institution.pk)
    else:
        form = InstitutionV2Form()
        campus_formset = CampusFormSet(prefix='campus')
        faculty_formset = FacultyFormSet(prefix='faculty')

    return render(request, 'material/institutions_v2/create.html', {
        'form': form,
        'campus_formset': campus_formset,
        'faculty_formset': faculty_formset,
    })

@login_required
def edit_institution_v2(request, pk):
    from django.db import DatabaseError

    def ensure_logo_b64_column():
        from django.db import connection
        table_name = 'material_institutionv2'
        column_name = 'logo_b64'
        with connection.cursor() as cursor:
            columns = [col.name for col in connection.introspection.get_table_description(cursor, table_name)]
            if column_name in columns:
                return
            if connection.vendor == 'postgresql':
                cursor.execute(f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "{column_name}" TEXT NULL')
            else:
                cursor.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" TEXT')

    try:
        ensure_logo_b64_column()
        institution = get_object_or_404(InstitutionV2, pk=pk, userinstitution__user=request.user)
    except DatabaseError as e:
        logger.error(f"Error DB en edit_institution_v2 (pk={pk}): {str(e)}", exc_info=True)
        messages.error(request, 'Error de base de datos al abrir la edicion de la institucion.')
        return redirect('material:institution_v2_list')
    
    CampusFormSet = modelformset_factory(
        CampusV2,
        form=CampusV2Form,
        extra=1,
        can_delete=True,
        min_num=0,  # Hacer completamente opcional
        validate_min=False
    )
    
    FacultyFormSet = modelformset_factory(
        FacultyV2,
        form=FacultyV2Form,
        extra=1,
        can_delete=True,
        min_num=0,  # Hacer completamente opcional
        validate_min=False
    )

    if request.method == 'POST':
        form = InstitutionV2Form(request.POST, request.FILES, instance=institution)
        campus_formset = CampusFormSet(
            request.POST,
            queryset=institution.campusv2_set.all(),
            prefix='campus'
        )
        faculty_formset = FacultyFormSet(
            request.POST,
            queryset=institution.facultyv2_set.all(),
            prefix='faculty'
        )

        if all([form.is_valid(), campus_formset.is_valid(), faculty_formset.is_valid()]):
            try:
                with transaction.atomic():
                    # Guardar institución (maneja logo automáticamente)
                    institution = form.save()

                    # Actualizar logo_b64 si se subió un nuevo logo
                    if request.FILES.get('logo'):
                        import base64
                        institution.logo.seek(0)
                        institution.logo_b64 = 'data:image/png;base64,' + base64.b64encode(institution.logo.read()).decode()
                        institution.save(update_fields=['logo_b64'])

                    # Procesar campus
                    for campus_form in campus_formset:
                        if campus_form.cleaned_data and not campus_form.cleaned_data.get('DELETE', False):
                            campus = campus_form.save(commit=False)
                            campus.institution = institution
                            campus.save()
                        elif campus_form.cleaned_data.get('DELETE', False) and campus_form.instance.pk:
                            campus_form.instance.delete()

                    # Procesar facultades
                    for faculty_form in faculty_formset:
                        if faculty_form.cleaned_data and not faculty_form.cleaned_data.get('DELETE', False):
                            faculty = faculty_form.save(commit=False)
                            faculty.institution = institution
                            faculty.save()
                        elif faculty_form.cleaned_data.get('DELETE', False) and faculty_form.instance.pk:
                            faculty_form.instance.delete()

                    messages.success(request, 'Institución actualizada correctamente', extra_tags='instituciones')
                    return redirect('material:institution_v2_detail', pk=institution.pk)

            except Exception as e:
                messages.error(request, f'Error al guardar los cambios: {str(e)}')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario')

    else:
        form = InstitutionV2Form(instance=institution)
        campus_formset = CampusFormSet(
            queryset=institution.campusv2_set.all(),
            prefix='campus'
        )
        faculty_formset = FacultyFormSet(
            queryset=institution.facultyv2_set.all(),
            prefix='faculty'
        )

    return render(request, 'material/institutions_v2/edit.html', {
        'form': form,
        'institution': institution,
        'campus_formset': campus_formset,
        'faculty_formset': faculty_formset,
    })

@login_required
def delete_institution_v2(request, pk):
    """Elimina físicamente la institución y sus relaciones"""
    institution = get_object_or_404(
        InstitutionV2, 
        pk=pk,
        userinstitution__user=request.user  # Solo el dueño puede eliminar
    )
    
    if request.method == 'POST':
        try:
            with transaction.atomic():  # Transacción atómica
                # 1. Eliminar relación UserInstitution primero
                UserInstitution.objects.filter(
                    institution=institution,
                    user=request.user
                ).delete()
                
                # 2. Eliminar campus y facultades
                CampusV2.objects.filter(institution=institution).delete()
                FacultyV2.objects.filter(institution=institution).delete()
                
                # 3. Eliminar logs asociados
                InstitutionLog.objects.filter(institution=institution).delete()
                
                # 4. Finalmente eliminar la institución
                institution_name = institution.name
                institution.delete()
                
                messages.success(request, f'Institución "{institution_name}" eliminada permanentemente.')
                return redirect('material:institution_v2_list')

        except ProtectedError as e:
            messages.error(request, _protected_error_message(e))
            return redirect('material:institution_v2_detail', pk=pk)
        except Exception as e:
            logger.error(f"Error eliminando institución: {str(e)}")
            messages.error(request, 'Ocurrió un error al eliminar la institución.')
            return redirect('material:institution_v2_detail', pk=pk)
    
    # Mostrar confirmación
    return render(request, 'material/institutions_v2/confirm_delete.html', {
        'institution': institution,
        'preview': get_delete_preview(institution),
    })


@login_required
@require_POST
def bulk_eliminar_instituciones_v2(request):
    """Borrado multiple de instituciones (mismo criterio que delete_institution_v2:
    borra relaciones, campus, facultades y logs antes de la institucion)."""
    ids_raw = request.POST.getlist('institution_ids')
    ids = [int(i) for i in ids_raw if i.isdigit()]
    if not ids:
        messages.error(request, 'No se seleccionó ninguna institución para eliminar.')
        return redirect('material:institution_v2_list')

    institutions = InstitutionV2.objects.filter(pk__in=ids, userinstitution__user=request.user).distinct()
    count = institutions.count()

    try:
        with transaction.atomic():
            for institution in institutions:
                UserInstitution.objects.filter(institution=institution, user=request.user).delete()
                CampusV2.objects.filter(institution=institution).delete()
                FacultyV2.objects.filter(institution=institution).delete()
                InstitutionLog.objects.filter(institution=institution).delete()
                institution.delete()
    except ProtectedError as e:
        messages.error(request, _protected_error_message(e))
        return redirect('material:institution_v2_list')
    except Exception as e:
        logger.error(f"Error en borrado multiple de instituciones: {str(e)}")
        messages.error(request, 'Ocurrió un error al eliminar las instituciones seleccionadas.')
        return redirect('material:institution_v2_list')

    if count == 1:
        messages.success(request, 'Se eliminó 1 institución permanentemente.')
    else:
        messages.success(request, f'Se eliminaron {count} instituciones permanentemente.')
    return redirect('material:institution_v2_list')

@login_required
def toggle_favorite_institution(request, pk):
    institution = get_object_or_404(InstitutionV2, pk=pk, userinstitution__user=request.user)
    user_institution, created = UserInstitution.objects.get_or_create(user=request.user, institution=institution)
    user_institution.is_favorite = not user_institution.is_favorite
    user_institution.save()
    return redirect('material:institution_v2_detail', pk=pk)

@login_required
def institution_v2_logs(request, pk):
    institution = get_object_or_404(
        InstitutionV2,
        pk=pk,
        userinstitution__user=request.user
    )
    
    logs = InstitutionLog.objects.filter(institution=institution).order_by('-created_at')
    
    return render(request, 'material/institutions_v2/logs.html', {
        'institution': institution,
        'logs': logs
    })

@login_required
def institution_v2_detail(request, pk):
    institution = get_object_or_404(
        InstitutionV2,
        pk=pk,
        userinstitution__user=request.user
    )
    is_favorite = UserInstitution.objects.filter(
        user=request.user,
        institution=institution,
        is_favorite=True
    ).exists()
    
    logs = InstitutionLog.objects.filter(institution=institution).order_by('-created_at')

    context = {
        'institution': institution,
        'is_favorite': is_favorite,
        'logs': logs
    }
    return render(request, 'material/institutions_v2/detail.html', context)

# CANDIDATO A BORRAR (auditoría de navegación 2026-08-03, ver memoria
# project_sidebar_navigation_redesign): create_campus_v2, create_faculty_v2,
# edit_campus_v2, delete_campus_v2, edit_faculty_v2 y delete_faculty_v2 (las
# 6 vistas siguientes con sufijo _v2 sobre Campus/Faculty) apuntan a templates
# que no existen en el proyecto (material/campuses_v2/*, material/faculties_v2/*)
# — confirmado que tiran 500 (TemplateDoesNotExist) si se las visita. La
# gestión real de sedes/facultades ya ocurre vía el formset embebido en
# edit_institution_v2. Ningún template las enlaza. Conservadas a propósito
# (no eliminadas) hasta la próxima auditoría de limpieza de código muerto.
@login_required
def create_campus_v2(request, institution_id):
    institution = get_object_or_404(InstitutionV2, pk=institution_id, userinstitution__user=request.user)
    if request.method == 'POST':
        form = CampusV2Form(request.POST)
        if form.is_valid():
            campus = form.save(commit=False)
            campus.institution = institution
            campus.save()
            messages.success(request, 'Sede creada con éxito.')
            return redirect('material:institution_v2_detail', pk=institution_id)
    else:
        form = CampusV2Form()
    return render(request, 'material/campuses_v2/create.html', {'form': form, 'institution': institution})

# CANDIDATO A BORRAR — ver nota arriba de create_campus_v2.
@login_required
def create_faculty_v2(request, institution_id):
    institution = get_object_or_404(InstitutionV2, pk=institution_id, userinstitution__user=request.user)
    if request.method == 'POST':
        form = FacultyV2Form(request.POST)
        if form.is_valid():
            faculty = form.save(commit=False)
            faculty.institution = institution
            faculty.save()
            messages.success(request, 'Facultad creada con éxito.')
            return redirect('material:institution_v2_detail', pk=institution_id)
    else:
        form = FacultyV2Form()
    return render(request, 'material/faculties_v2/create.html', {'form': form, 'institution': institution})

@login_required
def set_visual_theme(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    theme = request.POST.get('theme')
    valid_themes = {choice for choice, _ in Profile.VISUAL_THEME_CHOICES}
    if theme not in valid_themes:
        return JsonResponse({'success': False, 'error': 'Tema inválido'}, status=400)
    profile = request.user.profile
    profile.visual_theme = theme
    profile.save(update_fields=['visual_theme'])
    return JsonResponse({'success': True, 'theme': theme})

@login_required
def delete_institution_logo_v2(request, pk):
    institution = get_object_or_404(InstitutionV2, pk=pk, userinstitution__user=request.user)
    if request.method == 'POST':
        try:
            institution.logo.delete()
            institution.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

# CANDIDATO A BORRAR — ver nota arriba de create_campus_v2.
@login_required
def edit_campus_v2(request, institution_id, campus_id):
    institution = get_object_or_404(InstitutionV2, pk=institution_id, userinstitution__user=request.user)
    campus = get_object_or_404(CampusV2, pk=campus_id, institution=institution)
    if request.method == 'POST':
        form = CampusV2Form(request.POST, instance=campus)
        if form.is_valid():
            form.save()
            return redirect('material:institution_v2_detail', pk=institution.pk)
    else:
        form = CampusV2Form(instance=campus)
    return render(request, 'material/campuses_v2/edit.html', {'form': form, 'institution': institution})

# CANDIDATO A BORRAR — ver nota arriba de create_campus_v2.
@login_required
def delete_campus_v2(request, institution_id, campus_id):
    institution = get_object_or_404(InstitutionV2, pk=institution_id, userinstitution__user=request.user)
    campus = get_object_or_404(CampusV2, pk=campus_id, institution=institution)
    if request.method == 'POST':
        campus.is_active = False  # Desactivar en lugar de eliminar
        campus.save()
        messages.success(request, 'Sede desactivada con éxito.')
        return redirect('material:institution_v2_detail', pk=institution.pk)
    return render(request, 'material/campuses_v2/confirm_delete.html', {'campus': campus, 'institution': institution})

# CANDIDATO A BORRAR — ver nota arriba de create_campus_v2.
@login_required
def edit_faculty_v2(request, institution_id, faculty_id):
    institution = get_object_or_404(InstitutionV2, pk=institution_id, userinstitution__user=request.user)
    faculty = get_object_or_404(FacultyV2, pk=faculty_id, institution=institution)
    if request.method == 'POST':
        form = FacultyV2Form(request.POST, instance=faculty)
        if form.is_valid():
            form.save()
            return redirect('material:institution_v2_detail', pk=institution.pk)
    else:
        form = FacultyV2Form(instance=faculty)
    return render(request, 'material/faculties_v2/edit.html', {'form': form, 'institution': institution})

# CANDIDATO A BORRAR — ver nota arriba de create_campus_v2.
@login_required
def delete_faculty_v2(request, institution_id, faculty_id):
    institution = get_object_or_404(InstitutionV2, pk=institution_id, userinstitution__user=request.user)
    faculty = get_object_or_404(FacultyV2, pk=faculty_id, institution=institution)
    if request.method == 'POST':
        faculty.is_active = False  # Desactivar en lugar de eliminar
        faculty.save()
        messages.success(request, 'Facultad desactivada con éxito.')
        return redirect('material:institution_v2_detail', pk=institution.pk)
    return render(request, 'material/faculties_v2/confirm_delete.html', {'faculty': faculty, 'institution': institution})

def _safe_next_url(request, default):
    """Resuelve a dónde debe volver un botón "Volver" — ?next=... si vino de
    algún lado que lo necesite pasar (ver /favoritos/, que enlaza a exámenes/
    plantillas/materias/lotes/orales y quiere que el "Volver" de esas
    pantallas regrese ahí en vez de a su listado de siempre), o `default`
    (el listado de siempre) si no vino ninguno o no es una ruta propia del
    sitio — nunca se usa un ?next= que apunte a otro dominio."""
    from django.utils.http import url_has_allowed_host_and_scheme
    next_url = request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return default


# --- Favoritos (genérico: exámenes, plantillas, materias, lotes) ---
_FAVORITE_MODELS = {
    'exam': Exam,
    'examtemplate': ExamTemplate,
    'subject': Subject,
    'batch': ExamVersionBatch,
    'oral': OralExamSet,
}


def _favoritable_queryset(model_key, user):
    """Alcance de "lo que este usuario puede marcar/ver como favorito" para
    cada tipo — antes toggle_favorite hacía get_object_or_404(model_cls, ...)
    a secas, sin dueño: cualquier usuario logueado podía favoritear el
    examen/plantilla/lote de cualquier otro por ID. Subject usa
    get_visible_subjects (propias + compartidas), no solo created_by,
    porque una materia compartida por un grupo de confianza es
    legítimamente favoriteable aunque no sea propia."""
    if model_key == 'exam':
        return Exam.objects.filter(created_by=user)
    if model_key == 'examtemplate':
        return ExamTemplate.objects.filter(created_by=user)
    if model_key == 'batch':
        return ExamVersionBatch.objects.filter(created_by=user)
    if model_key == 'oral':
        return OralExamSet.objects.filter(user=user)
    if model_key == 'subject':
        from .content_visibility import get_visible_subjects
        return get_visible_subjects(user)
    return None


@login_required
def toggle_favorite(request):
    """
    Alterna favorito para cualquiera de los modelos en _FAVORITE_MODELS.
    POST: model ('exam'|'examtemplate'|'subject'|'batch'), object_id.
    Devuelve JSON {'is_favorite': bool} para actualizar el ícono sin recargar.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    model_key = request.POST.get('model')
    object_id = request.POST.get('object_id')
    qs = _favoritable_queryset(model_key, request.user)
    if qs is None or not object_id:
        return JsonResponse({'error': 'Parámetros inválidos'}, status=400)

    obj = get_object_or_404(qs, pk=object_id)
    content_type = ContentType.objects.get_for_model(_FAVORITE_MODELS[model_key])
    favorite, created = Favorite.objects.get_or_create(
        user=request.user, content_type=content_type, object_id=obj.pk
    )
    if not created:
        favorite.delete()
        return JsonResponse({'is_favorite': False})
    return JsonResponse({'is_favorite': True})


@login_required
def favoritos_list(request):
    """Todos los favoritos del usuario (exámenes, plantillas, materias,
    lotes) en una sola pantalla. Cada Favorite es una fila genérica (ver
    modelo), así que se resuelve en bloque por tipo — máximo 4 queries
    extra (una por modelo en _FAVORITE_MODELS), no una por favorito.
    Un favorito cuyo objeto ya no existe o ya no es visible para este
    usuario (borrado, o dejó de compartirse) simplemente no se muestra —
    no se autoborra la fila Favorite, por si vuelve a ser visible después."""
    favorites = Favorite.objects.filter(user=request.user).select_related('content_type').order_by('-created_at')

    ct_model_to_key = {
        ContentType.objects.get_for_model(model_cls).model: key
        for key, model_cls in _FAVORITE_MODELS.items()
    }

    favs_by_ct_model = {}
    for fav in favorites:
        favs_by_ct_model.setdefault(fav.content_type.model, []).append(fav)

    resolved = {}  # (ct_model, object_id) -> objeto
    for ct_model, favs_for_model in favs_by_ct_model.items():
        model_key = ct_model_to_key.get(ct_model)
        qs = _favoritable_queryset(model_key, request.user)
        if qs is None:
            continue
        ids = [f.object_id for f in favs_for_model]
        for obj in qs.filter(pk__in=ids):
            resolved[(ct_model, obj.pk)] = obj

    items = []
    for fav in favorites:
        obj = resolved.get((fav.content_type.model, fav.object_id))
        if obj is None:
            continue
        items.append({
            'kind': ct_model_to_key.get(fav.content_type.model),
            'object': obj,
            'favorited_at': fav.created_at,
        })

    return render(request, 'material/favoritos_list.html', {'items': items})

# Subjects CRUD
@login_required
def subject_list(request):
    from .content_visibility import get_visible_subjects
    subjects = get_visible_subjects(request.user)
    favorite_ids = set(Favorite.objects.filter(
        user=request.user, content_type=ContentType.objects.get_for_model(Subject)
    ).values_list('object_id', flat=True))
    if request.GET.get('favoritos') == '1':
        subjects = subjects.filter(pk__in=favorite_ids)
    return render(request, 'material/subjects/list.html', {
        'subjects': subjects,
        'favorite_ids': favorite_ids,
        'only_favorites': request.GET.get('favoritos') == '1',
    })

@login_required
def delete_subject(request, pk):
    # Solo el dueño puede borrar — las compartidas por otros vía grupos de
    # confianza son visibles/usables pero no borrables.
    subject = get_object_or_404(Subject, pk=pk, created_by=request.user)
    if request.method == 'POST':
        try:
            subject.delete()
        except ProtectedError as e:
            messages.error(request, _protected_error_message(e), extra_tags='materias')
            return redirect('material:subject_list')
        messages.success(request, 'Materia eliminada exitosamente', extra_tags='materias')
        return redirect('material:subject_list')
    return render(request, 'material/subjects/confirm_delete.html', {
        'subject': subject,
        'preview': get_delete_preview(subject),
    })


@login_required
@require_POST
def bulk_eliminar_subjects(request):
    ids_raw = request.POST.getlist('subject_ids')
    ids = [int(i) for i in ids_raw if i.isdigit()]
    if not ids:
        messages.error(request, 'No se seleccionó ninguna materia para eliminar.', extra_tags='materias')
        return redirect('material:subject_list')

    # Solo las propias — ver nota de ownership en delete_subject.
    subjects = Subject.objects.filter(pk__in=ids, created_by=request.user)
    count = subjects.count()
    try:
        subjects.delete()
    except ProtectedError as e:
        messages.error(request, _protected_error_message(e), extra_tags='materias')
        return redirect('material:subject_list')

    if count == 1:
        messages.success(request, 'Se eliminó 1 materia exitosamente.', extra_tags='materias')
    else:
        messages.success(request, f'Se eliminaron {count} materias exitosamente.', extra_tags='materias')
    return redirect('material:subject_list')

class SubjectDetailView(DetailView):
    model = Subject
    template_name = 'material/subjects/detail.html'
    context_object_name = 'subject'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['outcomes'] = self.object.outcome_relations.all()  # Eliminado .order_by('code')
        context['back_url'] = _safe_next_url(self.request, reverse('material:subject_list'))
        return context


# Careers CRUD (similar structure)
# Columnas filtrables de Carreras, con el mismo motor generico de
# material/column_filters.py que ya usan Plantillas y Mis examenes.
# faculties/campus/subjects son M2M (a diferencia de los FK de ExamTemplate),
# de ahi el value_field explicito y el .distinct() que ya aplica el motor.
CAREER_FILTER_FIELDS = [
    ColumnFilterField('faculties', 'Facultades', value_field='faculties__id', label_field='faculties__name'),
    ColumnFilterField('campus', 'Campus', value_field='campus__id', label_field='campus__name'),
    ColumnFilterField('subjects', 'Materias', value_field='subjects__id', label_field='subjects__name'),
]
CAREER_FILTER_COLUMNS = [{'field': f.name, 'label': f.label} for f in CAREER_FILTER_FIELDS]


@login_required
def career_list(request):
    # Career no tiene dueño propio (a diferencia de Subject, ver
    # [[project_subject_topic_global_sharing_bug]]) — mismo bug de fondo,
    # todavía no resuelto de raíz. Fix parcial acá: se acota a las
    # instituciones a las que pertenece el usuario actual (real o cuenta
    # del Área de Pruebas), que alcanza para separar una cuenta de otra —
    # dos usuarios reales que comparten la misma institución pública
    # todavía se ven las carreras entre sí, igual que pasaba con Subject
    # antes del fix completo.
    user_institution_ids = UserInstitution.objects.filter(user=request.user).values_list('institution_id', flat=True)
    careers = Career.objects.filter(faculties__institution_id__in=user_institution_ids)
    # Igual que institution_v2_list: is_seed_demo=False solo para cuentas
    # reales — la cuenta del Área de Pruebas está vinculada a propósito a
    # instituciones semilla, y sus carreras SÍ deben verse ahí.
    if not getattr(request.user.profile, 'is_training_account', False):
        careers = careers.filter(is_seed_demo=False)
    careers = careers.distinct().prefetch_related('faculties', 'campus', 'subjects')

    selected_filters = get_selected_filters(request, CAREER_FILTER_FIELDS)
    filter_options = get_filter_options(careers, CAREER_FILTER_FIELDS, selected_filters)
    careers = apply_column_filters(request, careers, CAREER_FILTER_FIELDS)

    paginator = Paginator(careers, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'material/careers/list.html', {
        'careers': page_obj,
        'filter_options': filter_options,
        'selected_filters': selected_filters,
        'active_filter_count': get_active_filter_count(selected_filters),
        'filter_querystring': get_filter_querystring(request),
        'filter_columns': CAREER_FILTER_COLUMNS,
    })


@login_required
@require_POST
def bulk_eliminar_careers(request):
    ids_raw = request.POST.getlist('career_ids')
    ids = [int(i) for i in ids_raw if i.isdigit()]
    if not ids:
        messages.error(request, 'No se seleccionó ninguna carrera para eliminar.', extra_tags='carreras')
        return redirect('material:career_list')

    careers = Career.objects.filter(pk__in=ids)
    count = careers.count()
    try:
        careers.delete()
    except ProtectedError as e:
        messages.error(request, _protected_error_message(e), extra_tags='carreras')
        return redirect('material:career_list')

    if count == 1:
        messages.success(request, 'Se eliminó 1 carrera exitosamente.', extra_tags='carreras')
    else:
        messages.success(request, f'Se eliminaron {count} carreras exitosamente.', extra_tags='carreras')
    return redirect('material:career_list')

@login_required
def delete_career(request, pk):
    career = get_object_or_404(Career, pk=pk)
    if request.method == 'POST':
        try:
            career.delete()
        except ProtectedError as e:
            messages.error(request, _protected_error_message(e), extra_tags='carreras')
            return redirect('material:career_list')
        messages.success(request, 'Carrera eliminada exitosamente', extra_tags='carreras')
        return redirect('material:career_list')
    return render(request, 'material/careers/confirm_delete.html', {
        'career': career,
        'preview': get_delete_preview(career),
    })

class CareerDetailView(DetailView):
    model = Career
    template_name = 'material/careers/detail.html'
    context_object_name = 'career'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['related_subjects'] = self.object.subjects.all()
        context['related_faculties'] = self.object.faculties.all()
        context['related_campuses'] = self.object.campus.all()
        return context

@login_required
def career_create_simple(request):
    if request.method == 'POST':
        form = CareerForm(request.POST)
        if form.is_valid():
            career = form.save()

            institution = form.cleaned_data.get('institution')
            if institution:
                InstitutionCareer.objects.update_or_create(
                    career=career,
                    defaults={'institution': institution, 'is_active': True}
                )

            messages.success(request, 'Carrera creada exitosamente', extra_tags='carreras')
            return redirect('material:career_detail', pk=career.pk)
    else:
        form = CareerForm()

    return render(request, 'material/careers/associations.html', {
        'form': form,
        'career': None,
        'is_create': True,
    })

@login_required
def career_associations(request, pk):
    career = get_object_or_404(Career, pk=pk)
    
    if request.method == 'POST':
        form = CareerForm(request.POST, instance=career, career_pk=pk)
        if form.is_valid():
            # Guardar la carrera
            career = form.save()
            
            # Manejar la asociación con institución
            institution = form.cleaned_data.get('institution')
            if institution:
                # Actualizar o crear la asociación institución-carrera
                InstitutionCareer.objects.update_or_create(
                    career=career,
                    defaults={'institution': institution, 'is_active': True}
                )
            
            messages.success(request, 'Asociaciones actualizadas correctamente', extra_tags='examenes')
            return redirect('material:career_detail', pk=pk)
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario', extra_tags='examenes')
    else:
        form = CareerForm(instance=career, career_pk=pk)
    
    return render(request, 'material/careers/associations.html', {
        'form': form,
        'career': career
    })





@login_required
@require_http_methods(["POST"])
def create_related_element(request):
    """
    Vista para crear elementos relacionados de forma atómica
    Compatible con: institution, campus, faculty, career, subject
    """
    try:
        data = json.loads(request.body)
        model_type = data.get('type')
        name = data.get('name', '').strip()
        institution_id = data.get('institution_id')

        if not model_type:
            return JsonResponse({
                'success': False,
                'error': 'Tipo de elemento no especificado'
            }, status=400)

        if not name:
            return JsonResponse({
                'success': False, 
                'error': 'El nombre no puede estar vacío'
            }, status=400)

        with transaction.atomic():
            # INSTITUCIÓN
            if model_type == 'institution':
                if InstitutionV2.objects.filter(name__iexact=name).exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'Ya existe una institución con este nombre'
                    }, status=400)

                institution = InstitutionV2.objects.create(name=name)
                UserInstitution.objects.create(
                    user=request.user,
                    institution=institution
                )

                return JsonResponse({
                    'success': True,
                    'id': institution.id,
                    'name': institution.name
                })

            # CAMPUS
            elif model_type == 'campus':
                if not institution_id:
                    return JsonResponse({
                        'success': False,
                        'error': 'Se debe seleccionar una institución primero'
                    }, status=400)

                institution = get_object_or_404(
                    InstitutionV2, 
                    pk=institution_id,
                    userinstitution__user=request.user
                )

                if CampusV2.objects.filter(
                    institution=institution, 
                    name__iexact=name
                ).exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'Ya existe una sede con este nombre en la institución'
                    }, status=400)

                campus = CampusV2.objects.create(
                    institution=institution,
                    name=name
                )

                return JsonResponse({
                    'success': True,
                    'id': campus.id,
                    'name': campus.name
                })

            # FACULTAD
            elif model_type == 'faculty':
                if not institution_id:
                    return JsonResponse({
                        'success': False,
                        'error': 'Se debe seleccionar una institución primero'
                    }, status=400)

                institution = get_object_or_404(
                    InstitutionV2, 
                    pk=institution_id,
                    userinstitution__user=request.user
                )

                if FacultyV2.objects.filter(
                    institution=institution,
                    name__iexact=name
                ).exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'Ya existe una facultad con este nombre en la institución'
                    }, status=400)

                faculty = FacultyV2.objects.create(
                    institution=institution,
                    name=name
                )

                return JsonResponse({
                    'success': True,
                    'id': faculty.id,
                    'name': faculty.name
                })

            # CARRERA
            elif model_type == 'career':
                if Career.objects.filter(name__iexact=name).exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'Ya existe una carrera con este nombre'
                    }, status=400)

                career = Career.objects.create(name=name)
                return JsonResponse({
                    'success': True,
                    'id': career.id,
                    'name': career.name
                })

            # MATERIA
            elif model_type == 'subject':
                # Las materias semilla del asistente (is_seed_demo) no cuentan
                # para este chequeo de duplicado: si alguien tipea el mismo
                # nombre que una materia de ejemplo, se le crea una real
                # aparte en vez de bloquearlo (ver get_or_create_real_subject).
                if Subject.objects.filter(name__iexact=name, is_seed_demo=False).exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'Ya existe una materia con este nombre'
                    }, status=400)

                subject = Subject.objects.create(name=name, is_seed_demo=False)
                return JsonResponse({
                    'success': True,
                    'id': subject.id,
                    'name': subject.name
                })

            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Tipo de elemento no válido: {model_type}'
                }, status=400)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Formato de datos inválido'
        }, status=400)

    except Exception as e:
        logger.error(f"Error creating {model_type}: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Error interno del servidor: {str(e)}'
        }, status=500)


def get_faculties_by_institution(request, institution_id):
    """
    Devuelve las facultades asociadas a una institución en formato JSON.
    """
    print(f"get_faculties_by_institution called with institution_id: {institution_id}")  # DEBUG
    try:
        faculties = FacultyV2.objects.filter(institution_id=institution_id)
        # Facultad semilla excluida salvo en el vistazo de solo lectura del
        # asistente (?demo_peek=1), donde la institución elegida es
        # justamente la semilla y necesita mostrar su facultad de ejemplo.
        if not request.session.get('onb2_demo_scheme_active'):
            faculties = faculties.filter(institution__is_seed_demo=False)
        faculties = faculties.values('id', 'name')
        print(f"Faculties found: {faculties}")  # DEBUG
        return JsonResponse({'faculties': list(faculties)})
    except Exception as e:
        print(f"Error in get_faculties_by_institution: {e}")  # DEBUG
        return JsonResponse({'error': str(e)}, status=500)

def get_campuses_by_institution(request, institution_id):
    """
    Devuelve las sedes (campus) asociadas a una institución en formato JSON.
    """
    print(f"get_campuses_by_institution called with institution_id: {institution_id}")  # DEBUG
    try:
        campuses = CampusV2.objects.filter(institution_id=institution_id)
        if not request.session.get('onb2_demo_scheme_active'):
            campuses = campuses.filter(institution__is_seed_demo=False)
        campuses = campuses.values('id', 'name')
        print(f"Campuses found: {campuses}")  # DEBUG
        return JsonResponse({'campuses': list(campuses)})
    except Exception as e:
        print(f"Error in get_campuses_by_institution: {e}")  # DEBUG
        return JsonResponse({'error': str(e)}, status=500)

class LearningOutcomeCreateView(CreateView):
    model = LearningOutcome
    form_class = LearningOutcomeForm
    template_name = 'material/learningoutcome_form.html'
    
    def get_success_url(self):
        return reverse_lazy('material:subject_detail', kwargs={'pk': self.object.subject.id})

    def get_initial(self):
        return {'subject': self.kwargs['subject_id']}

    def form_valid(self, form):
        form.instance.subject_id = self.kwargs['subject_id']
        response = super().form_valid(form)
        messages.success(self.request, 'Resultado de aprendizaje creado exitosamente', extra_tags='materias')
        return response

class LearningOutcomeListView(ListView):
    model = LearningOutcome
    template_name = 'material/learningoutcome_list.html'
    context_object_name = 'outcomes'
    
    def get_queryset(self):
        return LearningOutcome.objects.filter(
            subject_id=self.kwargs['subject_id']
        ).order_by('created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subject'] = Subject.objects.get(pk=self.kwargs['subject_id'])
        return context


class LearningOutcomeUpdateView(UpdateView):
    model = LearningOutcome
    form_class = LearningOutcomeForm
    template_name = 'material/learningoutcome_form.html'
    
    def get_success_url(self):
        try:
            if self.object and self.object.subject and self.object.subject.id:
                return reverse_lazy('material:subject_detail', kwargs={'pk': self.object.subject.id})
        except (AttributeError, ValueError):
            pass
        return reverse_lazy('material:subject_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Resultado de aprendizaje actualizado exitosamente', extra_tags='materias')
        return response


class LearningOutcomeDeleteView(DeleteView):
    model = LearningOutcome
    template_name = 'material/learningoutcomes/confirm_delete.html'
    
    def get_success_url(self):
        try:
            if self.object and self.object.subject and self.object.subject.id:
                return reverse_lazy('material:subject_detail', kwargs={'pk': self.object.subject.id})
        except (AttributeError, ValueError):
            pass
        return reverse_lazy('material:subject_list')

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, 'Resultado de aprendizaje eliminado exitosamente', extra_tags='materias')
        return response
    

class SubjectCreateView(CreateView):
    model = Subject
    form_class = SubjectForm
    template_name = 'material/subjects/form.html'
    success_url = reverse_lazy('material:subject_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['outcome_formset'] = LearningOutcomeFormSet(
                self.request.POST,
                prefix='outcomes'
            )
        else:
            context['outcome_formset'] = LearningOutcomeFormSet(
                prefix='outcomes'
            )
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        outcome_formset = context['outcome_formset']
        
        if not outcome_formset.is_valid():
            return self.form_invalid(form)
            
        self.object = form.save()
        
        # Procesar outcomes a través del formset directamente
        outcomes = outcome_formset.save(commit=False)
        for outcome in outcomes:
            outcome.subject = self.object
            outcome.save()
            
        return super().form_valid(form)

class SubjectUpdateView(UpdateView):
    model = Subject
    form_class = SubjectForm
    template_name = 'material/subjects/form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subject = self.get_object()
        
        if self.request.POST:
            context['outcome_formset'] = LearningOutcomeFormSet(
                self.request.POST,
                instance=subject,
                prefix='outcomes'
            )
        else:
            context['outcome_formset'] = LearningOutcomeFormSet(
                instance=subject,
                prefix='outcomes',
                queryset=subject.outcome_relations.all()
            )
        
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        outcome_formset = context['outcome_formset']
        
        with transaction.atomic():
            self.object = form.save()
            
            if outcome_formset.is_valid():
                outcomes = outcome_formset.save(commit=False)
                for outcome in outcomes:
                    outcome.subject = self.object  # Asignamos el subject aquí
                    outcome.save()
                
                messages.success(self.request, 'Cambios guardados correctamente')
                return redirect('material:subject_detail', pk=self.object.pk)
            
        return self.render_to_response(self.get_context_data(form=form))
    
# Agregar estas funciones al final de views.py

@require_POST
@login_required
def add_topic(request):
    try:
        # Cambiamos a request.POST para los datos del formulario
        name = request.POST.get('name', '').strip()
        subject_id = request.POST.get('subject_id')
        
        # Validaciones
        if not name:
            return JsonResponse({
                'success': False,
                'error': 'El nombre del tópico no puede estar vacío'
            }, status=400)
            
        if not subject_id:
            return JsonResponse({
                'success': False,
                'error': 'Debe seleccionar una materia'
            }, status=400)
            
        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Materia no encontrada'
            }, status=404)
            
        # Verificar duplicados (case insensitive)
        if Topic.objects.filter(name__iexact=name, subject=subject).exists():
            return JsonResponse({
                'success': False,
                'error': 'Ya existe un tópico con este nombre en esta materia'
            }, status=400)
            
        # Crear el tema
        topic = Topic.objects.create(
            name=name,
            subject=subject,
            importance=3  # Valor por defecto
        )
        
        return JsonResponse({
            'success': True,
            'topic': {
                'id': topic.id,
                'name': topic.name,
                'subject_id': subject.id
            }
        })
        
    except Exception as e:
        logger.error(f"Error al agregar tema: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)


@require_POST
@login_required
def add_subtopic(request):
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        topic_id = data.get('topic_id')
        
        # Validaciones
        if not name:
            return JsonResponse({
                'success': False,
                'error': 'El nombre del sub-tópico no puede estar vacío'
            }, status=400)
            
        if not topic_id:
            return JsonResponse({
                'success': False,
                'error': 'Debe seleccionar un tópico principal'
            }, status=400)
            
        try:
            topic = Topic.objects.get(id=topic_id)
        except Topic.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Tópico no encontrado'
            }, status=404)
            
        # Verificar duplicados
        if Subtopic.objects.filter(name__iexact=name, topic=topic).exists():
            return JsonResponse({
                'success': False,
                'error': 'Ya existe un sub-tópico con este nombre en este tópico'
            }, status=400)
            
        # Crear el subtema
        subtopic = Subtopic.objects.create(
            name=name,
            topic=topic
        )
        
        # Registrar acción
        logger.info(f"Usuario {request.user} creó subtema {subtopic.id} en tema {topic.id}")
        
        return JsonResponse({
            'success': True,
            'subtopic': {
                'id': subtopic.id,
                'name': subtopic.name,
                'topic_id': topic.id
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Formato de datos inválido'
        }, status=400)
        
    except Exception as e:
        logger.error(f"Error al agregar subtema: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)

# Vistas para Cuestionarios Orales
@login_required
def validate_oral_exam(request):
    """Vista AJAX para validar configuración de examen oral"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        import json
        from collections import defaultdict
        
        data = json.loads(request.body)
        subject_id = data.get('subject_id')
        topic_ids = data.get('topic_ids', [])
        total_students = data.get('total_students', 0)
        questions_per_student = data.get('questions_per_student', 3)
        
        if not all([subject_id, topic_ids, total_students > 0]):
            return JsonResponse({'success': False, 'error': 'Datos incompletos'})
        
        # Obtener preguntas disponibles
        available_questions = Question.objects.filter(
            subjects__id=subject_id,
            topic_id__in=topic_ids,
            user=request.user
        ).select_related('topic', 'subtopic')
        
        if not available_questions.exists():
            return JsonResponse({
                'success': False, 
                'error': 'No hay preguntas disponibles para los tópicos seleccionados'
            })
        
        # Contar subtemas
        subtopics_count = defaultdict(int)
        for question in available_questions:
            key = question.subtopic.id if question.subtopic else f"topic_{question.topic.id}"
            subtopics_count[key] += 1
        
        total_subtopics = len(subtopics_count)
        total_questions = available_questions.count()
        max_students_per_group = total_subtopics  # Máximo para evitar repeticiones
        
        return JsonResponse({
            'success': True,
            'info': {
                'total_questions': total_questions,
                'total_subtopics': total_subtopics,
                'max_students_per_group': max_students_per_group,
                'subtopics_detail': dict(subtopics_count)
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Formato JSON inválido'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def create_oral_exam(request):
    if request.method == 'POST':
        form = OralExamForm(request.POST, user=request.user)
        if form.is_valid():
            oral_exam = form.save(commit=False)
            oral_exam.user = request.user
            
            # Calcular distribución real de estudiantes
            total_students = form.cleaned_data['total_students']
            num_groups = form.cleaned_data['num_groups']
            students_per_group = form.cleaned_data['students_per_group']
            
            # Ajustar students_per_group si es necesario
            base_students_per_group = total_students // num_groups
            extra_students = total_students % num_groups
            
            # Si la división no es exacta, ajustar
            if extra_students > 0:
                # Algunos grupos tendrán un estudiante más
                oral_exam.students_per_group = base_students_per_group + 1
            else:
                oral_exam.students_per_group = base_students_per_group
            
            oral_exam.save()
            form.save_m2m()  # Guardar las relaciones many-to-many
            
            # Generar las preguntas para cada grupo y estudiante
            generate_oral_exam_questions(oral_exam)
            
            messages.success(request, 'Cuestionario oral creado exitosamente', extra_tags='cuestionarios_orales')
            return redirect('material:view_oral_exam', exam_id=oral_exam.id)
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario', extra_tags='cuestionarios_orales')
    else:
        form = OralExamForm(user=request.user)
    
    return render(request, 'material/oral_exams/create.html', {'form': form})

@login_required
def view_oral_exam(request, exam_id):
    oral_exam = get_object_or_404(OralExamSet, id=exam_id, user=request.user)
    groups = oral_exam.groups.all().prefetch_related(
        'students__oralexamstudentquestion_set__question'
    )
    
    # Calcular total de estudiantes
    total_students = oral_exam.num_groups * oral_exam.students_per_group
    
    # Calcular total de preguntas
    total_questions = total_students * oral_exam.questions_per_student
    
    return render(request, 'material/oral_exams/view.html', {
        'oral_exam': oral_exam,
        'groups': groups,
        'total_students': total_students,
        'total_questions': total_questions,
        'back_url': _safe_next_url(request, reverse('material:list_oral_exams')),
    })

ORAL_EXAM_FILTER_FIELDS = [
    ColumnFilterField('subject', 'Materia', value_field='subject_id', label_field='subject__name'),
    ColumnFilterField('num_groups', 'Grupos'),
]
ORAL_EXAM_FILTER_COLUMNS = [{'field': f.name, 'label': f.label} for f in ORAL_EXAM_FILTER_FIELDS]


@login_required
def list_oral_exams(request):
    base_qs = OralExamSet.objects.filter(user=request.user)

    selected_filters = get_selected_filters(request, ORAL_EXAM_FILTER_FIELDS)
    filter_options = get_filter_options(base_qs, ORAL_EXAM_FILTER_FIELDS, selected_filters)
    oral_exams = apply_column_filters(request, base_qs, ORAL_EXAM_FILTER_FIELDS).order_by('-created_at')

    favorite_ids = set(Favorite.objects.filter(
        user=request.user, content_type=ContentType.objects.get_for_model(OralExamSet)
    ).values_list('object_id', flat=True))
    only_favorites = request.GET.get('favoritos') == '1'
    if only_favorites:
        oral_exams = oral_exams.filter(pk__in=favorite_ids)

    # Agregar total de estudiantes a cada examen
    for exam in oral_exams:
        exam.total_students = exam.num_groups * exam.students_per_group

    return render(request, 'material/oral_exams/list.html', {
        'oral_exams': oral_exams,
        'filter_options': filter_options,
        'selected_filters': selected_filters,
        'active_filter_count': get_active_filter_count(selected_filters),
        'filter_querystring': get_filter_querystring(request),
        'filter_columns': ORAL_EXAM_FILTER_COLUMNS,
        'favorite_ids': favorite_ids,
        'only_favorites': only_favorites,
        'favorites_toggle_querystring': get_filter_querystring_excluding(request, 'favoritos'),
    })


@login_required
@require_POST
def bulk_eliminar_cuestionarios_orales(request):
    """Borrado multiple de cuestionarios orales (mismo criterio que delete_oral_exam)."""
    ids_raw = request.POST.getlist('oral_exam_ids')
    ids = [int(i) for i in ids_raw if i.isdigit()]
    if not ids:
        messages.error(request, 'No se seleccionó ningún cuestionario oral para eliminar.', extra_tags='cuestionarios_orales')
        return redirect('material:list_oral_exams')

    oral_exams = OralExamSet.objects.filter(pk__in=ids, user=request.user)
    count = oral_exams.count()
    oral_exams.delete()

    if count == 1:
        messages.success(request, 'Se eliminó 1 cuestionario oral permanentemente.', extra_tags='cuestionarios_orales')
    else:
        messages.success(request, f'Se eliminaron {count} cuestionarios orales permanentemente.', extra_tags='cuestionarios_orales')
    return redirect('material:list_oral_exams')

def generate_oral_exam_questions(oral_exam):
    """
    Genera las preguntas para cada estudiante en cada grupo,
    evitando repeticiones por subtema dentro del grupo y por ronda
    """
    from collections import defaultdict
    import random
    from .models import OralExamGroup, OralExamStudent, OralExamStudentQuestion
    
    # Obtener todas las preguntas disponibles de los temas seleccionados
    available_questions = Question.objects.filter(
        subjects__id=oral_exam.subject.id,
        topic__in=oral_exam.topics.all(),
        user=oral_exam.user
    ).select_related('topic', 'subtopic')
    
    if not available_questions.exists():
        raise ValueError("No hay preguntas disponibles para los tópicos seleccionados")
    
    # Agrupar preguntas por subtema (o por tema si no hay subtema)
    questions_by_subtopic = defaultdict(list)
    for question in available_questions:
        key = question.subtopic.id if question.subtopic else f"topic_{question.topic.id}"
        questions_by_subtopic[key].append(question)
    
    # Verificar que hay suficientes subtemas para el algoritmo
    total_subtopics = len(questions_by_subtopic)
    min_subtopics_needed = oral_exam.students_per_group * oral_exam.questions_per_student
    
    if total_subtopics < min_subtopics_needed:
        print(f"Advertencia: Solo hay {total_subtopics} subtemas disponibles para {min_subtopics_needed} preguntas necesarias por grupo")
    
    # Calcular distribución de estudiantes por grupo
    total_students = oral_exam.total_students
    base_students_per_group = total_students // oral_exam.num_groups
    extra_students = total_students % oral_exam.num_groups
    
    students_assigned = 0
    
    # Crear los grupos
    for group_num in range(1, oral_exam.num_groups + 1):
        group = OralExamGroup.objects.create(
            exam_set=oral_exam,
            group_number=group_num
        )
        
        # Determinar cuántos estudiantes van en este grupo
        students_in_this_group = base_students_per_group
        if group_num <= extra_students:  # Los primeros grupos tienen un estudiante extra
            students_in_this_group += 1
            
        # Evitar crear grupos vacíos o exceder el total
        if students_assigned >= total_students:
            break
            
        actual_students_in_group = min(students_in_this_group, total_students - students_assigned)
        
        # *** ALGORITMO HÍBRIDO CORREGIDO ***
        # Control de preguntas usadas por grupo Y control de subtemas por ronda
        used_questions_in_group = set()  # Control global de preguntas por grupo
        used_subtopics_by_round = defaultdict(set)  # Control de subtemas por ronda
        
        # Crear estudiantes en el grupo
        students = []
        for student_num in range(1, actual_students_in_group + 1):
            student = OralExamStudent.objects.create(
                group=group,
                student_number=student_num
            )
            students.append(student)
            
        students_assigned += actual_students_in_group
        
        # Asignar preguntas ronda por ronda para mejor distribución de subtemas
        for round_num in range(1, oral_exam.questions_per_student + 1):
            # Lista de subtemas disponibles para esta ronda
            available_subtopics_for_round = [
                key for key in questions_by_subtopic.keys() 
                if key not in used_subtopics_by_round[round_num]
            ]
            
            # Si no hay suficientes subtemas únicos, resetear la ronda
            if len(available_subtopics_for_round) < len(students):
                available_subtopics_for_round = list(questions_by_subtopic.keys())
                used_subtopics_by_round[round_num] = set()
            
            random.shuffle(available_subtopics_for_round)
            
            # Asignar una pregunta de cada subtema a cada estudiante en esta ronda
            for i, student in enumerate(students):
                selected_question = None
                
                # Intentar usar un subtema diferente para esta ronda
                if i < len(available_subtopics_for_round):
                    subtopic_key = available_subtopics_for_round[i]
                    subtopic_questions = questions_by_subtopic[subtopic_key]
                    
                    # Buscar una pregunta de este subtema que no haya sido usada en el grupo
                    available_questions_in_subtopic = [
                        q for q in subtopic_questions 
                        if q.id not in used_questions_in_group
                    ]
                    
                    if available_questions_in_subtopic:
                        selected_question = random.choice(available_questions_in_subtopic)
                        # Marcar subtema como usado en esta ronda
                        used_subtopics_by_round[round_num].add(subtopic_key)
                
                # Si no encontramos pregunta del subtema preferido, buscar cualquier pregunta no usada
                if selected_question is None:
                    all_unused_questions = [
                        q for q in available_questions 
                        if q.id not in used_questions_in_group
                    ]
                    
                    if all_unused_questions:
                        selected_question = random.choice(all_unused_questions)
                        # Marcar el subtema de la pregunta seleccionada
                        subtopic_key = selected_question.subtopic.id if selected_question.subtopic else f"topic_{selected_question.topic.id}"
                        used_subtopics_by_round[round_num].add(subtopic_key)
                    else:
                        # Caso extremo: reutilizar preguntas (pocas preguntas disponibles)
                        if available_questions:
                            selected_question = random.choice(list(available_questions))
                            print(f"ADVERTENCIA: Reutilizando pregunta en Grupo {group_num}, Ronda {round_num} - Pocas preguntas disponibles")
                        else:
                            print(f"ERROR CRÍTICO: No hay preguntas disponibles")
                            continue
                
                # Marcar pregunta como usada en este grupo
                used_questions_in_group.add(selected_question.id)
                
                # Crear la asignación estudiante-pregunta
                OralExamStudentQuestion.objects.create(
                    student=student,
                    question=selected_question,
                    order=round_num
                )
        
        print(f"Grupo {group_num}: {len(used_questions_in_group)} preguntas únicas asignadas a {len(students)} estudiantes")

@login_required
def delete_oral_exam(request, exam_id):
    oral_exam = get_object_or_404(OralExamSet, id=exam_id, user=request.user)
    
    if request.method == 'POST':
        exam_name = oral_exam.name
        oral_exam.delete()
        messages.success(request, f'Cuestionario oral "{exam_name}" eliminado exitosamente', extra_tags='cuestionarios_orales')
        return redirect('material:list_oral_exams')
    
    return redirect('material:list_oral_exams')

@login_required
@require_POST
def evaluate_oral_question(request):
    """Vista AJAX para evaluar una pregunta de examen oral"""
    try:
        student_question_id = request.POST.get('student_question_id')
        evaluation = request.POST.get('evaluation')
        notes = request.POST.get('notes', '')
        
        if not student_question_id or not evaluation:
            return JsonResponse({
                'success': False,
                'error': 'Faltan parámetros requeridos'
            }, status=400)
        
        if evaluation not in ['bien', 'regular', 'mal', 'pendiente']:
            return JsonResponse({
                'success': False,
                'error': 'Evaluación inválida'
            }, status=400)
        
        # Verificar que la pregunta pertenece al usuario
        student_question = get_object_or_404(
            OralExamStudentQuestion,
            id=student_question_id,
            student__group__exam_set__user=request.user
        )
        
        # Actualizar evaluación
        student_question.evaluation = evaluation
        student_question.notes = notes
        if evaluation != 'pendiente':
            student_question.evaluated_at = timezone.now()
        else:
            student_question.evaluated_at = None
        student_question.save()
        
        # Obtener conteos actualizados del estudiante
        student = student_question.student
        evaluation_counts = student.get_evaluation_counts()
        progress_percentage = student.get_progress_percentage()
        score_percentage = student.get_score_percentage()
        
        return JsonResponse({
            'success': True,
            'evaluation_counts': evaluation_counts,
            'progress_percentage': progress_percentage,
            'score_percentage': score_percentage
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required 
@require_POST
def assign_student_names(request):
    """Vista AJAX para asignar nombres de estudiantes aleatoriamente"""
    try:
        exam_id = request.POST.get('exam_id')
        student_names = request.POST.get('student_names', '').strip()
        
        if not exam_id or not student_names:
            return JsonResponse({
                'success': False,
                'error': 'Se requiere ID del examen y lista de nombres'
            }, status=400)
        
        oral_exam = get_object_or_404(OralExamSet, id=exam_id, user=request.user)
        
        # Procesar nombres (uno por línea)
        names_list = [name.strip() for name in student_names.split('\n') if name.strip()]
        
        if not names_list:
            return JsonResponse({
                'success': False,
                'error': 'No se encontraron nombres válidos'
            }, status=400)
        
        # Obtener todos los estudiantes del examen
        all_students = OralExamStudent.objects.filter(
            group__exam_set=oral_exam
        ).order_by('group__group_number', 'student_number')
        
        total_students = all_students.count()
        
        if len(names_list) < total_students:
            return JsonResponse({
                'success': False,
                'error': f'Se necesitan al menos {total_students} nombres, solo se proporcionaron {len(names_list)}'
            }, status=400)
        
        # Mezclar nombres aleatoriamente
        import random
        random.shuffle(names_list)
        
        # Asignar nombres a estudiantes
        updates = []
        for i, student in enumerate(all_students):
            if i < len(names_list):
                student.student_name = names_list[i]
                updates.append(student)
        
        # Actualizar en lote
        OralExamStudent.objects.bulk_update(updates, ['student_name'])
        
        return JsonResponse({
            'success': True,
            'message': f'Se asignaron {len(updates)} nombres exitosamente',
            'assigned_count': len(updates)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def get_available_questions(request):
    """Vista AJAX para obtener preguntas disponibles para intercambio"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"get_available_questions called with params: {request.GET}")
        
        group_id = request.GET.get('group_id')
        current_question_id = request.GET.get('current_question_id')
        
        logger.info(f"Extracted params - group_id: {group_id}, current_question_id: {current_question_id}")
        
        if not group_id:
            logger.error("Missing group_id parameter")
            return JsonResponse({
                'success': False,
                'error': 'Se requiere group_id'
            }, status=400)
        
        # Verificar que el grupo pertenece al usuario
        logger.info(f"Looking for group {group_id} for user {request.user}")
        group = get_object_or_404(
            OralExamGroup,
            id=group_id,
            exam_set__user=request.user
        )
        logger.info(f"Found group: {group}")
        
        # Obtener preguntas ya usadas en este grupo
        used_questions = OralExamStudentQuestion.objects.filter(
            student__group=group
        ).values_list('question_id', flat=True)
        logger.info(f"Used questions in group: {list(used_questions)}")
        
        # Obtener el exam_set para filtrar por materia/temas
        exam_set = group.exam_set
        subject = exam_set.subject
        logger.info(f"Exam set: {exam_set}, Subject: {subject}")
        
        # Obtener los temas seleccionados para este examen oral
        selected_topics = exam_set.topics.all()
        logger.info(f"Selected topics for this exam: {list(selected_topics)}")
        
        # Obtener preguntas disponibles (no usadas en el grupo) 
        # FILTRADAS POR LOS TEMAS SELECCIONADOS en el examen
        available_questions = Question.objects.filter(
            user=request.user,
            subjects=subject,
            topic__in=selected_topics  # Solo preguntas de los temas seleccionados
        ).exclude(
            id__in=used_questions
        ).select_related('topic')
        
        # Si hay una pregunta actual, también incluirla como opción
        if current_question_id:
            try:
                # Usar Q objects para incluir la pregunta actual
                from django.db.models import Q
                available_questions = Question.objects.filter(
                    Q(user=request.user, subjects=subject, topic__in=selected_topics) & 
                    (Q(id=current_question_id) | ~Q(id__in=used_questions))
                ).select_related('topic')
            except Question.DoesNotExist:
                pass
        
        # Formatear respuesta
        questions_data = []
        for question in available_questions:
            # Mapear dificultad numérica a texto descriptivo
            difficulty_map = {
                1: 'Muy Fácil',
                2: 'Fácil', 
                3: 'Normal',
                4: 'Difícil',
                5: 'Muy Difícil'
            }
            difficulty_value = difficulty_map.get(question.difficulty, 'Normal')
            
            questions_data.append({
                'id': question.id,
                'question_text': question.question_text[:100] + ('...' if len(question.question_text) > 100 else ''),
                'topic_name': question.topic.name if question.topic else 'Sin tópico',
                'difficulty': difficulty_value
            })
        
        logger.info(f"Returning {len(questions_data)} available questions")
        return JsonResponse({
            'success': True,
            'available_questions': questions_data,
            'count': len(questions_data)
        })
        
    except Exception as e:
        logger.error(f"Error in get_available_questions: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_POST  
@login_required
def exchange_question(request):
    """Vista AJAX para intercambiar una pregunta específica"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"exchange_question called with POST data: {request.POST}")
        
        student_question_id = request.POST.get('student_question_id')
        new_question_id = request.POST.get('new_question_id')
        
        logger.info(f"Parameters - student_question_id: {student_question_id}, new_question_id: {new_question_id}")
        
        if not student_question_id or not new_question_id:
            logger.error("Missing required parameters")
            return JsonResponse({
                'success': False,
                'error': 'Faltan parámetros requeridos'
            }, status=400)
        
        # Verificar que la pregunta del estudiante pertenece al usuario
        student_question = get_object_or_404(
            OralExamStudentQuestion,
            id=student_question_id,
            student__group__exam_set__user=request.user
        )
        
        # Verificar que la nueva pregunta pertenece al usuario
        new_question = get_object_or_404(
            Question,
            id=new_question_id,
            user=request.user
        )
        
        # Verificar que la nueva pregunta no está siendo usada en el mismo grupo
        group = student_question.student.group
        is_question_used_in_group = OralExamStudentQuestion.objects.filter(
            student__group=group,
            question=new_question
        ).exclude(id=student_question_id).exists()
        
        if is_question_used_in_group:
            return JsonResponse({
                'success': False,
                'error': 'Esta pregunta ya está siendo usada por otro estudiante en el mismo grupo'
            }, status=400)
        
        # Guardar pregunta anterior para el log
        old_question = student_question.question
        
        # Realizar el intercambio
        logger.info(f"Exchanging question for student_question {student_question_id}")
        student_question.question = new_question
        
        # Resetear evaluación al intercambiar (solo si los campos existen)
        if hasattr(student_question, 'evaluation'):
            student_question.evaluation = 'pendiente'
        if hasattr(student_question, 'evaluated_at'):
            student_question.evaluated_at = None
        if hasattr(student_question, 'notes'):
            student_question.notes = ''
            
        student_question.save()
        logger.info(f"Question exchange completed successfully")
        
        logger.info(f"Returning success response")
        return JsonResponse({
            'success': True,
            'message': f'Pregunta intercambiada exitosamente',
            'old_question': old_question.question_text[:100] + ('...' if len(old_question.question_text) > 100 else ''),
            'new_question': new_question.question_text[:100] + ('...' if len(new_question.question_text) > 100 else ''),
            'new_question_full': new_question.question_text,
            'new_topic': new_question.topic.name if new_question.topic else 'Sin tópico'
        })
        
    except Exception as e:
        logger.error(f"Error in exchange_question: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# --- ONBOARDING WIZARD (endpoint compartido, usado por el wizard v2) -----------
# onboarding_upload_contenido (el otro endpoint que vivía acá) se eliminó junto
# con el modal viejo; este endpoint sigue en uso por el wizard de página
# completa (ver ONBOARDING WIZARD V2 más abajo), que guarda acá los pasos 1-3.

@require_POST
@login_required
def onboarding_save_step(request):
    """
    Endpoint AJAX para guardar cada paso del wizard de onboarding.
    Pasos:
      step=1  ? nombre del docente (first_name, last_name)
      step=2  ? institucion (elegir existente o crear nueva + sedes + facultades opcionales)
      step=3  ? materia (nombre + resultados de aprendizaje + temas opcionales)
      step=done ? marca onboarding_completed=True
    Siempre devuelve {"ok": true} - el frontend puede continuar aunque algo falle.
    """
    import json as _json

    try:
        body = _json.loads(request.body)
    except _json.JSONDecodeError:
        body = {}

    step = body.get('step')
    profile = request.user.profile
    extra = {}  # institution_id/subject_id resueltos, para que el frontend los pueda usar sin adivinar

    try:
        if step == 1:
            # Paso 1: nombre del docente
            first_name = body.get('first_name', '').strip()
            last_name = body.get('last_name', '').strip()
            if first_name or last_name:
                request.user.first_name = first_name
                request.user.last_name = last_name
                request.user.save(update_fields=['first_name', 'last_name'])

        elif step == 2:
            # Paso 2: institucion
            institution_id = body.get('institution_id')
            new_inst_name = body.get('new_institution_name', '').strip()

            if institution_id and body.get('edit_institution'):
                # Editar institución existente — solo si el usuario YA era
                # miembro antes de este request (mismo criterio que
                # edit_institution_v2/delete_campus_v2/etc: no alcanza con
                # mandar un ID por POST y "unirse" recién acá para poder
                # editar/borrar sedes y facultades de otra institución).
                try:
                    inst = InstitutionV2.objects.get(pk=institution_id, is_active=True)
                    ya_era_miembro = UserInstitution.objects.filter(
                        user=request.user, institution=inst
                    ).exists()
                    UserInstitution.objects.get_or_create(user=request.user, institution=inst)
                    extra['institution_id'] = inst.id
                    if ya_era_miembro:
                        # Renombrar si se indica un nombre nuevo
                        new_name = body.get('new_name', '').strip()
                        if new_name and new_name != inst.name:
                            inst.name = new_name
                            inst.save(update_fields=['name'])
                        # Agregar sedes nuevas
                        for cn in body.get('add_campuses', []):
                            cn = cn.strip()
                            if cn:
                                CampusV2.objects.get_or_create(institution=inst, name=cn)
                        # Eliminar sedes
                        remove_ids = [int(x) for x in body.get('remove_campus_ids', []) if str(x).isdigit()]
                        if remove_ids:
                            CampusV2.objects.filter(pk__in=remove_ids, institution=inst).delete()
                        # Agregar facultades nuevas
                        for fn in body.get('add_faculties', []):
                            fn = fn.strip()
                            if fn:
                                FacultyV2.objects.get_or_create(institution=inst, name=fn)
                        # Eliminar facultades
                        remove_fac_ids = [int(x) for x in body.get('remove_faculty_ids', []) if str(x).isdigit()]
                        if remove_fac_ids:
                            FacultyV2.objects.filter(pk__in=remove_fac_ids, institution=inst).delete()
                except InstitutionV2.DoesNotExist:
                    pass
            elif institution_id:
                # Solo vincular institución existente sin editar
                try:
                    inst = InstitutionV2.objects.get(pk=institution_id, is_active=True)
                    UserInstitution.objects.get_or_create(user=request.user, institution=inst)
                    extra['institution_id'] = inst.id
                except InstitutionV2.DoesNotExist:
                    pass
            elif new_inst_name:
                # Crear nueva institucion
                inst, _ = InstitutionV2.objects.get_or_create(name=new_inst_name)
                UserInstitution.objects.get_or_create(user=request.user, institution=inst)
                extra['institution_id'] = inst.id

                # Sedes opcionales (lista de nombres)
                for campus_name in body.get('campuses', []):
                    campus_name = campus_name.strip()
                    if campus_name:
                        CampusV2.objects.get_or_create(institution=inst, name=campus_name)

                # Facultades opcionales (lista de nombres)
                for fac_name in body.get('faculties', []):
                    fac_name = fac_name.strip()
                    if fac_name:
                        FacultyV2.objects.get_or_create(institution=inst, name=fac_name)

        elif step == 3:
            # Paso 3: materia — puede ser existente (solo link o edit) o nueva
            existing_subject_id = body.get('existing_subject_id')
            subject_name = body.get('subject_name', '').strip()
            # Institución elegida en el paso 2, para vincularla acá con la
            # materia via InstitutionSubject (antes este vínculo no se creaba).
            step2_institution_id = body.get('institution_id')

            def _link_institution_subject(subject_id):
                if step2_institution_id and str(step2_institution_id).isdigit() and subject_id:
                    InstitutionSubject.objects.get_or_create(
                        institution_id=int(step2_institution_id),
                        subject_id=subject_id,
                    )

            if existing_subject_id and body.get('edit_subject'):
                # Editar materia existente — solo si es dueño (antes cualquier
                # usuario podía editar/renombrar la materia de otro con solo
                # conocer su ID, ver [[project_subject_topic_global_sharing_bug]])
                try:
                    subj = Subject.objects.get(pk=existing_subject_id, created_by=request.user)
                    extra['subject_id'] = subj.id
                    new_name = body.get('new_name', '').strip()
                    if new_name and new_name != subj.name:
                        subj.name = new_name
                        subj.save(update_fields=['name'])
                    # Agregar outcomes nuevos
                    for od in body.get('add_outcomes', []):
                        od = od.strip()
                        if od:
                            LearningOutcome.objects.get_or_create(subject=subj, description=od)
                    # Eliminar outcomes
                    remove_outcome_ids = [int(x) for x in body.get('remove_outcome_ids', []) if str(x).isdigit()]
                    if remove_outcome_ids:
                        LearningOutcome.objects.filter(pk__in=remove_outcome_ids, subject=subj).delete()
                    # Agregar temas nuevos
                    for tn in body.get('add_topics', []):
                        tn = tn.strip()
                        if tn:
                            Topic.objects.get_or_create(name=tn, subject=subj, defaults={'importance': 3})
                    # Eliminar temas
                    remove_topic_ids = [int(x) for x in body.get('remove_topic_ids', []) if str(x).isdigit()]
                    if remove_topic_ids:
                        Topic.objects.filter(pk__in=remove_topic_ids, subject=subj).delete()
                except Subject.DoesNotExist:
                    pass
            elif existing_subject_id:
                # Solo vincular — no editar. Se valida que la materia sea
                # visible para este usuario (propia o compartida): antes se
                # aceptaba cualquier ID sin chequeo, permitiendo vincular
                # (y de ahí en más, escribir temas/preguntas) sobre la
                # materia de otro usuario con solo conocer su ID.
                from .content_visibility import get_visible_subjects
                if get_visible_subjects(request.user).filter(pk=existing_subject_id).exists():
                    extra['subject_id'] = int(existing_subject_id)
            elif subject_name:
                subject, _ = get_or_create_real_subject(subject_name, request.user)
                extra['subject_id'] = subject.id

                # Resultados de aprendizaje opcionales
                for ra in body.get('learning_outcomes', []):
                    ra = ra.strip()
                    if ra:
                        LearningOutcome.objects.get_or_create(subject=subject, description=ra)

                # Temas opcionales
                for topic_name in body.get('topics', []):
                    topic_name = topic_name.strip()
                    if topic_name:
                        Topic.objects.get_or_create(name=topic_name, subject=subject,
                                                    defaults={'importance': 3})

            _link_institution_subject(extra.get('subject_id'))

        elif step == 'seed_pref':
            # Preferencia de sumar contenido semilla del sistema al examen de
            # prueba, elegida por el usuario en el paso 3 (materia con match
            # semilla) o sugerida en el paso 6 (pocas preguntas propias). Se
            # consume una sola vez al guardar el examen (ver _collect_exam_post_data).
            request.session['onb2_include_seed'] = bool(body.get('include_seed'))

        if body.get('done') or step == 'done':
            profile.onboarding_completed = True
            profile.save(update_fields=['onboarding_completed'])

    except Exception as e:
        logger.error(f"Error en onboarding_save_step (step={step}): {e}", exc_info=True)
        # No fallamos - el wizard continua igual

    return JsonResponse(dict({'ok': True}, **extra))


# --- FIN ONBOARDING WIZARD -----------------------------------------------------

# --- ONBOARDING WIZARD V2 (página completa) -------------------------------------
# ROLLBACK: eliminar este bloque, la ruta /comenzar/ y sus endpoints, y revertir
# la migracion:  .venv\Scripts\python.exe manage.py migrate material 0034

@login_required
def onboarding_v2_page(request):
    """
    Página completa del nuevo asistente de configuración. No marca
    onboarding_completed acá: OnboardingGateMiddleware mantiene al usuario
    encerrado en el asistente (no puede usar el resto del sistema) hasta que
    termine de verdad (onboarding_v2_finish) o salga explícitamente
    (onboarding_v2_exit / "Saltar asistente").
    """
    # ?first=1 (solo lo agrega OnboardingGateMiddleware, en la invitación real
    # de primer login) distingue esta visita de una posterior al asistente —
    # ej. desde la tarjeta "Asistente guiado" de Inicio. El tour de driver.js
    # y el badge "Recomendado" del esquema ya armado solo tienen sentido la
    # primera vez.
    is_first_visit = request.GET.get('first') == '1'
    return render(request, 'material/onboarding_v2.html', {'is_first_visit': is_first_visit})


@login_required
def onboarding_v2_demo_scheme(request):
    """
    Rama "Probar con un esquema ya armado" de la pantalla de decisión del
    wizard: arma automáticamente, en 1-2 clicks, un examen de prueba usando
    contenido semilla del sistema para la materia elegida (sin pasar por los
    pasos manuales 2-5 de institución/materia/contenido/IA).
    """
    import datetime

    subject_id = request.GET.get('subject_id', '')
    if not subject_id.isdigit():
        messages.error(request, 'Elegir una materia de ejemplo válida.', extra_tags='general')
        return redirect('material:onboarding_v2_page')

    subject = Subject.objects.filter(
        pk=int(subject_id),
        questions__user__username=settings.SEED_CONTENT_USERNAME,
    ).distinct().first()
    if not subject:
        messages.error(request, 'Esa materia de ejemplo no está disponible.', extra_tags='general')
        return redirect('material:onboarding_v2_page')

    inst_subject = InstitutionSubject.objects.filter(subject=subject).select_related('institution').first()
    today = datetime.date.today()

    request.session['preview_exam'] = {
        'subject': str(subject.id),
        'institucion': str(inst_subject.institution_id) if inst_subject else '',
        'topics': ['all'],
        'learning_outcomes': [],
        'questions': [],
        'num_versions': '1',
        # 5, no 10: el objetivo de este examen es mostrar el flujo completo
        # del vistazo (Crear Examen -> Ver examen) sin que la vista previa
        # ocupe más de una pantalla estándar al hacer scroll.
        'questions_per_version': '5',
        'balance_by_topic': '1',
        'tipo_examen': 'practico',
        'tipo_modalidad': 'individual',
        'profesor': str(request.user.id),
        'fecha': today.isoformat(),
        'year': str(today.year),
        # Marca este examen como demo: es lo que le dice a preview_exam /
        # save_exam_from_session que sumen contenido semilla del sistema
        # además de (inexistentes, en este caso) preguntas propias del usuario.
        'include_seed': True,
    }
    request.session.pop('preview_generated_versions_ids', None)
    request.session['onb2_wizard_active'] = True
    # Marca específica de "este preview_exam es el ejemplo enlatado del
    # asistente" — distinta de onb2_wizard_active (que también se activa en
    # el wizard manual, donde el examen SÍ debe guardarse de verdad). Le dice
    # a preview_exam que muestre el flujo de guardado simulado en vez del
    # real, para no ensuciar la cuenta del usuario con un Exam real antes de
    # que arme algo propio.
    request.session['onb2_demo_scheme_active'] = True
    # get_topics?for_exam=1 (usado por create_exam.js en el vistazo de
    # ?demo_peek=1) filtra tópicos por preguntas VISIBLES para este usuario,
    # y solo cuenta preguntas semilla si esta marca está activa — sin
    # setearla acá, el vistazo de Crear Examen mostraba tópicos y preguntas
    # vacíos (ninguna pregunta del ejemplo es "propia" de este usuario, son
    # todas del bot de contenido semilla).
    request.session['onb2_include_seed'] = True
    return redirect('material:onboarding_v2_demo_recap')


@login_required
def onboarding_v2_demo_update_selection(request):
    """
    El vistazo de solo lectura en /create-exam/?demo_peek=1 recorre con
    driver.js una selección real de tópicos/preguntas (ver create_exam.html)
    para enseñar el filtrado, pero ese formulario nunca se envía de verdad
    (es de lectura, no un submit real). Sin esto, preview_exam seguía
    mostrando el sentinel 'all' + autoselección de onboarding_v2_demo_scheme,
    y lo que se vio tildado en el recorrido no coincidía con el examen de
    la vista previa. Se llama justo antes de navegar a "Ver examen".
    """
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)
    exam_session = request.session.get('preview_exam')
    if not exam_session or not request.session.get('onb2_demo_scheme_active'):
        return JsonResponse({'success': False}, status=400)

    topics = [t for t in request.POST.getlist('topics') if t]
    questions = [q for q in request.POST.getlist('questions') if q]
    if topics:
        exam_session['topics'] = topics
    if questions:
        exam_session['questions'] = questions
    request.session['preview_exam'] = exam_session
    request.session.pop('preview_generated_versions_ids', None)
    return JsonResponse({'success': True})


@login_required
def onboarding_v2_demo_recap(request):
    """
    Pantalla intermedia entre elegir una materia de ejemplo y ver el examen
    armado. onboarding_v2_demo_scheme resuelve todo en un solo request
    server-side (sin pasar por Subir Contenido / Procesador de IA / Mis
    Preguntas / Crear Examen como haría un usuario real), lo que hacía que
    el atajo se sintiera instantáneo y sintético. Acá se muestra un
    resumen — con datos reales del contenido semilla, no inventados — de
    esos mismos pasos ya completados, antes de mostrar el examen.
    """
    exam_session = request.session.get('preview_exam')
    if not exam_session:
        return redirect('material:onboarding_v2_page')

    subject = Subject.objects.filter(pk=exam_session.get('subject')).first()
    if not subject:
        return redirect('material:onboarding_v2_page')

    institution = InstitutionV2.objects.filter(pk=exam_session.get('institucion')).first()
    topics = list(Topic.objects.filter(subject=subject).order_by('name').values_list('name', flat=True))
    seed_username = getattr(settings, 'SEED_CONTENT_USERNAME', 'educaapp_demo')
    questions_qs = Question.objects.filter(subjects=subject, user__username=seed_username)

    return render(request, 'material/onboarding_v2_demo_recap.html', {
        'subject': subject,
        'institution': institution,
        'topics': topics,
        'questions_count': questions_qs.count(),
        'approved_count': questions_qs.filter(ai_approved=True).count(),
    })


@login_required
def onboarding_v2_demo_exam_list(request):
    """
    "Mis Exámenes" simulado: se muestra después de simular el guardado del
    examen de ejemplo (ver preview_exam con is_demo=True) — un único ítem
    fijo, sin tocar la base de datos, para que el usuario vea cómo se vería
    su examen ya guardado en el listado real, sin ensuciar su cuenta con un
    Exam real todavía. Ver [[project_onboarding_reform_2026_08]].
    """
    exam_session = request.session.get('preview_exam')
    if not exam_session or not request.session.get('onb2_demo_scheme_active'):
        return redirect('material:onboarding_v2_page')

    subject = Subject.objects.filter(pk=exam_session.get('subject')).first()
    if not subject:
        return redirect('material:onboarding_v2_page')

    import datetime
    return render(request, 'material/onboarding_v2_demo_exam_list.html', {
        'subject': subject,
        'today': datetime.date.today(),
    })


@login_required
def onboarding_v2_subject_status(request):
    """
    Estado de una materia para decidir si sugerir sumar contenido semilla:
    cuántas preguntas propias tiene el usuario, si esa materia tiene contenido
    semilla disponible, y si la preferencia de sumarlo ya está activa (elegida
    antes, en el paso 3). Usado por el paso 6 del wizard para la sugerencia de
    "tenés pocas preguntas propias" — nunca mezcla materias distintas, siempre
    se consulta por un subject_id puntual.
    """
    subject_id = request.GET.get('subject_id', '')
    if not subject_id.isdigit():
        return JsonResponse({'own_count': 0, 'has_seed': False, 'include_seed_active': False})

    from .content_visibility import EXAM_ELIGIBLE_Q
    own_count = Question.objects.filter(
        EXAM_ELIGIBLE_Q, user=request.user, subjects__id=int(subject_id),
    ).distinct().count()
    has_seed = Question.objects.filter(
        subjects__id=int(subject_id), user__username=settings.SEED_CONTENT_USERNAME
    ).exists()
    return JsonResponse({
        'own_count': own_count,
        'has_seed': has_seed,
        'include_seed_active': bool(request.session.get('onb2_include_seed')),
    })


@login_required
def onboarding_v2_finish(request):
    """
    Pantalla final del wizard v2: se llega acá después de guardar un examen
    estando en modo asistente (ver onb2_wizard_active en save_exam_from_session).
    Marca onboarding_completed=True: recién acá el usuario queda liberado del
    "gate" que lo mantenía encerrado en el asistente.
    """
    request.session.pop('onb2_wizard_active', None)
    request.session.pop('onb2_include_seed', None)
    request.session.pop('onb2_demo_scheme_active', None)
    try:
        profile = request.user.profile
        if not profile.onboarding_completed:
            profile.onboarding_completed = True
            profile.save(update_fields=['onboarding_completed'])
    except Exception:
        pass
    return render(request, 'material/onboarding_v2_finish.html', {})


@login_required
def onboarding_v2_exit(request):
    """
    Salida explícita del asistente ("Salir del asistente" en el banner de los
    pasos 5/6, fuera de la SPA de /comenzar/). Igual que "Saltar asistente":
    libera al usuario del gate sin obligarlo a terminar el examen.
    """
    request.session.pop('onb2_wizard_active', None)
    request.session.pop('onb2_include_seed', None)
    request.session.pop('onb2_demo_scheme_active', None)
    try:
        profile = request.user.profile
        if not profile.onboarding_completed:
            profile.onboarding_completed = True
            profile.save(update_fields=['onboarding_completed'])
    except Exception:
        pass
    return redirect('material:index')


@require_POST
@login_required
def onboarding_v2_connect_gemini(request):
    """
    Permite pegar una API key de Gemini propia directamente desde el paso 5
    del wizard nuevo, sin pasar por la pantalla "Proveedor de IA".
    Valida la key contra la API de Gemini antes de guardarla.
    """
    import json as _json
    from .ai_router import GeminiBackend
    from .models import UserAIConfig

    try:
        body = _json.loads(request.body)
    except _json.JSONDecodeError:
        body = {}

    api_key = (body.get('api_key') or '').strip()
    if not api_key:
        return JsonResponse({'ok': False, 'error': 'Ingresar una API key.'}, status=400)

    backend = GeminiBackend(api_key=api_key)
    if not backend.is_available():
        error = backend._last_error or 'No se pudo validar la API key con Gemini.'
        return JsonResponse({'ok': False, 'error': error}, status=400)

    config, _created = UserAIConfig.objects.get_or_create(user=request.user)
    config.source = 'byok'
    config.provider = 'gemini'
    config.api_key = api_key
    config.model = config.model if config.model and config.model.startswith('gemini-') else 'gemini-2.5-flash-lite'
    config.save()

    return JsonResponse({'ok': True, 'status': backend.get_status()})

# --- FIN ONBOARDING WIZARD V2 ----------------------------------------------------

# --- RÚBRICAS ------------------------------------------------------------------

def _prepare_rubric_grid(rubric):
    """Devuelve un dict con la estructura de la rúbrica para renderizar en templates.
    {'title', 'levels': [str], 'rows': [{'name', 'cells': [str]}], 'body'}
    """
    ordered_levels = list(rubric.levels.order_by('order'))
    ordered_criteria = list(rubric.criteria.order_by('order'))
    if not ordered_levels:
        return {'title': rubric.title, 'levels': [], 'rows': []}
    cells_map = {
        (c.criterion_id, c.level_id): c.description
        for c in RubricCell.objects.filter(criterion__rubric=rubric)
    }
    return {
        'title': rubric.title,
        'levels': [lv.label for lv in ordered_levels],
        'rows': [
            {
                'name': cr.name,
                'cells': [cells_map.get((cr.id, lv.id), '') for lv in ordered_levels],
            }
            for cr in ordered_criteria
        ],
    }


@login_required
def rubric_list(request):
    from django.db.models import Count
    rubricas = Rubric.objects.filter(created_by=request.user).annotate(
        level_count=Count('levels', distinct=True),
        criterion_count=Count('criteria', distinct=True),
    )
    return render(request, 'material/rubricas/list.html', {'rubricas': rubricas})


def _save_rubric_grid(request, rubrica):
    """Parsea la grilla del POST y guarda niveles, criterios y celdas."""
    import json as _json
    level_count = int(request.POST.get('level_count', 0) or 0)
    criterion_count = int(request.POST.get('criterion_count', 0) or 0)

    # Borrar estructura anterior (cascada a celdas)
    rubrica.criteria.all().delete()
    rubrica.levels.all().delete()

    levels = []
    for i in range(level_count):
        label = request.POST.get(f'level_label_{i}', '').strip()
        if label:
            lv = RubricLevel.objects.create(rubric=rubrica, label=label, order=i)
            levels.append((i, lv))

    for j in range(criterion_count):
        name = request.POST.get(f'criterion_name_{j}', '').strip()
        if name:
            cr = RubricCriterion.objects.create(rubric=rubrica, name=name, order=j)
            for orig_i, lv in levels:
                desc = request.POST.get(f'cell_{j}_{orig_i}', '')
                RubricCell.objects.create(criterion=cr, level=lv, description=desc)


@login_required
def rubric_create(request):
    import json as _json
    DEFAULT_LEVELS = _json.dumps(['4', '3', '2', '1'])
    DEFAULT_CRITERIA = _json.dumps([{'name': '', 'cells': ['', '', '', '']}])

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, 'El título es obligatorio.')
        else:
            with transaction.atomic():
                rubrica = Rubric.objects.create(title=title, created_by=request.user)
                _save_rubric_grid(request, rubrica)
            messages.success(request, 'Rúbrica creada correctamente.')
            return redirect('material:rubric_list')

    return render(request, 'material/rubricas/form.html', {
        'action': 'Crear',
        'levels_json': DEFAULT_LEVELS,
        'criteria_json': DEFAULT_CRITERIA,
    })


@login_required
def rubric_edit(request, pk):
    import json as _json
    rubrica = get_object_or_404(Rubric, pk=pk, created_by=request.user)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, 'El título es obligatorio.')
        else:
            with transaction.atomic():
                rubrica.title = title
                rubrica.save()
                _save_rubric_grid(request, rubrica)
            messages.success(request, 'Rúbrica actualizada correctamente.')
            return redirect('material:rubric_list')

    # GET: cargar estructura existente
    ordered_levels = list(rubrica.levels.order_by('order'))
    ordered_criteria = list(rubrica.criteria.order_by('order'))
    cells_map = {
        (c.criterion_id, c.level_id): c.description
        for c in RubricCell.objects.filter(criterion__rubric=rubrica)
    }

    if not ordered_levels:
        levels_json = _json.dumps(['4', '3', '2', '1'])
        criteria_json = _json.dumps([{'name': '', 'cells': ['', '', '', '']}])
    else:
        levels_json = _json.dumps([lv.label for lv in ordered_levels])
        criteria_json = _json.dumps([
            {
                'name': cr.name,
                'cells': [cells_map.get((cr.id, lv.id), '') for lv in ordered_levels],
            }
            for cr in ordered_criteria
        ])

    return render(request, 'material/rubricas/form.html', {
        'action': 'Editar',
        'rubrica': rubrica,
        'levels_json': levels_json,
        'criteria_json': criteria_json,
    })


@login_required
def rubric_delete(request, pk):
    rubrica = get_object_or_404(Rubric, pk=pk, created_by=request.user)
    if request.method == 'POST':
        rubrica.delete()
        messages.success(request, 'Rúbrica eliminada.')
    return redirect('material:rubric_list')


def _can_manage_print_format(user, formato):
    if is_admin(user):
        return True
    if formato.user_id == user.id:
        return True
    institution_ids = UserInstitution.objects.filter(user=user).values_list('institution_id', flat=True)
    return formato.institution_id in institution_ids


@login_required
def formato_impresion_list(request):
    formatos = get_visible_print_formats(request.user).distinct().order_by('nombre')
    return render(request, 'material/formatos_impresion/list.html', {
        'formatos': formatos,
    })


@login_required
def formato_impresion_create(request):
    if request.method == 'POST':
        form = FormatoImpresionForm(request.POST, current_user=request.user)
        if form.is_valid():
            with transaction.atomic():
                formato = form.save(commit=False)
                if formato.es_default:
                    clear_existing_default_for_scope(user=formato.user, institution=formato.institution)
                formato.save()
            messages.success(request, 'Formato de impresión creado correctamente.')
            return redirect('material:formato_impresion_list')
    else:
        form = FormatoImpresionForm(current_user=request.user)

    return render(request, 'material/formatos_impresion/form.html', {'form': form, 'action': 'Crear'})


@login_required
def formato_impresion_edit(request, pk):
    formato = get_object_or_404(FormatoImpresion, pk=pk)
    if not _can_manage_print_format(request.user, formato):
        messages.error(request, 'No tienes permisos para editar este formato.')
        return redirect('material:formato_impresion_list')

    if request.method == 'POST':
        form = FormatoImpresionForm(request.POST, instance=formato, current_user=request.user)
        if form.is_valid():
            with transaction.atomic():
                formato = form.save(commit=False)
                if formato.es_default:
                    clear_existing_default_for_scope(user=formato.user, institution=formato.institution, exclude_id=formato.pk)
                formato.save()
                selected_exam_ids = [int(v) for v in request.POST.getlist('propagate_exam_ids') if str(v).isdigit()]
                if selected_exam_ids:
                    updated = propagate_print_format_to_exams(formato, selected_exam_ids)
                    messages.info(request, f'Se actualizaron {updated} examen(es) vinculados a este formato.')
            messages.success(request, 'Formato de impresión actualizado correctamente.')
            return redirect('material:formato_impresion_list')
    else:
        form = FormatoImpresionForm(instance=formato, current_user=request.user)

    assigned_exams = formato.formatos_asignados.select_related('exam', 'exam__subject').order_by('-updated_at') if formato.pk else []

    return render(request, 'material/formatos_impresion/form.html', {
        'form': form,
        'action': 'Editar',
        'formato': formato,
        'assigned_exams': assigned_exams,
    })


@login_required
@require_POST
def formato_impresion_delete(request, pk):
    formato = get_object_or_404(FormatoImpresion, pk=pk)
    if not _can_manage_print_format(request.user, formato):
        messages.error(request, 'No tienes permisos para eliminar este formato.')
        return redirect('material:formato_impresion_list')
    formato.delete()
    messages.success(request, 'Formato de impresión eliminado.')
    return redirect('material:formato_impresion_list')


@login_required
@require_POST
def formato_impresion_set_default(request, pk):
    formato = get_object_or_404(FormatoImpresion, pk=pk)
    if not _can_manage_print_format(request.user, formato):
        messages.error(request, 'No tienes permisos para marcar este formato como predeterminado.')
        return redirect('material:formato_impresion_list')
    with transaction.atomic():
        clear_existing_default_for_scope(user=formato.user, institution=formato.institution, exclude_id=formato.pk)
        formato.es_default = True
        formato.save(update_fields=['es_default'])
    messages.success(request, 'Formato marcado como predeterminado.')
    return redirect('material:formato_impresion_list')


@login_required
def exam_rubrics(request, exam_pk):
    from .content_visibility import get_visible_rubrics

    examen = get_object_or_404(Exam, pk=exam_pk, created_by=request.user)
    exam_rubric_qs = ExamRubric.objects.filter(exam=examen).select_related('rubric').order_by('position', 'id')
    associated_ids = exam_rubric_qs.values_list('rubric_id', flat=True)
    available_rubrics = get_visible_rubrics(request.user).exclude(id__in=associated_ids)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            rubric_id = request.POST.get('rubric_id')
            rubrica = get_object_or_404(get_visible_rubrics(request.user), pk=rubric_id)
            ExamRubric.objects.get_or_create(exam=examen, rubric=rubrica)
            messages.success(request, f'Rúbrica «{rubrica.title}» agregada.')
        elif action == 'remove':
            er_id = request.POST.get('exam_rubric_id')
            ExamRubric.objects.filter(pk=er_id, exam=examen).delete()
            messages.success(request, 'Rúbrica quitada del examen.')
        elif action == 'toggle':
            er_id = request.POST.get('exam_rubric_id')
            er = get_object_or_404(ExamRubric, pk=er_id, exam=examen)
            er.show_in_exam = not er.show_in_exam
            er.save()
        return redirect('material:exam_rubrics', exam_pk=exam_pk)

    # Preparar grillas para preview
    exam_rubric_grids = [
        {'er': er, 'grid': _prepare_rubric_grid(er.rubric)}
        for er in exam_rubric_qs
    ]
    available_rubric_grids = [
        {'rubrica': r, 'grid': _prepare_rubric_grid(r)}
        for r in available_rubrics
    ]

    return render(request, 'material/rubricas/exam_rubrics.html', {
        'examen': examen,
        'exam_rubric_grids': exam_rubric_grids,
        'available_rubric_grids': available_rubric_grids,
    })

# --- FIN RÚBRICAS --------------------------------------------------------------


# ---------------------------------------------------------------------------
# Configuración de proveedor de IA
# ---------------------------------------------------------------------------
@login_required
def ai_config_view(request):
    """Página donde el usuario elige su proveedor de IA."""
    from .models import UserAIConfig, InstitutionV2, UserInstitution

    config, _ = UserAIConfig.objects.get_or_create(user=request.user)

    # Instituciones con configuración IA activa a las que el usuario pertenece
    # Defensivo: puede que InstitutionAIConfig no exista en BD de producción
    institutions_with_ai = []
    try:
        user_inst_ids = UserInstitution.objects.filter(
            user=request.user
        ).values_list('institution_id', flat=True)
        institutions_with_ai = InstitutionV2.objects.filter(
            pk__in=user_inst_ids,
            ai_config__is_active=True,
        ).select_related('ai_config')
    except Exception:
        pass  # Si falla, simplemente no muestra instituciones con IA

    if request.method == 'POST':
        source = request.POST.get('source', 'ollama_local')
        config.source = source

        if source == 'ollama_local':
            raw_ollama_url = request.POST.get('ollama_url', '').strip()
            config.ollama_url = raw_ollama_url or None

        elif source == 'byok':
            config.provider = request.POST.get('provider', 'openai')
            provider = config.provider or 'openai'
            provider_defaults = {
                'openai': 'gpt-4o-mini',
                'gemini': 'gemini-2.5-flash-lite',
                'anthropic': 'claude-3-haiku-20240307',
                'groq': 'llama-3.1-8b-instant',
                'mistral': 'mistral-small-latest',
                'openrouter': 'openai/gpt-4o-mini',
                'openai_compatible': 'gpt-4o-mini',
            }
            model = request.POST.get('model', '').strip()
            default_model = provider_defaults.get(provider, 'gpt-4o-mini')
            if not model or model == 'gpt-4o-mini':
                model = default_model
            if provider == 'gemini' and not model.startswith('gemini-'):
                model = 'gemini-2.5-flash-lite'
            config.model = model
            config.base_url = request.POST.get('base_url', '').strip() or None
            raw_key = request.POST.get('api_key', '').strip()
            if raw_key:  # no sobrescribir si el campo quedó vacío
                config.api_key = raw_key

        elif source == 'institutional':
            inst_id = request.POST.get('institution_id', '').strip()
            if inst_id:
                try:
                    config.institution = InstitutionV2.objects.get(pk=int(inst_id))
                except (InstitutionV2.DoesNotExist, ValueError):
                    pass

        config.save()
        messages.success(request, 'Configuración de IA guardada correctamente.')
        return redirect('material:ai_config')

    context = {
        'config': config,
        'institutions_with_ai': institutions_with_ai,
        'has_api_key': bool(config.api_key_encrypted),
        'is_staff': is_admin(request.user),
        'default_ollama_url': 'http://192.168.12.236:11434',
    }
    return render(request, 'material/ai_config.html', context)


@login_required
def ai_config_list_models(request):
    """Endpoint JSON: consulta al proveedor la lista de modelos disponibles para la API key ingresada."""
    from django.http import JsonResponse
    from .ai_router import list_models_for_provider
    from .models import UserAIConfig

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

    provider = request.POST.get('provider', '').strip()
    base_url = request.POST.get('base_url', '').strip() or None
    api_key = request.POST.get('api_key', '').strip()

    if not api_key:
        # Si no se ingresó una key nueva, usar la ya guardada (si coincide el proveedor)
        config, _ = UserAIConfig.objects.get_or_create(user=request.user)
        if config.provider == provider and config.api_key_encrypted:
            api_key = config.api_key

    success, models, error = list_models_for_provider(provider, api_key, base_url)
    return JsonResponse({'success': success, 'models': models, 'error': error})


@login_required
def ai_config_status(request):
    """Endpoint JSON que devuelve el estado actual del backend configurado."""
    from django.http import JsonResponse
    from .ai_router import get_backend_for_user, get_global_demo_quota, ensure_fresh_demo_quota, SharedDemoBackend
    from .models import UserAIConfig

    config, _ = UserAIConfig.objects.get_or_create(user=request.user)
    backend = get_backend_for_user(request.user)
    is_global_fallback = isinstance(backend, SharedDemoBackend)
    try:
        status = backend.get_status()
        # Siempre devolver el source real del usuario como 'backend'
        status['backend'] = config.source
    except Exception as e:
        status = {'connected': False, 'error': str(e), 'backend': config.source}

    status['using_shared_fallback'] = is_global_fallback
    if is_global_fallback:
        ensure_fresh_demo_quota()
        quota = get_global_demo_quota()
        if quota:
            status['demo_quota'] = {
                'provider': quota['provider'],
                'checked_at': quota['checked_at'].isoformat(),
                'remaining_requests': quota['remaining_requests'],
                'limit_requests': quota['limit_requests'],
                'requests_reset_at': quota['requests_reset_at'].isoformat() if quota['requests_reset_at'] else None,
                'remaining_tokens': quota['remaining_tokens'],
                'limit_tokens': quota['limit_tokens'],
            }
    return JsonResponse(status)


@login_required
def institution_ai_config_view(request):
    """Vista para que los administradores gestionen InstitutionAIConfig."""
    from .models import InstitutionAIConfig, InstitutionV2

    if not is_admin(request.user):
        messages.error(request, 'No hay permiso para acceder a esta sección.')
        return redirect('material:ai_config')

    # ── Eliminar ──
    if 'delete' in request.GET and request.method == 'POST':
        try:
            cfg = InstitutionAIConfig.objects.get(pk=int(request.GET['delete']))
            cfg.delete()
            messages.success(request, 'Configuración eliminada.')
        except (InstitutionAIConfig.DoesNotExist, ValueError):
            messages.error(request, 'Configuración no encontrada.')
        return redirect('material:institution_ai_config')

    # ── Crear / Editar ──
    if request.method == 'POST':
        config_id = request.POST.get('config_id', '').strip()
        institution_id = request.POST.get('institution_id', '').strip()
        provider = request.POST.get('provider', 'openai').strip()
        model = request.POST.get('model', '').strip() or 'gpt-4o-mini'
        base_url = request.POST.get('base_url', '').strip() or None
        raw_key = request.POST.get('api_key', '').strip()
        is_active = bool(request.POST.get('is_active'))

        if config_id:
            try:
                cfg = InstitutionAIConfig.objects.get(pk=int(config_id))
            except (InstitutionAIConfig.DoesNotExist, ValueError):
                messages.error(request, 'Configuración no encontrada.')
                return redirect('material:institution_ai_config')
        else:
            try:
                institution = InstitutionV2.objects.get(pk=int(institution_id))
            except (InstitutionV2.DoesNotExist, ValueError):
                messages.error(request, 'Institución no válida.')
                return redirect('material:institution_ai_config')
            cfg = InstitutionAIConfig(institution=institution)

        cfg.provider = provider
        cfg.model = model
        cfg.base_url = base_url
        cfg.is_active = is_active
        if raw_key:
            cfg.api_key = raw_key
        cfg.save()
        messages.success(request, f'Configuración para "{cfg.institution.name}" guardada correctamente.')
        return redirect('material:institution_ai_config')

    # ── GET ──
    editing = None
    if 'edit' in request.GET:
        try:
            editing = InstitutionAIConfig.objects.select_related('institution').get(
                pk=int(request.GET['edit'])
            )
        except (InstitutionAIConfig.DoesNotExist, ValueError):
            pass

    configs = InstitutionAIConfig.objects.select_related('institution').order_by('institution__name')
    configured_ids = configs.values_list('institution_id', flat=True)
    available_institutions = InstitutionV2.objects.filter(
        is_active=True, is_seed_demo=False
    ).exclude(pk__in=configured_ids).order_by('name')

    return render(request, 'material/institution_ai_config.html', {
        'configs': configs,
        'editing': editing,
        'available_institutions': available_institutions,
    })


# --- GRUPOS DE CONFIANZA (compartir preguntas entre docentes) -----------------

@login_required
def grupos_list(request):
    from .models import SharingGroup, GroupMembership

    my_memberships = GroupMembership.objects.filter(
        user=request.user
    ).exclude(status='rejected').select_related('group').order_by('-created_at')

    context = {
        'my_memberships': my_memberships,
        'pending_invites_count': GroupMembership.objects.filter(
            user=request.user, status='pending'
        ).count(),
    }
    return render(request, 'material/groups/grupos_list.html', context)


@login_required
def grupo_crear(request):
    from .models import SharingGroup, GroupMembership

    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        if not name:
            messages.error(request, 'El grupo necesita un nombre.', extra_tags='grupos')
            return redirect('material:grupo_crear')
        group = SharingGroup.objects.create(name=name, created_by=request.user)
        GroupMembership.objects.create(
            group=group, user=request.user, status='accepted', invited_by=request.user,
            responded_at=timezone.now(),
        )
        messages.success(request, f'Grupo "{name}" creado.', extra_tags='grupos')
        return redirect('material:grupo_detalle', pk=group.pk)

    return render(request, 'material/groups/grupo_crear.html', {})


@login_required
def grupo_detalle(request, pk):
    from .models import SharingGroup, GroupMembership, SubjectShare
    from django.contrib.auth.models import User as UserModel

    group = get_object_or_404(SharingGroup, pk=pk)
    my_membership = GroupMembership.objects.filter(group=group, user=request.user).first()
    if my_membership is None:
        messages.error(request, 'No pertenecés a este grupo.', extra_tags='grupos')
        return redirect('material:grupos_list')

    is_accepted_member = my_membership.status == 'accepted'
    if not is_accepted_member:
        # Todavía no aceptó/rechazó la invitación: lo mandamos a resolverla ahí,
        # no le mostramos el detalle del grupo (materias compartidas, etc.).
        return redirect('material:invitaciones_pendientes')

    memberships = group.memberships.select_related('user', 'invited_by').order_by('status', 'user__username')
    member_ids = set(memberships.filter(status__in=['pending', 'accepted']).values_list('user_id', flat=True))
    invitable_users = UserModel.objects.filter(is_active=True).exclude(
        id__in=member_ids
    ).exclude(id=request.user.id).exclude(profile__is_training_account=True).order_by('username')

    my_subjects = Subject.objects.filter(questions__user=request.user).distinct().order_by('name')
    shared_subject_ids = set(
        SubjectShare.objects.filter(
            group=group, shared_by=request.user, is_active=True
        ).values_list('subject_id', flat=True)
    )

    from .models import Rubric, RubricShare
    my_rubrics = Rubric.objects.filter(created_by=request.user).order_by('title')
    shared_rubric_ids = set(
        RubricShare.objects.filter(
            group=group, shared_by=request.user, is_active=True
        ).values_list('rubric_id', flat=True)
    )

    context = {
        'group': group,
        'memberships': memberships,
        'invitable_users': invitable_users,
        'my_subjects': my_subjects,
        'shared_subject_ids': shared_subject_ids,
        'my_rubrics': my_rubrics,
        'shared_rubric_ids': shared_rubric_ids,
    }
    return render(request, 'material/groups/grupo_detalle.html', context)


@login_required
@require_POST
def grupo_invitar(request, pk):
    from .models import SharingGroup, GroupMembership

    group = get_object_or_404(SharingGroup, pk=pk)
    if not GroupMembership.objects.filter(group=group, user=request.user, status='accepted').exists():
        messages.error(request, 'Solo los miembros del grupo pueden invitar.', extra_tags='grupos')
        return redirect('material:grupos_list')

    user_id = request.POST.get('user_id')
    if str(user_id).isdigit():
        target = User.objects.filter(pk=int(user_id), is_active=True).exclude(
            pk=request.user.id
        ).exclude(profile__is_training_account=True).first()
        if target and not GroupMembership.objects.filter(group=group, user=target).exists():
            GroupMembership.objects.create(
                group=group, user=target, status='pending', invited_by=request.user,
            )
            messages.success(request, f'Invitación enviada a {target.username}.', extra_tags='grupos')
        else:
            messages.error(request, 'Ese usuario ya es miembro o ya fue invitado.', extra_tags='grupos')

    return redirect('material:grupo_detalle', pk=group.pk)


@login_required
def invitaciones_pendientes(request):
    from .models import GroupMembership

    if request.method == 'POST':
        membership_id = request.POST.get('membership_id')
        action = request.POST.get('action')
        membership = GroupMembership.objects.filter(
            pk=membership_id, user=request.user, status='pending'
        ).first()
        if membership and action in ('accept', 'reject'):
            membership.status = 'accepted' if action == 'accept' else 'rejected'
            membership.responded_at = timezone.now()
            membership.save(update_fields=['status', 'responded_at'])
            if action == 'accept':
                messages.success(request, f'Te uniste a "{membership.group.name}".', extra_tags='grupos')
            else:
                messages.info(request, f'Rechazaste la invitación a "{membership.group.name}".', extra_tags='grupos')
        return redirect('material:invitaciones_pendientes')

    pending = GroupMembership.objects.filter(
        user=request.user, status='pending'
    ).select_related('group', 'invited_by').order_by('-created_at')
    return render(request, 'material/groups/invitaciones_pendientes.html', {'pending': pending})


@login_required
@require_POST
def compartir_materia(request, pk):
    from .models import SharingGroup, GroupMembership, SubjectShare

    group = get_object_or_404(SharingGroup, pk=pk)
    if not GroupMembership.objects.filter(group=group, user=request.user, status='accepted').exists():
        messages.error(request, 'Solo los miembros del grupo pueden compartir materias.', extra_tags='grupos')
        return redirect('material:grupos_list')

    subject_id = request.POST.get('subject_id')
    if str(subject_id).isdigit():
        subject = Subject.objects.filter(pk=int(subject_id)).first()
        if subject:
            share, created = SubjectShare.objects.get_or_create(
                group=group, subject=subject, shared_by=request.user,
                defaults={'is_active': True},
            )
            if not created:
                share.is_active = not share.is_active
                share.save(update_fields=['is_active'])
            if share.is_active:
                messages.success(request, f'Compartiendo "{subject.name}" con el grupo.', extra_tags='grupos')
            else:
                messages.info(request, f'Dejaste de compartir "{subject.name}" con el grupo.', extra_tags='grupos')

    return redirect('material:grupo_detalle', pk=group.pk)


@login_required
@require_POST
def compartir_rubrica(request, pk):
    from .models import SharingGroup, GroupMembership, Rubric, RubricShare

    group = get_object_or_404(SharingGroup, pk=pk)
    if not GroupMembership.objects.filter(group=group, user=request.user, status='accepted').exists():
        messages.error(request, 'Solo los miembros del grupo pueden compartir rúbricas.', extra_tags='grupos')
        return redirect('material:grupos_list')

    rubric_id = request.POST.get('rubric_id')
    if str(rubric_id).isdigit():
        rubrica = Rubric.objects.filter(pk=int(rubric_id), created_by=request.user).first()
        if rubrica:
            share, created = RubricShare.objects.get_or_create(
                group=group, rubric=rubrica, shared_by=request.user,
                defaults={'is_active': True},
            )
            if not created:
                share.is_active = not share.is_active
                share.save(update_fields=['is_active'])
            if share.is_active:
                messages.success(request, f'Compartiendo "{rubrica.title}" con el grupo.', extra_tags='grupos')
            else:
                messages.info(request, f'Dejaste de compartir "{rubrica.title}" con el grupo.', extra_tags='grupos')

    return redirect('material:grupo_detalle', pk=group.pk)


def service_worker(request):
    """
    Sirve static/sw.js en la RAÍZ del sitio (/sw.js), no bajo /static/ —
    el scope por default de un service worker es la carpeta desde donde se
    sirve, así que para que cubra todo el sitio (no solo /static/) tiene
    que responder desde acá en vez de servirse como estático normal.
    """
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'sw.js')
    try:
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return HttpResponse('', content_type='application/javascript', status=404)
    return HttpResponse(content, content_type='application/javascript')


def health_check(request):
    # UptimeRobot pinguea esto seguido (cada ~5 min) para que Render no
    # duerma el free tier — se aprovecha ese mismo pulso como "reloj" del
    # monitoreo periódico de Groq (ver material/groq_monitor.py), pero
    # throttleado ahí adentro a ~4 veces/día para no pisarle el autosuspend a
    # Neon en cada ping (y las corridas automáticas se guardan primero en un
    # buffer local, no en Postgres directo — ver sync_buffer_to_db). No
    # bloquea la respuesta.
    try:
        from .groq_monitor import maybe_trigger_from_health_ping
        maybe_trigger_from_health_ping()
    except Exception:
        logger.exception('No se pudo chequear el disparador del monitoreo de Groq')
    return HttpResponse("OK", status=200)


@login_required
@user_passes_test(is_admin, login_url='/')
def question_generation_prompt_config(request):
    """
    Panel de administración (no Django Admin) para editar el prompt usado en
    la generación de preguntas con IA — ver
    views_document_processor.py::_build_generation_prompt.
    """
    from .models import QuestionGenerationConfig
    from .ai_prompts import DEFAULT_PROMPT_TEMPLATE, DEFAULT_TEMPERATURE, PROMPT_PLACEHOLDERS

    cfg, _ = QuestionGenerationConfig.objects.get_or_create(
        pk=1, defaults={'prompt_template': DEFAULT_PROMPT_TEMPLATE, 'temperature': DEFAULT_TEMPERATURE}
    )

    if request.method == 'POST':
        if request.POST.get('action') == 'restore_default':
            cfg.prompt_template = DEFAULT_PROMPT_TEMPLATE
            cfg.temperature = DEFAULT_TEMPERATURE
            cfg.save()
            messages.success(request, 'Prompt restaurado al default de fábrica.', extra_tags='general')
            return redirect('material:question_generation_prompt_config')

        new_template = request.POST.get('prompt_template', '').strip()
        try:
            new_temperature = float(request.POST.get('temperature', DEFAULT_TEMPERATURE))
        except (TypeError, ValueError):
            new_temperature = DEFAULT_TEMPERATURE
        new_temperature = max(0.0, min(1.0, new_temperature))

        if not new_template:
            messages.error(request, 'El prompt no puede quedar vacío.', extra_tags='general')
        else:
            # Validar que el template tenga los placeholders bien formados antes
            # de guardar — no dejamos guardar algo que ya sabemos que va a
            # romper el .format() en la próxima generación real.
            try:
                sample_context = {key: f'[{key}]' for key in PROMPT_PLACEHOLDERS}
                new_template.format(**sample_context)
            except (KeyError, ValueError, IndexError) as e:
                messages.error(
                    request,
                    f'El prompt tiene un placeholder inválido ({e}) — no se guardó. '
                    f'Revisar que solo se usen los placeholders documentados abajo.',
                    extra_tags='general',
                )
            else:
                cfg.prompt_template = new_template
                cfg.temperature = new_temperature
                cfg.save()
                messages.success(request, 'Prompt actualizado correctamente.', extra_tags='general')
                return redirect('material:question_generation_prompt_config')

    return render(request, 'material/question_generation_prompt_config.html', {
        'cfg': cfg,
        'placeholders': PROMPT_PLACEHOLDERS,
        'default_template': DEFAULT_PROMPT_TEMPLATE,
    })


@login_required
def groq_monitor_page(request):
    """
    Panel staff-only del monitoreo de carga de Groq (ver material/groq_monitor.py).
    Muestra el estado, permite arrancar/parar la ventana de 48h y correr una
    prueba manual, y lista el historial de corridas con un resumen de las
    últimas 12h.
    """
    from .models import GroqMonitorRun, GroqMonitorSchedule, GroqVisionTestRun, VisionMonitorSchedule
    from .groq_monitor import VISION_TEST_MODELS

    if not is_admin(request.user):
        messages.error(request, 'No hay permiso para acceder a esta sección.', extra_tags='general')
        return redirect('material:index')

    cfg, _ = GroqMonitorSchedule.objects.get_or_create(pk=1)
    vision_cfg, _ = VisionMonitorSchedule.objects.get_or_create(pk=1)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'run_vision':
            from .groq_monitor import run_vision_test
            model_name = (request.POST.get('vision_model') or '').strip()
            vision_provider = (request.POST.get('vision_provider') or 'gemini').strip()
            if model_name:
                run_vision_test(model_name, provider=vision_provider)
                messages.success(request, f'Prueba de visión ejecutada para "{vision_provider}: {model_name}" — mirá el resultado abajo.', extra_tags='general')
            return redirect('material:groq_monitor_page')
        if action == 'run_vision_load':
            from .groq_monitor import run_vision_load_test
            model_name = (request.POST.get('vision_model') or '').strip()
            vision_provider = (request.POST.get('vision_provider') or 'gemini').strip()
            try:
                count = max(1, min(30, int(request.POST.get('load_count', 8))))
            except (TypeError, ValueError):
                count = 8
            if model_name:
                runs = run_vision_load_test(count, provider=vision_provider, model=model_name)
                ok = sum(1 for r in runs if r.success)
                messages.success(
                    request,
                    f'Ráfaga de {count} llamadas a "{vision_provider}: {model_name}" terminada — '
                    f'{ok} exitosas, {count - ok} fallaron. Mirá el detalle y el historial de cortes abajo.',
                    extra_tags='general',
                )
            return redirect('material:groq_monitor_page')
        if action == 'start_vision':
            hours = 48
            try:
                hours = max(1, min(168, int(request.POST.get('vision_hours', 48))))
            except (TypeError, ValueError):
                pass
            model_name = (request.POST.get('vision_model') or vision_cfg.model or '').strip()
            vision_provider = (request.POST.get('vision_provider') or 'gemini').strip()
            now = timezone.now()
            vision_cfg.enabled = True
            vision_cfg.provider = vision_provider
            vision_cfg.model = model_name or vision_cfg.model
            vision_cfg.started_at = now
            vision_cfg.ends_at = now + timezone.timedelta(hours=hours)
            vision_cfg.last_run_at = None
            vision_cfg.save()
            messages.success(request, f'Monitoreo de visión activado por {hours} horas ({vision_cfg.provider}/{vision_cfg.model}).', extra_tags='general')
            return redirect('material:groq_monitor_page')
        if action == 'stop_vision':
            vision_cfg.enabled = False
            vision_cfg.save(update_fields=['enabled'])
            messages.success(request, 'Monitoreo de visión desactivado.', extra_tags='general')
            return redirect('material:groq_monitor_page')
        if action == 'start':
            hours = 48
            try:
                hours = max(1, min(168, int(request.POST.get('hours', 48))))
            except (TypeError, ValueError):
                pass
            now = timezone.now()
            cfg.enabled = True
            cfg.started_at = now
            cfg.ends_at = now + timezone.timedelta(hours=hours)
            cfg.last_run_at = None
            cfg.save()
            messages.success(request, f'Monitoreo activado por {hours} horas.', extra_tags='general')
        elif action == 'stop':
            cfg.enabled = False
            cfg.save(update_fields=['enabled'])
            messages.success(request, 'Monitoreo desactivado.', extra_tags='general')
        elif action == 'run_now':
            from .groq_monitor import run_test
            fixture_key = request.POST.get('fixture') or None
            run_test(fixture_key=fixture_key)
            messages.success(request, 'Corrida manual ejecutada — mirá el resultado en la tabla.', extra_tags='general')
        return redirect('material:groq_monitor_page')

    runs = list(GroqMonitorRun.objects.all()[:200])

    cutoff_12h = timezone.now() - timezone.timedelta(hours=12)
    recent_runs = [r for r in runs if r.created_at >= cutoff_12h]
    summary_12h = {
        'total': len(recent_runs),
        'met_target': sum(1 for r in recent_runs if r.met_target),
        'failed': sum(1 for r in recent_runs if not r.success),
    }
    latest_quota = next((r for r in runs if r.quota_remaining_requests is not None), None)

    from .groq_monitor import analyze_vision_quota_cycles
    vision_runs = list(GroqVisionTestRun.objects.all()[:50])
    latest_vision_quota = next((r for r in vision_runs if r.quota_remaining_requests is not None), None)
    vision_quota_cycles = analyze_vision_quota_cycles()

    context = {
        'cfg': cfg,
        'runs': runs,
        'summary_12h': summary_12h,
        'latest_quota': latest_quota,
        'vision_cfg': vision_cfg,
        'vision_test_models': VISION_TEST_MODELS,
        'vision_runs': vision_runs,
        'latest_vision_quota': latest_vision_quota,
        'vision_quota_cycles': vision_quota_cycles,
    }
    return render(request, 'material/groq_monitor.html', context)


@login_required
def neon_usage_page(request):
    """
    Panel staff-only: consulta la API de Neon (console.neon.tech), no la
    propia base de datos, para mostrar si el autosuspend está funcionando.

    Dos señales distintas, a propósito:
    - "% del período con el compute activo": promedio de TODO el período
      (desde el 1° del mes). Útil para ver la tendencia, pero NO distingue
      uso real de un bug tipo el de /health/ (antes del fix del
      2026-08-14) — ambos se ven igual acá, es solo volumen acumulado.
    - Estado del endpoint ahora mismo (current_state/last_active/
      suspended_at): esto SÍ es una prueba directa e inequívoca. Si dice
      "idle" con un suspended_at reciente, el autosuspend está funcionando
      en este instante — no hace falta inferir nada de un promedio.

    No reconstruye CU-hours exactas: dependen del tamaño del compute (CU) en
    cada momento, que esta llamada no expone. Para el número oficial de
    CU-hours consumidas del mes, remite a la consola de Neon.
    """
    if not is_admin(request.user):
        messages.error(request, 'No hay permiso para acceder a esta sección.', extra_tags='general')
        return redirect('material:index')

    import requests
    from django.db import connection
    from django.utils.dateparse import parse_datetime

    # Diagnóstico de la conexión Django→Postgres: no es la causa del consumo
    # excesivo (una conexión abierta e inactiva NO le impide a Neon
    # autosuspender — solo importa si hay queries activas), pero
    # CONN_MAX_AGE>0 combinado con el endpoint "-pooler" (PgBouncer en modo
    # transacción) puede traer otros problemas — Neon recomienda
    # CONN_MAX_AGE=0 en ese caso puntual. Se muestra acá en vez de
    # cambiarlo a ciegas, porque no hay forma de saber desde el repo si
    # DATABASE_URL en Render apunta al endpoint pooled o al directo.
    db_host = connection.settings_dict.get('HOST', '') or ''
    is_pooled = 'pooler' in db_host
    context = {
        'configured': bool(settings.NEON_API_KEY and settings.NEON_PROJECT_ID),
        'db_host': db_host,
        'db_is_pooled': is_pooled,
        'db_conn_max_age': connection.settings_dict.get('CONN_MAX_AGE'),
    }

    if context['configured']:
        try:
            resp = requests.get(
                f'https://console.neon.tech/api/v2/projects/{settings.NEON_PROJECT_ID}',
                headers={'Authorization': f'Bearer {settings.NEON_API_KEY}', 'Accept': 'application/json'},
                timeout=8,
            )
            resp.raise_for_status()
            project = resp.json().get('project', {})

            period_start = parse_datetime(project.get('consumption_period_start') or '')
            period_end = parse_datetime(project.get('consumption_period_end') or '')
            active_seconds = project.get('active_time_seconds') or 0
            now = timezone.now()

            elapsed_pct = active_pct_of_elapsed = None
            if period_start and period_end and period_end > period_start:
                elapsed = (min(now, period_end) - period_start).total_seconds()
                total = (period_end - period_start).total_seconds()
                elapsed_pct = round(100 * elapsed / total, 1)
                if elapsed > 0:
                    active_pct_of_elapsed = round(100 * active_seconds / elapsed, 1)

            context.update({
                'error': None,
                'active_hours': round(active_seconds / 3600, 2),
                'compute_hours': round((project.get('compute_time_seconds') or 0) / 3600, 2),
                'data_transfer_gb': round((project.get('data_transfer_bytes') or 0) / (1024 ** 3), 3),
                'period_start': period_start,
                'period_end': period_end,
                'elapsed_pct': elapsed_pct,
                'active_pct_of_elapsed': active_pct_of_elapsed,
            })

            # Estado del compute AHORA MISMO — a diferencia del % de arriba
            # (que es un promedio de todo el período y no distingue uso real
            # de un bug tipo el de /health/), esto es una prueba directa: si
            # dice "idle" y suspended_at es reciente, el autosuspend está
            # funcionando en este instante, sin ambigüedad ni inferencia.
            try:
                ep_resp = requests.get(
                    f'https://console.neon.tech/api/v2/projects/{settings.NEON_PROJECT_ID}/endpoints',
                    headers={'Authorization': f'Bearer {settings.NEON_API_KEY}', 'Accept': 'application/json'},
                    timeout=8,
                )
                ep_resp.raise_for_status()
                endpoints = ep_resp.json().get('endpoints') or []
                endpoint = endpoints[0] if endpoints else None
                if endpoint:
                    context.update({
                        'ep_state': endpoint.get('current_state'),
                        'ep_last_active': parse_datetime(endpoint.get('last_active') or ''),
                        'ep_suspended_at': parse_datetime(endpoint.get('suspended_at') or ''),
                        'ep_suspend_timeout_seconds': endpoint.get('suspend_timeout_seconds'),
                    })
            except Exception:
                logger.exception('Error consultando el estado del endpoint de Neon')
        except Exception as e:
            logger.exception('Error consultando la API de Neon')
            context['error'] = str(e)

    return render(request, 'material/neon_usage.html', context)


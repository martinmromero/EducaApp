from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Q


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

    topic_ids = [int(t) for t in exam.get('topics', []) if str(t).isdigit()]
    outcome_ids = [int(o) for o in exam.get('learning_outcomes', []) if str(o).isdigit()]
    manual_question_ids = [int(q) for q in exam.get('questions', []) if str(q).isdigit()]

    selected_topics = Topic.objects.filter(pk__in=topic_ids) if topic_ids else (Topic.objects.filter(subject=subject_obj) if subject_obj else Topic.objects.none())
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

    generated_versions = []
    if manual_question_ids and subject_obj:
        if versions_count == 1:
            generated_versions = [list(Question.objects.filter(
                pk__in=manual_question_ids,
                user=request.user,
                ai_approved=True,
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
                }
                for q in q_list
            ]
        })

    request.session['preview_generated_versions_ids'] = preview_ids

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
        'current_date': exam.get('fecha', '-'),
        'exam_type': _TIPO_EXAMEN_LABELS.get(exam.get('tipo_examen', ''), exam.get('tipo_examen') or '-'),
        'exam_mode': _TIPO_MODALIDAD_LABELS.get(exam.get('tipo_modalidad', ''), exam.get('tipo_modalidad') or '-'),
        'resolution_time': exam.get('duration_minutes', '-'),
        'instructions': exam.get('instructions', ''),
        'notes_and_recommendations': exam.get('notes_and_recommendations', ''),
        'bloom_display': bloom_display,
        'total_exam_questions': total_exam_questions,
        'print_style': get_print_style_context(
            resolve_print_format_for_context(
                user=request.user,
                institution_name=exam.get('institucion', '') or '',
            )
        ),
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
@require_GET
def get_exam_template(request, template_id):
    try:
        template = ExamTemplate.objects.get(id=template_id)
    except ExamTemplate.DoesNotExist:
        return JsonResponse({'error': 'Plantilla no encontrada'}, status=404)

    data = {
        'subject_id': template.subject.id if template.subject else None,
        'title': getattr(template, 'title', None),
        'instructions': getattr(template, 'notes_and_recommendations', None),
        'duration_minutes': template.resolution_time,
        'questions': list(template.question_set.values_list('id', flat=True)) if hasattr(template, 'question_set') else [],
        'topics': [int(tid) for tid in template.topics_to_evaluate.split(',') if tid.isdigit()] if template.topics_to_evaluate else [],
        'learning_outcomes': list(template.learning_outcomes.values_list('id', flat=True)),
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
@require_GET
def get_questions_by_topics(request):
    from .models import Question, Topic
    all_topics = request.GET.get('all', 'false') == 'true'
    subject_id = request.GET.get('subject_id')
    topics = request.GET.get('topics', '')
    topic_ids = [int(t) for t in topics.split(',') if t]
    review_filter = models.Q(ai_approved=True)
    questions = Question.objects.none()
    if all_topics and subject_id:
        questions = Question.objects.filter(subjects__id=subject_id).filter(review_filter).distinct()
    elif topic_ids:
        questions = Question.objects.filter(topic_id__in=topic_ids).filter(review_filter)
        if subject_id and str(subject_id).isdigit():
            questions = questions.filter(subjects__id=int(subject_id))
        questions = questions.distinct()
    data = [
        {'id': q.id, 'text': q.question_text[:80], 'topic_id': q.topic_id}
        for q in questions
    ]
    return JsonResponse(data, safe=False)

# AJAX: obtener carreras por facultad seleccionada
@require_GET
def get_careers_by_faculty(request, faculty_id):
    from .models import Career, FacultyV2
    careers = Career.objects.filter(faculties__id=faculty_id).distinct()
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
from .models import (InstitutionV2, CampusV2, FacultyV2, UserInstitution, InstitutionLog, InstitutionCareer)
from .forms import (
    CustomLoginForm, ExamForm, ExamTemplateForm, QuestionForm, 
    UserEditForm, ContenidoForm, 
    LearningOutcomeForm, SubjectForm, ProfileForm,CareerForm,CareerSimpleForm,
    OralExamForm, RubricForm, FormatoImpresionForm
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
from .exam_labels import get_exam_mode_label, get_exam_type_label
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.utils import OperationalError, ProgrammingError, DatabaseError
from django.db.models import Prefetch, F, Value, CharField
from django.db.models.functions import Concat
from .ia_processor import extract_text_from_file, generate_questions_from_text, extract_book_metadata
from django.utils import timezone 
from .forms import LearningOutcomeForm, ProfileForm


from .forms import InstitutionV2Form, CampusV2Form, FacultyV2Form

from django.db import transaction
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import ExamTemplate, LearningOutcome

from django.db import IntegrityError  # Agregar este import al inicio

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
    subject_id = request.GET.get('subject_id')
    topics = Topic.objects.filter(subject_id=subject_id).distinct().values('id', 'name')
    return JsonResponse(list(topics), safe=False)

def get_subtopics(request):
    topic_id = request.GET.get('topic_id')
    subtopics = Subtopic.objects.filter(topic_id=topic_id).values('id', 'name')
    return JsonResponse(list(subtopics), safe=False)

def get_faculties(request):
    institution_id = request.GET.get('institution_id')
    faculties = FacultyV2.objects.filter(
        institution_id=institution_id, 
        is_active=True
    ).values('id', 'name').order_by('name')
    return JsonResponse(list(faculties), safe=False)

def get_campus_by_institution(request):
    institution_id = request.GET.get('institution_id')
    campus = CampusV2.objects.filter(
        institution_id=institution_id
    ).values('id', 'name').order_by('name')
    return JsonResponse(list(campus), safe=False)

def is_admin(user):
    try:
        return user.profile.role == 'admin'
    except Profile.DoesNotExist:
        return False
    

class CustomLoginView(LoginView):
    form_class = CustomLoginForm
    template_name = 'registration/login.html'

    def form_invalid(self, form):
        """Maneja intentos fallidos de login"""
        messages.error(self.request, "Credenciales inválidas. Intente nuevamente.", extra_tags='general')
        return super().form_invalid(form)
    

@login_required
def index(request):
    context = {
        'is_admin': is_admin(request.user)
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
    return render(request, 'material/questions/upload.html', {'form': form})

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


@login_required
def generate_questions(request, contenido_id):
    contenido = Contenido.objects.get(id=contenido_id)
    num_questions = int(request.POST.get('num_questions', 20))
    try:
        text = extract_text_from_file(contenido.file.path)
    except ValueError as e:
        messages.error(request, str(e), extra_tags='contenidos')
        return redirect('material:mis_contenidos')
    questions_text = generate_questions_from_text(text, num_questions)
    request.session['generated_questions'] = questions_text.split('\n')
    return redirect('material:review_questions', contenido_id=contenido.id)

@login_required
def review_questions(request, contenido_id):
    contenido = Contenido.objects.get(id=contenido_id)
    questions_list = request.session.get('generated_questions', [])
    return render(request, 'material/review_questions.html', {
        'contenido': contenido,
        'questions': questions_list
    })

@login_required
def save_selected_questions(request, contenido_id):
    if request.method == 'POST':
        contenido = Contenido.objects.get(id=contenido_id)
        selected_questions = request.POST.getlist('selected_questions')
        questions_list = request.session.get('generated_questions', [])
        default_subject, _ = Subject.objects.get_or_create(name='Generado por IA')
        default_topic, _ = Topic.objects.get_or_create(name='Generado por IA', subject=default_subject)
        
        for i, question in enumerate(questions_list):
            if str(i) in selected_questions:
                q = Question.objects.create(
                    contenido=contenido,
                    question_text=question,
                    answer_text='Respuesta generada por IA',
                    topic=default_topic,
                    subtopic=None,
                    user=request.user,
                    generated_by_ai=True,
                    ai_approved=True
                )
                q.subjects.add(default_subject)
        messages.success(request, 'Preguntas guardadas correctamente.', extra_tags='preguntas')
        return redirect('material:lista_preguntas')

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
    exam_data['tipo_examen'] = request.POST.get('tipo_examen')
    exam_data['tipo_modalidad'] = request.POST.get('tipo_modalidad')
    exam_data['modalidad_resolucion'] = request.POST.getlist('modalidad_resolucion')
    exam_data['alumno'] = request.POST.get('alumno')
    exam_data['batch_name'] = request.POST.get('batch_name', '').strip()
    exam_data['batch_semester'] = request.POST.get('batch_semester', '').strip()
    exam_data['num_versions'] = request.POST.get('num_versions', '1').strip() or '1'
    exam_data['questions_per_version'] = request.POST.get('questions_per_version', '').strip()
    exam_data['balance_by_topic'] = '1' if request.POST.get('balance_by_topic') else '0'
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
    cuatri = exam_data.get('batch_semester') or 'sin cuatrimestre'
    year_str = str(year) if year else 'sin año'
    return f"{tipo} - {materia} - {institucion} - {cuatri} - {year_str} - {versions_count} opciones"


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


def _pick_questions_for_versions(subject, selected_topics, user, versions_count, questions_per_version, balance_by_topic=True, allowed_question_ids=None):
    import random
    from collections import defaultdict

    pools = defaultdict(list)
    base_qs = Question.objects.filter(
        subjects__id=subject.id,
        user=user,
        topic__in=selected_topics,
        ai_approved=True,
    ).select_related('topic').distinct()
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


def _get_exam_version_schema_state():
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


@login_required
def create_exam(request):
    from .models import FacultyV2, Career, CampusV2, Subject, ExamTemplate, InstitutionV2
    from django.contrib.auth.models import User

    instituciones = InstitutionV2.objects.filter(is_active=True)
    facultades = FacultyV2.objects.filter(is_active=True)
    carreras = Career.objects.all()
    sedes = CampusV2.objects.filter(is_active=True)
    materias = Subject.objects.all()
    profesores = User.objects.filter(profile__role='admin') | User.objects.filter(profile__role='user')
    templates = ExamTemplate.objects.all()

    if request.method == 'POST':
        form = ExamForm(request.POST)
        exam_data = _collect_exam_post_data(request, form)
        request.session['preview_exam'] = exam_data

        if 'save' in request.POST:
            return redirect('material:save_exam_from_session')
        return redirect('material:preview_exam')

    form = ExamForm()

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
        'prefill_data_json': prefill_data_json,
    }
    return render(request, 'material/exams/create_exam.html', context)

@login_required
def save_exam_from_session(request):
    """Guarda examen/es desde sesión. Soporta lote de versiones para examen escrito."""
    exam_data = request.session.get('preview_exam')
    if not exam_data:
        messages.error(request, 'No hay datos de examen para guardar.', extra_tags='general')
        return redirect('material:create_exam')

    from .models import Subject, Question, Topic, LearningOutcome, Exam as ExamModel
    from .models import InstitutionV2, FacultyV2, Career, CampusV2
    from django.contrib.auth.models import User

    # ── Subject ─────────────────────────────────────────────
    subject = None
    if exam_data.get('subject') and str(exam_data['subject']).isdigit():
        subject = Subject.objects.filter(pk=int(exam_data['subject'])).first()
    if not subject:
        messages.error(request, 'No se pudo determinar la materia del examen.', extra_tags='general')
        return redirect('material:preview_exam')

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

    # exam_type — store raw value (CharField, no DB constraint)
    exam_type = exam_data.get('tipo_examen') or None

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

    # year from fecha
    year = None
    if fecha:
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
        messages.error(request, 'Debe seleccionar al menos un tema para generar versiones.', extra_tags='examenes')
        return redirect('material:create_exam')

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

    if preview_version_ids:
        chosen_versions = [
            list(Question.objects.filter(pk__in=version_ids, user=request.user, ai_approved=True).distinct())
            for version_ids in preview_version_ids
            if version_ids
        ]
        versions_count = len(chosen_versions) if chosen_versions else versions_count
    elif q_ids:
        if versions_count == 1:
            chosen_versions = [list(Question.objects.filter(
                pk__in=q_ids,
                user=request.user,
                ai_approved=True,
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
        )
    if not chosen_versions or not chosen_versions[0]:
        messages.error(request, 'No hay preguntas suficientes para generar el examen.', extra_tags='examenes')
        return redirect('material:create_exam')

    editing_exam_id = request.session.get('editing_exam_id')
    editing_exam = None
    if str(editing_exam_id).isdigit():
        editing_exam = _get_compatible_exam_queryset().filter(pk=int(editing_exam_id), created_by=request.user).first()

    try:
        with transaction.atomic():
            batch_name = (exam_data.get('batch_name') or '').strip()
            if not batch_name:
                batch_name = _suggest_batch_name(subject, exam_data, institution_name, versions_count, year)

            batch = None
            if supports_version_batches and editing_exam is None:
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
                    'notes_and_recommendations': exam_data.get('notes_and_recommendations') or None,
                }
                for field_name, field_value in exam_kwargs.items():
                    setattr(editing_exam, field_name, field_value)
                editing_exam.save()
                editing_exam.topics.set(selected_topics)
                editing_exam.learning_outcomes.set(selected_outcomes)
                editing_exam.questions.set(chosen_versions[0])
                if not hasattr(editing_exam, 'formato_impresion_asignado'):
                    formato = resolve_print_format_for_exam(editing_exam)
                    if formato:
                        assign_print_format_to_exam(editing_exam, formato)
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
                    'notes_and_recommendations': exam_data.get('notes_and_recommendations') or None,
                }
                if supports_version_batches:
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
                formato = resolve_print_format_for_exam(exam_obj)
                if formato:
                    assign_print_format_to_exam(exam_obj, formato)
                created_exams.append(exam_obj)
    except Exception:
        logger.exception('Error guardando examenes desde /save-exam/.')
        messages.error(
            request,
            'No se pudo guardar el examen. Intenta nuevamente en unos segundos.',
            extra_tags='examenes'
        )
        return redirect('material:create_exam')

    del request.session['preview_exam']
    request.session.pop('preview_generated_versions_ids', None)
    request.session.pop('editing_exam_id', None)
    if supports_version_batches and batch is not None:
        messages.success(
            request,
            f'Se guardo el lote "{batch.name}" con {len(created_exams)} versiones.',
            extra_tags='examenes'
        )
        return redirect('material:view_exam_batch', batch_id=batch.id)

    if editing_exam is not None:
        messages.success(request, 'Examen actualizado correctamente.', extra_tags='examenes')
    else:
        messages.success(
            request,
            f'Se guardaron {len(created_exams)} examen(es). El agrupado por versiones quedara disponible cuando se apliquen las migraciones pendientes.',
            extra_tags='examenes'
        )
    return redirect('material:mis_examenes')

@login_required
def create_exam_template(request):
    # Obtener instituciones del usuario
    user_institutions = InstitutionV2.objects.filter(
        userinstitution__user=request.user,
        is_active=True
    )
    
    # Obtener materias del usuario (usando el related_name correcto)
    subjects = Subject.objects.filter(
        subject_institutions__institution__in=user_institutions
    ).distinct()

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
                    
                    resolution_time = (
                        f"{form.cleaned_data['resolution_time_number']} "
                        f"{form.cleaned_data['resolution_time_unit']}"
                    )
                    exam_template.notes_and_recommendations += (
                        f"\n\nDuración estimada: {resolution_time}"
                    )
                    
                    exam_template.save()
                    form.save_m2m()

                    # ── Poblar snapshots ──
                    exam_template.institution_name_snapshot = exam_template.institution.name if exam_template.institution_id else ''
                    exam_template.faculty_name_snapshot     = exam_template.faculty.name     if exam_template.faculty_id     else ''
                    exam_template.campus_name_snapshot      = exam_template.campus.name      if exam_template.campus_id      else ''
                    exam_template.career_name_snapshot      = exam_template.career.name      if exam_template.career_id      else ''
                    exam_template.subject_name_snapshot     = exam_template.subject.name     if exam_template.subject_id     else ''
                    raw_topics = exam_template.topics_to_evaluate or ''
                    exam_template.topics_snapshot = [t.strip() for t in raw_topics.split('\n') if t.strip()]
                    exam_template.outcomes_snapshot = list(
                        exam_template.learning_outcomes.values_list('description', flat=True)
                    )
                    exam_template.save(update_fields=[
                        'institution_name_snapshot', 'faculty_name_snapshot', 'campus_name_snapshot',
                        'career_name_snapshot', 'subject_name_snapshot', 'topics_snapshot', 'outcomes_snapshot',
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
        initial_data = {
            'resolution_time_number': 60,
            'resolution_time_unit': 'minutes'
        }
        
        form = ExamTemplateForm(
            initial=initial_data,
            user=request.user
        )
    
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
            institution_subjects = Subject.objects.filter(
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


@login_required
def exam_templates_tabs(request):
    from .models import ExamTemplate, InstitutionV2, LearningOutcome, Subject
    from django.core.paginator import Paginator

    user_institutions = InstitutionV2.objects.filter(
        userinstitution__user=request.user,
        is_active=True
    )
    subjects = Subject.objects.filter(
        subject_institutions__institution__in=user_institutions
    ).distinct()

    create_form = ExamTemplateForm(
        initial={'resolution_time_number': 60, 'resolution_time_unit': 'minutes'},
        user=request.user
    )

    templates = ExamTemplate.objects.filter(
        created_by=request.user
    ).select_related(
        'institution', 'faculty', 'career', 'subject', 'professor'
    ).prefetch_related('learning_outcomes').order_by('-created_at')

    subject_filter = request.GET.get('subject')
    if subject_filter:
        templates = templates.filter(subject_id=subject_filter)

    exam_mode_filter = request.GET.get('exam_mode')
    if exam_mode_filter:
        templates = templates.filter(exam_mode=exam_mode_filter)

    paginator = Paginator(templates, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'material/exams/exam_templates_tabs.html', {
        'create_form': create_form,
        'create_subjects': subjects,
        'create_learning_outcomes': LearningOutcome.objects.filter(subject__in=subjects).select_related('subject'),
        'create_edit_mode': False,
        'create_template': None,
        'list_exam_templates': page_obj,
        'list_subjects': subjects,
        'list_exam_modes': ExamTemplate.EXAM_TYPE_CHOICES,
    })

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

        # Crear un objeto exam-like para compatibilidad con el template base
        exam_data = {
            'title': '',  # Las plantillas no tienen título por defecto
            'instructions': request.POST.get('notes_and_recommendations', ''),
            'duration_minutes': request.POST.get('resolution_time', '60 minutos'),
            'tipo_examen': request.POST.get('exam_type', ''),
            'tipo_modalidad': request.POST.get('exam_mode', ''),
            'modalidad_resolucion': [],  # No disponible en plantillas
            'alumno': '',  # Campo vacío para plantillas
            'fecha': '',  # Campo vacío para plantillas
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
            'resolution_time': request.POST.get('resolution_time', '60 minutos'),
            'topics_to_evaluate': request.POST.get('topics_to_evaluate', ''),
            'notes_and_recommendations': request.POST.get('notes_and_recommendations', ''),
            'learning_outcomes': outcomes_to_display,
            'current_date': timezone.now().strftime("%d/%m/%Y"),
            'print_style': get_print_style_context(
                resolve_print_format_for_context(user=request.user, institution=institution)
            ),
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
                raw_topics = exam_template.topics_to_evaluate or ''
                exam_template.topics_snapshot = [t.strip() for t in raw_topics.split('\n') if t.strip()]
                exam_template.outcomes_snapshot = list(
                    exam_template.learning_outcomes.values_list('description', flat=True)
                )
                exam_template.save(update_fields=[
                    'institution_name_snapshot', 'faculty_name_snapshot', 'campus_name_snapshot',
                    'career_name_snapshot', 'subject_name_snapshot', 'topics_snapshot', 'outcomes_snapshot',
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

    # Obtener subjects disponibles para el usuario
    subjects = Subject.objects.all()
    if hasattr(request.user, 'profile') and hasattr(request.user.profile, 'institutions'):
        user_institutions = request.user.profile.institutions.all()
        if user_institutions:
            subjects = Subject.objects.filter(
                subject_institutions__institution__in=user_institutions
            ).distinct()

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

    # Crear un objeto exam-like para compatibilidad con el template base
    exam_data = {
        'title': getattr(template, 'title', ''),
        'instructions': template.notes_and_recommendations,
        'duration_minutes': template.resolution_time,
        'tipo_examen': template.get_exam_type_display(),
        'tipo_modalidad': template.get_exam_mode_display(),
        'curso': '',
        'turno': '',
        'sede': '',
        'alumno': '',
        'fecha': timezone.now().strftime("%d/%m/%Y"),
        'modalidad_resolucion': '',
    }

    context = {
        'exam': exam_data,
        'institution': template.institution,
        'faculty': template.faculty,
        'career': template.career,
        'subject': template.subject,
        'professor': template.professor,
        'exam_mode': template.get_exam_mode_display(),
        'exam_type': template.get_exam_type_display(),
        'resolution_time': template.resolution_time,
        'topics_to_evaluate': template.topics_to_evaluate,
        'notes_and_recommendations': template.notes_and_recommendations,
        'learning_outcomes': outcomes_to_display,
        'current_date': timezone.now().strftime("%d/%m/%Y"),
        'is_preview': False,
        'print_style': get_print_style_context(
            resolve_print_format_for_context(user=request.user, institution=template.institution)
        ),
    }

    return render(request, 'material/exams/preview_exam_template.html', context)

@login_required
@transaction.atomic
def save_exam_template(request):
    if request.method == 'POST':
        try:
            exam_template_data = {
                'institution_id': request.POST.get('institution'),
                'faculty_id': request.POST.get('faculty'),
                'career_id': request.POST.get('career'),
                'subject_id': request.POST.get('subject'),
                'exam_mode': request.POST.get('exam_mode'),
                'exam_type': request.POST.get('exam_type'),
                'resolution_time': request.POST.get('resolution_time', '60 minutos'),
                'created_by': request.user,
                'campus_id': request.POST.get('campus'),
                'professor_id': request.POST.get('professor', request.user.id),
                'topics_to_evaluate': request.POST.get('topics_to_evaluate', ''),
                'notes_and_recommendations': request.POST.get('notes_and_recommendations', ''),
                'year': timezone.now().year  # Asegurar que tenga año
            }

            # Validación mínima
            required_fields = ['institution_id', 'faculty_id', 'career_id', 'subject_id']
            if not all(exam_template_data[field] for field in required_fields):
                return JsonResponse({
                    'success': False, 
                    'error': 'Institución, Facultad, Carrera y Materia son requeridos'
                }, status=400)

            # Crear la plantilla
            exam_template = ExamTemplate(**exam_template_data)
            exam_template.save(skip_validation=True)

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
                    subject_id=exam_template_data['subject_id']
                )
                exam_template.learning_outcomes.set(outcomes)

            return JsonResponse({
                'success': True, 
                'message': 'Plantilla guardada correctamente',
                'template_id': exam_template.id
            })

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

@login_required
def list_exam_templates(request):
    # Consulta optimizada con select_related y prefetch_related
    templates = ExamTemplate.objects.filter(
        created_by=request.user
    ).select_related(
        'institution', 
        'faculty', 
        'career', 
        'subject',
        'professor'
    ).prefetch_related(
        'learning_outcomes'
    ).order_by('-created_at')

    # Filtros
    subject_filter = request.GET.get('subject')
    if subject_filter:
        templates = templates.filter(subject_id=subject_filter)

    exam_mode_filter = request.GET.get('exam_mode')
    if exam_mode_filter:
        templates = templates.filter(exam_mode=exam_mode_filter)

    # Paginación
    paginator = Paginator(templates, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Obtener materias para el filtro
    user_institutions = InstitutionV2.objects.filter(
        userinstitution__user=request.user
    )
    subjects = Subject.objects.filter(
        subject_institutions__institution__in=user_institutions
    ).distinct()

    context = {
        'exam_templates': page_obj,
        'subjects': subjects,
        'exam_modes': ExamTemplate.EXAM_TYPE_CHOICES,  # Cambiado a EXAM_TYPE_CHOICES
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
@user_passes_test(is_admin, login_url='/')
def user_list(request):
    users = User.objects.all()
    return render(request, 'material/user_list.html', {'users': users})

@login_required
@user_passes_test(is_admin, login_url='/')
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
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
        user.delete()
        messages.success(request, 'Usuario eliminado correctamente.', extra_tags='usuarios')
        return redirect('material:user_list')
    return render(request, 'material/confirm_delete_user.html', {'user': user})

@login_required
def mis_datos(request):
    user = request.user
    import logging
    logger = logging.getLogger(__name__)
    if request.method == 'POST':
        logger.info(f"POST DATA: {request.POST}")
        form = UserEditForm(request.POST, instance=user)
        logger.info(f"Form valid: {form.is_valid()}")
        if form.is_valid():
            logger.info(f"Form cleaned_data: {form.cleaned_data}")
            if form.has_changed():
                logger.info(f"ANTES DE GUARDAR: first_name={form.cleaned_data.get('first_name')}, last_name={form.cleaned_data.get('last_name')}")
                user = form.save()
                logger.info(f"DESPUES DE GUARDAR: first_name={user.first_name}, last_name={user.last_name}")
                update_session_auth_hash(request, user)
                messages.success(request, 'Sus cambios fueron guardados.')
            else:
                logger.info("No se realizaron cambios detectados por el formulario.")
                messages.info(request, 'No se realizaron cambios.')
            return redirect('material:mis_datos')
        else:
            logger.error(f"Errores en el formulario: {form.errors}")
    else:
        initial_data = {
            'role': user.profile.role,
            'institutions': user.profile.institutions.all(),
        }
        form = UserEditForm(instance=user, initial=initial_data)
    return render(request, 'material/mis_datos.html', {
        'form': form,
        'is_admin': is_admin(request.user)
    })

@login_required
def mis_examenes(request):
    has_exam_version_fields, has_batch_table = _get_exam_version_schema_state()

    try:
        examenes_qs = Exam.objects.filter(created_by=request.user).select_related('subject')

        if has_exam_version_fields:
            examenes_qs = examenes_qs.select_related('version_batch')
        else:
            # Evita SELECT de columnas nuevas cuando Neon no corrio las migraciones.
            examenes_qs = examenes_qs.defer('version_batch', 'version_number')

        examenes = list(examenes_qs)

        if has_batch_table and has_exam_version_fields:
            batches = list(
                ExamVersionBatch.objects.filter(created_by=request.user).select_related('subject')
            )
        else:
            batches = []
    except (OperationalError, ProgrammingError, DatabaseError):
        logger.warning('Esquema de examenes desfasado en produccion; degradando mis_examenes sin lotes.')
        examenes = list(
            Exam.objects.filter(created_by=request.user).select_related('subject').defer('version_batch', 'version_number')
        )
        batches = []
    return render(request, 'material/exams/mis_examenes_new.html', {
        'examenes': examenes,
        'batches': batches,
    })


@login_required
def view_exam_batch(request, batch_id):
    batch = get_object_or_404(ExamVersionBatch, id=batch_id, created_by=request.user)
    versions = batch.versions.all().prefetch_related('questions__topic').order_by('version_number', 'id')
    return render(request, 'material/exams/view_exam_batch.html', {
        'batch': batch,
        'versions': versions,
    })


@login_required
@require_POST
def update_exam_batch_name(request, batch_id):
    batch = get_object_or_404(ExamVersionBatch, id=batch_id, created_by=request.user)
    new_name = request.POST.get('name', '').strip()
    if new_name:
        batch.name = new_name
        batch.save(update_fields=['name'])
        messages.success(request, 'Nombre del lote actualizado.', extra_tags='examenes')
    else:
        messages.error(request, 'El nombre del lote no puede estar vacio.', extra_tags='examenes')
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
def exam_version_available_questions(request):
    exam_id = request.GET.get('exam_id')
    question_id = request.GET.get('question_id')
    if not (str(exam_id).isdigit() and str(question_id).isdigit()):
        return JsonResponse({'success': False, 'error': 'Parametros invalidos'}, status=400)

    exam = get_object_or_404(Exam, id=int(exam_id), created_by=request.user)
    current_question = get_object_or_404(Question, id=int(question_id), user=request.user)
    used_ids = set(exam.questions.values_list('id', flat=True))
    used_ids.discard(current_question.id)

    candidates = Question.objects.filter(
        user=request.user,
        subjects__id=exam.subject_id,
        topic_id=current_question.topic_id,
    ).exclude(id__in=used_ids).distinct()[:80]

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
    exam_id = request.POST.get('exam_id')
    old_question_id = request.POST.get('old_question_id')
    new_question_id = request.POST.get('new_question_id')
    if not (str(exam_id).isdigit() and str(old_question_id).isdigit() and str(new_question_id).isdigit()):
        return JsonResponse({'success': False, 'error': 'Parametros invalidos'}, status=400)

    exam = get_object_or_404(Exam, id=int(exam_id), created_by=request.user)
    old_q = get_object_or_404(Question, id=int(old_question_id), user=request.user)
    replace_mode = request.POST.get('replace_mode', 'same_topic')

    if replace_mode == 'random_other':
        import random
        used_ids = set(exam.questions.values_list('id', flat=True))
        used_ids.discard(old_q.id)
        candidates = list(
            Question.objects.filter(
                user=request.user,
                subjects__id=exam.subject_id,
            ).exclude(id__in=used_ids).exclude(topic_id=old_q.topic_id).distinct()
        )
        if not candidates:
            return JsonResponse({'success': False, 'error': 'No hay preguntas disponibles de otro tema.'}, status=400)
        new_q = random.choice(candidates)
    else:
        new_q = get_object_or_404(Question, id=int(new_question_id), user=request.user)

    if replace_mode != 'random_other' and old_q.topic_id != new_q.topic_id:
        return JsonResponse({'success': False, 'error': 'La nueva pregunta debe ser del mismo tema.'}, status=400)
    if exam.questions.filter(id=new_q.id).exists():
        return JsonResponse({'success': False, 'error': 'La pregunta ya esta en esta version.'}, status=400)

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

    current_question = get_object_or_404(Question, id=int(question_id), user=request.user)
    used_ids = set(preview_versions[version_index])
    used_ids.discard(current_question.id)

    candidates = Question.objects.filter(
        user=request.user,
        subjects__id=int(subject_id),
        topic_id=current_question.topic_id,
    ).exclude(id__in=used_ids).distinct()[:80]

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

    old_q = get_object_or_404(Question, id=int(old_question_id), user=request.user)
    replace_mode = request.POST.get('replace_mode', 'same_topic')

    if replace_mode == 'random_other':
        import random
        subject_id = request.session.get('preview_exam', {}).get('subject')
        used_ids = set(preview_versions[version_index])
        used_ids.discard(old_q.id)
        candidates = list(
            Question.objects.filter(
                user=request.user,
                subjects__id=int(subject_id),
            ).exclude(id__in=used_ids).exclude(topic_id=old_q.topic_id).distinct()
        )
        if not candidates:
            return JsonResponse({'success': False, 'error': 'No hay preguntas disponibles de otro tema.'}, status=400)
        new_q = random.choice(candidates)
    else:
        new_q = get_object_or_404(Question, id=int(new_question_id), user=request.user)

    if replace_mode != 'random_other' and old_q.topic_id != new_q.topic_id:
        return JsonResponse({'success': False, 'error': 'La nueva pregunta debe ser del mismo tema.'}, status=400)
    if int(new_q.id) in preview_versions[version_index]:
        return JsonResponse({'success': False, 'error': 'La pregunta ya esta en esta version.'}, status=400)

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
        'current_date': examen.date_str or '-',
        'exam_type': exam_type_display,
        'exam_mode': exam_mode_display,
        'resolution_time': examen.duration_minutes,
        'modalidad_resolucion': modalidad_list,
        'instructions': examen.instructions or '',
        'notes_and_recommendations': examen.notes_and_recommendations or '',
        'questions_texts': questions_texts,
        'outcomes_texts': outcomes_texts,
        'topics_texts': topics_texts,
        'bloom_display': bloom_display,
        'total_exam_questions': total_exam_questions,
        'print_style': get_print_style_context(print_format),
        'rubric_grids': rubric_grids,
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

@login_required
def lista_preguntas(request):
    # Obtener todas las preguntas del usuario
    preguntas = Question.objects.filter(user=request.user).prefetch_related('subjects').select_related('topic', 'subtopic', 'contenido')

    # Obtener materias que tienen preguntas del usuario
    subjects = Subject.objects.filter(
        questions__in=preguntas
    ).distinct().order_by('name')

    # Aplicar filtros
    subject_id = request.GET.get('subject', '')
    topic_id = request.GET.get('topic', '')
    subtopic_id = request.GET.get('subtopic', '')
    ai_approval = request.GET.get('ai_approval', '')

    # Filtrar por materia si corresponde
    if subject_id and subject_id.isdigit():
        sid = int(subject_id)
        preguntas = preguntas.filter(
            Q(subjects__id=sid) |
            Q(subjects__isnull=True, topic__subject_id=sid)
        ).distinct()
    # Filtrar por tema si corresponde
    if topic_id and topic_id.isdigit() and int(topic_id) > 0:
        preguntas = preguntas.filter(topic_id=int(topic_id))
    # Filtrar por subtema si corresponde
    if subtopic_id and subtopic_id.isdigit() and int(subtopic_id) > 0:
        preguntas = preguntas.filter(subtopic_id=int(subtopic_id))
    # Filtrar por estado de aprobación IA
    if ai_approval == 'aprobada':
        preguntas = preguntas.filter(generated_by_ai=True, ai_approved=True)
    elif ai_approval == 'rechazada':
        preguntas = preguntas.filter(generated_by_ai=True, ai_approved=False)
    elif ai_approval == 'sin_revisar':
        preguntas = preguntas.filter(generated_by_ai=True, ai_approved__isnull=True)
    elif ai_approval == 'ia_todas':
        preguntas = preguntas.filter(generated_by_ai=True)

    # Filtrar por nivel Bloom
    bloom_filter = request.GET.get('bloom_filter', '')
    if bloom_filter == 'con_bloom':
        preguntas = preguntas.filter(bloom_level__isnull=False)
    elif bloom_filter == 'sin_bloom':
        preguntas = preguntas.filter(bloom_level__isnull=True)
    elif bloom_filter.isdigit() and 1 <= int(bloom_filter) <= 6:
        preguntas = preguntas.filter(bloom_level=int(bloom_filter))

    # Obtener temas y subtemas basados en los filtros actuales
    topics = Topic.objects.none()
    subtopics = Subtopic.objects.none()

    if subject_id and subject_id.isdigit() and int(subject_id) > 0:
        topics = Topic.objects.filter(subject_id=int(subject_id)).distinct().order_by('name')

    if topic_id and topic_id.isdigit() and int(topic_id) > 0:
        subtopics = Subtopic.objects.filter(topic_id=int(topic_id)).distinct().order_by('name')

    paginator = Paginator(preguntas, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'preguntas': page_obj,
        'subjects': subjects,
        'topics': topics,
        'subtopics': subtopics,
        'selected_subject': subject_id if subject_id.isdigit() else '',
        'selected_topic': topic_id if topic_id.isdigit() else '',
        'selected_subtopic': subtopic_id if subtopic_id.isdigit() else '',
        'selected_ai_approval': ai_approval,
        'selected_bloom_filter': bloom_filter,
    }
    return render(request, 'material/questions/lista_preguntas.html', context)

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
        pregunta.delete()
        messages.success(request, 'Pregunta eliminada correctamente', extra_tags='preguntas')
        return redirect('material:lista_preguntas')
    
    return render(request, 'material/questions/confirmar_eliminar.html', {
        'pregunta': pregunta
    })

@login_required
@require_POST
def bulk_eliminar_preguntas(request):
    from urllib.parse import urlencode

    delete_all_filtered = request.POST.get('delete_all_filtered') == '1'

    if delete_all_filtered:
        preguntas = Question.objects.filter(user=request.user)
        subject_id = request.POST.get('subject', '')
        topic_id = request.POST.get('topic', '')
        subtopic_id = request.POST.get('subtopic', '')
        ai_approval = request.POST.get('ai_approval', '')
        if subject_id and subject_id.isdigit():
            preguntas = preguntas.filter(subjects__id=int(subject_id))
        if topic_id and topic_id.isdigit() and int(topic_id) > 0:
            preguntas = preguntas.filter(topic_id=int(topic_id))
        if subtopic_id and subtopic_id.isdigit() and int(subtopic_id) > 0:
            preguntas = preguntas.filter(subtopic_id=int(subtopic_id))
        if ai_approval == 'aprobada':
            preguntas = preguntas.filter(generated_by_ai=True, ai_approved=True)
        elif ai_approval == 'rechazada':
            preguntas = preguntas.filter(generated_by_ai=True, ai_approved=False)
        elif ai_approval == 'sin_revisar':
            preguntas = preguntas.filter(generated_by_ai=True, ai_approved__isnull=True)
        elif ai_approval == 'ia_todas':
            preguntas = preguntas.filter(generated_by_ai=True)
        count = preguntas.count()
        preguntas.delete()
    else:
        ids_raw = request.POST.getlist('pregunta_ids')
        ids = [int(i) for i in ids_raw if i.isdigit()]
        if not ids:
            messages.error(request, 'No se seleccionó ninguna pregunta para eliminar.', extra_tags='preguntas')
            return redirect('material:lista_preguntas')
        preguntas = Question.objects.filter(pk__in=ids, user=request.user)
        count = preguntas.count()
        preguntas.delete()

    if count == 1:
        messages.success(request, 'Se eliminó 1 pregunta correctamente.', extra_tags='preguntas')
    else:
        messages.success(request, f'Se eliminaron {count} preguntas correctamente.', extra_tags='preguntas')

    params = {}
    for key in ['subject', 'topic', 'subtopic', 'ai_approval']:
        val = request.POST.get(key, '')
        if val:
            params[key] = val
    redirect_url = reverse('material:lista_preguntas')
    if params:
        redirect_url += '?' + urlencode(params)
    return redirect(redirect_url)

@login_required
def mis_contenidos(request):
    contenidos = Contenido.objects.filter(uploaded_by=request.user)
    return render(request, 'material/questions/mis_contenidos.html', {'contenidos': contenidos})

@login_required
def delete_contenido(request):
    if request.method == 'POST':
        contenido_ids = request.POST.getlist('contenido_ids')
        if not contenido_ids:
            messages.error(request, 'No se seleccionó ningún documento para borrar.', extra_tags='contenidos')
            return redirect('material:mis_contenidos')
        contenidos = Contenido.objects.filter(id__in=contenido_ids, uploaded_by=request.user)
        count = contenidos.count()
        contenidos.delete()
        if count == 1:
            messages.success(request, 'El documento ha sido borrado correctamente.', extra_tags='contenidos')
        else:
            messages.success(request, f'Los {count} documentos han sido borrados correctamente.', extra_tags='contenidos')
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
        'dark_mode': request.session.get('dark_mode', False),
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


def _parse_options_json(raw_options):
    text = (raw_options or '').strip()
    if not text:
        return ''

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return json.dumps([str(v) for v in parsed[:4]])
    except Exception:
        pass

    # Fallback: "A|B|C|D"
    parts = [p.strip() for p in text.split('|') if p.strip()]
    if parts:
        return json.dumps(parts[:4])
    return ''


def process_csv_file(file, contenido, user):
    from .models import Subject, Topic, Subtopic, Question
    
    # Intentar múltiples codificaciones
    encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1', 'utf-16']
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
                
            # Obtener o crear la materia
            subject, _ = Subject.objects.get_or_create(name=row.get('materia', 'General'))
            
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
    encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1', 'utf-16']
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
    from .models import Subject, Topic, Subtopic, Question
    # Obtener o crear Subject
    subject, _ = Subject.objects.get_or_create(
        name=data.get('materia', 'General')
    )
    
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
        user=user
    )
    q.subjects.add(subject)


def download_template(request, format):
    if format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="template.csv"'
        writer = csv.writer(response)
        writer.writerow(['subject', 'question_text', 'answer_text', 'topic', 'subtopic', 'source_page', 'chapter'])
        writer.writerow(['Matemáticas', '¿Cuál es la capital de Francia?', 'París', 'Geografía', 'Capitales', 1, 'Capítulo 1: Introducción'])
        writer.writerow(['Literatura', '¿Quién escribió "Cien años de soledad"?', 'Gabriel García Márquez', 'Literatura', 'Autores', 2, 'Capítulo 2: Literatura Latinoamericana'])
        return response
    elif format == 'json':
        data = [
            {
                "subject": "Matemáticas",
                "question_text": "¿Cuál es la capital de Francia?",
                "answer_text": "París",
                "topic": "Geografía",
                "subtopic": "Capitales",
                "source_page": 1,
                "chapter": "Capítulo 1: Introducción"
            },
            {
                "subject": "Literatura",
                "question_text": "¿Quién escribió 'Cien años de soledad'?",
                "answer_text": "Gabriel García Márquez",
                "topic": "Literatura",
                "subtopic": "Autores",
                "source_page": 2,
                "chapter": "Capítulo 2: Literatura Latinoamericana"
            }
        ]
        response = HttpResponse(json.dumps(data, indent=4), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="template.json"'
        return response
    elif format == 'txt':
        content = """Subject: Matemáticas
Pregunta: ¿Cuál es la capital de Francia?
Respuesta: París
Tema: Geografía
Subtema: Capitales
Página: 1
Capítulo: Capítulo 1: Introducción

Subject: Literatura
Pregunta: ¿Quién escribió 'Cien años de soledad'?
Respuesta: Gabriel García Márquez
Tema: Literatura
Subtema: Autores
Página: 2
Capítulo: Capítulo 2: Literatura Latinoamericana"""
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

        # Filtrar solo instituciones activas (is_active=True)
        institutions = InstitutionV2.objects.filter(
            userinstitution__user=request.user,
            is_active=True  # Solo mostrar instituciones activas
        )

        if name_query:
            institutions = institutions.filter(name__icontains=name_query)

        if favorite_only:
            institutions = institutions.filter(
                userinstitution__user=request.user,
                userinstitution__is_favorite=True
            )

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

    except DatabaseError as e:
        logger.error(f"Error DB en institution_v2_list: {str(e)}", exc_info=True)
        messages.error(request, 'Se detecto un problema temporal de base de datos en Instituciones. Reintenta en unos minutos.')
        page_obj = Paginator([], 10).get_page(1)
        favorite_count = 0

    return render(request, 'material/institutions_v2/list.html', {
        'institutions': page_obj,
        'name_query': name_query,
        'favorite_only': favorite_only,
        'favorite_count': favorite_count,
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
                
        except Exception as e:
            logger.error(f"Error eliminando institución: {str(e)}")
            messages.error(request, 'Ocurrió un error al eliminar la institución.')
            return redirect('material:institution_v2_detail', pk=pk)
    
    # Mostrar confirmación
    return render(request, 'material/institutions_v2/confirm_delete.html', {
        'institution': institution,
        'campuses_count': institution.campusv2_set.count(),
        'faculties_count': institution.facultyv2_set.count()
    })

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

# Agregar al final de views.py
""" @login_required
def count_favorite_institutions(request):
        count = UserInstitution.objects.filter(
        user=request.user,
        is_favorite=True
    ).count()
    return JsonResponse({'count': count})
"""

# Subjects CRUD 
@login_required
def subject_list(request):
    subjects = Subject.objects.all()
    return render(request, 'material/subjects/list.html', {'subjects': subjects})

@login_required
def create_subject(request):
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save()
            messages.success(request, 'Materia creada exitosamente', extra_tags='materias')
            return redirect('material:subject_list')
    else:
        form = SubjectForm()
    return render(request, 'material/subjects/form.html', {'form': form, 'action': 'Crear'})

@login_required
def edit_subject(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            messages.success(request, 'Materia actualizada exitosamente', extra_tags='materias')
            return redirect('material:subject_detail', pk=pk)
    else:
        form = SubjectForm(instance=subject)
    return render(request, 'material/subjects/form.html', {'form': form, 'action': 'Editar'})

@login_required
def delete_subject(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == 'POST':
        subject.delete()
        messages.success(request, 'Materia eliminada exitosamente', extra_tags='materias')
        return redirect('material:subject_list')
    return render(request, 'material/subjects/confirm_delete.html', {'subject': subject})

class SubjectDetailView(DetailView):
    model = Subject
    template_name = 'material/subjects/detail.html'
    context_object_name = 'subject'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['outcomes'] = self.object.outcome_relations.all()  # Eliminado .order_by('code')
        return context


# Careers CRUD (similar structure)
@login_required
def career_list(request):
    careers = Career.objects.all().prefetch_related('faculties', 'campus', 'subjects')
    return render(request, 'material/careers/list.html', {'careers': careers})

@login_required
def create_career(request):
    if request.method == 'POST':
        form = CareerForm(request.POST)
        if form.is_valid():
            career = form.save()
            messages.success(request, 'Carrera creada exitosamente', extra_tags='carreras')
            return redirect('material:career_list')
    else:
        form = CareerForm()
    return render(request, 'material/careers/form.html', {
        'form': form,
        'action': 'Crear'
    })

@login_required
def delete_career(request, pk):
    career = get_object_or_404(Career, pk=pk)
    if request.method == 'POST':
        career.delete()
        messages.success(request, 'Carrera eliminada exitosamente', extra_tags='carreras')
        return redirect('material:career_list')
    return render(request, 'material/careers/confirm_delete.html', {'career': career})

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
                if Subject.objects.filter(name__iexact=name).exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'Ya existe una materia con este nombre'
                    }, status=400)

                subject = Subject.objects.create(name=name)
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
        faculties = FacultyV2.objects.filter(institution_id=institution_id).values('id', 'name')
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
        campuses = CampusV2.objects.filter(institution_id=institution_id).values('id', 'name')
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
        ).order_by('code')

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
                'error': 'El nombre del tema no puede estar vacío'
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
                'error': 'Ya existe un tema con este nombre en esta materia'
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
                'error': 'El nombre del subtema no puede estar vacío'
            }, status=400)
            
        if not topic_id:
            return JsonResponse({
                'success': False,
                'error': 'Debe seleccionar un tema principal'
            }, status=400)
            
        try:
            topic = Topic.objects.get(id=topic_id)
        except Topic.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Tema no encontrado'
            }, status=404)
            
        # Verificar duplicados
        if Subtopic.objects.filter(name__iexact=name, topic=topic).exists():
            return JsonResponse({
                'success': False,
                'error': 'Ya existe un subtema con este nombre en este tema'
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
                'error': 'No hay preguntas disponibles para los temas seleccionados'
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
        'total_questions': total_questions
    })

@login_required
def list_oral_exams(request):
    oral_exams = OralExamSet.objects.filter(user=request.user).order_by('-created_at')
    
    # Agregar total de estudiantes a cada examen
    for exam in oral_exams:
        exam.total_students = exam.num_groups * exam.students_per_group
    
    return render(request, 'material/oral_exams/list.html', {
        'oral_exams': oral_exams
    })

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
        raise ValueError("No hay preguntas disponibles para los temas seleccionados")
    
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
                'topic_name': question.topic.name if question.topic else 'Sin tema',
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
            'new_topic': new_question.topic.name if new_question.topic else 'Sin tema'
        })
        
    except Exception as e:
        logger.error(f"Error in exchange_question: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

# --- ONBOARDING WIZARD ---------------------------------------------------------
# ROLLBACK: eliminar este bloque completo (desde la linea marcada hasta FIN ONBOARDING)
# y revertir migracion:  .venv\Scripts\python.exe manage.py migrate material 0019

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
                # Editar institución existente
                try:
                    inst = InstitutionV2.objects.get(pk=institution_id, is_active=True)
                    UserInstitution.objects.get_or_create(user=request.user, institution=inst)
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
                except InstitutionV2.DoesNotExist:
                    pass
            elif new_inst_name:
                # Crear nueva institucion
                inst, _ = InstitutionV2.objects.get_or_create(name=new_inst_name)
                UserInstitution.objects.get_or_create(user=request.user, institution=inst)

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

            if existing_subject_id and body.get('edit_subject'):
                # Editar materia existente
                try:
                    subj = Subject.objects.get(pk=existing_subject_id)
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
                # Solo vincular — no editar
                pass
            elif subject_name:
                subject, _ = Subject.objects.get_or_create(name=subject_name)

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

        if body.get('done') or step == 'done':
            profile.onboarding_completed = True
            profile.save(update_fields=['onboarding_completed'])

    except Exception as e:
        logger.error(f"Error en onboarding_save_step (step={step}): {e}", exc_info=True)
        # No fallamos - el wizard continua igual

    return JsonResponse({'ok': True})


@require_POST
@login_required
def onboarding_upload_contenido(request):
    """
    Endpoint multipart para subir un contenido desde el wizard de onboarding (paso 4).
    Campos: title (texto), file (archivo), subject_id (opcional, int).
    """
    import os as _os
    title = request.POST.get('title', '').strip()
    uploaded_file = request.FILES.get('file')
    subject_id = request.POST.get('subject_id', '').strip()

    if not title or not uploaded_file:
        return JsonResponse({'ok': False, 'error': 'Título y archivo son requeridos.'}, status=400)

    allowed_extensions = {'.pdf', '.docx', '.doc', '.pptx', '.ppt'}
    ext = _os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in allowed_extensions:
        return JsonResponse({'ok': False, 'error': f'Tipo de archivo no permitido: {ext}'}, status=400)

    try:
        contenido = Contenido.objects.create(
            title=title,
            file=uploaded_file,
            uploaded_by=request.user,
        )
        if subject_id.isdigit():
            try:
                subj = Subject.objects.get(pk=int(subject_id))
                contenido.subjects.add(subj)
            except Subject.DoesNotExist:
                pass
        return JsonResponse({
            'ok': True,
            'contenido': {
                'id': contenido.id,
                'title': contenido.title,
                'subjects': [s.name for s in contenido.subjects.all()],
                'uploaded_at': contenido.uploaded_at.strftime('%d/%m/%Y'),
            }
        })
    except Exception as e:
        logger.error(f"Error en onboarding_upload_contenido: {e}", exc_info=True)
        return JsonResponse({'ok': False, 'error': 'Error al subir el archivo.'}, status=500)

# --- FIN ONBOARDING WIZARD -----------------------------------------------------

# --- RÚBRICAS ------------------------------------------------------------------

def _prepare_rubric_grid(rubric):
    """Devuelve un dict con la estructura de la rúbrica para renderizar en templates.
    {'title', 'levels': [str], 'rows': [{'name', 'cells': [str]}], 'body'}
    """
    ordered_levels = list(rubric.levels.order_by('order'))
    ordered_criteria = list(rubric.criteria.order_by('order'))
    if not ordered_levels:
        return {'title': rubric.title, 'levels': [], 'rows': [], 'body': rubric.body}
    cells_map = {
        (c.criterion_id, c.level_id): c.description
        for c in RubricCell.objects.filter(criterion__rubric=rubric)
    }
    return {
        'title': rubric.title,
        'body': rubric.body,
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
                rubrica.body = None
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
    examen = get_object_or_404(Exam, pk=exam_pk, created_by=request.user)
    exam_rubric_qs = ExamRubric.objects.filter(exam=examen).select_related('rubric').order_by('position', 'id')
    associated_ids = exam_rubric_qs.values_list('rubric_id', flat=True)
    available_rubrics = Rubric.objects.filter(created_by=request.user).exclude(id__in=associated_ids)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            rubric_id = request.POST.get('rubric_id')
            rubrica = get_object_or_404(Rubric, pk=rubric_id, created_by=request.user)
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
                'gemini': 'gemini-2.5-flash',
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
                model = 'gemini-2.5-flash'
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
        'is_staff': request.user.is_staff,
        'default_ollama_url': 'http://192.168.12.236:11434',
    }
    return render(request, 'material/ai_config.html', context)


@login_required
@login_required
def ai_config_status(request):
    """Endpoint JSON que devuelve el estado actual del backend configurado."""
    from django.http import JsonResponse
    from .ai_router import get_backend_for_user
    from .models import UserAIConfig

    config, _ = UserAIConfig.objects.get_or_create(user=request.user)
    backend = get_backend_for_user(request.user)
    try:
        status = backend.get_status()
        # Siempre devolver el source real del usuario como 'backend'
        status['backend'] = config.source
    except Exception as e:
        status = {'connected': False, 'error': str(e), 'backend': config.source}
    return JsonResponse(status)


@login_required
def institution_ai_config_view(request):
    """Vista para que los administradores gestionen InstitutionAIConfig."""
    from .models import InstitutionAIConfig, InstitutionV2

    if not request.user.is_staff:
        messages.error(request, 'No tenés permiso para acceder a esta sección.')
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
        is_active=True
    ).exclude(pk__in=configured_ids).order_by('name')

    return render(request, 'material/institution_ai_config.html', {
        'configs': configs,
        'editing': editing,
        'available_institutions': available_institutions,
    })


def health_check(request):
    return HttpResponse("OK", status=200)


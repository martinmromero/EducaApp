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
from django.views.generic import DetailView, UpdateView, CreateView, ListView
from django.urls import reverse_lazy
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods, require_POST
from django.core.paginator import Paginator
from django.db import models, transaction
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404, reverse
from .models import (Exam, ExamTemplate, Contenido, Profile, Question, Subject, Topic, 
    Subtopic,Institution, LearningOutcome, Campus, Faculty,Career)
from .models import (InstitutionV2, CampusV2, FacultyV2, UserInstitution, InstitutionLog)
from .forms import (
    CustomLoginForm, ExamForm, ExamTemplateForm, QuestionForm, 
    UserEditForm, ContenidoForm, InstitutionForm, 
    LearningOutcomeForm, SubjectForm, ProfileForm,CareerForm,CareerSimpleForm  
)
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Prefetch, F, Value, CharField
from django.db.models.functions import Concat
from .ia_processor import extract_text_from_file, generate_questions_from_text
from django.utils import timezone 
from .forms import InstitutionForm, LearningOutcomeForm, ProfileForm


from .forms import InstitutionV2Form, CampusV2Form, FacultyV2Form, InstitutionForm

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
    topics = Topic.objects.filter(subject_id=subject_id).values('id', 'name')
    return JsonResponse(list(topics), safe=False)

def get_subtopics(request):
    topic_id = request.GET.get('topic_id')
    subtopics = Subtopic.objects.filter(topic_id=topic_id).values('id', 'name')
    return JsonResponse(list(subtopics), safe=False)

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
        messages.error(self.request, "Credenciales inválidas. Intente nuevamente.")
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
            contenido = form.save(commit=False)
            contenido.uploaded_by = request.user
            contenido.save()
            messages.success(request, 'Los archivos se subieron correctamente.')
            return redirect('material:mis_contenidos')
    else:
        form = ContenidoForm()
    return render(request, 'material/questions/upload.html', {'form': form})

@login_required
def generate_questions(request, contenido_id):
    contenido = Contenido.objects.get(id=contenido_id)
    num_questions = int(request.POST.get('num_questions', 20))
    try:
        text = extract_text_from_file(contenido.file.path)
    except ValueError as e:
        messages.error(request, str(e))
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
        default_subject = Subject.objects.get_or_create(Nombre="Generado por IA")[0]
        default_topic = Topic.objects.get_or_create(name="Generado por IA", subject=default_subject)[0]
        
        for i, question in enumerate(questions_list):
            if str(i) in selected_questions:
                Question.objects.create(
                    contenido=contenido,
                    subject=default_subject,
                    question_text=question,
                    answer_text="Respuesta generada por IA",
                    topic=default_topic,
                    subtopic=None,
                    user=request.user
                )
        messages.success(request, 'Preguntas guardadas correctamente.')
        return redirect('material:lista_preguntas')

@login_required
def create_exam(request):
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.created_by = request.user
            exam.save()
            form.save_m2m()
            messages.success(request, 'Examen creado correctamente.')
            return redirect('material:mis_examenes')
    else:
        form = ExamForm()
    return render(request, 'material/create_exam.html', {'form': form})

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
                    
                    InstitutionLog.objects.create(
                        institution=exam_template.institution,
                        user=request.user,
                        action=f"Creó plantilla de examen: {exam_template}"
                    )
                    
                    messages.success(
                        request, 
                        'Plantilla creada correctamente',
                        extra_tags='exam_template'
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
        'material/create_exam_template.html',
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

        context = {
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
            'current_date': timezone.now().strftime("%d/%m/%Y")
        }

        return render(request, 'material/preview_exam_template.html', context)

    except Exception as e:
        logger.error(f"Preview error: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

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

    context = {
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
        'is_preview': False
    }

    return render(request, 'material/preview_exam_template.html', context)

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

    return render(request, 'material/list_exam_templates.html', context)

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
            messages.success(request, 'Usuario actualizado correctamente.')
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
        messages.success(request, 'Usuario eliminado correctamente.')
        return redirect('material:user_list')
    return render(request, 'material/confirm_delete_user.html', {'user': user})

@login_required
def mis_datos(request):
    user = request.user
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            if form.has_changed():
                user.username = form.cleaned_data['username']
                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                user.email = form.cleaned_data['email']
                user.save()
                profile = user.profile
                profile.role = form.cleaned_data['role']
                profile.save()
                profile.institutions.set(form.cleaned_data['institutions'])
                update_session_auth_hash(request, user)
                messages.success(request, 'Sus cambios fueron guardados.')
            else:
                messages.info(request, 'No se realizaron cambios.')
            return redirect('material:mis_datos')
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
    examenes = Exam.objects.filter(created_by=request.user)
    return render(request, 'material/mis_examenes.html', {'examenes': examenes})

@login_required
def lista_preguntas(request):
    preguntas = Question.objects.filter(
        models.Q(contenido__uploaded_by=request.user) | 
        models.Q(user=request.user)
    ).select_related('subject', 'topic', 'subtopic')

    subject_id = request.GET.get('subject', '')
    topic_id = request.GET.get('topic', '')
    subtopic_id = request.GET.get('subtopic', '')

    if subject_id.isdigit():
        preguntas = preguntas.filter(subject_id=int(subject_id))
    if topic_id.isdigit():
        preguntas = preguntas.filter(topic_id=int(topic_id))
    if subtopic_id.isdigit():
        preguntas = preguntas.filter(subtopic_id=int(subtopic_id))

    subjects = Subject.objects.filter(
        question__in=preguntas
    ).distinct().order_by('name')  # Cambiado de 'Nombre' a 'name'

    topics = Topic.objects.filter(
        subject__question__in=preguntas
    ).distinct().order_by('name') if subject_id.isdigit() else Topic.objects.none()

    subtopics = Subtopic.objects.filter(
        topic__subject__question__in=preguntas
    ).distinct().order_by('name') if topic_id.isdigit() else Subtopic.objects.none()

    paginator = Paginator(preguntas, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'preguntas': page_obj,
        'subjects_unicos': subjects,
        'topics_unicos': topics,
        'subtopics_unicos': subtopics,
        'selected_subject': subject_id if subject_id.isdigit() else '',
        'selected_topic': topic_id if topic_id.isdigit() else '',
        'selected_subtopic': subtopic_id if subtopic_id.isdigit() else '',
    }
    return render(request, 'material/questions/lista_preguntas.html', context)


@login_required
def editar_pregunta(request, pk):
    pregunta = get_object_or_404(Question, pk=pk, contenido__uploaded_by=request.user)
    
    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=pregunta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pregunta actualizada correctamente')
            return redirect('material:lista_preguntas')
    else:
        form = QuestionForm(instance=pregunta)
    
    return render(request, 'material/editar_pregunta.html', {
        'form': form,
        'pregunta': pregunta
    })

@login_required
def eliminar_pregunta(request, pk):
    pregunta = get_object_or_404(Question, pk=pk, contenido__uploaded_by=request.user)
    
    if request.method == 'POST':
        pregunta.delete()
        messages.success(request, 'Pregunta eliminada correctamente')
        return redirect('material:lista_preguntas')
    
    return render(request, 'material/confirmar_eliminar.html', {
        'pregunta': pregunta
    })

@login_required
def mis_contenidos(request):
    contenidos = Contenido.objects.filter(uploaded_by=request.user)
    return render(request, 'material/questions/mis_contenidos.html', {'contenidos': contenidos})

@login_required
def delete_contenido(request):
    if request.method == 'POST':
        contenido_ids = request.POST.getlist('contenido_ids')
        if not contenido_ids:
            messages.error(request, 'No se seleccionó ningún documento para borrar.')
            return redirect('material:mis_contenidos')
        contenidos = Contenido.objects.filter(id__in=contenido_ids, uploaded_by=request.user)
        count = contenidos.count()
        contenidos.delete()
        if count == 1:
            messages.success(request, 'El documento ha sido borrado correctamente.')
        else:
            messages.success(request, f'Los {count} documentos han sido borrados correctamente.')
    return redirect('material:mis_contenidos')

@login_required
def upload_questions(request):
    """
    Vista para subir preguntas, tanto individualmente como por lotes (CSV/TXT)
    """
    if request.method == 'POST':
        form = QuestionForm(request.POST, request.FILES, current_user=request.user)
        
        if form.is_valid():
            try:
                # Procesamiento para archivos CSV/TXT
                if 'file' in request.FILES:
                    file = request.FILES['file']
                    file_extension = os.path.splitext(file.name)[1].lower()
                    
                    # Crear contenido por defecto asociado
                    default_contenido, created = Contenido.objects.get_or_create(
                        title="Contenido por Defecto",
                        defaults={
                            'uploaded_by': request.user,
                            'subject': form.cleaned_data['subject']
                        }
                    )
                    
                    if file_extension == '.csv':
                        questions_created = process_csv_file(file, default_contenido, request.user)
                        messages.success(request, f'{questions_created} preguntas creadas desde archivo CSV.')
                    elif file_extension == '.txt':
                        questions_created = process_txt_file(file, default_contenido, request.user)
                        messages.success(request, f'{questions_created} preguntas creadas desde archivo TXT.')
                    else:
                        messages.error(request, 'Formato de archivo no soportado. Use CSV o TXT.')
                        return redirect('material:upload_questions')
                    
                # Procesamiento para pregunta individual
                else:
                    question = form.save(commit=False)
                    question.user = request.user
                    
                    # Asignar contenido si se seleccionó
                    if form.cleaned_data['contenido']:
                        question.contenido = form.cleaned_data['contenido']
                    else:
                        # Crear contenido por defecto si no se seleccionó uno
                        default_contenido = Contenido.objects.create(
                            title="Contenido Automático",
                            uploaded_by=request.user,
                            subject=form.cleaned_data['subject']
                        )
                        question.contenido = default_contenido
                    
                    question.save()
                    messages.success(request, 'Pregunta guardada correctamente.')
                
                return redirect('material:lista_preguntas')
            
            except Exception as e:
                logger.error(f"Error al procesar preguntas: {str(e)}", exc_info=True)
                messages.error(request, f'Ocurrió un error: {str(e)}')
                return redirect('material:upload_questions')
        
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = QuestionForm(current_user=request.user)
    
    context = {
        'form': form,
        'dark_mode': request.session.get('dark_mode', False),
        'current_tab': request.session.get('upload_questions_tab', 'single')
    }
    
    return render(request, 'material/questions/upload_questions.html', context)

# Funciones auxiliares para procesamiento de archivos
def process_csv_file(file, contenido, user):
    decoded_file = file.read().decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_file)
    questions_created = 0

    for row in reader:
        try:
            Question.objects.create(
                contenido=contenido,
                subject=Subject.objects.get_or_create(Nombre=row.get('materia', 'General'))[0],
                question_text=row['pregunta'],
                answer_text=row['respuesta'],
                topic=Topic.objects.get_or_create(
                    name=row.get('tema', 'General'),
                    subject=Subject.objects.get_or_create(Nombre=row.get('materia', 'General'))[0]
                )[0],
                subtopic=Subtopic.objects.get_or_create(
                    name=row.get('subtema'),
                    topic=Topic.objects.get_or_create(
                        name=row.get('tema', 'General'),
                        subject=Subject.objects.get_or_create(Nombre=row.get('materia', 'General'))[0]
                    )[0]
                )[0] if row.get('subtema') else None,
                unit=row.get('unidad'),
                reference_book=row.get('libro_referencia'),
                source_page=row.get('pagina'),
                chapter=row.get('capitulo'),
                user=user
            )
            questions_created += 1
        except Exception as e:
            logger.error(f"Error creando pregunta desde CSV: {str(e)}")
            continue

    return questions_created

def process_txt_file(file, contenido, user):
    lines = file.read().decode('utf-8').splitlines()
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
    # Obtener o crear Subject
    subject, _ = Subject.objects.get_or_create(
        Nombre=data.get('materia', 'General')
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
    
    # Crear la pregunta
    Question.objects.create(
        contenido=contenido,
        subject=subject,
        question_text=data.get('pregunta', ''),
        answer_text=data.get('respuesta', ''),
        topic=topic,
        subtopic=subtopic,
        unit=data.get('unidad'),
        reference_book=data.get('libro_referencia'),
        source_page=data.get('pagina'),
        chapter=data.get('capitulo'),
        user=user
    )


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
        messages.error(request, 'Formato de plantilla no soportado.')
        return redirect('material:upload_questions')

@login_required
def delete_exam_template(request):
    if request.method == 'POST':
        template_ids = request.POST.getlist('template_ids')
        ExamTemplate.objects.filter(id__in=template_ids, created_by=request.user).delete()
        messages.success(request, 'Las plantillas seleccionadas se han eliminado correctamente.', extra_tags='exam_template')
    return redirect('material:list_exam_templates')


@login_required
def manage_learning_outcomes(request):
    if request.method == 'POST':
        form = LearningOutcomeForm(request.POST)
        if form.is_valid():
            outcome = form.save()
            messages.success(request, 'Resultado de aprendizaje guardado correctamente.')
            return redirect('material:manage_learning_outcomes')
    else:
        form = LearningOutcomeForm()

    outcomes = LearningOutcome.objects.select_related('subject').all()
    return render(request, 'material/manage_learning_outcomes.html', {
        'outcomes': outcomes,
        'form': form
    })

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
def manage_institutions(request):
    if request.method == 'POST':
        try:
            form = InstitutionForm(request.POST, request.FILES)
            if form.is_valid():
                institution = form.save(commit=False)
                institution.owner = request.user
                institution.save()
                
                # Procesar sedes
                for campus_name in request.POST.getlist('campuses'):
                    if campus_name.strip():
                        Campus.objects.create(
                            name=campus_name.strip(),
                            institution=institution
                        )
                
                # Procesar facultades
                for name, code in zip(
                    request.POST.getlist('faculty_names'),
                    request.POST.getlist('faculty_codes')
                ):
                    if name.strip():
                        Faculty.objects.create(
                            name=name.strip(),
                            code=code.strip(),
                            institution=institution
                        )
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'html': render_to_string('material/institution_row.html', {
                            'institution': institution
                        })
                    })
                messages.success(request, 'Institución creada correctamente')
                return redirect('material:manage_institutions')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
            
            messages.error(request, 'Error en el formulario')
            return redirect('material:manage_institutions')
            
        except Exception as e:
            logger.error(f"Error al guardar institución: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=500)
            messages.error(request, 'Error al procesar la solicitud')
            return redirect('material:manage_institutions')

    institutions = Institution.objects.filter(owner=request.user).prefetch_related('campuses', 'faculties')
    return render(request, 'material/manage_institutions.html', {
        'institutions': institutions
    })

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
            messages.success(request, 'Institución eliminada correctamente')
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

                messages.success(request, 'Institución creada con éxito.')
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
    institution = get_object_or_404(InstitutionV2, pk=pk, userinstitution__user=request.user)
    
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

                    messages.success(request, 'Institución actualizada correctamente')
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
            messages.success(request, 'Materia creada exitosamente')
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
            messages.success(request, 'Materia actualizada exitosamente')
            return redirect('material:subject_detail', pk=pk)
    else:
        form = SubjectForm(instance=subject)
    return render(request, 'material/subjects/form.html', {'form': form, 'action': 'Editar'})

@login_required
def delete_subject(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == 'POST':
        subject.delete()
        messages.success(request, 'Materia eliminada exitosamente')
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
            messages.success(request, 'Carrera creada exitosamente')
            return redirect('material:career_list')
    else:
        form = CareerForm()
    return render(request, 'material/careers/form.html', {
        'form': form,
        'action': 'Crear'
    })

@login_required
def edit_career(request, pk):
    career = get_object_or_404(Career, pk=pk)
    if request.method == 'POST':
        form = CareerForm(request.POST, instance=career)
        if form.is_valid():
            form.save()
            messages.success(request, 'Carrera actualizada exitosamente')
            return redirect('material:career_detail', pk=pk)
    else:
        form = CareerForm(instance=career)
    return render(request, 'material/careers/form.html', {
        'form': form,
        'action': 'Editar',
        'career': career
    })

@login_required
def delete_career(request, pk):
    career = get_object_or_404(Career, pk=pk)
    if request.method == 'POST':
        career.delete()
        messages.success(request, 'Carrera eliminada exitosamente')
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
        form = CareerSimpleForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('material:career_list')  # Redirige a la lista de carreras
    else:
        form = CareerSimpleForm()

    return render(request, 'material/careers/form.html', {'form': form})

@login_required
def career_associations(request, pk):
    career = get_object_or_404(Career, pk=pk)
    
    if request.method == 'POST':
        form = CareerForm(request.POST, instance=career)
        if form.is_valid():
            form.save()
            messages.success(request, 'Asociaciones actualizadas correctamente')
            return redirect('material:career_detail', pk=pk)
    else:
        form = CareerForm(instance=career)
    
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
        return reverse_lazy('subject_detail', kwargs={'pk': self.object.subject.id})

    def get_initial(self):
        return {'subject': self.kwargs['subject_id']}

    def form_valid(self, form):
        form.instance.subject_id = self.kwargs['subject_id']
        response = super().form_valid(form)
        messages.success(self.request, 'Resultado de aprendizaje creado')
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
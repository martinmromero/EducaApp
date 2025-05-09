# Standard library imports
import csv
import json
import logging

# Django core imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db import models, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404, reverse
from .models import (Exam, ExamTemplate, Contenido, Profile, Question, Subject, Topic, 
    Subtopic,Institution, LearningOutcome, Campus, Faculty)
from .forms import (
    CustomLoginForm, ExamForm, ExamTemplateForm, QuestionForm, 
    UserEditForm, ContenidoForm, InstitutionForm, 
    LearningOutcomeForm, ProfileForm
)
from django.db.models import Prefetch
from .ia_processor import extract_text_from_file, generate_questions_from_text
from django.utils import timezone  # Añadir al inicio del archivo
from .forms import InstitutionForm, LearningOutcomeForm, ProfileForm
# Modelos
from .models import InstitutionV2, CampusV2, FacultyV2, UserInstitution, InstitutionLog

# Formularios
from .forms import InstitutionV2Form, CampusV2Form, FacultyV2Form, FavoriteInstitutionForm


# Logger configuration
logger = logging.getLogger(__name__)

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
    return render(request, 'material/upload.html', {'form': form})

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
    if request.method == 'POST':
        form = ExamTemplateForm(request.POST, request.FILES)
        if form.is_valid():
            exam_template = form.save(commit=False)
            exam_template.created_by = request.user
            exam_template.save()
            form.save_m2m()
            messages.success(request, 'Plantilla de examen creada correctamente.')
            return redirect('material:list_exam_templates')
    else:
        form = ExamTemplateForm()
    return render(request, 'material/create_exam_template.html', {'form': form})

@login_required
def preview_exam_template(request, template_id):
    exam_template = get_object_or_404(ExamTemplate, id=template_id)
    return render(request, 'material/preview_exam_template.html', {'exam_template': exam_template})

@login_required
def list_exam_templates(request):
    exam_templates = ExamTemplate.objects.filter(created_by=request.user)
    return render(request, 'material/list_exam_templates.html', {'exam_templates': exam_templates})

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
    ).distinct().order_by('Nombre')

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
    return render(request, 'material/lista_preguntas.html', context)

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
    return render(request, 'material/mis_contenidos.html', {'contenidos': contenidos})

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
    if request.method == 'POST':
        form = QuestionForm(request.POST, request.FILES)
        if form.is_valid():
            default_contenido, created = Contenido.objects.get_or_create(
                title="Contenido por Defecto",
                defaults={
                    'uploaded_by': request.user,
                }
            )
            if 'file' in request.FILES:
                file = request.FILES['file']
                if file.name.endswith('.csv'):
                    decoded_file = file.read().decode('utf-8').splitlines()
                    reader = csv.DictReader(decoded_file)
                    for row in reader:
                        Question.objects.create(
                            contenido=default_contenido,
                            subject=row['subject'],
                            question_text=row['question_text'],
                            answer_text=row['answer_text'],
                            topic=row['topic'],
                            subtopic=row['subtopic'],
                            source_page=int(row['source_page']),
                            chapter=row['chapter'],
                        )
                    messages.success(request, 'Preguntas subidas correctamente desde el archivo CSV.')
                elif file.name.endswith('.json'):
                    data = json.loads(file.read().decode('utf-8'))
                    for item in data:
                        Question.objects.create(
                            contenido=default_contenido,
                            subject=item['subject'],
                            question_text=item['question_text'],
                            answer_text=item['answer_text'],
                            topic=item['topic'],
                            subtopic=item['subtopic'],
                            source_page=int(item['source_page']),
                            chapter=item['chapter'],
                        )
                    messages.success(request, 'Preguntas subidas correctamente desde el archivo JSON.')
                elif file.name.endswith('.txt'):
                    lines = file.read().decode('utf-8').splitlines()
                    question_data = {}
                    for line in lines:
                        if line.strip():
                            key, value = line.split(':', 1)
                            question_data[key.strip().lower()] = value.strip()
                        else:
                            Question.objects.create(
                                contenido=default_contenido,
                                subject=question_data.get('subject', ''),
                                question_text=question_data.get('pregunta', ''),
                                answer_text=question_data.get('respuesta', ''),
                                topic=question_data.get('tema', ''),
                                subtopic=question_data.get('subtema', ''),
                                source_page=int(question_data.get('página', 0)),
                                chapter=question_data.get('capítulo', ''),
                            )
                            question_data = {}
                    if question_data:
                        Question.objects.create(
                            contenido=default_contenido,
                            subject=question_data.get('subject', ''),
                            question_text=question_data.get('pregunta', ''),
                            answer_text=question_data.get('respuesta', ''),
                            topic=question_data.get('tema', ''),
                            subtopic=question_data.get('subtema', ''),
                            source_page=int(question_data.get('página', 0)),
                            chapter=question_data.get('capítulo', ''),
                        )
                    messages.success(request, 'Preguntas subidas correctamente desde el archivo TXT.')
                else:
                    messages.error(request, 'Formato de archivo no soportado.')
            else:
                grid_data = request.POST.get('grid_data')
                if grid_data:
                    data = json.loads(grid_data)
                    for item in data:
                        Question.objects.create(
                            contenido=default_contenido,
                            subject=item['subject'],
                            question_text=item['question_text'],
                            answer_text=item['answer_text'],
                            topic=item['topic'],
                            subtopic=item['subtopic'],
                            source_page=int(item['source_page']),
                            chapter=item['chapter'],
                        )
                    messages.success(request, 'Preguntas subidas correctamente desde la grilla.')
            return redirect('material:upload_questions')
    else:
        form = QuestionForm()
    return render(request, 'material/upload_questions.html', {'form': form})

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
    outcomes = LearningOutcome.objects.all()
    if request.method == 'POST':
        form = LearningOutcomeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Resultado de aprendizaje guardado correctamente.')
            return redirect('material:manage_learning_outcomes')
    else:
        form = LearningOutcomeForm()
    return render(request, 'material/manage_learning_outcomes.html', {
        'outcomes': outcomes,
        'form': form
    })

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
def list_institutions_v2(request):
    institutions = InstitutionV2.objects.filter(
        userinstitution__user=request.user, is_active=True
    ).prefetch_related('campusv2_set', 'facultyv2_set').order_by('name') # Añadir prefetch_related
    return render(request, 'material/institutions_v2/list.html', {'institutions': institutions})

@login_required
def create_institution_v2(request):
    if request.method == 'POST':
        form = InstitutionV2Form(request.POST, request.FILES)
        if form.is_valid():
            institution = form.save(commit=False)
            institution.save()
            UserInstitution.objects.create(user=request.user, institution=institution)

            campuses_data = request.POST.getlist('campuses[]')
            if campuses_data:
                for campus_name in campuses_data:
                    if campus_name.strip():
                        CampusV2.objects.create(institution=institution, name=campus_name.strip())

            faculty_names = request.POST.getlist('faculty_names[]')
            faculty_codes = request.POST.getlist('faculty_codes[]')
            if faculty_names:
                for i in range(len(faculty_names)):
                    if faculty_names[i].strip():
                        FacultyV2.objects.create(
                            institution=institution,
                            name=faculty_names[i].strip(),
                            code=faculty_codes[i].strip()
                        )

            messages.success(request, 'Institución creada con éxito.')
            return redirect('material:list_institutions_v2')
        else:
            messages.error(request, 'Por favor, corrija los errores del formulario.')
    else:
        form = InstitutionV2Form()
    return render(request, 'material/institutions_v2/create.html', {'form': form})

@login_required
def institution_v2_detail(request, pk):
    institution = get_object_or_404(
        InstitutionV2.objects.prefetch_related(
            Prefetch('campusv2_set', queryset=CampusV2.objects.filter(is_active=True), to_attr='active_campuses'),
            Prefetch('facultyv2_set', queryset=FacultyV2.objects.filter(is_active=True), to_attr='active_faculties')
        ),
        pk=pk,
        userinstitution__user=request.user
    )
    return render(request, 'material/institutions_v2/detail.html', {
        'institution': institution,
        'is_favorite': institution.userinstitution_set.filter(
            user=request.user,
            is_favorite=True
        ).exists(),
        'campuses': institution.active_campuses,
        'faculties': institution.active_faculties,
    })

@login_required
@transaction.atomic
def edit_institution_v2(request, pk):
    institution = get_object_or_404(InstitutionV2, pk=pk, userinstitution__user=request.user)

    if request.method == 'POST':
        form = InstitutionV2Form(request.POST, request.FILES, instance=institution)
        if form.is_valid():
            form.save()

            # Manejar sedes
            existing_campus_ids = set(request.POST.getlist('campus_ids'))
            existing_campuses = {c.id: c for c in institution.campusv2_set.all()}

            for campus_id, campus_name in zip(request.POST.getlist('campus_ids'), request.POST.getlist('campus_names')):
                campus_id = int(campus_id)
                if campus_id in existing_campuses:
                    campus = existing_campuses[campus_id]
                    campus.name = campus_name
                    campus.is_active = True  # Reactivar si es necesario
                    campus.save()
                    existing_campuses.pop(campus_id)  # Eliminar del diccionario
                else:
                    CampusV2.objects.create(institution=institution, name=campus_name, is_active=True)

            # Desactivar sedes eliminadas
            for campus in existing_campuses.values():
                campus.is_active = False
                campus.save()

            # Manejar facultades
            existing_faculty_ids = set(request.POST.getlist('faculty_ids'))
            existing_faculties = {f.id: f for f in institution.facultyv2_set.all()}

            for faculty_id, faculty_name, faculty_code in zip(
                request.POST.getlist('faculty_ids'),
                request.POST.getlist('faculty_names'),
                request.POST.getlist('faculty_codes')
            ):
                faculty_id = int(faculty_id)
                if faculty_id in existing_faculties:
                    faculty = existing_faculties[faculty_id]
                    faculty.name = faculty_name
                    faculty.code = faculty_code
                    faculty.is_active = True  # Reactivar si es necesario
                    faculty.save()
                    existing_faculties.pop(faculty_id)
                else:
                    FacultyV2.objects.create(institution=institution, name=faculty_name, code=faculty_code, is_active=True)

            # Desactivar facultades eliminadas
            for faculty in existing_faculties.values():
                faculty.is_active = False
                faculty.save()

            # Manejar nuevas sedes
            for campus_name in request.POST.getlist('new_campuses'):
                if campus_name:
                    CampusV2.objects.create(institution=institution, name=campus_name, is_active=True)

            # Manejar nuevas facultades
            for faculty_name, faculty_code in zip(request.POST.getlist('new_faculty_names'), request.POST.getlist('new_faculty_codes')):
                if faculty_name:
                    FacultyV2.objects.create(institution=institution, name=faculty_name, code=faculty_code, is_active=True)

            return redirect('material:institution_v2_detail', pk=institution.pk)
    else:
        form = InstitutionV2Form(instance=institution)

    return render(request, 'material/institutions_v2/edit.html', {'form': form, 'institution': institution})

@login_required
def delete_institution_v2(request, pk):
    institution = get_object_or_404(InstitutionV2, pk=pk, userinstitution__user=request.user)
    if request.method == 'POST':
        institution.is_active = False
        institution.save()
        messages.success(request, 'Institución eliminada con éxito.')
        return redirect('material:list_institutions_v2')
    return render(request, 'material/institutions_v2/confirm_delete.html', {'institution': institution})

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
def create_campus_v2(request, institution_id):
    institution = get_object_or_404(InstitutionV2, pk=institution_id, userinstitution__user=request.user)
    if request.method == 'POST':
        form = CampusV2Form(request.POST)
        if form.is_valid():
            campus = form.save(commit=False)
            campus.institution = institution
            campus.save()
            return redirect('material:institution_v2_detail', pk=institution.pk)
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
            return redirect('material:institution_v2_detail', pk=institution.pk)
    else:
        form = FacultyV2Form()
    return render(request, 'material/faculties_v2/create.html', {'form': form, 'institution': institution})

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

# Agregar al final de views.py
@login_required
def count_favorite_institutions(request):
    count = UserInstitution.objects.filter(
        user=request.user,
        is_favorite=True
    ).count()
    return JsonResponse({'count': count})
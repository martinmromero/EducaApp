# Standard library imports
import csv
import json
import logging

# Django core imports
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
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
from .ia_processor import extract_text_from_file, generate_questions_from_text

from .forms import InstitutionForm, LearningOutcomeForm, ProfileForm

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
@transaction.atomic
def manage_institutions(request):
    """
    Vista principal para gestionar instituciones
    """
    try:
        institutions = Institution.objects.filter(owner=request.user).prefetch_related('campus_set', 'faculty_set')
        
        if request.method == 'POST':
            form = InstitutionForm(request.POST, request.FILES)
            
            if form.is_valid():
                try:
                    institution = form.save(commit=False)
                    institution.owner = request.user
                    institution.save()
                    
                    # Procesar sedes
                    campuses = request.POST.getlist('campuses', [])
                    campus_ids = request.POST.getlist('campus_ids', [])
                    
                    current_campus_ids = []
                    for campus_name, campus_id in zip(campuses, campus_ids):
                        if campus_name.strip():
                            campus, _ = Campus.objects.update_or_create(
                                id=campus_id if campus_id else None,
                                defaults={
                                    'name': campus_name.strip(),
                                    'institution': institution
                                }
                            )
                            current_campus_ids.append(campus.id)
                    
                    institution.campus_set.exclude(id__in=current_campus_ids).delete()
                    
                    # Procesar facultades
                    faculties = request.POST.getlist('faculties', [])
                    faculty_ids = request.POST.getlist('faculty_ids', [])
                    
                    current_faculty_ids = []
                    for faculty_name, faculty_id in zip(faculties, faculty_ids):
                        if faculty_name.strip():
                            faculty, _ = Faculty.objects.update_or_create(
                                id=faculty_id if faculty_id else None,
                                defaults={
                                    'name': faculty_name.strip(),
                                    'institution': institution
                                }
                            )
                            current_faculty_ids.append(faculty.id)
                    
                    institution.faculty_set.exclude(id__in=current_faculty_ids).delete()
                    
                    messages.success(request, 'Institución guardada correctamente!')
                    return redirect('material:manage_institutions')
                
                except Exception as e:
                    logger.error(f"Error al guardar: {str(e)}", exc_info=True)
                    messages.error(request, 'Error al procesar los datos')
            else:
                error_msg = "Errores en el formulario:<br>" + "<br>".join(
                    [f"{field}: {', '.join(errors)}" 
                     for field, errors in form.errors.items()]
                )
                messages.error(request, error_msg)
        else:
            form = InstitutionForm()
        
        return render(request, 'material/manage_institutions.html', {
            'form': form,
            'institutions': institutions or []
        })
    
    except Exception as e:
        logger.critical(f"Error inesperado: {str(e)}", exc_info=True)
        messages.error(request, 'Error del sistema')
        return redirect('material:index')
    
    
@login_required
def edit_institution(request, pk):
    """
    Vista para editar una institución existente
    """
    institution = get_object_or_404(Institution, pk=pk, owner=request.user)
    if request.method == 'POST':
        form = InstitutionForm(request.POST, request.FILES, instance=institution)
        if form.is_valid():
            form.save()
            messages.success(request, 'Institución actualizada correctamente')
            return redirect('material:manage_institutions')
    else:
        form = InstitutionForm(instance=institution)
    
    return render(request, 'material/manage_institutions.html', {
        'form': form,
        'institutions': Institution.objects.filter(owner=request.user)
    })

@login_required
def delete_institution(request, pk):
    """
    Vista para eliminar una institución
    """
    institution = get_object_or_404(Institution, pk=pk, owner=request.user)
    if request.method == 'POST':
        institution.delete()
        messages.success(request, 'Institución eliminada correctamente')
        return redirect('material:manage_institutions')
    
    return render(request, 'material/confirm_delete.html', {
        'object': institution,
        'back_url': 'material:manage_institutions'
    })
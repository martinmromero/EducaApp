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
from django.db import models
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

# Local application imports
from .forms import (
    CustomLoginForm,
    ExamForm,
    ExamTemplateForm,
    MaterialForm,
    QuestionForm,
    UserEditForm
)
from .ia_processor import extract_text_from_file, generate_questions_from_text
from .models import Exam, ExamTemplate, Material, Profile, Question, Subject,Topic, Subtopic





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

@login_required
def index(request):
    context = {
        'is_admin': is_admin(request.user)
    }
    return render(request, 'material/index.html', context)

@login_required
def upload_material(request):
    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.uploaded_by = request.user
            material.save()
            messages.success(request, 'Los archivos se subieron correctamente.')
            return redirect('material:mis_materiales')
    else:
        form = MaterialForm()
    return render(request, 'material/upload.html', {'form': form})

@login_required
def generate_questions(request, material_id):
    material = Material.objects.get(id=material_id)
    num_questions = int(request.POST.get('num_questions', 20))
    try:
        text = extract_text_from_file(material.file.path)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('material:mis_materiales')
    questions_text = generate_questions_from_text(text, num_questions)
    request.session['generated_questions'] = questions_text.split('\n')
    return redirect('material:review_questions', material_id=material.id)

@login_required
def review_questions(request, material_id):
    material = Material.objects.get(id=material_id)
    questions_list = request.session.get('generated_questions', [])
    return render(request, 'material/review_questions.html', {
        'material': material,
        'questions': questions_list
    })

@login_required
def save_selected_questions(request, material_id):
    if request.method == 'POST':
        material = Material.objects.get(id=material_id)
        selected_questions = request.POST.getlist('selected_questions')
        questions_list = request.session.get('generated_questions', [])
        for i, question in enumerate(questions_list):
            if str(i) in selected_questions:
                Question.objects.create(
                    material=material,
                    subject="Tema generado por IA",
                    question_text=question,
                    answer_text="Respuesta generada por IA",
                    topic="Tema generado por IA",
                    subtopic="Subtema generado por IA",
                    source_page=1
                )
        if 'generated_questions' in request.session:
            del request.session['generated_questions']
        messages.success(request, 'Preguntas seleccionadas guardadas correctamente.')
        return redirect('material:mis_preguntas')
    return redirect('material:review_questions', material_id=material_id)

@login_required
def create_exam(request):
    questions = Question.objects.all()
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.save()
            exam.questions.set(request.POST.getlist('questions'))
            return redirect('material:index')
    else:
        form = ExamForm()
    return render(request, 'material/create_exam.html', {'form': form, 'questions': questions})

@login_required
def create_exam_template(request):
    if request.method == 'POST':
        form = ExamTemplateForm(request.POST, request.FILES)
        if form.is_valid():
            exam_template = form.save(commit=False)
            exam_template.created_by = request.user
            exam_template.save()
            messages.success(request, 'La plantilla de examen se ha creado correctamente.')
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

class CustomLoginView(LoginView):
    form_class = CustomLoginForm
    template_name = 'registration/login.html'

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
                update_session_auth_hash(request, user)
                messages.success(request, 'Sus cambios fueron guardados.')
            else:
                messages.info(request, 'No se realizaron cambios.')
            return redirect('material:mis_datos')
    else:
        form = UserEditForm(instance=user)
    return render(request, 'material/mis_datos.html', {'form': form, 'is_admin': is_admin(request.user)})

@login_required
def mis_examenes(request):
    examenes = Exam.objects.filter(created_by=request.user)
    return render(request, 'material/mis_examenes.html', {'examenes': examenes})

@login_required
def lista_preguntas(request):
    # Query base
    preguntas = Question.objects.filter(
        models.Q(material__uploaded_by=request.user) | 
        models.Q(user=request.user)
    ).select_related('subject', 'topic', 'subtopic')

    # Filtros con validación
    subject_id = request.GET.get('subject', '')
    topic_id = request.GET.get('topic', '')
    subtopic_id = request.GET.get('subtopic', '')

    # Aplicar filtros solo si tienen valor numérico
    if subject_id.isdigit():
        preguntas = preguntas.filter(subject_id=int(subject_id))
    if topic_id.isdigit():
        preguntas = preguntas.filter(topic_id=int(topic_id))
    if subtopic_id.isdigit():
        preguntas = preguntas.filter(subtopic_id=int(subtopic_id))

    # Obtener opciones para dropdowns
    subjects = Subject.objects.filter(
        question__in=preguntas
    ).distinct().order_by('Nombre')

    topics = Topic.objects.filter(
        subject__question__in=preguntas
    ).distinct().order_by('name') if subject_id.isdigit() else Topic.objects.none()

    subtopics = Subtopic.objects.filter(
        topic__subject__question__in=preguntas
    ).distinct().order_by('name') if topic_id.isdigit() else Subtopic.objects.none()

    # Paginación
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
    pregunta = get_object_or_404(Question, pk=pk, material__uploaded_by=request.user)
    
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
    pregunta = get_object_or_404(Question, pk=pk, material__uploaded_by=request.user)
    
    if request.method == 'POST':
        pregunta.delete()
        messages.success(request, 'Pregunta eliminada correctamente')
        return redirect('material:lista_preguntas')
    
    return render(request, 'material/confirmar_eliminar.html', {
        'pregunta': pregunta
    })



@login_required
def mis_materiales(request):
    materiales = Material.objects.filter(uploaded_by=request.user)
    return render(request, 'material/mis_materiales.html', {'materiales': materiales})

@login_required
def delete_material(request):
    if request.method == 'POST':
        material_ids = request.POST.getlist('material_ids')
        if not material_ids:
            messages.error(request, 'No se seleccionó ningún documento para borrar.')
            return redirect('material:mis_materiales')
        materiales = Material.objects.filter(id__in=material_ids, uploaded_by=request.user)
        count = materiales.count()
        materiales.delete()
        if count == 1:
            messages.success(request, 'El documento ha sido borrado correctamente.')
        else:
            messages.success(request, f'Los {count} documentos han sido borrados correctamente.')
    return redirect('material:mis_materiales')

@login_required
def upload_questions(request):
    if request.method == 'POST':
        form = QuestionForm(request.POST, request.FILES)
        if form.is_valid():
            default_material, created = Material.objects.get_or_create(
                title="Material por Defecto",
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
                            material=default_material,
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
                            material=default_material,
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
                                material=default_material,
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
                            material=default_material,
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
                            material=default_material,
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
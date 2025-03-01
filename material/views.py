from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, update_session_auth_hash
from django.contrib import messages
from .models import Material, Question, Exam, Profile
from .forms import MaterialForm, ExamForm, UserEditForm, CustomLoginForm, QuestionForm
from .ia_processor import generate_questions_from_text, extract_text_from_file
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.http import HttpResponse
import csv
import json

# Función para verificar si el usuario es administrador
def is_admin(user):
    try:
        # Verificar si el usuario tiene un perfil y si su rol es 'admin'
        return user.profile.role == 'admin'
    except Profile.DoesNotExist:
        # Si el usuario no tiene perfil, no es administrador
        return False

@login_required
def index(request):
    # Pasar el valor de is_admin al contexto
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
    
    # Obtener el número de preguntas desde el formulario o usar 20 por defecto
    num_questions = int(request.POST.get('num_questions', 20))
    
    # Extraer texto del archivo
    try:
        text = extract_text_from_file(material.file.path)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('material:mis_materiales')
    
    # Generar preguntas y respuestas usando IA
    questions_text = generate_questions_from_text(text, num_questions)
    
    # Guardar las preguntas en la sesión para revisión
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
        
        # Guardar solo las preguntas seleccionadas
        for i, question in enumerate(questions_list):
            if str(i) in selected_questions:
                Question.objects.create(
                    material=material,
                    question_text=question,
                    answer_text="Respuesta generada por IA",
                    topic="Tema generado por IA",
                    subtopic="Subtema generado por IA",
                    source_page=1
                )
        
        # Limpiar la sesión
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
                # Guardar los cambios sin modificar el estado is_active
                user.username = form.cleaned_data['username']
                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                user.email = form.cleaned_data['email']
                user.save()
                update_session_auth_hash(request, user)  # Actualiza la sesión para evitar cierre de sesión
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
    preguntas = Question.objects.all()
    return render(request, 'material/lista_preguntas.html', {'preguntas': preguntas})

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
            upload_type = form.cleaned_data['upload_type']
            # Crear un material por defecto si no existe
            default_material, created = Material.objects.get_or_create(
                title="Material por Defecto",
                defaults={
                    'uploaded_by': request.user,
                }
            )
            if upload_type == QuestionForm.SINGLE:
                # Guardar una sola pregunta
                Question.objects.create(
                    material=default_material,
                    question_text=form.cleaned_data['question_text'],
                    answer_text=form.cleaned_data['answer_text'],
                    topic=form.cleaned_data['topic'],
                    subtopic=form.cleaned_data['subtopic'],
                    source_page=form.cleaned_data['source_page'],
                    chapter=form.cleaned_data['chapter'],
                )
                messages.success(request, 'Pregunta subida correctamente.')
            else:
                # Procesar archivo de múltiples preguntas
                if 'file' in request.FILES:
                    file = request.FILES['file']
                    if file.name.endswith('.csv'):
                        # Procesar CSV
                        decoded_file = file.read().decode('utf-8').splitlines()
                        reader = csv.DictReader(decoded_file)
                        for row in reader:
                            Question.objects.create(
                                material=default_material,
                                question_text=row['question_text'],
                                answer_text=row['answer_text'],
                                topic=row['topic'],
                                subtopic=row['subtopic'],
                                source_page=int(row['source_page']),
                                chapter=row['chapter'],
                            )
                        messages.success(request, 'Preguntas subidas correctamente desde el archivo CSV.')
                    elif file.name.endswith('.json'):
                        # Procesar JSON
                        data = json.loads(file.read().decode('utf-8'))
                        for item in data:
                            Question.objects.create(
                                material=default_material,
                                question_text=item['question_text'],
                                answer_text=item['answer_text'],
                                topic=item['topic'],
                                subtopic=item['subtopic'],
                                source_page=int(item['source_page']),
                                chapter=item['chapter'],
                            )
                        messages.success(request, 'Preguntas subidas correctamente desde el archivo JSON.')
                    elif file.name.endswith('.txt'):
                        # Procesar TXT
                        lines = file.read().decode('utf-8').splitlines()
                        question_data = {}
                        for line in lines:
                            if line.strip():
                                key, value = line.split(':', 1)
                                question_data[key.strip().lower()] = value.strip()
                            else:
                                # Guardar la pregunta cuando se encuentra una línea vacía
                                Question.objects.create(
                                    material=default_material,
                                    question_text=question_data.get('pregunta', ''),
                                    answer_text=question_data.get('respuesta', ''),
                                    topic=question_data.get('tema', ''),
                                    subtopic=question_data.get('subtema', ''),
                                    source_page=int(question_data.get('página', 0)),
                                    chapter=question_data.get('capítulo', ''),
                                )
                                question_data = {}  # Reiniciar para la siguiente pregunta
                        # Guardar la última pregunta si no hay una línea vacía al final
                        if question_data:
                            Question.objects.create(
                                material=default_material,
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
                    # Procesar datos de la grilla
                    grid_data = request.POST.get('grid_data')
                    if grid_data:
                        data = json.loads(grid_data)
                        for item in data:
                            Question.objects.create(
                                material=default_material,
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

# Nueva vista para descargar plantillas
def download_template(request, format):
    if format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="template.csv"'
        writer = csv.writer(response)
        writer.writerow(['question_text', 'answer_text', 'topic', 'subtopic', 'source_page', 'chapter'])
        writer.writerow(['¿Cuál es la capital de Francia?', 'París', 'Geografía', 'Capitales', 1, 'Capítulo 1: Introducción'])
        writer.writerow(['¿Quién escribió "Cien años de soledad"?', 'Gabriel García Márquez', 'Literatura', 'Autores', 2, 'Capítulo 2: Literatura Latinoamericana'])
        return response
    elif format == 'json':
        data = [
            {
                "question_text": "¿Cuál es la capital de Francia?",
                "answer_text": "París",
                "topic": "Geografía",
                "subtopic": "Capitales",
                "source_page": 1,
                "chapter": "Capítulo 1: Introducción"
            },
            {
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
        content = """Pregunta: ¿Cuál es la capital de Francia?
Respuesta: París
Tema: Geografía
Subtema: Capitales
Página: 1
Capítulo: Capítulo 1: Introducción

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
from django import forms
from django.contrib.auth.models import User
from .models import Contenido, Question, Exam, Profile, ExamTemplate
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

class ContenidoForm(forms.ModelForm):
    file = forms.FileField(widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))
    subject = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Subject"
    )

    class Meta:
        model = Contenido
        fields = ['subject', 'title', 'file']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': 'Título del Contenido',
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['subject', 'topic', 'subtopic', 'question_text', 'answer_text', 'source_page', 'chapter']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Matemáticas'}),
            'topic': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Álgebra'}),
            'subtopic': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Ecuaciones cuadráticas'}),
            'question_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Texto de la pregunta'}),
            'answer_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Texto de la respuesta'}),
            'source_page': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Número de página'}),
            'chapter': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Capítulo o sección'}),
        }
        labels = {
            'subject': 'Subject',
            'topic': 'Tema',
            'subtopic': 'Subtema',
            'question_text': 'Pregunta',
            'answer_text': 'Respuesta',
            'source_page': 'Página de referencia',
            'chapter': 'Capítulo',
        }

class ExamForm(forms.ModelForm):
    subject = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label="Subject"
    )

    class Meta:
        model = Exam
        fields = ['subject', 'title', 'topics', 'questions']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'topics': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'questions': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

class ExamTemplateForm(forms.ModelForm):
    class Meta:
        model = ExamTemplate
        fields = [
            'institution_logo', 'institution_name', 'career_name', 'subject_name',
            'professor_name', 'year', 'exam_type', 'exam_mode',
            'notes_and_recommendations', 'topics_to_evaluate'
        ]
        widgets = {
            'institution_name': forms.TextInput(attrs={'class': 'form-control'}),
            'career_name': forms.TextInput(attrs={'class': 'form-control'}),
            'subject_name': forms.TextInput(attrs={'class': 'form-control'}),
            'professor_name': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'exam_type': forms.Select(attrs={'class': 'form-control'}),
            'exam_mode': forms.Select(attrs={'class': 'form-control'}),
            'notes_and_recommendations': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'topics_to_evaluate': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class UserEditForm(forms.ModelForm):
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, label="Rol", widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'role']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile'):
            self.initial['role'] = self.instance.profile.role

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            if hasattr(user, 'profile'):
                user.profile.role = self.cleaned_data['role']
                user.profile.save()
        return user

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Usuario'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'})
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username is not None and password:
            try:
                user = User.objects.get(username=username)
                if not user.is_active:
                    raise ValidationError("El usuario está desactivado. Contacta al administrador.")
            except User.DoesNotExist:
                pass
        return cleaned_data

class BulkQuestionUploadForm(forms.Form):
    UPLOAD_TYPE_CHOICES = [
        ('csv', 'Archivo CSV'),
        ('json', 'Archivo JSON'),
    ]
    
    upload_type = forms.ChoiceField(
        choices=UPLOAD_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='csv',
        label="Formato del archivo"
    )
    file = forms.FileField(
        label="Archivo de preguntas",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        help_text="Formatos soportados: CSV o JSON. Estructura requerida: subject, topic, subtopic, question_text, answer_text, source_page, chapter"
    )
    contenido = forms.ModelChoiceField(
        queryset=Contenido.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Contenido asociado",
        required=False
    )

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            ext = file.name.split('.')[-1].lower()
            if ext not in ['csv', 'json']:
                raise ValidationError("Solo se permiten archivos CSV o JSON.")
        return file
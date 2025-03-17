from django import forms
from django.contrib.auth.models import User
from .models import Material, Question, Exam, Profile, ExamTemplate
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

class MaterialForm(forms.ModelForm):
    file = forms.FileField(widget=forms.ClearableFileInput())

    class Meta:
        model = Material
        fields = ['title', 'file']
        widgets = {
            'title': forms.TextInput(attrs={'required': False}),
        }

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['title', 'topics', 'questions']

class ExamTemplateForm(forms.ModelForm):
    class Meta:
        model = ExamTemplate
        fields = [
            'institution_logo', 'institution_name', 'career_name', 'subject_name', 
            'professor_name', 'year', 'exam_type', 'exam_mode', 
            'notes_and_recommendations', 'topics_to_evaluate'
        ]
        widgets = {
            'notes_and_recommendations': forms.Textarea(attrs={'rows': 4}),
            'topics_to_evaluate': forms.Textarea(attrs={'rows': 4}),
        }

class UserEditForm(forms.ModelForm):
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, label="Rol")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'role']

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
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            try:
                user = User.objects.get(username=username)
                if not user.is_active:
                    raise ValidationError("El usuario está desactivado. Póngase en contacto con su administrador.")
            except User.DoesNotExist:
                pass

        return super().clean()

class QuestionForm(forms.Form):
    SINGLE = 'single'
    MULTIPLE = 'multiple'
    UPLOAD_TYPE_CHOICES = [
        (SINGLE, 'Subir una sola pregunta'),
        (MULTIPLE, 'Subir múltiples preguntas (CSV, JSON o TXT)'),
    ]

    upload_type = forms.ChoiceField(
        choices=UPLOAD_TYPE_CHOICES,
        widget=forms.RadioSelect,
        initial=SINGLE,
        label="Tipo de subida"
    )

    question_text = forms.CharField(
        label="Texto de la pregunta",
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False
    )
    answer_text = forms.CharField(
        label="Texto de la respuesta",
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False
    )
    topic = forms.CharField(
        label="Tema",
        max_length=255,
        required=False
    )
    subtopic = forms.CharField(
        label="Subtema",
        max_length=255,
        required=False
    )
    source_page = forms.IntegerField(
        label="Página de referencia",
        required=False
    )
    chapter = forms.CharField(
        label="Capítulo",
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False
    )

    file = forms.FileField(
        label="Archivo de preguntas (CSV, JSON o TXT)",
        required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        upload_type = cleaned_data.get('upload_type')
        file = cleaned_data.get('file')

        if upload_type == self.SINGLE:
            if not all([
                cleaned_data.get('question_text'),
                cleaned_data.get('answer_text'),
                cleaned_data.get('topic'),
                cleaned_data.get('subtopic'),
                cleaned_data.get('source_page'),
                cleaned_data.get('chapter'),
            ]):
                raise ValidationError("Todos los campos son obligatorios para subir una sola pregunta.")
        elif upload_type == self.MULTIPLE:
            if not file:
                raise ValidationError("Debes subir un archivo para cargar múltiples preguntas.")
            if not file.name.endswith(('.csv', '.json', '.txt')):
                raise ValidationError("El archivo debe ser un CSV, JSON o TXT.")

        return cleaned_data
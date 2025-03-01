from django import forms
from django.contrib.auth.models import User
from .models import Material, Question, Exam, Profile
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

class MaterialForm(forms.ModelForm):
    file = forms.FileField(widget=forms.ClearableFileInput())  # Permitir un solo archivo

    class Meta:
        model = Material
        fields = ['title', 'file']
        widgets = {
            'title': forms.TextInput(attrs={'required': False}),  # Hacemos que el campo no sea obligatorio
        }

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['title', 'topics', 'questions']

class UserEditForm(forms.ModelForm):
    # Campo para el rol del usuario
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, label="Rol")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'role']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Establecer el valor inicial del campo 'role' desde el perfil del usuario
        if self.instance and hasattr(self.instance, 'profile'):
            self.initial['role'] = self.instance.profile.role

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Guardar el rol en el perfil del usuario
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
                # Si el usuario no existe, dejamos que el formulario de autenticación maneje el error
                pass

        # Llamamos al método clean de la clase padre para realizar la autenticación
        return super().clean()

# Nuevo formulario para subir preguntas
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

    # Campos para subir una sola pregunta
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

    # Campo para subir múltiples preguntas
    file = forms.FileField(
        label="Archivo de preguntas (CSV, JSON o TXT)",
        required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        upload_type = cleaned_data.get('upload_type')
        file = cleaned_data.get('file')

        if upload_type == self.SINGLE:
            # Validar que los campos de una sola pregunta estén completos
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
            # Validar que se haya subido un archivo
            if not file:
                raise ValidationError("Debes subir un archivo para cargar múltiples preguntas.")
            # Validar el tipo de archivo
            if not file.name.endswith(('.csv', '.json', '.txt')):
                raise ValidationError("El archivo debe ser un CSV, JSON o TXT.")

        return cleaned_data
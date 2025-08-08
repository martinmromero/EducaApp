from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from .models import (
    Contenido, Question, Exam, ExamTemplate, Profile,
    Subject, Topic, Subtopic, Institution, LearningOutcome, Campus, Faculty, User,
    InstitutionV2, CampusV2, FacultyV2, Career, InstitutionCareer, CareerSubject, UserInstitution
)
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution
        fields = ['name', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'required': 'required',
                'minlength': '3'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.jpg,.jpeg,.png,.svg'
            })
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if len(name) < 3:
            raise ValidationError("El nombre debe tener al menos 3 caracteres")
        return name

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        if logo:
            if logo.size > 2 * 1024 * 1024:
                raise ValidationError("El logo no debe exceder 2MB")
            if not logo.content_type in ['image/jpeg', 'image/png', 'image/svg+xml']:
                raise ValidationError("Formato de imagen no válido (solo JPG, PNG, SVG)")
        return logo

class CampusForm(forms.ModelForm):
    class Meta:
        model = Campus
        fields = ['name', 'address', 'institution']
        widgets = {
            'institution': forms.HiddenInput(),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'})
        }

class FacultyForm(forms.ModelForm):
    class Meta:
        model = Faculty
        fields = ['name', 'code', 'institution']
        widgets = {
            'institution': forms.HiddenInput(),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'})
        }

class LearningOutcomeForm(forms.ModelForm):
    class Meta:
        model = LearningOutcome
        fields = ['description']  # Eliminamos 'subject' de los fields
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'minlength': '10',
                'required': 'required',
                'placeholder': 'Descripción del resultado de aprendizaje...'
            })
        }
        labels = {
            'description': 'Descripción *'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Eliminamos la lógica relacionada con subject ya que no lo necesitamos en el form

    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        if len(description) < 10:
            raise ValidationError("La descripción debe tener al menos 10 caracteres")
        return description

class ContenidoForm(forms.ModelForm):
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Subject"
    )

    class Meta:
        model = Contenido
        fields = ['subject', 'title', 'file', 'isbn', 'edition', 'pages', 'publisher', 'year']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control'}),
            'edition': forms.TextInput(attrs={'class': 'form-control'}),
            'pages': forms.NumberInput(attrs={'class': 'form-control'}),
            'publisher': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': 'Título del Contenido',
        }

class QuestionForm(forms.ModelForm):
    topic = forms.ModelChoiceField(
        queryset=Topic.objects.none(),
        required=False,
        label="Tema Principal"
    )
    subtopic = forms.ModelChoiceField(
        queryset=Subtopic.objects.none(),
        required=False,
        label="Subtema"
    )

    class Meta:
        model = Question
        fields = ['subject', 'topic', 'subtopic', 'question_text', 'answer_text', 
                 'question_image', 'answer_image', 'unit', 'reference_book', 
                 'source_page', 'chapter']  # Eliminado 'file' y agregados campos correctos

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subject'].queryset = Subject.objects.all()
        
        if 'subject' in self.data:
            try:
                subject_id = int(self.data.get('subject'))
                self.fields['topic'].queryset = Topic.objects.filter(subject_id=subject_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['topic'].queryset = self.instance.subject.topic_set.all()

        if 'topic' in self.data:
            try:
                topic_id = int(self.data.get('topic'))
                self.fields['subtopic'].queryset = Subtopic.objects.filter(topic_id=topic_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.topic:
            self.fields['subtopic'].queryset = self.instance.topic.subtopic_set.all()

class ExamForm(forms.ModelForm):
    learning_outcomes = forms.ModelMultipleChoiceField(
        queryset=LearningOutcome.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False,
        label="Resultados de aprendizaje"
    )

    class Meta:
        model = Exam
        fields = ['title', 'subject', 'topics', 'questions', 'learning_outcomes',
                 'instructions', 'duration_minutes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'topics': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'questions': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'subject' in self.data:
            try:
                subject_id = int(self.data.get('subject'))
                self.fields['topics'].queryset = Topic.objects.filter(subject_id=subject_id)
                self.fields['learning_outcomes'].queryset = LearningOutcome.objects.filter(subject_id=subject_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['topics'].queryset = self.instance.subject.topic_set.all()
            self.fields['learning_outcomes'].queryset = LearningOutcome.objects.filter(subject=self.instance.subject)

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['role', 'institutions']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'institutions': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

class ExamTemplateForm(forms.ModelForm):
    class Meta:
        model = ExamTemplate
        exclude = ['exam_group']
        fields = [
            'institution', 'faculty', 'career', 'subject', 'campus', 'professor',
            'exam_mode', 'exam_group', 'shift',
            'learning_outcomes', 'notes_and_recommendations', 'topics_to_evaluate'
        ]
        widgets = {
            'learning_outcomes': forms.CheckboxSelectMultiple(
                attrs={'class': 'learning-outcomes-checkbox'}
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['institution'].queryset = InstitutionV2.objects.filter(
                userinstitution__user=user, 
                is_active=True
            )
        else:
            self.fields['institution'].queryset = InstitutionV2.objects.none()

        self.fields['faculty'].queryset = FacultyV2.objects.none()
        self.fields['campus'].queryset = CampusV2.objects.none()
        self.fields['professor'].queryset = User.objects.filter(is_active=True)
        self.fields['professor'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name} ({obj.username})"
        
        # Configurar outcomes basado en la materia seleccionada
        if 'subject' in self.data:
            try:
                subject_id = int(self.data.get('subject'))
                self.fields['learning_outcomes'].queryset = LearningOutcome.objects.filter(
                    subject_id=subject_id
                )
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.subject:
            self.fields['learning_outcomes'].queryset = LearningOutcome.objects.filter(
                subject=self.instance.subject
            )

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError(
                "Cuenta inactiva. Contacta al administrador.",
                code='inactive',
            )

class UserEditForm(forms.ModelForm):
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, label="Rol",
                            widget=forms.Select(attrs={'class': 'form-control'}))
    institutions = forms.ModelMultipleChoiceField(
        queryset=Institution.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'role', 'institutions']
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
            self.initial['institutions'] = self.instance.profile.institutions.all()

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            if hasattr(user, 'profile'):
                user.profile.role = self.cleaned_data['role']
                user.profile.save()
                user.profile.institutions.set(self.cleaned_data['institutions'])
        return user

class InstitutionV2Form(forms.ModelForm):
    class Meta:
        model = InstitutionV2
        fields = ['name', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'required': 'required',
                'minlength': '2'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.jpg,.jpeg,.png,.svg'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['logo'].required = False

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:  # Valida None o cadena vacía
            raise ValidationError("El nombre de la institución es obligatorio")
        
        name = name.strip()
        if len(name) < 2:
            raise ValidationError("El nombre debe tener al menos 2 caracteres")
        
        # Validación adicional para nombres duplicados
        if InstitutionV2.objects.filter(name__iexact=name).exclude(pk=getattr(self.instance, 'pk', None)).exists():
            raise ValidationError("Ya existe una institución con este nombre")
            
        return name

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')

        # Validación solo si hay un logo nuevo
        if logo and hasattr(logo, 'content_type'):
            # Validar tamaño (2MB máximo)
            if logo.size > 2 * 1024 * 1024:
                raise ValidationError("El logo no debe exceder 2MB")

            # Validar tipo de archivo
            valid_types = ['image/jpeg', 'image/png', 'image/svg+xml']
            if logo.content_type not in valid_types:
                raise ValidationError("Adjunte una imagen válida (JPG, PNG o SVG)")

        return logo

class CampusV2Form(forms.ModelForm):
    class Meta:
        model = CampusV2
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Sede Central',
                'minlength': '2',
                'maxlength': '255'
            })
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 2:
            raise ValidationError("El nombre debe tener al menos 2 caracteres")
        if len(name) > 255:
            raise ValidationError("El nombre no puede exceder 255 caracteres")
        return name

class FacultyV2Form(forms.ModelForm):
    class Meta:
        model = FacultyV2
        fields = ['name']  # Elimina 'code' de la lista de campos
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Facultad de Ingeniería',
                'minlength': '2',
                'maxlength': '255'
            })
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 2:
            raise ValidationError("El nombre debe tener al menos 2 caracteres")
        if len(name) > 255:
            raise ValidationError("El nombre no puede exceder 255 caracteres")
        return name
    
    # Elimina el método clean_code() completo

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la materia',
                'required': 'required'
            })
        }
        labels = {
            'name': 'Nombre de la materia *'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = "Nombre de la materia *"

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name or len(name.strip()) < 3:
            raise ValidationError("El nombre debe tener al menos 3 caracteres")
        return name.strip()

    # Eliminamos el método clean() que validaba min_outcomes

class CareerForm(forms.ModelForm):
    class Meta:
        model = Career
        fields = ['name', 'faculties', 'campus', 'subjects']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'faculties': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'campus': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'subjects': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }

class InstitutionCareerForm(forms.ModelForm):
    class Meta:
        model = InstitutionCareer
        fields = ['institution', 'career']

class CareerSimpleForm(forms.ModelForm):
    class Meta:
        model = Career
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la carrera'
            })
        }
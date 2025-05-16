from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from .models import InstitutionV2 
from .models import (
    Contenido, Question, Exam, ExamTemplate, Profile,
    Subject, Topic, Subtopic , Institution, LearningOutcome, Campus, Faculty,InstitutionV2,
    CampusV2,FacultyV2,UserInstitution
)

from django import forms  
from .models import Institution, Campus, Faculty  

from django import forms
from .models import Institution
from django.core.exceptions import ValidationError
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
        if logo:  # Solo validar si hay logo (campo opcional)
            if logo.size > 2 * 1024 * 1024:
                raise ValidationError("El logo no debe exceder 2MB")
            if not logo.content_type in ['image/jpeg', 'image/png', 'image/svg+xml']:
                raise ValidationError("Formato de imagen no válido (solo JPG, PNG, SVG)")
        return logo  # Retorna None si no hay logo (válido)

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
        fields = '__all__'
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'level': forms.Select(attrs={'class': 'form-control'}),
        }

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
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'data-dark-mode': 'bg-dark text-light'
        }),
        required=True,
        label="Materia"
    )
    
    topic = forms.ModelChoiceField(
        queryset=Topic.objects.none(),  # Se actualiza dinámicamente via JS
        widget=forms.Select(attrs={
            'class': 'form-control',
            'data-dark-mode': 'bg-dark text-light'
        }),
        required=True,
        label="Tema principal"
    )
    
    subtopic = forms.ModelChoiceField(
        queryset=Subtopic.objects.none(),  # Se actualiza dinámicamente via JS
        widget=forms.Select(attrs={
            'class': 'form-control',
            'data-dark-mode': 'bg-dark text-light',
            'disabled': 'disabled'
        }),
        required=False,
        label="Subtema (opcional)"
    )

    question_image = forms.ImageField(
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control-file',
            'accept': '.jpg,.jpeg,.png,.svg',
            'data-dark-mode': 'text-light'
        }),
        required=False,
        label="Imagen de la pregunta (opcional)"
    )

    answer_image = forms.ImageField(
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control-file',
            'accept': '.jpg,.jpeg,.png,.svg',
            'data-dark-mode': 'text-light'
        }),
        required=False,
        label="Imagen de la respuesta (opcional)"
    )

    class Meta:
        model = Question
        fields = [
            'subject', 'question_text', 'question_image',
            'answer_text', 'answer_image', 'topic', 'subtopic',
            'unit', 'reference_book', 'source_page', 'chapter'
        ]
        widgets = {
            'question_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'data-dark-mode': 'bg-dark text-light'
            }),
            'answer_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'data-dark-mode': 'bg-dark text-light'
            }),
            'unit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Unidad 3 - Álgebra',
                'data-dark-mode': 'bg-dark text-light'
            }),
            'reference_book': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Cálculo de Stewart - 8va Edición',
                'data-dark-mode': 'bg-dark text-light'
            }),
            'source_page': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 145',
                'data-dark-mode': 'bg-dark text-light'
            }),
            'chapter': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Capítulo 5 - Derivadas',
                'data-dark-mode': 'bg-dark text-light'
            }),
        }
        labels = {
            'unit': 'Unidad (opcional)',
            'reference_book': 'Libro o documento de referencia (opcional)',
            'source_page': 'Página de referencia (opcional)',
            'chapter': 'Capítulo (opcional)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Actualizar querysets si ya hay un subject/topic seleccionado
        if 'subject' in self.data:
            try:
                subject_id = int(self.data.get('subject'))
                self.fields['topic'].queryset = Topic.objects.filter(subject_id=subject_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['topic'].queryset = self.instance.subject.topic_set.all()
            if self.instance.topic:
                self.fields['subtopic'].queryset = self.instance.topic.subtopic_set.all()
                self.fields['subtopic'].widget.attrs.pop('disabled')

    def clean(self):
        cleaned_data = super().clean()
        
        # Validar imágenes
        for field in ['question_image', 'answer_image']:
            if file := cleaned_data.get(field):
                if not file.name.lower().endswith(('.jpg', '.jpeg', '.png', '.svg')):
                    self.add_error(field, 'Formato no soportado. Use JPG, PNG o SVG.')
        
        # Validar tema si subtema está presente
        if cleaned_data.get('subtopic') and not cleaned_data.get('topic'):
            self.add_error('topic', 'Seleccione un tema principal para asignar un subtema.')
        
        return cleaned_data

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

class ExamTemplateForm(forms.ModelForm):
    institution = forms.ModelChoiceField(
        queryset=Institution.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    professor = forms.ModelChoiceField(
        queryset=User.objects.filter(profile__role='admin'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    
    class Meta:
        model = ExamTemplate
        fields = [
            'institution', 'career_name', 'subject', 'professor',
            'year', 'exam_type', 'partial_number', 'exam_mode', 'exam_group',
            'campus', 'shift', 'resolution_time', 'topics_to_evaluate',
            'notes_and_recommendations', 'learning_outcomes'
        ]
        widgets = {
            'career_name': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'exam_type': forms.Select(attrs={'class': 'form-control'}),
            'partial_number': forms.Select(attrs={'class': 'form-control'}),
            'exam_mode': forms.Select(attrs={'class': 'form-control'}),
            'exam_group': forms.Select(attrs={'class': 'form-control'}),
            'campus': forms.TextInput(attrs={'class': 'form-control'}),
            'shift': forms.Select(attrs={'class': 'form-control'}),
            'resolution_time': forms.TextInput(attrs={'class': 'form-control'}),
            'topics_to_evaluate': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'notes_and_recommendations': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'learning_outcomes': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['role', 'institutions']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'institutions': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def confirm_login_allowed(self, user):
        """Solo verifica is_active, sin restricciones adicionales"""
        if not user.is_active:
            raise forms.ValidationError(
                "Cuenta inactiva. Contacta al administrador.",
                code='inactive',
            )

class UserEditForm(forms.ModelForm):
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, label="Rol", widget=forms.Select(attrs={'class': 'form-control'}))
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
    

    # material/forms.py - Agregar al final del archivo

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
        fields = ['name']  # Solo mostramos el nombre
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la sede',
                'required': False  # Hacer opcional
            })
        }

class FacultyV2Form(forms.ModelForm):
    class Meta:
        model = FacultyV2
        fields = ['name']  # Solo mostramos el nombre
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la facultad',
                'required': False  # Hacer opcional
            })
        }


class FavoriteInstitutionForm(forms.ModelForm):
    class Meta:
        model = InstitutionV2
        fields = ['is_favorite']
    class Meta:
        model = UserInstitution
        fields = ['is_favorite']
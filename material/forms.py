from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
import math
from .models import (
    Contenido, Question, Exam, ExamTemplate, Profile,
    Subject, Topic, Subtopic, Institution, LearningOutcome, Campus, Faculty, User,
    InstitutionV2, CampusV2, FacultyV2, Career, InstitutionCareer, CareerSubject, UserInstitution,
    OralExamSet
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
        fields = ['description']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
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

    # Eliminada la validación de longitud mínima para description

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
        required=True,
        label="Tema Principal"
    )
    subtopic = forms.ModelChoiceField(
        queryset=Subtopic.objects.none(),
        required=False,
        label="Subtema (opcional)"
    )

    class Meta:
        model = Question
        fields = ['subject', 'topic', 'subtopic', 'question_text', 'answer_text', 
                 'question_image', 'answer_image', 'contenido', 'source_page']
        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'answer_text': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'question_image': forms.FileInput(attrs={'class': 'form-control-file'}),
            'answer_image': forms.FileInput(attrs={'class': 'form-control-file'}),
            'source_page': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        
        self.fields['subject'].queryset = Subject.objects.all()
        self.fields['subject'].widget.attrs.update({'class': 'form-control'})
        
        self.fields['contenido'].queryset = Contenido.objects.filter(
            uploaded_by=self.current_user
        ) if self.current_user else Contenido.objects.none()
        self.fields['contenido'].widget.attrs.update({'class': 'form-control'})
        
        self.fields['topic'].widget.attrs.update({'class': 'form-control'})
        self.fields['subtopic'].widget.attrs.update({'class': 'form-control'})

        # Si ya hay una instancia, cargar los temas/subtemas correspondientes
        if self.instance.pk and self.instance.subject:
            self.fields['topic'].queryset = Topic.objects.filter(subject=self.instance.subject)
            if self.instance.topic:
                self.fields['subtopic'].queryset = Subtopic.objects.filter(topic=self.instance.topic)
        # Si hay datos en el POST, actualizar los querysets
        elif 'subject' in self.data:
            try:
                subject_id = int(self.data.get('subject'))
                self.fields['topic'].queryset = Topic.objects.filter(subject_id=subject_id)
                
                if 'topic' in self.data:
                    topic_id = int(self.data.get('topic'))
                    self.fields['subtopic'].queryset = Subtopic.objects.filter(topic_id=topic_id)
            except (ValueError, TypeError):
                pass
            
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
        fields = [
            'institution', 'faculty', 'career', 'subject', 'campus', 'professor',
            'resolution_time',
            'learning_outcomes', 'notes_and_recommendations', 'topics_to_evaluate'
        ]
        widgets = {
            'learning_outcomes': forms.CheckboxSelectMultiple(
                attrs={'class': 'learning-outcomes-checkbox'}
            ),
            'notes_and_recommendations': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'topics_to_evaluate': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
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
                            widget=forms.Select(attrs={'class': 'form-control'}), required=False)
    def clean(self):
        cleaned_data = super().clean()
        # Si el campo 'role' no viene en el POST, asignar el actual
        if not cleaned_data.get('role') and self.instance and hasattr(self.instance, 'profile'):
            cleaned_data['role'] = self.instance.profile.role
        return cleaned_data
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
        # Solo setear initial extra en GET (cuando no hay data)
        if not self.data and self.instance and hasattr(self.instance, 'profile'):
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

class OralExamForm(forms.ModelForm):
    topics = forms.ModelMultipleChoiceField(
        queryset=Topic.objects.none(),  # Se establecerá dinámicamente
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True,
        label='Temas a evaluar'
    )
    
    # Campos adicionales para la validación
    total_students = forms.IntegerField(
        label='Total de estudiantes',
        min_value=1,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 24',
            'id': 'id_total_students'
        }),
        help_text='Cantidad total de estudiantes que rendirán el examen'
    )
    
    class Meta:
        model = OralExamSet
        fields = ['name', 'subject', 'topics', 'total_students', 'questions_per_student', 'num_groups', 'students_per_group']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Examen Oral Final - Matemáticas'
            }),
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'num_groups': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '10'
            }),
            'students_per_group': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '20'
            }),
            'questions_per_student': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '10',
                'value': '3'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Guardar el usuario en initial para acceso posterior
        if self.user:
            if 'initial' not in kwargs:
                self.initial = {}
            self.initial['user'] = self.user
        
        # Filtrar materias por usuario
        if self.user:
            user_subjects = Subject.objects.filter(
                question__user=self.user
            ).distinct()
            self.fields['subject'].queryset = user_subjects
        
        # Si hay una materia seleccionada, mostrar sus temas
        if 'subject' in self.data:
            try:
                subject_id = int(self.data.get('subject'))
                self.fields['topics'].queryset = Topic.objects.filter(subject_id=subject_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['topics'].queryset = self.instance.subject.topics.all()
    
    def clean(self):
        cleaned_data = super().clean()
        total_students = cleaned_data.get('total_students')
        questions_per_student = cleaned_data.get('questions_per_student')
        num_groups = cleaned_data.get('num_groups')
        students_per_group = cleaned_data.get('students_per_group')
        topics = cleaned_data.get('topics')
        subject = cleaned_data.get('subject')
        
        if not all([total_students, questions_per_student, topics, subject]):
            return cleaned_data
        
        # Validar que el total de estudiantes sea lógico con la configuración de grupos
        if num_groups and students_per_group:
            calculated_total = num_groups * students_per_group
            # Permitir cierta flexibilidad: el cálculo puede ser mayor que el total (grupos no completos)
            # pero no debe ser menor (faltarían estudiantes)
            if calculated_total < total_students:
                raise ValidationError(
                    f'La configuración de grupos ({num_groups} × {students_per_group} = {calculated_total}) '
                    f'es insuficiente para {total_students} estudiantes. Aumente el número de grupos o estudiantes por grupo.'
                )
            
            # Si la diferencia es muy grande (más del 20%), dar una advertencia
            difference_percentage = ((calculated_total - total_students) / total_students) * 100
            if difference_percentage > 20:
                # Solo advertencia, no error
                import warnings
                warnings.warn(
                    f'La configuración genera {calculated_total - total_students} lugares vacíos '
                    f'({difference_percentage:.1f}% de espacios no utilizados)'
                )
        
        # Contar preguntas disponibles por subtema
        from collections import defaultdict
        from .models import Question
        
        user = self.initial.get('user') if hasattr(self, 'initial') else None
        available_questions = Question.objects.filter(
            subject=subject,
            topic__in=topics,
            user=user
        ).select_related('topic', 'subtopic')
        
        if not available_questions.exists():
            raise ValidationError('No hay preguntas disponibles para los temas seleccionados')
        
        # Agrupar por subtema
        subtopics_count = defaultdict(int)
        for question in available_questions:
            key = question.subtopic.id if question.subtopic else f"topic_{question.topic.id}"
            subtopics_count[key] += 1
        
        total_subtopics = len(subtopics_count)
        total_questions = available_questions.count()
        
        # Calcular grupos óptimos
        if students_per_group and questions_per_student:
            # Para evitar repeticiones, necesitamos al menos tantos subtemas como estudiantes por grupo
            max_students_per_group_by_subtopics = total_subtopics
            
            if students_per_group > max_students_per_group_by_subtopics:
                suggested_groups = math.ceil(total_students / max_students_per_group_by_subtopics)
                suggested_students_per_group = math.ceil(total_students / suggested_groups)
                
                raise ValidationError(
                    f'Con {total_subtopics} subtemas disponibles, el máximo recomendado por grupo es {max_students_per_group_by_subtopics} estudiantes '
                    f'para evitar repeticiones de temas. Sugerencia: {suggested_groups} grupos de {suggested_students_per_group} estudiantes cada uno.'
                )
        
        # Agregar información útil a los cleaned_data para mostrar en el template
        cleaned_data['_validation_info'] = {
            'total_questions': total_questions,
            'total_subtopics': total_subtopics,
            'subtopics_detail': dict(subtopics_count),
            'max_students_per_group': max_students_per_group_by_subtopics if 'max_students_per_group_by_subtopics' in locals() else total_subtopics
        }
        
        return cleaned_data
    
    def get_validation_info(self):
        """Método para obtener información de validación después del clean()"""
        return getattr(self, '_validation_info', {})
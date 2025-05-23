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
        queryset=Topic.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-control',
            'data-dark-mode': 'bg-dark text-light'
        }),
        required=True,
        label="Tema principal"
    )

    subtopic = forms.ModelChoiceField(
        queryset=Subtopic.objects.none(),
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
            'unit', 'reference_book', 'source_page'
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
        }
        labels = {
            'unit': 'Unidad (opcional)',
            'reference_book': 'Libro o documento de referencia (opcional)',
            'source_page': 'Página de referencia (opcional)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

        for field in ['question_image', 'answer_image']:
            if file := cleaned_data.get(field):
                if not file.name.lower().endswith(('.jpg', '.jpeg', '.png', '.svg')):
                    self.add_error(field, 'Formato no soportado. Use JPG, PNG o SVG.')

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
            self.fields['learning_outcomes'].queryset = self.instance.subject.learningoutcome_set.all()


   
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
            'year', 'exam_type', 'partial_number', 'exam_mode', 'exam_group',
            'shift', 'resolution_time_number', 'resolution_time_unit',  # Cambiados
            'learning_outcomes', 'notes_and_recommendations', 'topics_to_evaluate'
        ]
        widgets = {
            'resolution_time_number': forms.NumberInput(attrs={
                'min': 1,
                'class': 'form-control',
                'placeholder': 'Ej: 90'
            }),
            'resolution_time_unit': forms.Select(attrs={
                'class': 'form-control'
            }),
            'exam_mode': forms.Select(attrs={
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Configuración inicial de querysets
        if user:
            self.fields['institution'].queryset = InstitutionV2.objects.filter(
                userinstitution__user=user, 
                is_active=True
            )
        else:
            self.fields['institution'].queryset = InstitutionV2.objects.none()

        self.fields['faculty'].queryset = FacultyV2.objects.none()
        self.fields['campus'].queryset = CampusV2.objects.none()

        # Configuración del campo profesor
        self.fields['professor'].queryset = User.objects.filter(is_active=True)
        self.fields['professor'].label_from_instance = lambda obj: f"{obj.first_name} {obj.last_name} ({obj.username})"
        
        # Punto 7 - Mejora para learning_outcomes
        self.fields['learning_outcomes'].queryset = LearningOutcome.objects.all()
        self.fields['learning_outcomes'].widget = forms.CheckboxSelectMultiple(
            attrs={'class': 'learning-outcomes-checkbox'}
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
        fields = ['name', 'code']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Facultad de Ingeniería',
                'minlength': '2',
                'maxlength': '255'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código opcional',
                'maxlength': '20'
            })
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 2:
            raise ValidationError("El nombre debe tener al menos 2 caracteres")
        if len(name) > 255:
            raise ValidationError("El nombre no puede exceder 255 caracteres")
        return name
    
    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip()
        if code and len(code) > 20:
            raise ValidationError("El código no puede exceder 20 caracteres")
        return code or None

class SubjectForm(forms.ModelForm):
    learning_outcomes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Ejemplo: LO-1: Resolver ecuaciones básicas - Nivel 1\nLO-2: Analizar problemas complejos - Nivel 2'
        }),
        label='Resultados de Aprendizaje',
        help_text='''<small class="form-text text-muted">
            Ingrese un resultado por línea con formato:<br>
            <code>CÓDIGO: Descripción - Nivel X</code><br>
            Ejemplo: <code>MATH-101: Resolver ecuaciones cuadráticas - Nivel 2</code>
        </small>''',
        required=False,
        strip=True
    )

    class Meta:
        model = Subject
        fields = ['name', 'learning_outcomes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la materia'
            })
        }
        labels = {
            'name': 'Nombre'
        }

    def clean_learning_outcomes(self):
        data = self.cleaned_data['learning_outcomes']
        if not data:
            return data
        
        validated_lines = []
        for i, line in enumerate(data.splitlines(), start=1):
            line = line.strip()
            if line:
                # Validación básica de formato
                if ':' not in line:
                    raise forms.ValidationError(
                        f"Línea {i}: Falta separador ':' entre código y descripción. "
                        f"Formato requerido: CÓDIGO: Descripción - Nivel X"
                    )
                
                # Verificar nivel si está presente
                if '-' in line:
                    desc_part = line.split(':', 1)[1]
                    if 'nivel' in desc_part.lower():
                        try:
                            level = int(desc_part.split('-')[1].lower().replace('nivel', '').strip())
                            if not 1 <= level <= 3:
                                raise ValueError
                        except ValueError:
                            raise forms.ValidationError(
                                f"Línea {i}: Nivel debe ser entre 1 y 3. "
                                f"Ejemplo válido: 'LO-1: Descripción - Nivel 2'"
                            )
                
                validated_lines.append(line)
        
        return '\n'.join(validated_lines)
        

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
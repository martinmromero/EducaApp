from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator, MaxValueValidator  
from django.core.exceptions import ValidationError
import json

# --- MODELOS V2 PRIMERO (para evitar referencias circulares) ---

from django.db import models
from django.core.exceptions import ValidationError

class InstitutionV2(models.Model):
    name = models.CharField(
        max_length=255,
        verbose_name="Nombre",
        help_text="Nombre completo de la institución"
    )
    logo = models.ImageField(
        upload_to='institution_logos_v2/',
        null=True,
        blank=True,
        verbose_name="Logo",
        help_text="Subir imagen del logo institucional"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa",
        help_text="Indica si la institución está activa en el sistema"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización"
    )

    class Meta:
        verbose_name = "Institución V2"
        verbose_name_plural = "Instituciones V2"
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                condition=models.Q(is_active=True),
                name='unique_active_institution_name'
            )
        ]

    def __str__(self):
        return self.name

# UserInstitution DEBE estar inmediatamente después
class UserInstitution(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    institution = models.ForeignKey('material.InstitutionV2', on_delete=models.CASCADE)  # Usar string reference
    is_favorite = models.BooleanField(default=False)
    
    class Meta:
        app_label = 'material'
        unique_together = ('user', 'institution')

class CampusV2(models.Model):
    institution = models.ForeignKey(
        InstitutionV2,
        on_delete=models.CASCADE,
        related_name='campusv2_set',
        verbose_name="Institución"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Nombre de la Sede",
        help_text="Nombre de la sede"
    )
    address = models.TextField(
        verbose_name="Dirección",
        help_text="Dirección completa de la sede",
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa",
        help_text="Indica si la sede está activa"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sede V2"
        verbose_name_plural = "Sedes V2"
        constraints = [
            models.UniqueConstraint(
                fields=['institution', 'name'],
                name='unique_campus_name_per_institution'
            )
        ]

    def clean(self):
        if not self.name or not self.name.strip():
            raise ValidationError("El nombre de la sede no puede estar vacío")
        
        if self.institution_id and CampusV2.objects.filter(
            institution=self.institution,
            name__iexact=self.name.strip()
        ).exclude(id=self.id).exists():
            raise ValidationError("Ya existe una sede con este nombre en la institución")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.institution})"

class FacultyV2(models.Model):
    institution = models.ForeignKey(
        InstitutionV2,
        on_delete=models.CASCADE,
        related_name='facultyv2_set',
        verbose_name="Institución"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Nombre de la Facultad",
        help_text="Nombre de la facultad"
    )
    code = models.CharField(
        max_length=20,
        verbose_name="Código",
        help_text="Código de la facultad (opcional)",
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa",
        help_text="Indica si la facultad está activa"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Facultad V2"
        verbose_name_plural = "Facultades V2"
        constraints = [
            models.UniqueConstraint(
                fields=['institution', 'name'],
                name='unique_faculty_name_per_institution'
            )
        ]

    def clean(self):
        if not self.name or not self.name.strip():
            raise ValidationError("El nombre de la facultad no puede estar vacío")
        
        if self.institution_id and FacultyV2.objects.filter(
            institution=self.institution,
            name__iexact=self.name.strip()
        ).exclude(id=self.id).exists():
            raise ValidationError("Ya existe una facultad con este nombre en la institución")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.institution})"

class InstitutionLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Creación'),
        ('update', 'Actualización'),
        ('delete', 'Eliminación'),
        ('favorite', 'Favorito'),
    ]

    institution = models.ForeignKey(InstitutionV2, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Log de Institución"
        verbose_name_plural = "Logs de Instituciones"

# --- MODELOS ORIGINALES (se mantienen igual) ---

class Institution(models.Model):
    name = models.CharField(max_length=255, unique=True)
    logo = models.ImageField(upload_to='institution_logos/', null=True, blank=True)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='institutions'
    )

    def clean(self):
        # Validación pre-guardado
        if not self.name.strip():
            raise ValidationError("El nombre no puede estar vacío")
        if Institution.objects.filter(name=self.name).exclude(id=self.id).exists():
            raise ValidationError("Nombre ya existe")

    def save(self, *args, **kwargs):
        self.full_clean()  # Ejecuta clean() antes de guardar
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            # Garantiza que el nombre no sea vacío a nivel de BD
            models.CheckConstraint(
                check=models.Q(name__gt=''),
                name="non_empty_name"
            ),
            # Evita duplicados por owner (opcional)
            models.UniqueConstraint(
                fields=['name', 'owner'],
                name='unique_institution_owner'
            )
        ]

class Campus(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    institution = models.ForeignKey(
        'Institution',  # Usar string para referencia
        on_delete=models.CASCADE,
        related_name='campuses'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'institution'],
                name='unique_campus_per_institution'
            )
        ]
        verbose_name_plural = "Campuses"

class Faculty(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, blank=True)
    institution = models.ForeignKey(
        'Institution',  # Usar string para referencia
        on_delete=models.CASCADE,
        related_name='faculties'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'institution'],
                name='unique_faculty_per_institution'
            )
        ]
        verbose_name_plural = "Faculties"

class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre")
    learning_outcomes = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Resultados de aprendizaje",
        help_text="Ingrese un resultado por línea. Puede usar el formato 'Código: Descripción' o simplemente la descripción."
    )

    def get_learning_outcomes_list(self):
        """Devuelve los resultados de aprendizaje como lista estructurada"""
        if not self.learning_outcomes:
            return []
        
        try:
            # Intentar parsear como JSON
            return json.loads(self.learning_outcomes)
        except json.JSONDecodeError:
            # Si no es JSON, parsear como texto plano
            outcomes = []
            for i, line in enumerate(self.learning_outcomes.splitlines(), start=1):
                line = line.strip()
                if line:
                    parts = line.split(':', 1)
                    code = parts[0].strip() if len(parts) > 1 else f"LO-{i}"
                    description = parts[1].strip() if len(parts) > 1 else line
                    
                    outcomes.append({
                        'code': code,
                        'description': description,
                        'level': 1
                    })
            return outcomes

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'material_subjects'
        verbose_name = "Materia"
        verbose_name_plural = "Materias"

class LearningOutcome(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='outcomes')
    code = models.CharField(max_length=20)
    description = models.TextField()
    level = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        help_text="Nivel de dominio (1: Básico, 2: Intermedio, 3: Avanzado)"
    )

    def __str__(self):
        return f"{self.code} - {self.description[:50]}..."

    class Meta:
        unique_together = ('subject', 'code')

class Topic(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nombre del Tema")
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        verbose_name="Asignatura relacionada"
    )
    importance = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Importancia (1-5)"
    )

    def __str__(self):
        return f"{self.subject.name} - {self.name}"

    class Meta:
        unique_together = ('name', 'subject')

class Subtopic(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nombre del Subtema")
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        verbose_name="Tema relacionado"
    )

    def __str__(self):
        return f"{self.topic} → {self.name}"

    class Meta:
        unique_together = ('name', 'topic')

class Contenido(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='contenidos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_DEFAULT,
        default=1,
        verbose_name="Subject"
    )
    isbn = models.CharField(max_length=20, blank=True, null=True)
    edition = models.CharField(max_length=50, blank=True, null=True)
    pages = models.PositiveIntegerField(blank=True, null=True)
    publisher = models.CharField(max_length=100, blank=True, null=True)
    year = models.PositiveIntegerField(blank=True, null=True)
    chapter = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Capítulo (opcional)'
    )

    def __str__(self):
        return f"{self.subject} - {self.title}"

class Question(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('opcion_multiple', 'Opción múltiple'),
        ('verdadero_falso', 'Verdadero/Falso'),
        ('desarrollo', 'Desarrollo'),
    ]

    contenido = models.ForeignKey(
        'Contenido',
        on_delete=models.CASCADE,
        verbose_name='Contenido relacionado',
        null=True,
        blank=True,
        related_name='preguntas'
    )
    subject = models.ForeignKey(
        'Subject',
        on_delete=models.SET_DEFAULT,
        default=1,
        verbose_name='Materia'
    )
    topic = models.ForeignKey(
        'Topic',
        on_delete=models.SET_NULL,
        null=True,
        blank=False,
        verbose_name='Tema principal'
    )
    subtopic = models.ForeignKey(
        'Subtopic',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Subtema (opcional)'
    )
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPE_CHOICES,
        default='opcion_multiple',
        verbose_name='Tipo de pregunta'
    )
    question_text = models.TextField(verbose_name='Texto de la pregunta')
    answer_text = models.TextField(verbose_name='Texto de la respuesta')
    question_image = models.ImageField(
        upload_to='questions/images/',
        null=True,
        blank=True,
        verbose_name='Imagen de la pregunta (opcional)',
        help_text='Formatos: JPG, PNG, SVG'
    )
    answer_image = models.ImageField(
        upload_to='answers/images/',
        null=True,
        blank=True,
        verbose_name='Imagen de la respuesta (opcional)',
        help_text='Formatos: JPG, PNG, SVG'
    )
    options_json = models.TextField(
        blank=True,
        null=True,
        verbose_name='Opciones (JSON)'
    )
    difficulty = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Dificultad (1-5)'
    )
    source_page = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Página de referencia'
    )
    unit = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Unidad (opcional)'
    )
    reference_book = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='Libro/Documento (opcional)'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Usuario',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['subject', 'topic', 'subtopic', 'difficulty']
        verbose_name = 'Pregunta'
        verbose_name_plural = 'Preguntas'
        unique_together = ('contenido', 'source_page')

    @property
    def options(self):
        if self.options_json:
            try:
                return json.loads(self.options_json)
            except json.JSONDecodeError:
                return None
        return None

    @options.setter
    def options(self, value):
        self.options_json = json.dumps(value) if value else None

    def clean(self):
        super().clean()
        for field_name in ['question_image', 'answer_image']:
            image = getattr(self, field_name)
            if image and not image.name.lower().endswith(('.jpg', '.jpeg', '.png', '.svg')):
                raise ValidationError(f'Formato no válido para {field_name}. Use JPG, PNG o SVG.')

    def __str__(self):
        return f"{self.subject} - {self.question_text[:50]}..."


class Exam(models.Model):
    title = models.CharField(
        max_length=255,
        verbose_name="Título del examen",
        help_text="Ej: Parcial 1 - Matemáticas"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_DEFAULT,
        default=1,
        verbose_name="Asignatura",
        related_name="exams"
    )
    topics = models.ManyToManyField(
        Topic,
        verbose_name="Temas evaluados",
        blank=True,
        related_name="exams"
    )
    questions = models.ManyToManyField(
        Question,
        verbose_name="Preguntas",
        related_name="exams"
    )
    instructions = models.TextField(
        verbose_name="Instrucciones generales",
        blank=True,
        null=True
    )
    duration_minutes = models.PositiveIntegerField(
        verbose_name="Duración (minutos)",
        default=60
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    created_by = models.ForeignKey(
    User,
    on_delete=models.CASCADE,
    verbose_name="Creado por",
    related_name="created_exams",  # Cambiado a nombre único
    related_query_name="exam"      # Añadido para queries
    )
    
    is_published = models.BooleanField(
        default=False,
        verbose_name="Publicado"
    )
    learning_outcomes = models.ManyToManyField(
        LearningOutcome,
        verbose_name="Resultados de aprendizaje",
        blank=True
    )

    class Meta:
        verbose_name = "Examen"
        verbose_name_plural = "Exámenes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["subject"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.subject})"

    def get_questions_by_topic(self):
        return {
            topic: self.questions.filter(topic=topic)
            for topic in self.topics.all()
        }

    def total_points(self):
        return sum(q.difficulty for q in self.questions.all())


    EXAM_TYPE_CHOICES = [  
        ('final', 'Final'),  
        ('parcial', 'Parcial'),  
    ]  
    EXAM_MODE_CHOICES = [  
        ('oral', 'Oral'),  
        ('escrito', 'Escrito'),  
    ]  
    EXAM_PARTIAL_CHOICES = [  
        ('1ro', 'Primer Parcial'),  
        ('2do', 'Segundo Parcial'),  
        ('3ro', 'Tercer Parcial'),  
        ('4to', 'Cuarto Parcial'),  
    ]  
    EXAM_GROUP_CHOICES = [  
        ('individual', 'Individual'),  
        ('grupal', 'Grupal'),  
    ]  
    SHIFT_CHOICES = [  
        ('mañana', 'Mañana'),  
        ('tarde', 'Tarde'),  
        ('noche', 'Noche'),  
    ]  

    institution = models.ForeignKey(  
        'Institution',  
        on_delete=models.SET_NULL,  
        null=True,  
        blank=True,  
        verbose_name="Institución"  
    )  
    faculty = models.ForeignKey(  
        'Faculty',  
        on_delete=models.SET_NULL,  
        null=True,  
        blank=True,  
        verbose_name="Facultad"  
    )  
    campus = models.ForeignKey(  
        'Campus',  
        on_delete=models.SET_NULL,  
        null=True,  
        blank=True,  
        verbose_name="Sede"  
    )  
    career_name = models.CharField(max_length=255, verbose_name="Carrera")  
    subject = models.ForeignKey(  
        'Subject',  
        on_delete=models.SET_NULL,  
        null=True,  
        blank=True,  
        verbose_name="Materia"  
    )  
    professor = models.ForeignKey(  
        User,  
        on_delete=models.SET_NULL,  
        null=True,  
        blank=True,  
        verbose_name="Profesor"  
    )  
    year = models.IntegerField(verbose_name="Año")  
    exam_type = models.CharField(  
        max_length=10,  
        choices=EXAM_TYPE_CHOICES,  
        verbose_name="Tipo de examen"  
    )  
    partial_number = models.CharField(  
        max_length=10,  
        choices=EXAM_PARTIAL_CHOICES,  
        blank=True,  
        null=True,  
        verbose_name="Número de parcial"  
    )  
    exam_mode = models.CharField(  
        max_length=10,  
        choices=EXAM_MODE_CHOICES,  
        verbose_name="Modalidad de examen"  
    )  
    exam_group = models.CharField(  
        max_length=10,  
        choices=EXAM_GROUP_CHOICES,  
        default='individual',  
        verbose_name="Modalidad grupal"  
    )  
    shift = models.CharField(  
        max_length=10,  
        choices=SHIFT_CHOICES,  
        blank=True,  
        null=True,  
        verbose_name="Turno"  
    )  
    resolution_time = models.CharField(  
        max_length=50,  
        blank=True,  
        null=True,  
        verbose_name="Tiempo de resolución"  
    )  
    topics_to_evaluate = models.TextField(  
        blank=True,  
        null=True,  
        verbose_name="Temas a evaluar"  
    )  
    notes_and_recommendations = models.TextField(  
        blank=True,  
        null=True,  
        verbose_name="Notas y recomendaciones"  
    )  
    learning_outcomes = models.ManyToManyField(  
        'LearningOutcome',  
        blank=True,  
        verbose_name="Resultados de aprendizaje"  
    )  
    created_by = models.ForeignKey(  
        User,  
        on_delete=models.CASCADE,  
        related_name='exam_templates'  
    )  
    created_at = models.DateTimeField(auto_now_add=True)  

    def __str__(self):  
        exam_name = f"{self.get_exam_type_display()}"  
        if self.exam_type == 'parcial' and self.partial_number:  
            exam_name += f" {self.get_partial_number_display()}"  
        return f"{self.subject} - {exam_name} ({self.year})"  

    class Meta:  
        verbose_name = "Plantilla de Examen"  
        verbose_name_plural = "Plantillas de Examen"  
        ordering = ["-created_at"]  
        indexes = [  
            models.Index(fields=["exam_type", "year"]),  
            models.Index(fields=["subject"]),  
        ]  

class Profile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('user', 'Usuario'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    institutions = models.ManyToManyField(
        Institution,
        blank=True,
        verbose_name="Instituciones"
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

class Career(models.Model):
    name = models.CharField(
        max_length=255,
        verbose_name="Nombre de la Carrera",
        unique=True,
        help_text="Nombre completo de la carrera"
    )
    faculties = models.ManyToManyField(
        FacultyV2,
        blank=True,
        verbose_name="Facultades",
        related_name="careers"
    )
 
    subjects = models.ManyToManyField(
        Subject,
        blank=True,
        verbose_name="Materias",
        related_name="careers"

    ) 
 
    campus = models.ManyToManyField(
        CampusV2,
        blank=True,
        verbose_name="Campus",
        related_name="careers_campus"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización"
    )

    class Meta:
        verbose_name = "Carrera"
        verbose_name_plural = "Carreras"
        ordering = ['name']

    def __str__(self):
        return self.name

#nuevas clases para relacionar instituciones con carreras y materias.  falta ajustar carreras, materias e instituciones
class InstitutionCareer(models.Model):
    institution = models.ForeignKey(
        InstitutionV2,
        on_delete=models.CASCADE,
        verbose_name="Institución",
        related_name='institution_careers'
    )
    career = models.ForeignKey(
        'Career',
        on_delete=models.CASCADE,
        verbose_name="Carrera",
        related_name='career_institutions'
    )
    date_created = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )

    class Meta:
        unique_together = ('institution', 'career')
        verbose_name = "Relación Institución-Carrera"
        verbose_name_plural = "Relaciones Institución-Carreras"
        ordering = ['-date_created']

    def __str__(self):
        return f"{self.institution.name} - {self.career.name}"

class InstitutionSubject(models.Model):
    institution = models.ForeignKey(
        InstitutionV2,
        on_delete=models.CASCADE,
        verbose_name="Institución",
        related_name='institution_subjects'
    )
    subject = models.ForeignKey(
        'Subject',
        on_delete=models.CASCADE,
        verbose_name="Materia",
        related_name='subject_institutions'
    )
    date_created = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    is_core = models.BooleanField(
        default=True,
        verbose_name="Materia troncal",
        help_text="Indica si es una materia troncal/obligatoria"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )

    class Meta:
        unique_together = ('institution', 'subject')
        verbose_name = "Relación Institución-Materia"
        verbose_name_plural = "Relaciones Institución-Materias"
        ordering = ['-date_created']

    def __str__(self):
        return f"{self.institution.name} - {self.subject.name}"

class CareerSubject(models.Model):
    career = models.ForeignKey(
        'Career',
        on_delete=models.CASCADE,
        verbose_name="Carrera",
        related_name='career_subjects'
    )
    subject = models.ForeignKey(
        'Subject',
        on_delete=models.CASCADE,
        verbose_name="Materia",
        related_name='subject_careers'
    )
    semester = models.PositiveSmallIntegerField(
        verbose_name="Semestre",
        help_text="Semestre en que se cursa la materia",
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        null=True,
        blank=True
    )
    is_optional = models.BooleanField(
        default=False,
        verbose_name="Optativa",
        help_text="Indica si la materia es optativa"
    )
    workload_hours = models.PositiveSmallIntegerField(
        verbose_name="Carga horaria",
        help_text="Horas totales de la materia",
        null=True,
        blank=True
    )
    date_created = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )

    class Meta:
        unique_together = ('career', 'subject')
        verbose_name = "Relación Carrera-Materia"
        verbose_name_plural = "Relaciones Carrera-Materias"
        ordering = ['semester', 'subject__name']

    def __str__(self):
        optional_str = " (Optativa)" if self.is_optional else ""
        return f"{self.career.name} - {self.subject.name} (Sem {self.semester}){optional_str}"

class ExamTemplate(models.Model):
    # Opciones de modalidad
    EXAM_MODE_CHOICES = [
        ('presencial', 'Presencial'),
        ('virtual', 'Virtual'),
        ('domiciliario', 'Domiciliario'),
        ('hibrido', 'Híbrido'),
        ('otro', 'Otro')
    ]
    
    # Opciones de tipo de examen
    EXAM_TYPE_CHOICES = [
        ('1er_parcial', '1er. Parcial'),
        ('2do_parcial', '2do. Parcial'), 
        ('3er_parcial', '3er. Parcial'),
        ('final', 'Final'),
        ('recuperatorio', 'Recuperatorio'),
        ('practico', 'Práctico')
    ]
    
    # Opciones de turno
    SHIFT_CHOICES = [
        ('manana', 'Mañana'),
        ('tarde', 'Tarde'),
        ('noche', 'Noche')
    ]

    # Relaciones institucionales
    institution = models.ForeignKey(
        InstitutionV2,
        on_delete=models.PROTECT,
        verbose_name="Institución"
    )
    faculty = models.ForeignKey(
        FacultyV2,
        on_delete=models.PROTECT,
        verbose_name="Facultad"
    )
    career = models.ForeignKey(
        Career,
        on_delete=models.PROTECT,
        verbose_name="Carrera"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        verbose_name="Materia"
    )
    campus = models.ForeignKey(
        CampusV2,
        on_delete=models.PROTECT,
        verbose_name="Sede/Campus"
    )
    professor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='professor_exam_templates',
        verbose_name="Profesor"
    )
    
    # Configuración del examen
    year = models.PositiveIntegerField(
        verbose_name="Año académico",
        default=2023
    )
    exam_type = models.CharField(
        max_length=20,
        choices=EXAM_TYPE_CHOICES,
        verbose_name="Tipo de examen"
    )
    exam_mode = models.CharField(
        max_length=20,
        choices=EXAM_MODE_CHOICES,
        verbose_name="Modalidad de examen"
    )
    shift = models.CharField(
        max_length=20,
        choices=SHIFT_CHOICES,
        verbose_name="Turno",
        blank=True,
        null=True
    )
    
    # Duración como string combinado (simplificado)
    resolution_time = models.CharField(
        max_length=50,
        verbose_name="Duración del examen",
        help_text="Ej: 90 minutos, 2 horas",
        default="60 minutos"
    )
    
    # Contenido evaluativo
    learning_outcomes = models.ManyToManyField(
        LearningOutcome,
        verbose_name="Resultados de aprendizaje",
        blank=True
    )
    topics_to_evaluate = models.TextField(
        verbose_name="Temas a evaluar",
        help_text="Listado de temas incluidos en el examen",
        blank=True
    )
    notes_and_recommendations = models.TextField(
        verbose_name="Notas y recomendaciones",
        blank=True
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_exam_templates',
        verbose_name="Creado por"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )
    
    # Diseño
    institution_logo = models.ImageField(
        upload_to='exam_templates/logos/',
        null=True,
        blank=True,
        verbose_name="Logo institucional"
    )
    custom_css = models.TextField(
        blank=True,
        help_text="CSS personalizado para la plantilla",
        verbose_name="Estilos CSS"
    )
    
    class Meta:
        verbose_name = "Plantilla de examen"
        verbose_name_plural = "Plantillas de examen"
        ordering = ['-created_at']
        permissions = [
            ('can_share_template', 'Puede compartir plantillas'),
        ]
        indexes = [
            models.Index(fields=['exam_type', 'year']),
            models.Index(fields=['subject']),
        ]
    
    def __str__(self):
        return f"{self.get_exam_type_display()} - {self.subject} ({self.year})"
    
    def clean(self):
        # Validación personalizada
        if not self.resolution_time:
            raise ValidationError("Debe especificar la duración del examen")
        
        # Validar formato de tiempo (opcional)
        if not any(unit in self.resolution_time.lower() for unit in ['minuto', 'hora', 'día', 'semana']):
            raise ValidationError("Formato de duración inválido. Use 'minutos', 'horas', 'días' o 'semanas'")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        Profile.objects.create(user=instance)
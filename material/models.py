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

# educaapp/material/models.py
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
                name='unique_active_institution_name',
                condition=models.Q(is_active=True)
            )
        ]
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active'])
        ]

    def __str__(self):
        status = " (Inactiva)" if not self.is_active else ""
        return f"{self.name}{status}"

    def clean(self):
        if len(self.name.strip()) < 3:
            raise ValidationError("El nombre debe tener al menos 3 caracteres")

        if self.is_active and InstitutionV2.objects.filter(
            name__iexact=self.name,
            is_active=True
        ).exclude(pk=self.pk).exists():
            raise ValidationError("Ya existe una institución activa con este nombre")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Sobrescribe el delete para hacer eliminación lógica
        """
        self.is_active = False
        self.save()
        
# UserInstitution DEBE estar inmediatamente después
class UserInstitution(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    institution = models.ForeignKey('material.InstitutionV2', on_delete=models.CASCADE)  # Usar string reference
    is_favorite = models.BooleanField(default=False)
    
    class Meta:
        app_label = 'material'
        unique_together = ('user', 'institution')







class CampusV2(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    institution = models.ForeignKey(InstitutionV2, on_delete=models.CASCADE, related_name='campuses')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Sede V2"
        verbose_name_plural = "Sedes V2"
        constraints = [
            models.UniqueConstraint(fields=['name', 'institution'], name='unique_campusv2_per_institution')
        ]

class FacultyV2(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, blank=True)
    institution = models.ForeignKey(InstitutionV2, on_delete=models.CASCADE, related_name='faculties')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Facultad V2"
        verbose_name_plural = "Facultades V2"
        constraints = [
            models.UniqueConstraint(fields=['name', 'institution'], name='unique_facultyv2_per_institution')
        ]

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
    learning_outcomes = models.TextField(blank=True, null=True, verbose_name="Resultados de aprendizaje")

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'material_subjects'
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"

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
        verbose_name='Asignatura'
    )
    topic = models.ForeignKey(
        'Topic',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Tema principal'
    )
    subtopic = models.ForeignKey(
        'Subtopic',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Subtema'
    )
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPE_CHOICES,
        default='opcion_multiple',
        verbose_name='Tipo de pregunta'
    )
    question_text = models.TextField(verbose_name='Texto de la pregunta')
    answer_text = models.TextField(verbose_name='Texto de la respuesta')
    options_json = models.TextField(
        blank=True,
        null=True,
        verbose_name='Opciones (JSON como texto)',
        help_text='Formato: {"opciones": ["A", "B", "C"]}'
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
    chapter = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Capítulo'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Usuario creador',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['subject', 'topic', 'subtopic', 'difficulty']
        verbose_name = 'Pregunta'
        verbose_name_plural = 'Preguntas'
        indexes = [
            models.Index(fields=['subject', 'question_type']),
            models.Index(fields=['contenido']),
        ]

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

    def __str__(self):
        return f"{self.subject} - {self.question_text[:50]}..."

class ExamTemplate(models.Model):
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
    related_name='created_templates',  # Cambiado de 'exam_templates'
    related_query_name='exam_template' # Añadido para queries
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
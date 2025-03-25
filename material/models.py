from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Subject(models.Model):
    Nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre")

    def __str__(self):
        return self.Nombre

    class Meta:
        db_table = 'material_subjects'
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"

class Material(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='materials/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_DEFAULT,
        default=1,  # ID del subject "General"
        verbose_name="Subject"
    )

    def __str__(self):
        return f"{self.subject} - {self.title}"

class Question(models.Model):
    material = models.ForeignKey(
        'Material', 
        on_delete=models.CASCADE,
        verbose_name='Material relacionado'
    )
    subject = models.ForeignKey(
        'Subject',
        on_delete=models.SET_DEFAULT,
        default=1,
        verbose_name='Asignatura'
    )
    
    # CAMPO NUEVO - Configuración temporal para la migración
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Usuario asignado',
        help_text='Usuario responsable de esta pregunta',
        null=True,       # Permite valores nulos temporalmente
        blank=True,      # Permite omitir en formularios
        default=None     # No asigna valor por defecto
    )
    
    # ... (mantener todos tus otros campos existentes igual)
    question_text = models.TextField(verbose_name='Texto de la pregunta')
    answer_text = models.TextField(verbose_name='Texto de la respuesta')
    topic = models.CharField(max_length=255, verbose_name='Tema principal')
    subtopic = models.CharField(max_length=255, verbose_name='Subtema')
    source_page = models.IntegerField(verbose_name='Página de referencia')
    chapter = models.TextField(blank=True, null=True, verbose_name='Capítulo')

    class Meta:
        ordering = ['subject', 'topic', 'subtopic']
        verbose_name = 'Pregunta'
        verbose_name_plural = 'Preguntas'
        
    def __str__(self):
        return f"{self.subject} - {self.topic}: {self.question_text[:50]}..."


class Exam(models.Model):
    title = models.CharField(max_length=255)
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_DEFAULT,
        default=1,
        verbose_name='Subject'
    )
    topics = models.TextField()
    questions = models.ManyToManyField(Question)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.subject} - {self.title}"

class ExamTemplate(models.Model):
    EXAM_TYPE_CHOICES = [
        ('final', 'Final'),
        ('parcial', 'Parcial'),
    ]
    EXAM_MODE_CHOICES = [
        ('oral', 'Oral'),
        ('escrito', 'Escrito'),
    ]

    institution_logo = models.ImageField(upload_to='institution_logos/', null=True, blank=True)
    institution_name = models.CharField(max_length=255)
    career_name = models.CharField(max_length=255)
    subject_name = models.CharField(max_length=255)
    professor_name = models.CharField(max_length=255)
    year = models.IntegerField()
    exam_type = models.CharField(max_length=10, choices=EXAM_TYPE_CHOICES)
    exam_mode = models.CharField(max_length=10, choices=EXAM_MODE_CHOICES)
    notes_and_recommendations = models.TextField()
    topics_to_evaluate = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject_name} - {self.exam_type} ({self.year})"

class Profile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('user', 'Usuario'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

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
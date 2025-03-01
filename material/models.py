from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Material(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='materials/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.title

class Question(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    question_text = models.TextField()
    answer_text = models.TextField()
    topic = models.CharField(max_length=255)
    subtopic = models.CharField(max_length=255)
    source_page = models.IntegerField()
    chapter = models.TextField(blank=True, null=True)  # Nuevo campo agregado

    def __str__(self):
        return self.question_text

class Exam(models.Model):
    title = models.CharField(max_length=255)
    topics = models.TextField()
    questions = models.ManyToManyField(Question)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.title

class Profile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('user', 'Usuario'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

# Señal para crear un perfil automáticamente cuando se crea un usuario
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

# Señal para guardar el perfil cuando se guarda el usuario
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        Profile.objects.create(user=instance)
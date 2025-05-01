from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Crea un perfil automáticamente al registrar un nuevo usuario.
    Usa get_or_create para evitar duplicados en caso de señales duplicadas.
    """
    if created:
        try:
            Profile.objects.get_or_create(
                user=instance,
                defaults={'role': 'user'}  # Valor por defecto para nuevos perfiles
            )
            logger.info(f"Perfil creado para usuario {instance.username}")
        except Exception as e:
            logger.error(f"Error creando perfil para {instance.username}: {str(e)}")

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Garantiza que el perfil se guarde correctamente tras actualizar el usuario.
    """
    try:
        Profile.objects.get_or_create(user=instance)
        instance.profile.save()
        logger.debug(f"Perfil actualizado para {instance.username}")
    except Exception as e:
        logger.error(f"Error actualizando perfil de {instance.username}: {str(e)}")
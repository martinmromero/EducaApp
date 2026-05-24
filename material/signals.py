from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_out
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


@receiver(user_logged_out)
def delete_contenido_files_on_logout(sender, request, user, **kwargs):
    """
    Al cerrar sesión, elimina todos los archivos de Contenido del usuario.
    Los metadatos (ISBN, título, etc.) y las preguntas vinculadas se conservan.
    """
    if user is None:
        return
    try:
        from .cleanup import cleanup_files_for_user
        cleanup_files_for_user(user)
    except Exception as exc:
        logger.warning(
            "Error al limpiar archivos de contenido en logout de %s: %s",
            getattr(user, 'username', '?'), exc
        )
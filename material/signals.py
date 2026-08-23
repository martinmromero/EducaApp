from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_out
from .models import Profile
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, raw=False, **kwargs):
    """
    Crea un perfil automáticamente al registrar un nuevo usuario.
    raw=True durante loaddata — se omite para no duplicar perfiles del fixture.
    """
    if raw or not created:
        return
    try:
        Profile.objects.get_or_create(
            user=instance,
            defaults={'role': 'user'}
        )
        logger.info(f"Perfil creado para usuario {instance.username}")
    except Exception as e:
        logger.error(f"Error creando perfil para {instance.username}: {str(e)}")

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, raw=False, **kwargs):
    """
    Garantiza que todo User tenga un Profile asociado (red de seguridad para
    cuentas viejas o casos donde el Profile se haya borrado por separado) —
    NO lo vuelve a guardar si ya existe. Antes hacía `instance.profile.save()`
    a ciegas en cada save() de User, incluido uno disparado por algo tan
    ajeno como actualizar `last_login` en un login: si esa instancia de User
    ya tenía `.profile` cacheado en memoria con datos viejos (ej. el `role`
    de antes de un cambio hecho por otro camino, como `Profile.objects.
    filter(...).update(role=...)`), ese resave pisaba el cambio nuevo con el
    valor viejo cacheado — bug real, encontrado 2026-08-22 probando permisos
    de edición con `Client.force_login()` (reutiliza la instancia de User tal
    cual se le pasa). Quien necesita persistir un cambio de Profile ya lo
    hace explícito con su propio profile.save() (ver UserEditForm,
    UserCreateForm, _apply_real_user_preferences en training_accounts.py) —
    ninguno de esos depende de este signal para guardar.
    raw=True durante loaddata — se omite para no duplicar perfiles del fixture.
    """
    if raw:
        return
    try:
        Profile.objects.get_or_create(user=instance)
    except Exception as e:
        logger.error(f"Error asegurando perfil de {instance.username}: {str(e)}")


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
"""
Rutina de limpieza de archivos de Contenido vinculados a sesiones cerradas.

Los archivos físicos se eliminan cuando la sesión del usuario termina (logout
o expiración). El registro en BD se conserva con todos los metadatos (título,
ISBN, edición, editorial, año, páginas) para que las preguntas vinculadas
mantengan su trazabilidad.

La limpieza se dispara de dos maneras:
  1. Señal user_logged_out  → borra inmediatamente los archivos del usuario
     que acaba de cerrar sesión.
  2. AppConfig.ready()      → al arrancar la app borra archivos de usuarios
     sin ninguna sesión activa en la base de datos de sesiones.
"""
import hashlib
import logging
import os

logger = logging.getLogger(__name__)


def compute_file_hash(file_obj_or_bytes):
    """
    Calcula el hash SHA-256 de un archivo.

    Acepta:
    - bytes directamente
    - cualquier objeto file-like con método read() (InMemoryUploadedFile,
      TemporaryUploadedFile, etc.)

    Siempre deja el puntero al inicio si el objeto tiene seek().
    Retorna el hexdigest (64 caracteres).
    """
    sha256 = hashlib.sha256()
    if isinstance(file_obj_or_bytes, (bytes, bytearray)):
        sha256.update(file_obj_or_bytes)
    else:
        if hasattr(file_obj_or_bytes, 'seek'):
            file_obj_or_bytes.seek(0)
        for chunk in iter(lambda: file_obj_or_bytes.read(65536), b''):
            sha256.update(chunk)
        if hasattr(file_obj_or_bytes, 'seek'):
            file_obj_or_bytes.seek(0)
    return sha256.hexdigest()


def _delete_files_for_queryset(candidatos):
    """
    Elimina físicamente los archivos de un queryset de Contenido y marca
    file_deleted_at. Retorna la cantidad eliminada.
    """
    from django.utils import timezone
    from django.core.files.storage import default_storage

    deleted_count = 0
    for contenido in candidatos:
        # Intentar obtener ruta local
        file_path = None
        try:
            if contenido.file and contenido.file.name:
                file_path = contenido.file.path
        except (ValueError, AttributeError, NotImplementedError):
            pass

        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(
                    "Archivo eliminado (sesión cerrada): %s (contenido_id=%s)",
                    file_path, contenido.pk
                )
            except OSError as exc:
                logger.error("No se pudo eliminar %s: %s", file_path, exc)
                continue
        elif contenido.file and contenido.file.name:
            # Fallback para storage remoto (S3, R2, Azure Blob, etc.)
            try:
                if default_storage.exists(contenido.file.name):
                    default_storage.delete(contenido.file.name)
                    logger.info(
                        "Archivo eliminado de storage remoto (sesión cerrada): %s (contenido_id=%s)",
                        contenido.file.name, contenido.pk
                    )
            except Exception as exc:
                logger.error(
                    "No se pudo eliminar %s de storage remoto: %s",
                    contenido.file.name, exc
                )
                continue

        contenido.file = None
        contenido.file_deleted_at = timezone.now()
        contenido.save(update_fields=['file', 'file_deleted_at'])
        deleted_count += 1

    return deleted_count


def cleanup_files_for_user(user):
    """
    Elimina todos los archivos de Contenido activos del usuario indicado.
    Se llama desde la señal user_logged_out.
    """
    try:
        from material.models import Contenido
    except Exception as exc:
        logger.warning("cleanup_files_for_user: no se pudo importar el modelo (%s)", exc)
        return 0

    candidatos = Contenido.objects.filter(
        uploaded_by=user,
        file_deleted_at__isnull=True,
    ).exclude(file='')

    count = _delete_files_for_queryset(candidatos)
    if count:
        logger.info(
            "Logout de %s: %d archivo(s) de contenido eliminado(s).", user.username, count
        )
    return count


def cleanup_files_for_inactive_sessions():
    """
    Al arrancar la app, elimina archivos de Contenido cuyos usuarios no tienen
    ninguna sesión activa en la base de datos de sesiones de Django.

    Idempotente: solo actúa sobre registros con file_deleted_at IS NULL.
    Requiere el backend de sesiones en base de datos (django.contrib.sessions.backends.db).
    Si se usa otro backend, registra un warning y no hace nada.
    """
    from django.utils import timezone

    try:
        from material.models import Contenido
        from django.contrib.sessions.models import Session
    except Exception as exc:
        logger.warning(
            "cleanup_files_for_inactive_sessions: no se pudieron importar modelos (%s)", exc
        )
        return 0

    try:
        # IDs de usuarios con al menos una sesión activa
        active_sessions = Session.objects.filter(expire_date__gt=timezone.now())
        active_user_ids = set()
        for session in active_sessions:
            data = session.get_decoded()
            uid = data.get('_auth_user_id')
            if uid:
                active_user_ids.add(int(uid))
    except Exception as exc:
        logger.warning(
            "cleanup_files_for_inactive_sessions: no se pudo leer la tabla de sesiones (%s). "
            "Verificá que uses el backend de sesiones en base de datos.",
            exc
        )
        return 0

    candidatos = Contenido.objects.filter(
        file_deleted_at__isnull=True,
    ).exclude(file='').exclude(uploaded_by_id__in=active_user_ids)

    count = _delete_files_for_queryset(candidatos)
    if count:
        logger.info(
            "Limpieza al inicio: %d archivo(s) de contenido sin sesión activa eliminado(s).", count
        )
    return count

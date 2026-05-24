from django.apps import AppConfig

class MaterialConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'material'

    def ready(self):
        # Importar las señales para asegurar que se registren
        from . import signals

        # Arrancar el hilo de warmup/keepalive de Ollama en background.
        # El hilo es daemon, así que se detiene automáticamente al cerrar el proceso.
        # Se importa aquí (no en el módulo) para evitar imports circulares en startup.
        try:
            from .local_ai_client import local_ai
            local_ai.start_keepalive()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"No se pudo iniciar keepalive de Ollama: {e}")

        # Limpieza al inicio: elimina archivos de Contenido cuyos usuarios
        # no tienen ninguna sesión activa (p. ej. archivos que quedaron
        # pendientes por un crash o cierre forzado de la app).
        # Se ejecuta en un hilo daemon para no bloquear el arranque.
        import threading

        def _run_cleanup():
            try:
                from .cleanup import cleanup_files_for_inactive_sessions
                cleanup_files_for_inactive_sessions()
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning(
                    "Error en la limpieza de contenidos sin sesión activa: %s", exc
                )

        t = threading.Thread(target=_run_cleanup, daemon=True, name="contenido-cleanup")
        t.start()
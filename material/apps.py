from django.apps import AppConfig

class MaterialConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'material'

    def ready(self):
        # Importar las señales para asegurar que se registren
        import material.signals
from django.core.management.base import BaseCommand
from material.models import Materia, Question

class Command(BaseCommand):
    help = 'Crea la tabla Materias y asigna "General" a preguntas existentes'

    def handle(self, *args, **kwargs):
        # Crear materia "General" si no existe
        materia, created = Materia.objects.get_or_create(nombre="General")
        
        # Asignar "General" a todas las preguntas
        updated = Question.objects.filter(materia__isnull=True).update(materia=materia)
        
        self.stdout.write(
            self.style.SUCCESS(f'✔ Materia "General" creada. {updated} preguntas actualizadas.')
        )
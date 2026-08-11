# candidato a borrar: limpieza de una sola vez para contenidos con los
# títulos placeholder de abajo (bug ya corregido en el flujo que los
# generaba) — no referenciado en render.yaml ni en ningún otro deploy
# config. Ver auditoría de código 2026-08-10.
from django.core.management.base import BaseCommand
from material.models import Contenido, Question

class Command(BaseCommand):
    help = 'Elimina contenidos automáticos y desasocia preguntas.'

    def handle(self, *args, **options):
        titulos_auto = [
            "Contenido Automático",
            "Contenido generado automáticamente",
            "Contenido por Defecto"
        ]
        contenidos_auto = Contenido.objects.filter(title__in=titulos_auto)
        self.stdout.write(f"Encontrados {contenidos_auto.count()} contenidos automáticos.")
        preguntas_afectadas = Question.objects.filter(contenido__in=contenidos_auto)
        self.stdout.write(f"Desasociando {preguntas_afectadas.count()} preguntas...")
        preguntas_afectadas.update(contenido=None)
        eliminados = contenidos_auto.count()
        contenidos_auto.delete()
        self.stdout.write(self.style.SUCCESS(f"Eliminados {eliminados} contenidos automáticos."))

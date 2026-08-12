"""
Se corre en cada deploy (build command de Render) para garantizar que
siempre haya al menos una cuenta del Área de Pruebas lista sin asignar
(ver SPARE_POOL_TARGET_SIZE en material/training_accounts.py) — así el
primer docente que hace clic en "Área de Pruebas" en cada entorno nuevo
también entra instantáneo, sin esperar el clonado sincrónico de contenido
semilla. Idempotente: si el pool ya está completo, no hace nada.
"""
from django.core.management.base import BaseCommand

from material.training_accounts import ensure_spare_pool


class Command(BaseCommand):
    help = 'Repone el pool de repuestos del Área de Pruebas hasta el tamaño objetivo.'

    def handle(self, *args, **options):
        created = ensure_spare_pool()
        if created:
            self.stdout.write(self.style.SUCCESS(f'Pool de Área de Pruebas: {created} repuesto(s) nuevo(s) creado(s).'))
        else:
            self.stdout.write('Pool de Área de Pruebas: ya estaba completo.')

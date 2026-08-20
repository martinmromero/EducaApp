"""
Import del catálogo académico (Institución/Facultad/Carrera/Materia) desde un
CSV — ver informe de rediseño del catálogo. Reutilizable para las próximas
instituciones/facultades: solo cambia el archivo y --institucion.

Columnas esperadas (encabezados exactos, en cualquier orden):
    facultad, carrera, numero de materia, materia,
    año de cursada, cuatrimestre de cursada

Reglas:
- Materias con nombre genérico ("Optativa", "Optativa I", "Optativa II", …)
  se excluyen — el usuario las solicita después vía "Solicitar alta".
- Matcheo de Carrera/Materia por nombre EXACTO, case-sensitive (confirmado) —
  si ya existe una fila con ese nombre exacto, se reutiliza en vez de
  duplicar. Facultad se matchea (institución, nombre) — ya es case-sensitive
  por unicidad activa del modelo.
- numero de materia/año/cuatrimestre son datos DE LA CARRERA (CareerSubject),
  no de la Materia en sí — la misma materia puede tener año/cuatrimestre
  distintos en cada carrera que la incluya.
- Idempotente: se puede correr de nuevo sin duplicar (get_or_create en todos
  los niveles); una fila de CareerSubject ya existente NO se pisa (por si el
  admin ya la editó a mano).
"""
import csv
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from material.models import Career, CareerSubject, FacultyV2, InstitutionV2, Subject

OPTATIVA_RE = re.compile(r'(?i)^\s*optativa\b')
NUMBER_RE = re.compile(r'\d+')


class Command(BaseCommand):
    help = 'Importa el catálogo Institución/Facultad/Carrera/Materia desde un CSV.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', help='Ruta al archivo CSV')
        parser.add_argument('--institucion', required=True, help='Nombre exacto de la Institución (se crea si no existe)')
        parser.add_argument('--dry-run', action='store_true', help='Solo muestra qué haría, no escribe nada')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        institucion_name = options['institucion'].strip()
        dry_run = options['dry_run']

        try:
            with open(csv_path, encoding='utf-8-sig', newline='') as f:
                rows = list(csv.DictReader(f))
        except FileNotFoundError:
            raise CommandError(f'No existe el archivo: {csv_path}')

        required_cols = {'facultad', 'carrera', 'numero de materia', 'materia', 'año de cursada', 'cuatrimestre de cursada'}
        missing = required_cols - set(rows[0].keys()) if rows else required_cols
        if missing:
            raise CommandError(f'Faltan columnas en el CSV: {sorted(missing)}')

        stats = {
            'filas': len(rows), 'excluidas_optativa': 0,
            'facultades_nuevas': 0, 'carreras_nuevas': 0, 'materias_nuevas': 0,
            'career_subjects_nuevos': 0, 'career_subjects_existentes': 0,
        }

        with transaction.atomic():
            institucion, inst_created = InstitutionV2.objects.get_or_create(name=institucion_name)
            if inst_created:
                self.stdout.write(f'Institución nueva: {institucion_name}')

            for row in rows:
                materia_name = (row.get('materia') or '').strip()
                if not materia_name:
                    continue
                if OPTATIVA_RE.match(materia_name):
                    stats['excluidas_optativa'] += 1
                    continue

                facultad_name = (row.get('facultad') or '').strip()
                carrera_name = (row.get('carrera') or '').strip()
                numero = (row.get('numero de materia') or '').strip()
                anio_raw = (row.get('año de cursada') or '').strip()
                cuatri_raw = (row.get('cuatrimestre de cursada') or '').strip()

                facultad, fac_created = FacultyV2.objects.get_or_create(
                    institution=institucion, name=facultad_name, defaults={'is_active': True},
                )
                if fac_created:
                    stats['facultades_nuevas'] += 1

                career, career_created = Career.objects.get_or_create(name=carrera_name)
                if career_created:
                    stats['carreras_nuevas'] += 1
                career.faculties.add(facultad)

                subject, subj_created = Subject.objects.get_or_create(name=materia_name)
                if subj_created:
                    stats['materias_nuevas'] += 1

                anio_match = NUMBER_RE.search(anio_raw)
                anio_cursada = int(anio_match.group()) if anio_match else None
                cuatri_match = NUMBER_RE.search(cuatri_raw)
                cuatrimestre_cursada = f'{cuatri_match.group()}C' if cuatri_match else cuatri_raw

                cs, cs_created = CareerSubject.objects.get_or_create(
                    career=career, subject=subject,
                    defaults={
                        'numero_materia': numero,
                        'anio_cursada': anio_cursada,
                        'cuatrimestre_cursada': cuatrimestre_cursada,
                    },
                )
                stats['career_subjects_nuevos' if cs_created else 'career_subjects_existentes'] += 1

            if dry_run:
                self.stdout.write(self.style.WARNING('--dry-run: se descartan los cambios.'))
                transaction.set_rollback(True)

        for key, value in stats.items():
            self.stdout.write(f'{key}: {value}')
        self.stdout.write(self.style.SUCCESS('Listo.' if not dry_run else 'Listo (dry-run, nada escrito).'))

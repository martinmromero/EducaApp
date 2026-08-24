"""
Borrado completo de produccion (corrida 1, pre-UAT — ver memoria
project_db_reset_before_thesis_defense).

Borra TODO el contenido generado (instituciones, carreras, materias, temas,
preguntas, examenes, plantillas, rubricas, formatos de impresion, grupos de
confianza, favoritos, invitaciones, cuentas de Area de Pruebas, logs de
monitoreo de Groq/Vision) y TODOS los usuarios no-superusuario.

Conserva: cuentas con is_superuser=True (y su Profile, via cascade normal),
y la configuracion de la app que no es "contenido" — GlobalAIConfig,
GroqMonitorSchedule, VisionMonitorSchedule, QuestionGenerationConfig — para
no romper la generacion por IA despues del borrado.

Por defecto corre en dry-run (solo cuenta filas, no borra nada). Hace falta
--execute para borrar de verdad. Todo el borrado real corre dentro de una
unica transaccion atomica: si algo falla a mitad de camino (ej. una
restriccion que no se contemplo), se revierte entero — nunca queda un
borrado parcial.

ExamTemplate va primero en MODELS_TO_WIPE porque es el unico modelo del
esquema con relaciones on_delete=PROTECT (contra institution/faculty/
career/subject/campus/professor/created_by) — borrarlo antes evita que esas
resten bloqueadas. El resto del orden no es critico para la integridad (la
transaccion atomica cubre cualquier caso no contemplado), solo minimiza el
trabajo de cascada que Django tiene que resolver.
"""
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import transaction

from material.models import (
    CampusV2, Career, CareerSubject, CatalogRequest, Contenido, ContentShare,
    Exam, ExamRubric, ExamTemplate, ExamVersionBatch, Favorite, FacultyV2,
    FormatoImpresion, FormatoImpresionAsignado, GroqMonitorRun,
    GroqVisionTestRun, GroupMembership, Invitation, InstitutionAIConfig,
    InstitutionCareer, InstitutionLog, InstitutionSubject, InstitutionV2,
    LearningOutcome, OralExamGroup, OralExamSet, OralExamStudent,
    OralExamStudentQuestion, Question, Rubric, RubricCell, RubricCriterion,
    RubricLevel, SharingGroup, Subject, Subtopic, TestChecklistItem,
    TestResult, Topic, TrainingAccountLink, Unidad, UserAIConfig,
    UserInstitution,
)

MODELS_TO_WIPE = [
    ExamTemplate,
    OralExamStudentQuestion, OralExamStudent, OralExamGroup, OralExamSet,
    ExamRubric, RubricCell, RubricCriterion, RubricLevel, Rubric,
    ExamVersionBatch, Exam, Question,
    FormatoImpresionAsignado, FormatoImpresion,
    ContentShare, GroupMembership, SharingGroup, Favorite,
    Contenido, Subtopic, Topic, Unidad, LearningOutcome,
    CareerSubject, InstitutionCareer, InstitutionSubject, CatalogRequest,
    Subject, Career,
    InstitutionAIConfig, CampusV2, FacultyV2, InstitutionLog,
    UserInstitution, InstitutionV2,
    UserAIConfig, TrainingAccountLink, TestResult, TestChecklistItem,
    Invitation, GroqMonitorRun, GroqVisionTestRun,
]


class Command(BaseCommand):
    help = (
        'Borrado completo de produccion: borra todo el contenido y los '
        'usuarios no-superusuario, conserva superusuarios. Dry-run por '
        'defecto; pasar --execute para borrar de verdad.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--execute', action='store_true',
            help='Ejecuta el borrado de verdad. Sin este flag, solo reporta '
                 'cuantas filas se borrarian (dry-run, no toca nada).'
        )

    def handle(self, *args, **options):
        execute = options['execute']
        superusers = User.objects.filter(is_superuser=True)
        non_superusers = User.objects.filter(is_superuser=False)

        self.stdout.write(self.style.WARNING(
            ('EJECUTANDO BORRADO' if execute else 'DRY-RUN (no se borra nada)')
            + f' — se conservan {superusers.count()} superusuario(s): '
            + (', '.join(superusers.values_list('username', flat=True)) or '(NINGUNO — revisar antes de --execute)')
        ))

        total = 0
        for Model in MODELS_TO_WIPE:
            count = Model.objects.count()
            total += count
            self.stdout.write(f'  {Model.__name__}: {count} fila(s)')
        self.stdout.write(f'  User (no superusuario): {non_superusers.count()} fila(s)')
        self.stdout.write(f'  Session: {Session.objects.count()} fila(s)')
        self.stdout.write(self.style.WARNING(
            f'TOTAL a borrar: {total + non_superusers.count()} filas de contenido/usuarios '
            f'+ {Session.objects.count()} sesion(es)'
        ))

        if not execute:
            self.stdout.write(self.style.NOTICE(
                'Dry-run: no se borro nada. Correr con --execute para borrar de verdad.'
            ))
            return

        with transaction.atomic():
            for Model in MODELS_TO_WIPE:
                Model.objects.all().delete()
            non_superusers.delete()
            Session.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(
            'Borrado completo. Falta re-sembrar: clean_seed_subjects, '
            'seed_demo_content, seed_test_checklist, ensure_training_spare_pool.'
        ))

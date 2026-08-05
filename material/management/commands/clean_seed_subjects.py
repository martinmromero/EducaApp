"""
Limpia las materias semilla (Programación I, Bases de Datos, Biología
Celular) de cualquier pregunta real de otro usuario que haya quedado
mezclada ahí por el bug de Subject compartido por nombre (ver
[[project_subject_topic_global_sharing_bug]] y get_or_create_real_subject
en material/models.py, que ya evita que vuelva a pasar de acá en adelante).

Para cada pregunta de un usuario distinto del bot semilla que esté colgada
de la materia semilla:
  1. Resuelve (o crea) una materia REAL aparte con el mismo nombre —
     nunca reutiliza la fila semilla, aunque todavía no esté marcada
     is_seed_demo=True (por eso NO usa get_or_create_real_subject acá: esa
     función matchea por is_seed_demo=False, y la fila semilla justamente
     tiene ese flag en False mientras siga contaminada — sería circular).
  2. Si la pregunta tenía un tópico de la materia semilla, resuelve/crea el
     tópico equivalente bajo la materia real y reasigna la pregunta ahí.
  3. Reemplaza la materia semilla por la real en Question.subjects.

Al final marca la materia semilla is_seed_demo=True (ya limpia).

Es idempotente y seguro de correr en producción — no borra nada, solo
reasigna. Uso: python manage.py clean_seed_subjects
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from material.models import Question, Subject, Topic

SEED_SUBJECT_NAMES = ['Programación I', 'Bases de Datos', 'Biología Celular']


class Command(BaseCommand):
    help = 'Mueve preguntas de otros usuarios mezcladas en materias semilla a una materia real aparte.'

    def handle(self, *args, **options):
        seed_username = getattr(settings, 'SEED_CONTENT_USERNAME', 'educaapp_demo')

        for name in SEED_SUBJECT_NAMES:
            seed_subject = Subject.objects.filter(
                name=name, questions__user__username=seed_username
            ).distinct().first()
            if not seed_subject:
                seed_subject = Subject.objects.filter(name=name).first()
            if not seed_subject:
                self.stdout.write(f'"{name}": no existe, se omite.')
                continue

            contaminated = list(Question.objects.filter(subjects=seed_subject).exclude(
                user__username=seed_username
            ))

            if not contaminated:
                if not seed_subject.is_seed_demo:
                    seed_subject.is_seed_demo = True
                    seed_subject.save(update_fields=['is_seed_demo'])
                    self.stdout.write(self.style.SUCCESS(f'"{name}": ya estaba limpia, marcada is_seed_demo=True.'))
                else:
                    self.stdout.write(f'"{name}": limpia, sin cambios.')
                continue

            # Materia real aparte — nunca la fila semilla, aunque todavía
            # tenga is_seed_demo=False por seguir contaminada.
            real_subject = Subject.objects.filter(
                name=name, is_seed_demo=False
            ).exclude(pk=seed_subject.pk).first()
            created_real = False
            if not real_subject:
                real_subject = Subject.objects.create(name=name, is_seed_demo=False)
                created_real = True

            self.stdout.write(
                f'"{name}": {len(contaminated)} pregunta(s) ajena(s) -> '
                f'Subject id={real_subject.id} ({"nueva" if created_real else "existente"}).'
            )

            topic_map = {}
            for question in contaminated:
                if question.topic_id and question.topic.subject_id == seed_subject.id:
                    old_topic = question.topic
                    if old_topic.id not in topic_map:
                        new_topic, _ = Topic.objects.get_or_create(
                            name=old_topic.name, subject=real_subject,
                            defaults={'importance': old_topic.importance},
                        )
                        topic_map[old_topic.id] = new_topic
                    question.topic = topic_map[old_topic.id]
                    question.save(update_fields=['topic'])

                question.subjects.remove(seed_subject)
                question.subjects.add(real_subject)
                self.stdout.write(f'  - pregunta #{question.id} (usuario {question.user.username}) movida.')

            seed_subject.is_seed_demo = True
            seed_subject.save(update_fields=['is_seed_demo'])
            self.stdout.write(self.style.SUCCESS(f'"{name}": quedó limpia, marcada is_seed_demo=True.'))

        self.stdout.write(self.style.SUCCESS('Listo.'))

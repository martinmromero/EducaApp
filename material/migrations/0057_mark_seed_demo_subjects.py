from django.conf import settings
from django.db import migrations

SEED_SUBJECT_NAMES = ['Programación I', 'Bases de Datos', 'Biología Celular']


def mark_seed_subjects(apps, schema_editor):
    """
    Marca is_seed_demo=True SOLO en las materias semilla que todavía no
    tienen ninguna pregunta real de otro usuario mezclada — antes del fix
    de get_or_create_real_subject(), un docente real que tipeaba el mismo
    nombre (ej. "Programación I") podía terminar compartiendo la misma fila
    de Subject que el contenido semilla (ver
    [[project_subject_topic_global_sharing_bug]]). Si eso ya pasó en
    producción, marcar esa fila como semilla la ocultaría de los
    selectores normales y el docente perdería acceso a su propio
    contenido — se prefiere dejarla sin marcar y resolverlo a mano en vez
    de arriesgar esconder datos reales de alguien.
    """
    Subject = apps.get_model('material', 'Subject')
    Question = apps.get_model('material', 'Question')
    seed_username = getattr(settings, 'SEED_CONTENT_USERNAME', 'educaapp_demo')

    for subject in Subject.objects.filter(name__in=SEED_SUBJECT_NAMES):
        has_other_users_questions = Question.objects.filter(
            subjects=subject
        ).exclude(user__username=seed_username).exists()
        if not has_other_users_questions:
            subject.is_seed_demo = True
            subject.save(update_fields=['is_seed_demo'])


def unmark_seed_subjects(apps, schema_editor):
    Subject = apps.get_model('material', 'Subject')
    Subject.objects.filter(name__in=SEED_SUBJECT_NAMES).update(is_seed_demo=False)


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0056_subject_is_seed_demo'),
    ]

    operations = [
        migrations.RunPython(mark_seed_subjects, unmark_seed_subjects),
    ]

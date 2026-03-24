from django.db import migrations, models


def copy_fk_to_m2m(apps, schema_editor):
    """
    Copia los subject_id existentes de Contenido y Question
    a las nuevas tablas M2M antes de eliminar los FK.
    """
    Contenido = apps.get_model('material', 'Contenido')
    Question = apps.get_model('material', 'Question')

    for contenido in Contenido.objects.exclude(subject_id__isnull=True):
        contenido.subjects.add(contenido.subject_id)

    for question in Question.objects.exclude(subject_id__isnull=True):
        question.subjects.add(question.subject_id)


def reverse_m2m_to_fk(apps, schema_editor):
    """
    Reversión: toma el primer subject M2M y lo pone de vuelta como FK.
    """
    Contenido = apps.get_model('material', 'Contenido')
    Question = apps.get_model('material', 'Question')

    for contenido in Contenido.objects.all():
        first = contenido.subjects.first()
        if first:
            contenido.subject_id = first.pk
            contenido.save(update_fields=['subject_id'])

    for question in Question.objects.all():
        first = question.subjects.first()
        if first:
            question.subject_id = first.pk
            question.save(update_fields=['subject_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0015_alter_facultyv2_options_question_ai_approved_and_more'),
    ]

    operations = [
        # 1. Agregar el campo M2M en Contenido (con la FK todavía presente)
        migrations.AddField(
            model_name='contenido',
            name='subjects',
            field=models.ManyToManyField(
                blank=True,
                related_name='contenidos',
                to='material.subject',
                verbose_name='Materias',
            ),
        ),
        # 2. Agregar el campo M2M en Question (con la FK todavía presente)
        migrations.AddField(
            model_name='question',
            name='subjects',
            field=models.ManyToManyField(
                blank=True,
                related_name='questions',
                to='material.subject',
                verbose_name='Materias',
            ),
        ),
        # 3. Data migration: copiar FK → M2M
        migrations.RunPython(copy_fk_to_m2m, reverse_code=reverse_m2m_to_fk),
        # 4. Eliminar FK en Contenido
        migrations.RemoveField(
            model_name='contenido',
            name='subject',
        ),
        # 5. Eliminar FK en Question
        migrations.RemoveField(
            model_name='question',
            name='subject',
        ),
    ]

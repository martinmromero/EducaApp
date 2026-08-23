from django.db import migrations


def delete_orphaned_learning_outcomes(apps, schema_editor):
    """
    0080 agregó LearningOutcome.career_subject (nullable) y sacó el viejo
    campo `subject` sin backfill — cualquier fila que ya existiera en la
    base quedó con career_subject NULL y su vínculo a materia
    irrecuperable (subject_id ya no existe en la tabla). 0081 intenta
    volver career_subject obligatorio como estaba planeado desde el
    principio ("Fase 4: reset de datos, tabla vacía" — ver comentario en
    LearningOutcome en models.py), lo que rompe si sobreviven filas
    huérfanas de antes del refactor del catálogo. Se borran acá porque no
    tienen forma de recuperar a qué materia/carrera correspondían.
    """
    LearningOutcome = apps.get_model('material', 'LearningOutcome')
    deleted, _ = LearningOutcome.objects.filter(career_subject__isnull=True).delete()
    if deleted:
        print(f'[0080_1] Borradas {deleted} fila(s) de LearningOutcome huérfanas (career_subject NULL).')


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0080_careersubject_catalogrequest_contentshare_unidad_and_more'),
    ]

    operations = [
        migrations.RunPython(delete_orphaned_learning_outcomes, reverse_code=migrations.RunPython.noop),
    ]

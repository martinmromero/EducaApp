from django.db import migrations


def marcar_subjects_personales_sin_carrera(apps, schema_editor):
    """De antes de este campo existir, quedaban filas de Subject creadas
    por get_or_create_real_subject (un docente tipeó un nombre de materia
    para su propio uso) que nunca se vincularon a ninguna Carrera — esas
    NO son catálogo institucional real, aunque el default del campo sea
    True. Se corrigen a personales (es_catalogo_institucional=False) acá
    en vez de asumirlas institucionales por el simple hecho de existir."""
    Subject = apps.get_model('material', 'Subject')
    Subject.objects.filter(
        created_by__isnull=False,
        careersubject__isnull=True,
    ).distinct().update(es_catalogo_institucional=False)


def sin_reversa(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0085_remove_facultyv2_unique_active_faculty_name_per_institution_and_more'),
    ]

    operations = [
        migrations.RunPython(marcar_subjects_personales_sin_carrera, sin_reversa),
    ]

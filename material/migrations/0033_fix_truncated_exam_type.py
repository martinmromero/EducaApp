from django.db import migrations

# Antes de la migracion 0032, Exam.exam_type tenia max_length=10 y un
# workaround en views.py truncaba silenciosamente los valores mas largos
# antes de guardar (para evitar el error de Postgres "value too long").
# Esto corrompio datos reales: '2do_parcial' quedaba guardado como
# '2do_parcia', etc. Esta migracion repara los valores truncados conocidos
# ahora que la columna ya tiene espacio suficiente (max_length=20).
TRUNCATED_TO_CORRECT = {
    '1er_parcia': '1er_parcial',
    '2do_parcia': '2do_parcial',
    '3er_parcia': '3er_parcial',
    'recuperato': 'recuperatorio',
}


def fix_truncated_exam_type(apps, schema_editor):
    Exam = apps.get_model('material', 'Exam')
    for truncated, correct in TRUNCATED_TO_CORRECT.items():
        Exam.objects.filter(exam_type=truncated).update(exam_type=correct)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0032_alter_exam_exam_type'),
    ]

    operations = [
        migrations.RunPython(fix_truncated_exam_type, noop),
    ]

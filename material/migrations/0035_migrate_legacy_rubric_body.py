from django.db import migrations


def convert_legacy_body_to_grid(apps, schema_editor):
    Rubric = apps.get_model('material', 'Rubric')
    RubricLevel = apps.get_model('material', 'RubricLevel')
    RubricCriterion = apps.get_model('material', 'RubricCriterion')
    RubricCell = apps.get_model('material', 'RubricCell')

    legacy_rubrics = Rubric.objects.filter(
        levels__isnull=True,
    ).exclude(body__isnull=True).exclude(body='').distinct()

    for rubric in legacy_rubrics:
        level = RubricLevel.objects.create(rubric=rubric, label='Descripción', order=0)
        criterion = RubricCriterion.objects.create(rubric=rubric, name='General', order=0)
        RubricCell.objects.create(criterion=criterion, level=level, description=rubric.body)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0034_alter_exam_exam_type'),
    ]

    operations = [
        migrations.RunPython(convert_legacy_body_to_grid, noop_reverse),
    ]

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0035_migrate_legacy_rubric_body'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='rubric',
            name='body',
        ),
    ]

# ONBOARDING WIZARD — ROLLBACK: eliminar este archivo y revertir con
#   .venv\Scripts\python.exe manage.py migrate material 0019
from django.db import migrations, models


def mark_existing_users_done(apps, schema_editor):
    """Usuarios existentes ya están configurados: no mostrarles el wizard."""
    Profile = apps.get_model('material', 'Profile')
    Profile.objects.update(onboarding_completed=True)


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0019_exam_text_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='onboarding_completed',
            field=models.BooleanField(
                default=False,
                verbose_name='Onboarding completado',
                help_text='Indica si el usuario completó o saltó el wizard de configuración inicial.',
            ),
        ),
        migrations.RunPython(mark_existing_users_done, migrations.RunPython.noop),
    ]

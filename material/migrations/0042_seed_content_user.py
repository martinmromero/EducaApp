from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations


def create_seed_content_user(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    username = getattr(settings, 'SEED_CONTENT_USERNAME', 'educaapp_demo')
    User.objects.get_or_create(
        username=username,
        defaults={
            'first_name': 'Contenido',
            'last_name': 'de ejemplo (sistema)',
            'is_active': False,
            'is_staff': False,
            'is_superuser': False,
            # Historical model no expone set_unusable_password(); make_password(None)
            # produce el mismo formato de contraseña inutilizable.
            'password': make_password(None),
        },
    )


def delete_seed_content_user(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    username = getattr(settings, 'SEED_CONTENT_USERNAME', 'educaapp_demo')
    User.objects.filter(username=username).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0041_topic_subtopic_verbose_names'),
    ]

    operations = [
        migrations.RunPython(create_seed_content_user, delete_seed_content_user),
    ]

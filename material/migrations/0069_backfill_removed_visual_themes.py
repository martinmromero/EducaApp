from django.db import migrations


def backfill_removed_visual_themes(apps, schema_editor):
    """
    "bmw" y "clay" se sacaron de VISUAL_THEME_CHOICES (ya no tienen skin en
    static/css/skins.css ni aparecen en el dropdown) — a los perfiles que
    los tenían guardados se los pasa a "default" para que no queden con un
    data-visual-theme sin estilos definidos.
    """
    Profile = apps.get_model('material', 'Profile')
    Profile.objects.filter(visual_theme__in=['bmw', 'clay']).update(visual_theme='default')


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0068_alter_profile_visual_theme'),
    ]

    operations = [
        migrations.RunPython(backfill_removed_visual_themes, noop_reverse),
    ]

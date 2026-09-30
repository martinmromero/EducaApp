from django.db import migrations, models


def merge_pinterest_into_replicate(apps, schema_editor):
    """
    "pinterest" y "replicate" eran dos skins con un rojo casi idéntico; se
    unificaron en "replicate" (con un rojo más tenue, ver static/css/skins.css).
    A los perfiles que tenían "pinterest" guardado se los pasa a "replicate"
    para que conserven un tema rojo en vez de caer en un data-visual-theme
    sin estilos definidos.
    """
    Profile = apps.get_model('material', 'Profile')
    Profile.objects.filter(visual_theme='pinterest').update(visual_theme='replicate')
    # "miro" (negro monocromo) era casi igual a "figma".
    Profile.objects.filter(visual_theme='miro').update(visual_theme='figma')
    # "slack" se eliminó sin reemplazo: vuelve al tema por defecto.
    Profile.objects.filter(visual_theme='slack').update(visual_theme='default')


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0099_learningoutcome_personal_space'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='visual_theme',
            field=models.CharField(choices=[('default', 'EducaApp'), ('linear', 'Linear'), ('figma', 'Figma'), ('replicate', 'Replicate'), ('starbucks', 'Starbucks'), ('uai', 'UAI'), ('lapiz_rojo', 'Lápiz rojo')], default='default', help_text='Skin de colores/tipografía elegido por el usuario para la interfaz.', max_length=20, verbose_name='Tema visual'),
        ),
        migrations.RunPython(merge_pinterest_into_replicate, noop_reverse),
    ]

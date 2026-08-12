from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('material', '0064_backfill_subject_created_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='is_training_account',
            field=models.BooleanField(default=False, help_text='Cuenta espejo automática, nunca un docente real — se excluye de selectores de usuario.', verbose_name='Es cuenta del Área de Pruebas'),
        ),
        migrations.CreateModel(
            name='TrainingAccountLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('real_user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='training_link', to=settings.AUTH_USER_MODEL, verbose_name='Docente real')),
                ('training_user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='real_account_link', to=settings.AUTH_USER_MODEL, verbose_name='Cuenta del Área de Pruebas')),
            ],
            options={
                'verbose_name': 'Vínculo de Área de Pruebas',
                'verbose_name_plural': 'Vínculos de Área de Pruebas',
            },
        ),
    ]

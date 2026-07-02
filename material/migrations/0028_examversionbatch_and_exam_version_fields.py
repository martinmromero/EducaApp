# Generated manually on 2026-07-01

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0027_add_logo_b64_to_institutionv2'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ExamVersionBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Nombre del lote')),
                ('institution_name', models.CharField(blank=True, default='', max_length=255)),
                ('exam_type', models.CharField(blank=True, default='', max_length=50)),
                ('semester', models.CharField(blank=True, default='', max_length=50)),
                ('year', models.IntegerField(blank=True, null=True)),
                ('version_count', models.PositiveIntegerField(default=1)),
                ('questions_per_version', models.PositiveIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exam_version_batches', to=settings.AUTH_USER_MODEL, verbose_name='Creado por')),
                ('subject', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='material.subject', verbose_name='Materia')),
            ],
            options={
                'verbose_name': 'Lote de versiones de examen',
                'verbose_name_plural': 'Lotes de versiones de examen',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='exam',
            name='version_batch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='versions', to='material.examversionbatch', verbose_name='Lote de versiones'),
        ),
        migrations.AddField(
            model_name='exam',
            name='version_number',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Numero de version'),
        ),
    ]

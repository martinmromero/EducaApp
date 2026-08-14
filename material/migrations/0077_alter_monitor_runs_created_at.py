# Generated manually 2026-08-14 — auto_now_add=True -> default=timezone.now
# en GroqMonitorRun/GroqVisionTestRun.created_at, para poder preservar la
# hora real de la corrida al insertarla desde el buffer local (ver
# material/groq_monitor.py sync_buffer_to_db). No-op a nivel de columna en
# Postgres, solo cambia cómo Django completa el valor al guardar.

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0076_examtemplate_rubrics_rubricshare'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groqmonitorrun',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Fecha'),
        ),
        migrations.AlterField(
            model_name='groqvisiontestrun',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Fecha'),
        ),
    ]

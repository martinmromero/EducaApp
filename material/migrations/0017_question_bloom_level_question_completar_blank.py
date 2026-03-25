# Generated manually 2026-03-24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0016_contenido_subjects_m2m_question_subjects_m2m'),
    ]

    operations = [
        # Agregar campo bloom_level
        migrations.AddField(
            model_name='question',
            name='bloom_level',
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                choices=[
                    (1, 'Recordar'),
                    (2, 'Comprender'),
                    (3, 'Aplicar'),
                    (4, 'Analizar'),
                    (5, 'Evaluar'),
                    (6, 'Crear'),
                ],
                verbose_name='Nivel Bloom',
                help_text='Nivel cognitivo según taxonomía de Bloom (1=Recordar … 6=Crear). Solo visible para el docente.',
            ),
        ),
        # Ampliar max_length de question_type y agregar 'completar_blank' a las choices
        migrations.AlterField(
            model_name='question',
            name='question_type',
            field=models.CharField(
                choices=[
                    ('opcion_multiple', 'Opción múltiple'),
                    ('verdadero_falso', 'Verdadero/Falso'),
                    ('completar_blank', 'Completar el espacio'),
                    ('desarrollo', 'Desarrollo'),
                ],
                default='opcion_multiple',
                max_length=20,
                verbose_name='Tipo de pregunta',
            ),
        ),
    ]

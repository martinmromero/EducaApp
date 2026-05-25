from django.db import migrations, models


class Migration(migrations.Migration):

    # Depende de las dos hojas activas del árbol de migraciones.
    # En dev (SQLite) y prod (Neon/PostgreSQL) ambas deben estar aplicadas.
    dependencies = [
        ('material', '0025_useraiconfig_ollama_url'),
        ('material', '0024_contenido_file_hash'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='question_image_b64',
            field=models.TextField(
                blank=True,
                null=True,
                verbose_name='Imagen de pregunta (Base64)',
            ),
        ),
        migrations.AddField(
            model_name='question',
            name='answer_image_b64',
            field=models.TextField(
                blank=True,
                null=True,
                verbose_name='Imagen de respuesta (Base64)',
            ),
        ),
    ]

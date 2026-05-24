from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0025_useraiconfig_ollama_url'),
    ]

    operations = [
        # Hacer el campo file nullable (para cuando se elimine el archivo físico)
        migrations.AlterField(
            model_name='contenido',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='contenidos/'),
        ),
        # Campo para registrar cuándo se eliminó el archivo físico
        migrations.AddField(
            model_name='contenido',
            name='file_deleted_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Archivo eliminado el',
                help_text='Fecha en que el archivo físico fue eliminado automáticamente (7 días tras la subida). Los metadatos se conservan.'
            ),
        ),
    ]

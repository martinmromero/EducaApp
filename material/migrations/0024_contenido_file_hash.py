from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0023_contenido_file_expiry'),
    ]

    operations = [
        migrations.AddField(
            model_name='contenido',
            name='file_hash',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Huella digital del archivo para detectar duplicados. Se calcula al subir.',
                max_length=64,
                null=True,
                verbose_name='Hash SHA-256 del archivo'
            ),
        ),
    ]

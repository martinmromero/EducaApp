from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0024_ai_config_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='useraiconfig',
            name='ollama_url',
            field=models.URLField(
                blank=True,
                null=True,
                verbose_name='URL de Ollama',
                help_text='URL del servidor Ollama. Por defecto: http://192.168.12.236:11434',
            ),
        ),
    ]

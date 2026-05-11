# Generated manually – 2026-05-10

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0023_rubric_grid_structure'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='InstitutionAIConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(
                    choices=[
                        ('openai', 'OpenAI (GPT-4o, GPT-4, etc.)'),
                        ('anthropic', 'Anthropic (Claude 3, etc.)'),
                        ('openai_compatible', 'Compatible con OpenAI (Groq, Mistral, OpenRouter…)'),
                    ],
                    max_length=30,
                    verbose_name='Proveedor',
                )),
                ('api_key_encrypted', models.TextField(blank=True, verbose_name='API Key (cifrada)')),
                ('model', models.CharField(default='gpt-4o-mini', max_length=100, verbose_name='Modelo')),
                ('base_url', models.URLField(
                    blank=True,
                    null=True,
                    verbose_name='URL base',
                    help_text='Solo para endpoints compatibles con OpenAI (ej. Groq, OpenRouter).',
                )),
                ('is_active', models.BooleanField(default=True, verbose_name='Activa')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('institution', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ai_config',
                    to='material.institutionv2',
                    verbose_name='Institución',
                )),
            ],
            options={
                'verbose_name': 'Configuración IA Institucional',
                'verbose_name_plural': 'Configuraciones IA Institucionales',
            },
        ),
        migrations.CreateModel(
            name='UserAIConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(
                    choices=[
                        ('ollama_local', 'IA Local (Ollama)'),
                        ('byok', 'Mi propia API Key (BYOK)'),
                        ('institutional', 'Configuración de la Institución'),
                    ],
                    default='ollama_local',
                    max_length=20,
                    verbose_name='Fuente de IA',
                )),
                ('provider', models.CharField(
                    blank=True,
                    choices=[
                        ('openai', 'OpenAI (GPT-4o, GPT-4, etc.)'),
                        ('anthropic', 'Anthropic (Claude 3, etc.)'),
                        ('openai_compatible', 'Compatible con OpenAI (Groq, Mistral, OpenRouter…)'),
                    ],
                    max_length=30,
                    verbose_name='Proveedor',
                )),
                ('api_key_encrypted', models.TextField(blank=True, verbose_name='API Key (cifrada)')),
                ('model', models.CharField(blank=True, default='gpt-4o-mini', max_length=100, verbose_name='Modelo')),
                ('base_url', models.URLField(
                    blank=True,
                    null=True,
                    verbose_name='URL base',
                    help_text='Solo para endpoints compatibles con OpenAI.',
                )),
                ('institution', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='ai_user_configs',
                    to='material.institutionv2',
                    verbose_name='Institución',
                )),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ai_config',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Usuario',
                )),
            ],
            options={
                'verbose_name': 'Configuración IA de Usuario',
                'verbose_name_plural': 'Configuraciones IA de Usuarios',
            },
        ),
    ]

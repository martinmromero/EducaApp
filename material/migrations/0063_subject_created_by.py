from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('material', '0062_remove_career_subject'),
    ]

    operations = [
        migrations.AddField(
            model_name='subject',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_subjects', to=settings.AUTH_USER_MODEL, verbose_name='Creada por'),
        ),
    ]

from django.db import migrations


def backfill_training_account_institutions(apps, schema_editor):
    """
    Vincula las cuentas del Área de Pruebas que ya existían ANTES del fix de
    30f6afe a las instituciones semilla — ese commit solo vinculaba en el
    momento de crear la cuenta o de resetearla, así que una cuenta creada
    antes se quedó sin ninguna UserInstitution (por eso /instituciones-v2/
    y /careers/ le seguían apareciendo vacías). No toca nada del contenido
    ya creado en la cuenta de práctica — solo agrega el vínculo que faltaba.
    """
    TrainingAccountLink = apps.get_model('material', 'TrainingAccountLink')
    InstitutionV2 = apps.get_model('material', 'InstitutionV2')
    UserInstitution = apps.get_model('material', 'UserInstitution')

    seed_institution_ids = list(
        InstitutionV2.objects.filter(is_seed_demo=True).values_list('id', flat=True)
    )
    if not seed_institution_ids:
        return

    for link in TrainingAccountLink.objects.all():
        for institution_id in seed_institution_ids:
            UserInstitution.objects.get_or_create(
                user_id=link.training_user_id, institution_id=institution_id,
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0065_training_account_link'),
    ]

    operations = [
        migrations.RunPython(backfill_training_account_institutions, noop_reverse),
    ]

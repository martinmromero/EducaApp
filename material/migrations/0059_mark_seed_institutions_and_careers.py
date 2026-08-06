from django.db import migrations

SEED_INSTITUTION_NAMES = [
    'Universidad Nacional Demostración',
    'Instituto Superior del Profesorado Demo',
]
SEED_CAREER_NAMES = [
    'Licenciatura en Sistemas de Información',
    'Profesorado en Biología',
]


def mark_seed_institutions_and_careers(apps, schema_editor):
    """
    Institución: se marca is_seed_demo=True siempre, sin chequeo
    conservador — a diferencia de Subject (0057), ocultar una InstitutionV2
    del selector no le esconde a nadie contenido propio (Exam guarda el
    nombre de institución como texto resuelto, no FK); lo único que puede
    haber colgado es una UserInstitution vieja de una cuenta de prueba que
    pasó por el wizard antes de este fix — perderla del selector no borra
    nada. (Confirmado en desarrollo: con el chequeo conservador, la cuenta
    de pruebas "prueba_wizard" bloqueaba el marcado indefinidamente.)

    Carrera: si mantiene el criterio conservador — a diferencia de
    Institución, un docente real podría haber usado CareerForm para
    vincular sus propias materias reales (M2M `subjects`) a una carrera
    con el mismo nombre que la semilla (ej. "Profesorado en Biología" es
    un nombre de carrera real y común) — ocultarla arrastraría esa
    asociación real.
    """
    InstitutionV2 = apps.get_model('material', 'InstitutionV2')
    Career = apps.get_model('material', 'Career')

    InstitutionV2.objects.filter(name__in=SEED_INSTITUTION_NAMES).update(is_seed_demo=True)

    for career in Career.objects.filter(name__in=SEED_CAREER_NAMES):
        if not career.subjects.filter(is_seed_demo=False).exists():
            career.is_seed_demo = True
            career.save(update_fields=['is_seed_demo'])


def unmark_seed_institutions_and_careers(apps, schema_editor):
    InstitutionV2 = apps.get_model('material', 'InstitutionV2')
    Career = apps.get_model('material', 'Career')
    InstitutionV2.objects.filter(name__in=SEED_INSTITUTION_NAMES).update(is_seed_demo=False)
    Career.objects.filter(name__in=SEED_CAREER_NAMES).update(is_seed_demo=False)


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0058_career_is_seed_demo_institutionv2_is_seed_demo'),
    ]

    operations = [
        migrations.RunPython(mark_seed_institutions_and_careers, unmark_seed_institutions_and_careers),
    ]

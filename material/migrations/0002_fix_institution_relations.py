from django.db import migrations

def forwards_func(apps, schema_editor):
    # Obtiene los modelos históricos
    Institution = apps.get_model('material', 'Institution')
    Campus = apps.get_model('material', 'Campus')
    Faculty = apps.get_model('material', 'Faculty')
    
    # Actualiza las relaciones
    for campus in Campus.objects.all():
        if not hasattr(campus, 'institution'):
            continue
        if campus.institution_id:
            campus.institution = Institution.objects.get(id=campus.institution_id)
            campus.save()

    for faculty in Faculty.objects.all():
        if not hasattr(faculty, 'institution'):
            continue
        if faculty.institution_id:
            faculty.institution = Institution.objects.get(id=faculty.institution_id)
            faculty.save()

def reverse_func(apps, schema_editor):
    pass  # No necesitamos hacer nada para revertir

class Migration(migrations.Migration):
    dependencies = [
        ('material', '0001_initial'),  # Asegúrate que este número coincida con tu migración inicial
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
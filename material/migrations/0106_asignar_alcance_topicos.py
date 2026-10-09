from django.db import migrations


def asignar_alcance_a_topicos(apps, schema_editor):
    """Rellena los campos nuevos de los tópicos y sub-tópicos que ya existían.

    - Materia personal (no del catálogo): sus tópicos y sub-tópicos pasan a ser
      personales y del dueño de la materia.
    - Materia del catálogo con UNA sola carrera: el tópico queda asignado a esa
      carrera-materia.
    - Materia del catálogo en varias carreras: el tópico queda sin carrera
      asignada (se ve en todas) hasta que se lo asigne a una desde la ficha de
      la materia. No se duplican tópicos: las preguntas ya cargadas no se pueden
      repartir sin saber a qué carrera pertenecen.
    Neon todavía no es producción, por eso alcanza con un relleno razonable.

    Va en su propia migración y no junto con el esquema (0103): PostgreSQL no deja
    hacer ALTER TABLE en una tabla con cambios de filas pendientes dentro de la misma
    transacción, y Django crea las claves foráneas nuevas AL FINAL de la migración
    del esquema, es decir, después de este relleno.
    """
    Topic = apps.get_model('material', 'Topic')
    Subtopic = apps.get_model('material', 'Subtopic')
    CareerSubject = apps.get_model('material', 'CareerSubject')
    for topic in Topic.objects.select_related('subject').iterator():
        subject = topic.subject
        campos = []

        carreras = list(CareerSubject.objects.filter(subject_id=subject.pk).values_list('pk', flat=True)[:2])
        career_subject_id = carreras[0] if len(carreras) == 1 else None
        if career_subject_id is not None:
            topic.career_subject_id = career_subject_id
            campos.append('career_subject')

        if not subject.es_catalogo_institucional:
            topic.es_catalogo_institucional = False
            campos.append('es_catalogo_institucional')
            dueno_id = subject.created_by_id
            if topic.created_by_id is None and dueno_id:
                # Si el dueño ya tiene un tópico con el mismo nombre en esa materia y
                # carrera, asignarle este también chocaría con la restricción de
                # unicidad (nombre, materia, carrera, creador): se deja sin dueño.
                choque = Topic.objects.filter(
                    subject_id=subject.pk, name=topic.name, created_by_id=dueno_id,
                    career_subject_id=career_subject_id,
                ).exclude(pk=topic.pk).exists()
                if not choque:
                    topic.created_by_id = dueno_id
                    campos.append('created_by')
            Subtopic.objects.filter(topic_id=topic.pk).update(
                es_catalogo_institucional=False, created_by_id=topic.created_by_id,
            )
        if campos:
            topic.save(update_fields=campos)


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0105_modo_interfaz'),
    ]

    operations = [
        migrations.RunPython(asignar_alcance_a_topicos, migrations.RunPython.noop),
    ]

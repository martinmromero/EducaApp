from django.conf import settings
from django.db import migrations

SHARE_GROUP_NAME_PREFIX = 'Materia compartida automáticamente: '


def backfill_subject_owners(apps, schema_editor):
    """
    Asigna Subject.created_by con la mejor información disponible, sin
    inventar datos que no se puedan inferir con certeza.

    - Semilla (is_seed_demo=True): dueño es la cuenta semilla
      (SEED_CONTENT_USERNAME) — igual quedan ocultas de /materias/ por
      is_seed_demo, esto es solo prolijidad.
    - Un solo usuario con Question/Contenido en esa materia: ese es el
      dueño, caso claro y mayoritario.
    - Cero usuarios (materia vacía, sin contenido real todavía): se deja
      sin dueño (created_by=NULL) — no aparece en /materias/ de nadie hasta
      que alguien le agregue contenido real y quede matcheada de nuevo por
      get_or_create_real_subject().
    - Más de un usuario (colisión real: antes de este fix, Subject se
      matcheaba solo por nombre, así que dos docentes con el mismo nombre
      de materia terminaban compartiendo la fila — ver
      [[project_subject_topic_global_sharing_bug]]): no hay forma de saber
      con certeza a cuál de ellos pertenece cada Topic/LearningOutcome (no
      tienen dueño propio), así que en vez de adivinar y mover/duplicar esos
      datos, se elige como dueño principal a quien más contenido tiene en
      esa materia y a los demás se les da acceso a la misma fila vía un
      grupo de confianza automático — nadie pierde de vista una materia que
      ya venía usando.
    """
    Subject = apps.get_model('material', 'Subject')
    Question = apps.get_model('material', 'Question')
    Contenido = apps.get_model('material', 'Contenido')
    User = apps.get_model('auth', 'User')
    SharingGroup = apps.get_model('material', 'SharingGroup')
    GroupMembership = apps.get_model('material', 'GroupMembership')
    SubjectShare = apps.get_model('material', 'SubjectShare')

    seed_username = getattr(settings, 'SEED_CONTENT_USERNAME', 'educaapp_demo')
    seed_user = User.objects.filter(username=seed_username).first()

    for subject in Subject.objects.all():
        if subject.is_seed_demo:
            if seed_user:
                subject.created_by_id = seed_user.id
                subject.save(update_fields=['created_by'])
            continue

        q_user_ids = set(
            Question.objects.filter(subjects=subject).values_list('user_id', flat=True)
        )
        q_user_ids.discard(None)
        c_user_ids = set(
            Contenido.objects.filter(subjects=subject).values_list('uploaded_by_id', flat=True)
        )
        c_user_ids.discard(None)
        owner_ids = q_user_ids | c_user_ids

        if not owner_ids:
            continue

        if len(owner_ids) == 1:
            subject.created_by_id = owner_ids.pop()
            subject.save(update_fields=['created_by'])
            continue

        counts = {
            uid: (
                Question.objects.filter(subjects=subject, user_id=uid).count()
                + Contenido.objects.filter(subjects=subject, uploaded_by_id=uid).count()
            )
            for uid in owner_ids
        }
        primary_id = max(counts, key=lambda uid: counts[uid])
        subject.created_by_id = primary_id
        subject.save(update_fields=['created_by'])

        for other_id in sorted(owner_ids - {primary_id}):
            group = SharingGroup.objects.create(
                name=f'{SHARE_GROUP_NAME_PREFIX}{subject.name}',
                created_by_id=primary_id,
            )
            GroupMembership.objects.create(group=group, user_id=primary_id, status='accepted')
            GroupMembership.objects.create(group=group, user_id=other_id, status='accepted')
            SubjectShare.objects.create(group=group, subject=subject, shared_by_id=primary_id)


def unassign_subject_owners(apps, schema_editor):
    Subject = apps.get_model('material', 'Subject')
    SharingGroup = apps.get_model('material', 'SharingGroup')
    Subject.objects.update(created_by=None)
    SharingGroup.objects.filter(name__startswith=SHARE_GROUP_NAME_PREFIX).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('material', '0063_subject_created_by'),
    ]

    operations = [
        migrations.RunPython(backfill_subject_owners, unassign_subject_owners),
    ]

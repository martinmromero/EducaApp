# ONBOARDING WIZARD — ROLLBACK: eliminar este archivo y quitar su entrada de settings.py TEMPLATES
import json as _json
from django.conf import settings
from .models import InstitutionV2, UserInstitution, Subject, LearningOutcome, Topic, Contenido, InstitutionSubject


def onboarding_context(request):
    """
    Inyecta datos para el wizard de onboarding/configuracion en todos los templates
    que extiendan base.html.  Solo se ejecuta para usuarios autenticados.
    """
    if not request.user.is_authenticated:
        return {}
    try:
        profile = request.user.profile
    except Exception:
        return {}

    # Todas las instituciones activas (para el selector)
    all_institutions = list(
        InstitutionV2.objects.filter(is_active=True).order_by('name').values('id', 'name')
    )

    # Instituciones ya vinculadas al usuario
    user_inst_ids = set(
        UserInstitution.objects.filter(user=request.user)
        .values_list('institution_id', flat=True)
    )
    user_institutions = [
        {'id': inst.id, 'name': inst.name, 'logo_src': inst.logo_src}
        for inst in InstitutionV2.objects.filter(id__in=user_inst_ids).order_by('name')
    ]

    # Materias del usuario (via contenidos subidos por el)
    user_subjects = list(
        Subject.objects.filter(contenidos__uploaded_by=request.user)
        .distinct().order_by('name').values('id', 'name')
    )

    # Todas las materias del sistema para el picker, con outcomes y topics (incluyen id)
    outcomes_by_subj = {}
    for lo in LearningOutcome.objects.values('id', 'subject_id', 'description'):
        outcomes_by_subj.setdefault(lo['subject_id'], []).append({'id': lo['id'], 'text': lo['description']})

    topics_by_subj = {}
    for t in Topic.objects.values('id', 'subject_id', 'name'):
        topics_by_subj.setdefault(t['subject_id'], []).append({'id': t['id'], 'text': t['name']})

    all_subjects = [
        {
            'id': s['id'],
            'name': s['name'],
            'outcomes': outcomes_by_subj.get(s['id'], []),
            'topics': topics_by_subj.get(s['id'], []),
        }
        for s in Subject.objects.order_by('name').values('id', 'name')
    ]

    # Contenidos subidos por el usuario (últimos 20)
    contenidos_qs = (
        Contenido.objects.filter(uploaded_by=request.user)
        .prefetch_related('subjects')
        .order_by('-uploaded_at')[:20]
    )
    user_contenidos = [
        {
            'id': c.id,
            'title': c.title,
            'subjects': [s.name for s in c.subjects.all()],
            'uploaded_at': c.uploaded_at.strftime('%d/%m/%Y'),
        }
        for c in contenidos_qs
    ]

    # Materias con contenido semilla del sistema (para la rama "esquema
    # precargado" del paso de decisión del wizard, ver [[project_onboarding_seed_content_plan]]).
    seed_username = getattr(settings, 'SEED_CONTENT_USERNAME', 'educaapp_demo')
    demo_subject_ids = list(
        Subject.objects.filter(questions__user__username=seed_username)
        .distinct().values_list('id', flat=True)
    )
    demo_institution_names = {
        row['subject_id']: row['institution__name']
        for row in InstitutionSubject.objects.filter(subject_id__in=demo_subject_ids)
        .values('subject_id', 'institution__name')
    }
    demo_subjects = [
        {
            'id': s['id'],
            'name': s['name'],
            'institution_name': demo_institution_names.get(s['id'], ''),
        }
        for s in Subject.objects.filter(id__in=demo_subject_ids).order_by('name').values('id', 'name')
    ]

    onb_data = {
        'autoShow': not profile.onboarding_completed,
        'userInstIds': list(user_inst_ids),
        'userInstitutions': user_institutions,
        'userSubjects': user_subjects,
        'allSubjects': all_subjects,
        'userContenidos': user_contenidos,
        'demoSubjects': demo_subjects,
    }

    return {
        'onboarding_institutions': all_institutions,
        'onb_data_json': _json.dumps(onb_data),
    }

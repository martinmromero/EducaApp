# ONBOARDING WIZARD — ROLLBACK: eliminar este archivo y quitar su entrada de settings.py TEMPLATES
import json as _json
from .models import InstitutionV2, UserInstitution, Subject, LearningOutcome, Topic


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
    user_institutions = [i for i in all_institutions if i['id'] in user_inst_ids]

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

    onb_data = {
        'autoShow': not profile.onboarding_completed,
        'userInstIds': list(user_inst_ids),
        'userInstitutions': user_institutions,
        'userSubjects': user_subjects,
        'allSubjects': all_subjects,
    }

    return {
        'onboarding_institutions': all_institutions,
        'onb_data_json': _json.dumps(onb_data),
    }

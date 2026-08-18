# ONBOARDING WIZARD — ROLLBACK: eliminar este archivo y quitar su entrada de settings.py TEMPLATES
import json as _json
from django.conf import settings
from .models import (
    InstitutionV2, UserInstitution, Subject, LearningOutcome, Topic, Contenido,
    InstitutionSubject, GroupMembership,
)
from .content_visibility import get_visible_subjects
from .views import is_admin as _is_admin


def onboarding_context(request):
    """
    Inyecta datos para el wizard de onboarding/configuracion, el badge de
    invitaciones pendientes y la visibilidad de "Administración" en todos
    los templates que extiendan base.html. Solo se ejecuta para usuarios
    autenticados.

    Las consultas pesadas del wizard (todas las materias/outcomes/topics del
    sistema, etc.) sólo se calculan cuando la página actual es el propio
    asistente (`comenzar/`): son la única vista que usa `onb_data_json` /
    `onboarding_institutions`, y antes se recalculaban en cada navegación
    (plantillas, exámenes, ...) siendo el mayor costo fijo por request.
    """
    if not request.user.is_authenticated:
        return {}
    try:
        profile = request.user.profile
    except Exception:
        return {}

    pending_invites_count = GroupMembership.objects.filter(
        user=request.user, status='pending'
    ).count()

    base_ctx = {
        'onboarding_institutions': [],
        'onb_data_json': _json.dumps({'autoShow': not profile.onboarding_completed}),
        'pending_invites_count': pending_invites_count,
        'is_admin': _is_admin(request.user),
        'visual_theme': profile.visual_theme,
        'visual_theme_choices': profile.VISUAL_THEME_CHOICES,
        # Área de Pruebas: la marca de sesión (ver training_views.py) es lo
        # único que hace falta acá — no una consulta a TrainingAccountLink,
        # ya se revalidó contra esa tabla al entrar/salir.
        'in_training_mode': bool(request.session.get('acting_as_training_for')),
        # Modo Testing (panel de UAT) — ver testing_panel_views.py.
        'is_tester': profile.is_tester,
        'testing_mode_active': profile.is_tester and bool(request.session.get('testing_mode_active')),
    }

    is_wizard_page = (
        getattr(request.resolver_match, 'url_name', None) == 'onboarding_v2_page'
    )
    if not is_wizard_page:
        return base_ctx

    # Todas las instituciones activas (para el selector) — se excluyen las
    # institución(es) semilla (ver seed_demo_content): existen solo para el
    # examen de ejemplo de "esquema ya armado", no para que un docente real
    # las elija como su propia institución en el paso manual del wizard.
    all_institutions = list(
        InstitutionV2.objects.filter(is_active=True, is_seed_demo=False).order_by('name').values('id', 'name')
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

    # Materias del usuario (dueño real, no ya no se infiere solo de haber
    # subido un Contenido: una materia armada solo con preguntas también
    # cuenta como propia)
    user_subjects = list(
        Subject.objects.filter(created_by=request.user, is_seed_demo=False)
        .order_by('name').values('id', 'name')
    )

    # Materias visibles para el picker "elegí materia existente" del paso 3:
    # propias + compartidas por otros vía grupos de confianza. Antes era
    # Subject.objects.filter(is_seed_demo=False) a secas — TODAS las materias
    # reales del sistema, de cualquier docente, quedaban expuestas (con sus
    # temas y resultados de aprendizaje) y hasta editables por ID desde acá.
    # Ver [[project_subject_topic_global_sharing_bug]].
    visible_subject_ids = list(get_visible_subjects(request.user).values_list('id', flat=True))

    outcomes_by_subj = {}
    for lo in LearningOutcome.objects.filter(subject_id__in=visible_subject_ids).values('id', 'subject_id', 'description'):
        outcomes_by_subj.setdefault(lo['subject_id'], []).append({'id': lo['id'], 'text': lo['description']})

    topics_by_subj = {}
    for t in Topic.objects.filter(subject_id__in=visible_subject_ids).values('id', 'subject_id', 'name'):
        topics_by_subj.setdefault(t['subject_id'], []).append({'id': t['id'], 'text': t['name']})

    all_subjects = [
        {
            'id': s['id'],
            'name': s['name'],
            'outcomes': outcomes_by_subj.get(s['id'], []),
            'topics': topics_by_subj.get(s['id'], []),
        }
        for s in Subject.objects.filter(id__in=visible_subject_ids).order_by('name').values('id', 'name')
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
        **base_ctx,
        'onboarding_institutions': all_institutions,
        'onb_data_json': _json.dumps(onb_data),
    }

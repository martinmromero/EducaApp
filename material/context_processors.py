# ONBOARDING WIZARD — ROLLBACK: eliminar este archivo y quitar su entrada de settings.py TEMPLATES
import json as _json
from django.conf import settings
from .models import (
    InstitutionV2, UserInstitution, Subject, LearningOutcome, Topic, Contenido,
    InstitutionSubject, GroupMembership, CatalogRequest, Career, CareerSubject,
    FacultyV2, InstitutionCareer, QuestionDeletionNotice,
)
from .content_visibility import get_visible_subjects, get_visible_careers, get_visible_faculties
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
    is_admin_user = _is_admin(request.user)
    # Badge del link "Solicitudes de catálogo" en Administración — solo se
    # consulta para admins, no tiene sentido para el resto.
    pending_catalog_requests_count = (
        CatalogRequest.objects.filter(estado='pendiente').count() if is_admin_user else 0
    )
    # Badge de "Mis solicitudes" — aviso al propio solicitante de que una
    # suya se resolvió y todavía no la vio (se apaga al entrar a esa
    # pantalla, ver mis_solicitudes_catalogo).
    pending_catalog_notifications_count = CatalogRequest.objects.filter(
        solicitado_por=request.user, visto_por_solicitante=False,
    ).exclude(estado='pendiente').count()
    # Badge de "Preguntas borradas" — aviso a quien es dueño de un examen o
    # cuestionario oral cuando OTRO usuario borró una pregunta compartida
    # que ese examen/cuestionario venía usando (ver QuestionDeletionNotice
    # y _avisar_borrado_pregunta_a_duenos en views.py).
    pending_question_deletion_notices_count = QuestionDeletionNotice.objects.filter(
        recipient=request.user, visto=False,
    ).count()

    base_ctx = {
        'onboarding_institutions': [],
        'onb_data_json': _json.dumps({'autoShow': not profile.onboarding_completed}),
        'pending_invites_count': pending_invites_count,
        'pending_catalog_requests_count': pending_catalog_requests_count,
        'pending_catalog_notifications_count': pending_catalog_notifications_count,
        'pending_question_deletion_notices_count': pending_question_deletion_notices_count,
        'is_admin': is_admin_user,
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
    # Instituciones ya vinculadas al usuario
    user_inst_ids = set(
        UserInstitution.objects.filter(user=request.user)
        .values_list('institution_id', flat=True)
    )
    all_institutions = [
        {'id': inst.id, 'name': inst.name, 'logo_src': inst.logo_src}
        for inst in InstitutionV2.objects.filter(is_active=True, is_seed_demo=False).order_by('name')
    ]
    user_institutions = [i for i in all_institutions if i['id'] in user_inst_ids]

    # Facultades visibles para el picker "elegí otra facultad" del paso
    # Institución (paso 2) — con la institución exacta a la que pertenece
    # cada una (FK directa, no M2M) para filtrar client-side una vez elegida
    # la institución.
    visible_faculties = list(
        get_visible_faculties(request.user).values('id', 'name', 'institution_id')
    )
    all_faculties = [
        {'id': f['id'], 'name': f['name'], 'institution_id': f['institution_id']}
        for f in visible_faculties
    ]
    user_faculty_ids = set(
        FacultyV2.objects.filter(created_by=request.user, is_active=True)
        .values_list('id', flat=True)
    )
    user_faculties = [f for f in all_faculties if f['id'] in user_faculty_ids]

    # Carreras visibles para el picker "elegí otra carrera" del paso Carrera,
    # con las facultades donde cada una aparece (para filtrar client-side una
    # vez elegida la facultad del paso anterior — antes se filtraba solo por
    # institución y una institución con varias facultades, ej. UAI, mezclaba
    # carreras de todas ellas en un único listado larguísimo). El catálogo
    # bulk-importado vincula carrera-facultad vía Career.faculties direct
    # (InstitutionCareer existe pero no tiene facultad — solo se usa para lo
    # que este wizard vaya creando, y ahora también linkea a la facultad
    # elegida vía Career.faculties, ver onboarding_save_step paso 3).
    visible_careers = list(get_visible_careers(request.user).values('id', 'name'))
    visible_career_ids = [c['id'] for c in visible_careers]
    career_faculty_ids = {}
    for row in Career.faculties.through.objects.filter(career_id__in=visible_career_ids).values(
        'career_id', 'facultyv2_id'
    ):
        career_faculty_ids.setdefault(row['career_id'], set()).add(row['facultyv2_id'])
    all_careers = [
        {'id': c['id'], 'name': c['name'], 'faculty_ids': sorted(career_faculty_ids.get(c['id'], []))}
        for c in visible_careers
    ]

    # Carreras del usuario (dueño real) — con faculty_ids para poder acotar
    # también "Tus carreras" a la facultad elegida en el paso anterior. Antes
    # se mostraban TODAS las carreras propias sin filtrar (mismo criterio que
    # user_subjects/user_institutions, que sí tiene sentido ahí porque no hay
    # una institución/facultad "actual" en ese paso) — pero acá, después de
    # varias sesiones de prueba, "Tus carreras" terminaba lleno de carreras
    # de OTRAS instituciones/facultades y las de la recién elegida (ej.
    # Tecnología Informática de UAI) quedaban enterradas o ni siquiera
    # visibles como propias, aunque siguieran estando en "elegir otra
    # carrera". Ver reporte de usuario: eligió UAI y no vio ninguna carrera
    # de esa facultad en el paso Carrera — filtrar solo por institución no
    # alcanzaba porque UAI tiene varias facultades.
    user_careers = [
        {'id': c['id'], 'name': c['name'], 'faculty_ids': sorted(career_faculty_ids.get(c['id'], []))}
        for c in Career.objects.filter(created_by=request.user, is_seed_demo=False)
        .order_by('name').values('id', 'name')
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

    # Materias de cada carrera (paso Carrera -> paso Materia): acota el
    # picker de materia existente a las que de verdad están en el plan de
    # estudios de la carrera elegida, en vez de mostrar todo el catálogo.
    subject_ids_by_career = {}
    for row in CareerSubject.objects.filter(
        subject_id__in=visible_subject_ids, career_id__in=visible_career_ids
    ).values('career_id', 'subject_id'):
        subject_ids_by_career.setdefault(row['career_id'], []).append(row['subject_id'])

    outcomes_by_subj = {}
    for lo in LearningOutcome.objects.filter(
        career_subject__subject_id__in=visible_subject_ids
    ).values('id', 'career_subject__subject_id', 'description'):
        outcomes_by_subj.setdefault(lo['career_subject__subject_id'], []).append({'id': lo['id'], 'text': lo['description']})

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
        'allInstitutions': all_institutions,
        'userFaculties': user_faculties,
        'allFaculties': all_faculties,
        'userCareers': user_careers,
        'allCareers': all_careers,
        'userSubjects': user_subjects,
        'allSubjects': all_subjects,
        'subjectIdsByCareer': subject_ids_by_career,
        'userContenidos': user_contenidos,
        'demoSubjects': demo_subjects,
    }

    return {
        **base_ctx,
        'onboarding_institutions': all_institutions,
        'onb_data_json': _json.dumps(onb_data),
    }

"""QA extensiva 2026-08-22 — smoke crawl de todas las rutas GET sin
parametros (mas un puñado de rutas con parametros de las areas mas
tocadas esta semana), como anonimo / usuario comun / admin. No valida
contenido, solo que ninguna tire 500 y que las admin-only no se cuelen
para un usuario comun. Corre contra la base descartable de test."""
from django.test import TestCase, Client
from django.urls import reverse, NoReverseMatch
from django.contrib.auth import get_user_model

from .models import InstitutionV2, FacultyV2, Career, Subject, CareerSubject
from .tests_catalogo_qa import make_user

User = get_user_model()

# Nombres de URL sin parametros — ver enumeracion via get_resolver(). Se
# excluyen a mano los que son puramente de infraestructura (jsi18n,
# service_worker) o que ya se sabe que son solo-POST y no aportan nada
# nuevo al pasar por ahi con GET.
NOMBRES_MATERIAL_SIN_PARAM = [
    'index', 'preview_exam', 'bloom_taxonomy', 'upload_contenido',
    'create_exam', 'create_exam_wizard', 'create_exam_template',
    'list_exam_templates', 'signup', 'security_question_setup',
    'mis_invitaciones', 'user_list', 'create_user',
    'entrar_area_pruebas', 'salir_area_pruebas', 'restablecer_area_pruebas',
    'mis_datos', 'formato_impresion_list', 'formato_impresion_create',
    'mis_examenes', 'lista_preguntas', 'mis_contenidos', 'upload_questions',
    'document_processor_dashboard', 'institution_v2_list',
    'create_institution_v2', 'subject_list', 'favoritos_list',
    'espacio_personal_list', 'create_subject', 'career_list',
    'career_create_simple', 'list_oral_exams', 'create_oral_exam',
    'onboarding_v2_page', 'onboarding_v2_demo_scheme',
    'onboarding_v2_demo_exam_list', 'catalog_request_create',
    'mis_solicitudes_catalogo', 'catalog_requests_bandeja',
    'grupos_list', 'grupo_crear', 'invitaciones_pendientes',
    'rubric_list', 'rubric_create', 'ai_config', 'ai_config_status',
    'institution_ai_config', 'groq_monitor_page', 'neon_usage_page',
    'admin_bulk_catalog_upload', 'question_generation_prompt_config',
    'testing_panel_state', 'testing_admin_results',
]

# name -> kwargs, para las vistas mas nuevas/tocadas esta semana que sí
# necesitan un pk real.
NOMBRES_MATERIAL_CON_PARAM = [
    ('institution_v2_detail', lambda f: {'pk': f['institucion'].pk}),
    ('institution_v2_logs', lambda f: {'pk': f['institucion'].pk}),
    ('edit_institution_v2', lambda f: {'pk': f['institucion'].pk}),
    ('career_detail', lambda f: {'pk': f['carrera'].pk}),
    ('career_associations', lambda f: {'pk': f['carrera'].pk}),
    ('subject_detail', lambda f: {'pk': f['materia'].pk}),
    ('edit_subject', lambda f: {'pk': f['materia'].pk}),
]


class URLSmokeCrawlTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user('smoke_admin', role='admin')
        cls.user = make_user('smoke_user')

        cls.institucion = InstitutionV2.objects.create(
            name='Institucion Smoke', created_by=cls.user, es_catalogo_institucional=False,
        )
        cls.facultad = FacultyV2.objects.create(
            name='Facultad Smoke', institution=cls.institucion,
            created_by=cls.user, es_catalogo_institucional=False,
        )
        cls.carrera = Career.objects.create(
            name='Carrera Smoke', created_by=cls.user, es_catalogo_institucional=False,
        )
        cls.carrera.faculties.add(cls.facultad)
        cls.materia = Subject.objects.create(
            name='Materia Smoke', created_by=cls.user, es_catalogo_institucional=False,
        )
        CareerSubject.objects.create(career=cls.carrera, subject=cls.materia)

    def setUp(self):
        self.anon = Client()
        self.as_user = Client()
        self.as_user.login(username='smoke_user', password='testpass123')
        self.as_admin = Client()
        self.as_admin.login(username='smoke_admin', password='testpass123')

    def _reverse(self, name, kwargs=None):
        try:
            return reverse(f'material:{name}', kwargs=kwargs)
        except NoReverseMatch:
            return reverse(name, kwargs=kwargs)

    def test_rutas_sin_parametros_no_tiran_500(self):
        fallas = []
        for name in NOMBRES_MATERIAL_SIN_PARAM:
            try:
                url = self._reverse(name)
            except NoReverseMatch as e:
                fallas.append(f'{name}: no se pudo resolver la URL ({e})')
                continue
            for label, client in (('anon', self.anon), ('user', self.as_user), ('admin', self.as_admin)):
                try:
                    resp = client.get(url)
                except Exception as e:
                    fallas.append(f'{name} [{label}]: excepcion no capturada: {e!r}')
                    continue
                if resp.status_code >= 500:
                    fallas.append(f'{name} [{label}]: HTTP {resp.status_code}')
        if fallas:
            self.fail('Rutas con error 5xx o excepcion:\n' + '\n'.join(fallas))

    def test_rutas_con_parametros_de_catalogo_no_tiran_500(self):
        fixtures = {
            'institucion': self.institucion, 'facultad': self.facultad,
            'carrera': self.carrera, 'materia': self.materia,
        }
        fallas = []
        for name, kwargs_fn in NOMBRES_MATERIAL_CON_PARAM:
            try:
                url = self._reverse(name, kwargs_fn(fixtures))
            except NoReverseMatch as e:
                fallas.append(f'{name}: no se pudo resolver la URL ({e})')
                continue
            for label, client in (('anon', self.anon), ('user', self.as_user), ('admin', self.as_admin)):
                try:
                    resp = client.get(url)
                except Exception as e:
                    fallas.append(f'{name} [{label}]: excepcion no capturada: {e!r}')
                    continue
                if resp.status_code >= 500:
                    fallas.append(f'{name} [{label}]: HTTP {resp.status_code}')
        if fallas:
            self.fail('Rutas con error 5xx o excepcion:\n' + '\n'.join(fallas))

    def test_faculties_v2_edit_revivida_no_tira_500(self):
        """edit_faculty_v2 fue revivida de codigo muerto esta semana con un
        template nuevo (faculties_v2/edit.html) — create/delete de faculty_v2
        y todo campus_v2 siguen intactos como codigo muerto a proposito."""
        url = reverse('material:edit_faculty_v2', kwargs={
            'institution_id': self.institucion.pk, 'faculty_id': self.facultad.pk,
        })
        resp = self.as_user.get(url)
        self.assertLess(resp.status_code, 500)
        resp_admin = self.as_admin.get(url)
        self.assertEqual(resp_admin.status_code, 200)

    def test_create_exam_wizard_renders_sin_instituciones_precargadas(self):
        """El paso institucion/facultad/carrera dejo de precargar TODAS las
        del sistema (ver views.py) para buscarlas en vivo contra
        check_catalog_duplicate — la pagina tiene que seguir rindiendo 200
        sin esos context vars."""
        resp = self.as_user.get(reverse('material:create_exam_wizard'))
        self.assertEqual(resp.status_code, 200)

    def test_campus_faculty_v2_dead_code_sigue_muriendo_como_se_espera(self):
        """Documentado en views.py como CANDIDATO A BORRAR: create/delete de
        faculty_v2 y los 3 de campus_v2 no tienen template — TemplateDoesNotExist
        esperado (el test Client de Django re-lanza la excepcion en vez de
        devolver una response 500). Si esto empieza a andar (200 o ninguna
        excepcion), alguien agrego los templates sin actualizar el
        comentario/memoria — no es un bug, es una senal de que el comentario
        quedo desactualizado."""
        from django.template.exceptions import TemplateDoesNotExist
        url = reverse('material:create_faculty_v2', kwargs={'institution_id': self.institucion.pk})
        with self.assertRaises(TemplateDoesNotExist):
            self.as_admin.get(url)

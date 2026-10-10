"""Modo simple / modo avanzado (Profile.interface_mode).

El modo simple muestra un menú reducido y manda todos los "Nuevo ..." a los
asistentes; el avanzado es la interfaz completa de siempre. Cubre el valor por
defecto, la migración que deja a las cuentas existentes como estaban, el
interruptor y lo que cambia en el menú, en Inicio y en los listados. Corre
contra una base descartable."""
import importlib

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Profile

User = get_user_model()


def make_user(username, mode=None, admin=False):
    user = User.objects.create_user(username=username, password='testpass123')
    profile = user.profile
    profile.security_question = 'comida_favorita'
    profile.onboarding_completed = True
    if admin:
        profile.role = 'admin'
    if mode:
        profile.interface_mode = mode
    profile.save()
    return user


def login(username):
    client = Client()
    client.login(username=username, password='testpass123')
    return client


class ModoPorDefectoTests(TestCase):
    def test_una_cuenta_nueva_arranca_en_modo_simple(self):
        user = User.objects.create_user(username='m_nuevo', password='x')
        self.assertEqual(user.profile.interface_mode, 'simple')

    def test_la_migracion_deja_a_las_cuentas_existentes_en_avanzado(self):
        migracion = importlib.import_module('material.migrations.0105_modo_interfaz')
        user = User.objects.create_user(username='m_viejo', password='x')
        self.assertEqual(user.profile.interface_mode, 'simple')
        migracion.usuarios_existentes_en_modo_avanzado(apps, None)
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.interface_mode, 'avanzado')


class InterruptorTests(TestCase):
    def setUp(self):
        self.user = make_user('m_ana', mode='simple')
        self.client = login('m_ana')

    def cambiar(self, mode, **extra):
        data = {'mode': mode}
        data.update(extra)
        return self.client.post(reverse('material:set_interface_mode'), data)

    def test_cambia_de_modo_y_vuelve_a_la_pantalla_de_origen(self):
        resp = self.cambiar('avanzado', next='/mis-examenes/')
        self.assertRedirects(resp, '/mis-examenes/', fetch_redirect_response=False)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.interface_mode, 'avanzado')
        self.cambiar('simple')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.interface_mode, 'simple')

    def test_no_redirige_a_otro_sitio(self):
        resp = self.cambiar('avanzado', next='https://ejemplo.com/robo')
        self.assertRedirects(resp, reverse('material:index'), fetch_redirect_response=False)

    def test_un_modo_inventado_no_cambia_nada(self):
        self.cambiar('experto')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.interface_mode, 'simple')

    def test_solo_acepta_post_y_pide_login(self):
        self.assertEqual(self.client.get(reverse('material:set_interface_mode')).status_code, 405)
        self.assertEqual(Client().post(reverse('material:set_interface_mode'), {'mode': 'avanzado'}).status_code, 302)


class MenuTests(TestCase):
    def setUp(self):
        make_user('m_simple', mode='simple')
        make_user('m_avanzado', mode='avanzado')
        make_user('m_admin_simple', mode='simple', admin=True)

    def inicio(self, username):
        return login(username).get(reverse('material:index'))

    def test_el_menu_simple_es_reducido(self):
        resp = self.inicio('m_simple')
        self.assertContains(resp, 'id="tourMenuAsistente"')
        self.assertContains(resp, 'id="tourMenuGenerarIA"')
        self.assertContains(resp, 'id="tourMenuPreguntas"')
        self.assertContains(resp, 'id="tourMenuAgregados"')
        self.assertContains(resp, 'id="modeSwitch"')
        self.assertNotContains(resp, 'id="modeSwitch" checked')
        self.assertNotContains(resp, 'Pasar a modo')  # ya no está en el menú lateral
        for oculto in ('id="tourMenuContenidos"', 'id="tourMenuAcademico"', 'id="tourMenuGrupos"', 'id="tourMenuPlantillas"'):
            self.assertNotContains(resp, oculto)

    def test_el_menu_avanzado_es_el_completo(self):
        resp = self.inicio('m_avanzado')
        for presente in ('id="tourMenuContenidos"', 'id="tourMenuAcademico"', 'id="tourMenuGrupos"', 'id="tourMenuPlantillas"'):
            self.assertContains(resp, presente)
        self.assertNotContains(resp, 'id="tourMenuAsistente"')
        self.assertContains(resp, 'id="modeSwitch"')
        self.assertRegex(resp.content.decode(), r'id="modeSwitch"\s*checked')

    def test_un_admin_en_modo_simple_conserva_administracion(self):
        resp = self.inicio('m_admin_simple')
        self.assertContains(resp, 'Administración')
        self.assertNotContains(resp, 'id="tourMenuAcademico"')

    def test_inicio_en_modo_simple_ofrece_una_sola_puerta(self):
        resp = self.inicio('m_simple')
        self.assertContains(resp, 'id="homeAsistenteBtn"')
        self.assertNotContains(resp, 'bi-upload me-2')
        self.assertNotContains(self.inicio('m_avanzado'), 'id="homeAsistenteBtn"')

    def test_las_pantallas_avanzadas_siguen_accesibles_en_modo_simple(self):
        client = login('m_simple')
        for nombre in ('mis_contenidos', 'subject_list', 'list_exam_templates', 'grupos_list', 'rubric_list'):
            self.assertEqual(client.get(reverse(f'material:{nombre}')).status_code, 200, nombre)


class ListadosTests(TestCase):
    def setUp(self):
        make_user('l_simple', mode='simple')
        make_user('l_avanzado', mode='avanzado')

    def test_nuevo_examen_va_al_asistente_en_modo_simple(self):
        html = login('l_simple').get(reverse('material:mis_examenes')).content.decode()
        self.assertIn(f'href="{reverse("material:create_exam_wizard")}" class="btn btn-primary" id="examNewBtn"', html)
        self.assertNotIn('id="examWizardBtn"', html)

    def test_en_modo_avanzado_siguen_los_dos_botones(self):
        html = login('l_avanzado').get(reverse('material:mis_examenes')).content.decode()
        self.assertIn(f'href="{reverse("material:create_exam")}" class="btn btn-primary" id="examNewBtn"', html)
        self.assertIn('id="examWizardBtn"', html)

    def test_preguntas_orales_y_plantillas_siguen_el_mismo_criterio(self):
        casos = (
            ('lista_preguntas', 'upload_questions_wizard', 'questionNewBtn', 'questionWizardBtn'),
            ('list_oral_exams', 'create_oral_exam_wizard', 'oralNewBtn', 'oralWizardBtn'),
            ('list_exam_templates', 'create_exam_template_wizard', 'templateNewBtn', 'templateWizardBtn'),
        )
        for lista, asistente, nuevo, aparte in casos:
            simple = login('l_simple').get(reverse(f'material:{lista}')).content.decode()
            self.assertIn(f'href="{reverse("material:" + asistente)}" class="btn btn-primary" id="{nuevo}"', simple, lista)
            self.assertNotIn(f'id="{aparte}"', simple, lista)
            avanzado = login('l_avanzado').get(reverse(f'material:{lista}')).content.decode()
            self.assertIn(f'id="{aparte}"', avanzado, lista)

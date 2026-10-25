"""Correcciones del recorrido completo como docente plano (2026-10-26): lo que encontró el recorrido en
navegador real antes de dar cuentas al jurado. Corre contra una base descartable."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


def docente(nombre='r_docente'):
    user = User.objects.create_user(username=nombre, password='testpass123')
    user.profile.security_question = 'comida_favorita'
    user.profile.onboarding_completed = True
    user.profile.save()
    return user


def leer_estatico(ruta):
    from django.contrib.staticfiles import finders
    completa = finders.find(ruta)
    assert completa, 'no existe el archivo estático ' + ruta
    return open(completa, encoding='utf8').read()


class AvisoSoloAdministradoresTests(TestCase):
    """Todas las pantallas de administrador avisan lo mismo a un docente (antes algunas decían
    "No hay permiso para acceder a esta sección." en un cuadro de error y otras no decían nada)."""

    def setUp(self):
        self.user = docente()
        self.client = Client()
        self.client.force_login(self.user)

    def test_los_paneles_de_herramientas_avisan_con_el_mismo_texto(self):
        for nombre in ('groq_monitor_page', 'neon_usage_page', 'mis_invitaciones'):
            r = self.client.get(reverse('material:' + nombre), follow=True)
            self.assertContains(r, 'solo para administradores', msg_prefix=nombre)
            self.assertNotContains(r, 'No hay permiso para acceder', msg_prefix=nombre)


class SesionVencidaYTituloDelExamenTests(TestCase):
    def setUp(self):
        self.user = docente('r_docente2')
        self.client = Client()
        self.client.force_login(self.user)

    def test_el_aviso_de_sesion_vencida_se_carga_en_todas_las_pantallas(self):
        r = self.client.get(reverse('material:index'))
        self.assertContains(r, 'session_guard')

    def test_el_aviso_de_sesion_vencida_detecta_el_redireccionamiento_al_ingreso(self):
        js = leer_estatico('js/session_guard.js')
        self.assertIn('respuesta.redirected', js)
        self.assertIn('/accounts/login', js)
        self.assertIn('Sesión vencida', js)

    def test_el_titulo_sugerido_del_examen_no_usa_los_textos_de_ayuda_de_los_desplegables(self):
        js = leer_estatico('material/js/create_exam.js')
        # Sin institución elegida el <select> muestra "Seleccionar institución": no debe terminar en el nombre.
        self.assertIn("var institutionLabel = 'sin institución';", js)
        self.assertIn('institution.value', js)
        self.assertIn("'sin materia'", js)
        self.assertNotIn("'sin anio'", js)
        wizard = leer_estatico('material/js/create_exam_wizard.js')
        self.assertNotIn("'sin anio'", wizard)

"""Tamaño de letra por cuenta (2026-10-29): endpoint, atributo en <html> y menú."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

User = get_user_model()


def _crear(nombre):
    u = User.objects.create_user(username=nombre, password='testpass123')
    u.profile.security_question = 'comida_favorita'
    u.profile.onboarding_completed = True
    u.profile.save()
    return u


@override_settings(TAMANO_LETRA_SELECTOR=True)
class TamanoLetraTests(TestCase):
    def setUp(self):
        self.u = _crear('tl_docente')
        self.c = Client()
        self.c.force_login(self.u)

    def test_por_defecto_es_automatico_y_no_pone_atributo(self):
        self.assertEqual(self.u.profile.font_scale, 'auto')
        html = self.c.get(reverse('material:index')).content.decode()
        self.assertNotIn('data-font-scale', html.split('<head>')[0])

    def test_el_menu_ofrece_los_cuatro_tamanos(self):
        html = self.c.get(reverse('material:index')).content.decode()
        for valor in ('auto', 'normal', 'grande', 'muy_grande'):
            self.assertIn(f'data-scale-value="{valor}"', html)

    def test_guardar_tamano_lo_persiste_y_lo_aplica_al_html(self):
        r = self.c.post(reverse('material:set_font_scale'), {'scale': 'muy_grande'})
        self.assertEqual(r.status_code, 200)
        self.u.profile.refresh_from_db()
        self.assertEqual(self.u.profile.font_scale, 'muy_grande')
        html = self.c.get(reverse('material:index')).content.decode()
        self.assertIn('data-font-scale="muy_grande"', html.split('<head>')[0])

    def test_valor_invalido_se_rechaza(self):
        r = self.c.post(reverse('material:set_font_scale'), {'scale': '500'})
        self.assertEqual(r.status_code, 400)
        self.u.profile.refresh_from_db()
        self.assertEqual(self.u.profile.font_scale, 'auto')

    def test_solo_post_y_con_login(self):
        self.assertEqual(self.c.get(reverse('material:set_font_scale')).status_code, 405)
        self.assertEqual(Client().post(reverse('material:set_font_scale'), {'scale': 'grande'}).status_code, 302)


class TamanoLetraOcultoTests(TestCase):
    """Con el interruptor apagado (el valor por defecto) el selector no se ve ni se aplica lo guardado."""

    def setUp(self):
        self.u = _crear('tl_oculto')
        self.c = Client()
        self.c.force_login(self.u)

    def test_apagado_por_defecto_no_muestra_el_selector(self):
        html = self.c.get(reverse('material:index')).content.decode()
        self.assertNotIn('data-scale-value', html)
        self.assertNotIn('font-scale-row', html)
        # Un comentario de plantilla mal escrito (de varias líneas) se vería como texto en el menú.
        self.assertNotIn('{#', html)
        self.assertNotIn('TAMANO_LETRA', html)

    def test_una_preferencia_guardada_no_se_aplica_si_esta_apagado(self):
        self.u.profile.font_scale = 'muy_grande'
        self.u.profile.save()
        html = self.c.get(reverse('material:index')).content.decode()
        self.assertNotIn('data-font-scale', html.split('<head>')[0])


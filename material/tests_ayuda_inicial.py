"""Ayuda de primer ingreso (2026-10-30): "No volver a mostrar" por cuenta y pantalla inicial sin textos repetidos."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


def _nuevo(nombre):
    u = User.objects.create_user(username=nombre, password='testpass123')
    u.profile.security_question = 'comida_favorita'
    u.profile.onboarding_completed = False
    u.profile.save()
    return u


class AyudaInicialTests(TestCase):
    def setUp(self):
        self.u = _nuevo('ai_nuevo')
        self.c = Client()
        self.c.force_login(self.u)

    def test_el_recorrido_arranca_solo_en_el_primer_ingreso(self):
        html = self.c.get(reverse('material:onboarding_v2_page') + '?first=1').content.decode()
        self.assertIn('var arrancaSolo = true;', html)

    def test_sin_first_no_arranca_solo(self):
        html = self.c.get(reverse('material:onboarding_v2_page')).content.decode()
        self.assertIn('var arrancaSolo = false;', html)

    def test_no_volver_a_mostrar_se_guarda_en_la_cuenta(self):
        r = self.c.post(reverse('material:ayuda_no_mostrar'))
        self.assertEqual(r.status_code, 200)
        self.u.profile.refresh_from_db()
        self.assertTrue(self.u.profile.ayuda_inicial_oculta)
        html = self.c.get(reverse('material:onboarding_v2_page') + '?first=1').content.decode()
        self.assertIn('var arrancaSolo = false;', html)

    def test_la_preferencia_es_de_cada_cuenta(self):
        self.c.post(reverse('material:ayuda_no_mostrar'))
        otra = _nuevo('ai_otra')
        c2 = Client()
        c2.force_login(otra)
        html = c2.get(reverse('material:onboarding_v2_page') + '?first=1').content.decode()
        self.assertIn('var arrancaSolo = true;', html)

    def test_solo_post_y_con_login(self):
        self.assertEqual(self.c.get(reverse('material:ayuda_no_mostrar')).status_code, 405)
        self.assertEqual(Client().post(reverse('material:ayuda_no_mostrar')).status_code, 302)

    def test_la_pantalla_inicial_no_repite_la_misma_instruccion(self):
        html = self.c.get(reverse('material:onboarding_v2_page') + '?first=1').content.decode()
        self.assertIn('¿Cómo se va a usar EducaApp?', html)
        self.assertEqual(html.count('Elegir cómo se va a usar'), 0)
        self.assertNotIn('Elegir cómo se va a usar la app y empezar', html)

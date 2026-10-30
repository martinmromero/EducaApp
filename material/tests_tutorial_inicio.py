"""Tutorial de inicio (2026-10-30): textos, botones grandes ocultos, recorrido de la demo con el menú cerrado y aviso
al crear la cuenta por invitación."""
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


def _leer(*partes):
    with open(os.path.join(settings.BASE_DIR, *partes), encoding='utf8') as f:
        return f.read()


class TutorialDeInicioTests(TestCase):
    def setUp(self):
        u = User.objects.create_user(username='tut_ana', password='testpass123')
        u.profile.security_question = 'comida_favorita'
        u.profile.save()
        self.c = Client()
        self.c.force_login(u)

    def test_los_dos_botones_grandes_estan_ocultos_pero_siguen_en_la_pagina(self):
        html = self.c.get(reverse('material:onboarding_v2_page') + '?first=1').content.decode()
        self.assertIn('id="onb2GatewayChoices"', html)
        fila = html[html.index('<div class="row g-3 justify-content-center'):][:120]
        self.assertIn('d-none', fila)
        self.assertIn('id="onb2GatewayStartBtn"', html)
        self.assertIn('Se puede cambiar entre modos cuando se desee', html)

    def test_textos_del_recorrido_general(self):
        js = _leer('static', 'js', 'tour.js')
        self.assertIn("element: '#tourHelpBtn'", js)
        self.assertIn('se pueden subir directo, tanto individualmente como en lotes', js)
        self.assertIn('Los elementos (materias, carreras, tópicos...) que se cargaron al espacio personal.', js)
        self.assertIn('Se puede cambiar entre modos cuando se desee.', js)

    def test_el_recorrido_de_la_demo_abre_el_menu_colapsado_y_espera_a_la_carga(self):
        html = _leer('material', 'templates', 'material', 'onboarding_v2_demo_recap.html')
        self.assertIn('sb-pre', html)
        self.assertIn("window.addEventListener('load', arrancarRecorrido)", html)
        self.assertIn("progressText: '{{current}} de {{total}}'", html)

    def test_crear_cuenta_por_invitacion_avisa_que_esta_trabajando(self):
        html = _leer('material', 'templates', 'registration', 'invitacion_aceptar.html')
        self.assertIn('aceptarInvitacionSpinner', html)
        self.assertIn('Creando la cuenta', html)

"""Inicio y menú "?" (2026-10-30): orden de los botones, "Probar con un ejemplo" en el menú de ayuda y numeración del
recorrido del ejemplo."""
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


def _docente(nombre, modo):
    u = User.objects.create_user(username=nombre, password='testpass123')
    u.profile.security_question = 'comida_favorita'
    u.profile.onboarding_completed = True
    u.profile.interface_mode = modo
    u.profile.save()
    return u


class InicioOrdenTests(TestCase):
    def _inicio(self, modo):
        c = Client()
        c.force_login(_docente(f'io_{modo}', modo))
        return c.get(reverse('material:index')).content.decode()

    def test_modo_avanzado_tres_botones_en_orden(self):
        html = self._inicio('avanzado')
        cuerpo = html.split('<h1 class="h2">¿Por dónde empezar?</h1>')[1].split('index-stat-tab')[0]
        orden = [cuerpo.index(x) for x in ('id="homeAsistenteBtn"', 'Generar preguntas con IA', 'Crear examen')]
        self.assertEqual(orden, sorted(orden))
        self.assertNotIn('Subir material', cuerpo)
        self.assertNotIn('Probar con un ejemplo', cuerpo)

    def test_modo_simple_sin_probar_con_un_ejemplo_en_el_inicio(self):
        cuerpo = self._inicio('simple').split('<h1 class="h2">¿Por dónde empezar?</h1>')[1].split('index-stat-tab')[0]
        self.assertNotIn('Probar con un ejemplo', cuerpo)
        self.assertIn('id="homeAsistenteBtn"', cuerpo)

    def test_probar_con_un_ejemplo_esta_en_el_menu_de_ayuda(self):
        html = self._inicio('avanzado')
        menu = html.split('id="tourHelpMenu"')[1].split('</ul>')[0]
        self.assertIn('Probar con un ejemplo', menu)
        self.assertIn(reverse('material:onboarding_v2_page') + '?demo=1', menu)

    def test_el_recorrido_del_ejemplo_conserva_las_llaves_del_progreso(self):
        # La plantilla es de Django: sin templatetag, {{current}} y {{total}} se renderizaban vacíos (" de ").
        fuente = (Path(__file__).parent / 'templates' / 'material' / 'onboarding_v2_demo_recap.html').read_text(encoding='utf-8')
        self.assertNotIn("progressText: '{{current}}", fuente)
        self.assertIn('{% templatetag openvariable %}current{% templatetag closevariable %}', fuente)

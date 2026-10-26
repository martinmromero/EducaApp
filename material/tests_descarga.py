"""Descargas de PDF/DOCX con aviso de "Preparando…" (2026-10-26)."""
import os

from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class DescargaConAvisoTests(TestCase):
    def setUp(self):
        u = User.objects.create_user(username='desc_ana', password='testpass123')
        u.profile.security_question = 'comida_favorita'
        u.profile.onboarding_completed = True
        u.profile.save()
        self.c = Client()
        self.c.force_login(u)

    def test_todas_las_pantallas_cargan_el_script_de_descarga(self):
        html = self.c.get(reverse('material:mis_solicitudes_catalogo')).content.decode()
        self.assertIn('js/descarga_guard', html)

    def test_el_script_engancha_los_enlaces_de_exportar_y_avisa_si_falla(self):
        ruta = os.path.join(settings.BASE_DIR, 'static', 'js', 'descarga_guard.js')
        with open(ruta, encoding='utf8') as f:
            js = f.read()
        self.assertIn('/exportar/', js)
        self.assertIn('Preparando', js)
        self.assertIn('No se pudo preparar el archivo', js)

    def test_la_pantalla_del_examen_baja_los_archivos_con_el_aviso(self):
        ruta = os.path.join(settings.BASE_DIR, 'material', 'templates', 'material', 'exams', 'ver_examen.html')
        with open(ruta, encoding='utf8') as f:
            html = f.read()
        self.assertIn('EducaAppDescargar(', html)
        self.assertNotIn('window.location.href = baseUrl', html)

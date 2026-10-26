"""Descargas de PDF/DOCX con aviso de "Preparando…" (2026-10-26)."""
import os

from django.contrib.auth import get_user_model
from django.conf import settings
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase
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
        self.assertIn('descarga_token', js)

    def test_la_pantalla_del_examen_baja_los_archivos_con_el_aviso(self):
        ruta = os.path.join(settings.BASE_DIR, 'material', 'templates', 'material', 'exams', 'ver_examen.html')
        with open(ruta, encoding='utf8') as f:
            html = f.read()
        self.assertIn('EducaAppDescargar(', html)
        self.assertNotIn('window.location.href = baseUrl', html)

    def test_el_servidor_deja_la_cookie_de_fin_de_descarga_solo_si_el_archivo_sale(self):
        from .views_export import avisa_fin_de_descarga

        @avisa_fin_de_descarga
        def archivo(request):
            return HttpResponse(b'x', status=200 if request.GET.get('ok', '1') == '1' else 500)

        rf = RequestFactory()
        r = archivo(rf.get('/x/', {'descarga_token': 'abc123'}))
        self.assertIn('descarga_abc123', r.cookies)
        self.assertNotIn('descarga_abc123', archivo(rf.get('/x/', {'descarga_token': 'abc123', 'ok': '0'})).cookies)
        self.assertEqual(len(archivo(rf.get('/x/')).cookies), 0)
        self.assertEqual(len(archivo(rf.get('/x/', {'descarga_token': 'a;b'})).cookies), 0)

    def test_la_pantalla_base_del_examen_carga_el_script(self):
        ruta = os.path.join(settings.BASE_DIR, 'material', 'templates', 'material', 'exams', 'base_exam_preview.html')
        with open(ruta, encoding='utf8') as f:
            self.assertIn('descarga_guard.js', f.read())

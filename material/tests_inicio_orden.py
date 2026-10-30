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
        cuerpo = html.split('<h1 class="h2">¿Por dónde empezar?</h1>')[1].split('edu-stat-grid')[0]
        orden = [cuerpo.index(x) for x in ('id="homeAsistenteBtn"', 'Generar preguntas con IA', 'Crear examen')]
        self.assertEqual(orden, sorted(orden))
        self.assertNotIn('Subir material', cuerpo)
        self.assertNotIn('Probar con un ejemplo', cuerpo)

    def test_modo_simple_sin_probar_con_un_ejemplo_en_el_inicio(self):
        cuerpo = self._inicio('simple').split('<h1 class="h2">¿Por dónde empezar?</h1>')[1].split('edu-stat-grid')[0]
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


class MenuLateralTests(TestCase):
    def _lateral(self, modo, admin=False):
        u = _docente(f'ml_{modo}_{int(admin)}', modo)
        if admin:
            u.profile.role = 'admin'
            u.profile.save()
        c = Client()
        c.force_login(u)
        html = c.get(reverse('material:index')).content.decode()
        return html.split('id="sidebar"')[1].split('class="bottom-links"')[0]

    def test_orden_del_menu_en_modo_avanzado(self):
        lateral = self._lateral('avanzado', admin=True)
        ids = ['tourMenuAsistente', 'tourMenuGenerarIA', 'tourMenuPreguntas', 'tourMenuExamenes', 'tourMenuAcademico',
               'tourMenuFormatosPlantillas', 'tourMenuGrupos', 'bi-shield-lock-fill']
        posiciones = [lateral.index(i) for i in ids]
        self.assertEqual(posiciones, sorted(posiciones))

    def test_contenidos_vive_dentro_de_mi_espacio_academico(self):
        lateral = self._lateral('avanzado')
        academico = lateral.split('id="tourMenuAcademico"')[1].split('id="tourMenuFormatosPlantillas"')[0]
        self.assertIn('id="tourMenuContenidos"', academico)
        # "Mis agregados" abre el submenú; plantillas, rúbricas y formatos ya no están acá
        self.assertLess(academico.index('Mis agregados'), academico.index('Instituciones'))
        for movido in ('tourMenuPlantillas', 'tourMenuFormatos"', 'Rúbricas'):
            self.assertNotIn(movido, academico)
        self.assertEqual(lateral.count('id="tourMenuContenidos"'), 1)
        self.assertNotIn('Asistente paso a paso', academico)

    def test_la_configuracion_de_ia_ya_no_esta_en_el_menu_lateral(self):
        for modo in ('simple', 'avanzado'):
            html = self._lateral(modo)
            self.assertNotIn(reverse('material:ai_config'), html)
            self.assertNotIn('Proveedor de IA', html)

    def test_la_configuracion_de_ia_se_encuentra_en_generar_con_ia_con_su_nombre(self):
        u = _docente('ml_doc', 'avanzado')
        c = Client()
        c.force_login(u)
        html = c.get(reverse('material:document_processor_dashboard')).content.decode()
        self.assertIn('id="docAiConfigBtn"', html)
        boton = html.split('id="docAiConfigBtn"')[1].split('</a>')[0]
        self.assertIn('Configuración de IA', boton)

    def test_formatos_y_plantillas_es_un_menu_propio(self):
        lateral = self._lateral('avanzado')
        grupo = lateral.split('id="tourMenuFormatosPlantillas"')[1].split('id="tourMenuGrupos"')[0]
        for presente in ('id="tourMenuPlantillas"', 'Rúbricas', 'id="tourMenuFormatos"'):
            self.assertIn(presente, grupo)


class ContadoresTests(TestCase):
    """Los contadores de Inicio y de Mis Preguntas comparten un solo componente (.edu-stat)."""

    def setUp(self):
        self.c = Client()
        self.c.force_login(_docente('ct_docente', 'avanzado'))

    def test_inicio_tiene_cuatro_contadores_con_color_y_enlace(self):
        html = self.c.get(reverse('material:index')).content.decode()
        self.assertEqual(html.count('class="edu-stat edu-stat--'), 4)
        self.assertEqual(html.count('edu-stat--link'), 4)
        for color in ('primary', 'info', 'warning', 'secondary'):
            self.assertIn(f'edu-stat--{color}', html)

    def test_mis_preguntas_usa_el_mismo_componente(self):
        html = self.c.get(reverse('material:lista_preguntas')).content.decode()
        fila = html.split('id="questionStatsRow"')[1].split('id="templateFiltersForm"')[0]
        self.assertEqual(fila.count('class="edu-stat edu-stat--'), 3)
        for etiqueta in ('Preguntas', 'Materias', 'Tópicos'):
            self.assertIn(etiqueta, fila)
        for quitada in ('Sub-tópicos', 'Generadas por IA'):
            self.assertNotIn(quitada, fila)
        self.assertNotIn('stat-tab', html)

    def test_inicio_ya_no_tiene_contenidos_subidos(self):
        html = self.c.get(reverse('material:index')).content.decode()
        self.assertNotIn('Contenidos subidos', html)
        for etiqueta in ('Preguntas en el banco', 'Exámenes armados', 'Favoritos', 'Espacio personal'):
            self.assertIn(etiqueta, html)


class MenuExamenesTests(TestCase):
    def test_el_menu_se_llama_mis_examenes_con_escritos_y_orales(self):
        c = Client()
        c.force_login(_docente('me_docente', 'avanzado'))
        html = c.get(reverse('material:index')).content.decode()
        lateral = html.split('id="tourMenuExamenes"')[1].split('id="tourMenuAcademico"')[0]
        self.assertIn('Mis exámenes', lateral)
        self.assertIn('Escritos</a>', lateral)
        self.assertIn('Orales</a>', lateral)
        self.assertNotIn('Cuestionarios Orales', lateral)

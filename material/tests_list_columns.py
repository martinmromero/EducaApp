"""Vista configurable de listados (columnas, orden y líneas del texto largo
por usuario): resolución de la configuración, validación y endpoint de
guardado, y que los templates registrados marquen todas sus columnas con
data-col y manden el texto de la pregunta completo."""
import json
import re

from django.test import TestCase, Client
from django.urls import reverse

from .list_columns import LIST_REGISTRY, resolve_config, sanitize
from .models import Question, Subject, Topic
from .tests_catalogo_qa import make_user


def _ready(user):
    """Un usuario que ya pasó el onboarding, para que el middleware no lo
    redirija y los listados rindan 200."""
    profile = user.profile
    profile.onboarding_completed = True
    profile.security_question = 'primera_mascota'
    profile.security_answer = 'x'
    profile.save()
    return user


class ResolveConfigTests(TestCase):
    def test_sin_preferencias_usa_defaults_del_registro(self):
        user = make_user('lc_defaults')
        cfg = resolve_config(user.profile, 'preguntas')
        keys = [c['key'] for c in cfg['columns']]
        self.assertEqual(keys, [c['key'] for c in LIST_REGISTRY['preguntas']['columns']])
        visibles = {c['key'] for c in cfg['columns'] if c['visible']}
        self.assertIn('pregunta', visibles)
        self.assertNotIn('tipo', visibles)
        self.assertEqual(cfg['lines'], 3)

    def test_respeta_orden_y_visibilidad_guardados(self):
        user = make_user('lc_saved')
        user.profile.list_view_prefs = {'preguntas': {
            'order': ['pregunta', 'materia', 'topico', 'subtopico', 'bloom', 'estado', 'origen', 'tipo', 'creada'],
            'visible': ['pregunta', 'tipo'],
            'lines': 0,
        }}
        cfg = resolve_config(user.profile, 'preguntas')
        self.assertEqual(cfg['columns'][0]['key'], 'pregunta')
        self.assertEqual({c['key'] for c in cfg['columns'] if c['visible']}, {'pregunta', 'tipo'})
        self.assertEqual(cfg['lines'], 0)
        self.assertIn('[data-col="materia"]{display:none}', cfg['hidden_css'])
        self.assertNotIn('[data-col="pregunta"]', cfg['hidden_css'])

    def test_columna_nueva_va_al_final_con_su_default(self):
        user = make_user('lc_new_col')
        # El usuario guardó antes de que existieran 'tipo' y 'creada'.
        user.profile.list_view_prefs = {'preguntas': {
            'order': ['pregunta', 'materia'], 'visible': ['pregunta'], 'lines': 2,
        }}
        cfg = resolve_config(user.profile, 'preguntas')
        keys = [c['key'] for c in cfg['columns']]
        self.assertEqual(keys[:2], ['pregunta', 'materia'])
        self.assertEqual(len(keys), len(LIST_REGISTRY['preguntas']['columns']))
        by_key = {c['key']: c['visible'] for c in cfg['columns']}
        self.assertFalse(by_key['materia'])   # la apagó a propósito
        self.assertTrue(by_key['bloom'])      # nunca la vio: default visible
        self.assertFalse(by_key['tipo'])      # nunca la vio: default oculta

    def test_claves_desconocidas_guardadas_se_ignoran(self):
        user = make_user('lc_stale')
        user.profile.list_view_prefs = {'preguntas': {
            'order': ['borrada', 'pregunta'], 'visible': ['borrada', 'pregunta'], 'lines': 99,
        }}
        cfg = resolve_config(user.profile, 'preguntas')
        self.assertNotIn('borrada', [c['key'] for c in cfg['columns']])
        self.assertEqual(cfg['lines'], 3)  # valor inválido: vuelve al default


class SanitizeTests(TestCase):
    def test_rechaza_columna_inventada(self):
        with self.assertRaises(ValueError):
            sanitize('preguntas', {'order': ['pregunta', 'hack'], 'visible': ['pregunta']})

    def test_rechaza_sin_columnas_visibles(self):
        with self.assertRaises(ValueError):
            sanitize('preguntas', {'order': ['pregunta'], 'visible': []})

    def test_rechaza_lineas_invalidas(self):
        for bad in (4, -1, '3', True):
            with self.assertRaises(ValueError):
                sanitize('preguntas', {'order': ['pregunta'], 'visible': ['pregunta'], 'lines': bad})

    def test_listado_sin_texto_largo_ignora_lineas(self):
        clean = sanitize('mis_examenes', {'order': ['nombre'], 'visible': ['nombre'], 'lines': 2})
        self.assertNotIn('lines', clean)

    def test_quita_duplicados(self):
        clean = sanitize('preguntas', {'order': ['pregunta', 'pregunta', 'materia'], 'visible': ['pregunta']})
        self.assertEqual(clean['order'], ['pregunta', 'materia'])


class SaveListViewEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = _ready(make_user('lc_user'))
        cls.other = _ready(make_user('lc_other'))

    def setUp(self):
        self.client = Client()
        self.client.login(username='lc_user', password='testpass123')
        self.url = reverse('material:save_list_view', args=['preguntas'])

    def post(self, body, url=None):
        return self.client.post(url or self.url, data=json.dumps(body), content_type='application/json')

    def test_requiere_login(self):
        resp = Client().post(self.url, data='{}', content_type='application/json')
        self.assertEqual(resp.status_code, 302)

    def test_solo_acepta_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_listado_desconocido_da_404(self):
        resp = self.post({}, reverse('material:save_list_view', args=['inexistente']))
        self.assertEqual(resp.status_code, 404)

    def test_guarda_y_devuelve_configuracion_efectiva(self):
        resp = self.post({'order': ['pregunta', 'bloom'], 'visible': ['pregunta'], 'lines': 1})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['config']['lines'], 1)
        self.assertNotIn('hidden_css', data['config'])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.list_view_prefs['preguntas']['visible'], ['pregunta'])

    def test_datos_invalidos_dan_400_y_no_guardan(self):
        for body in ({'order': ['x'], 'visible': ['x']}, {'order': ['pregunta'], 'visible': []}):
            self.assertEqual(self.post(body).status_code, 400)
        resp = self.client.post(self.url, data='no es json', content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        resp = self.client.post(self.url, data='[1,2]', content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.list_view_prefs, {})

    def test_cada_usuario_y_cada_listado_son_independientes(self):
        self.post({'order': ['pregunta'], 'visible': ['pregunta'], 'lines': 2})
        self.post({'order': ['nombre'], 'visible': ['nombre']},
                  reverse('material:save_list_view', args=['mis_examenes']))
        self.user.profile.refresh_from_db()
        self.other.profile.refresh_from_db()
        self.assertEqual(set(self.user.profile.list_view_prefs), {'preguntas', 'mis_examenes'})
        self.assertEqual(self.other.profile.list_view_prefs, {})

    def test_reset_borra_solo_ese_listado(self):
        self.post({'order': ['pregunta'], 'visible': ['pregunta'], 'lines': 2})
        self.post({'order': ['nombre'], 'visible': ['nombre']},
                  reverse('material:save_list_view', args=['mis_examenes']))
        resp = self.post({'reset': True})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['config']['lines'], 3)
        self.user.profile.refresh_from_db()
        self.assertEqual(set(self.user.profile.list_view_prefs), {'mis_examenes'})


class ListadosRenderTests(TestCase):
    """Los listados registrados tienen que marcar cada columna del registro
    con data-col (si no, el panel Columnas no la encuentra) y mandar el texto
    de la pregunta completo, sin cortarlo en el servidor."""

    @classmethod
    def setUpTestData(cls):
        cls.user = _ready(make_user('lc_render'))
        cls.subject = Subject.objects.create(name='Materia LC', created_by=cls.user, es_catalogo_institucional=False)
        cls.topic = Topic.objects.create(name='Tópico LC', subject=cls.subject)
        cls.texto_largo = 'Explique detalladamente ' + ('el proceso completo y sus consecuencias ' * 6) + 'FIN-DEL-TEXTO'
        cls.pregunta = Question.objects.create(
            user=cls.user, topic=cls.topic, question_text=cls.texto_largo, answer_text='r',
        )
        cls.pregunta.subjects.add(cls.subject)

    def setUp(self):
        self.client = Client()
        self.client.login(username='lc_render', password='testpass123')

    def test_preguntas_marca_columnas_y_no_trunca_el_texto(self):
        resp = self.client.get(reverse('material:lista_preguntas'))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('FIN-DEL-TEXTO', html)
        head = re.search(r'<thead>(.*?)</thead>', html, re.S).group(1)
        marcadas = set(re.findall(r'data-col="(\w+)"', head))
        esperadas = {c['key'] for c in LIST_REGISTRY['preguntas']['columns']}
        # Sub-tópico solo aparece si hay subtópicos cargados.
        self.assertEqual(marcadas, esperadas - {'subtopico'})
        self.assertIn('id="lcCfg"', html)
        self.assertIn('id="listColumnsBtn"', html)

    def test_columna_oculta_sale_en_el_css_inicial(self):
        self.client.post(
            reverse('material:save_list_view', args=['preguntas']),
            data=json.dumps({'order': ['pregunta', 'materia'], 'visible': ['pregunta']}),
            content_type='application/json',
        )
        html = self.client.get(reverse('material:lista_preguntas')).content.decode()
        self.assertIn('.lc-table [data-col="materia"]{display:none}', html)
        self.assertNotIn('.lc-table [data-col="pregunta"]{display:none}', html)

    def test_mis_examenes_marca_columnas(self):
        from .models import Exam
        Exam.objects.create(created_by=self.user, title='Parcial LC', subject=self.subject)
        resp = self.client.get(reverse('material:mis_examenes'))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        head = re.search(r'<thead>(.*?)</thead>', html, re.S).group(1)
        marcadas = set(re.findall(r'data-col="(\w+)"', head))
        self.assertEqual(marcadas, {c['key'] for c in LIST_REGISTRY['mis_examenes']['columns']})

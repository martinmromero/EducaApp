"""XSS almacenado: texto que escribe un usuario (y puede llegar a otro por un
grupo de confianza) no debe poder ejecutar código en el navegador de quien lo
ve. Cubre el lado servidor (JSON embebido en <script>) y que el helper de
escape del lado cliente esté disponible en todas las páginas."""
import json

from django.template import Context, Template
from django.test import Client, TestCase
from django.urls import reverse

from .models import Question, Subject, Topic
from .tests_catalogo_qa import make_user
from .tests_list_columns import _ready

CIERRE_SCRIPT = '</script><script>window.__xss = 1</script>'


class JsonEmbedFilterTests(TestCase):
    def render(self, value):
        return Template('{% load filter_tags %}{{ v|json_embed }}').render(Context({'v': value}))

    def test_no_deja_pasar_etiquetas(self):
        salida = self.render(json.dumps({'texto': CIERRE_SCRIPT}))
        self.assertNotIn('<', salida)
        self.assertNotIn('>', salida)

    def test_sigue_siendo_json_equivalente(self):
        original = {'texto': CIERRE_SCRIPT + ' & más', 'n': 3, 'lista': ['a<b', "c'd"]}
        self.assertEqual(json.loads(self.render(json.dumps(original))), original)

    def test_escapa_separadores_de_linea_unicode(self):
        salida = self.render(json.dumps({'t': 'a b c'}, ensure_ascii=False))
        self.assertNotIn(' ', salida)
        self.assertNotIn(' ', salida)

    def test_none_da_vacio(self):
        self.assertEqual(self.render(None), '')


class ScriptEmbedEnPaginasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = _ready(make_user('xss_user'))
        cls.materia = Subject.objects.create(name='Materia XSS', created_by=cls.user, es_catalogo_institucional=False)
        cls.topic = Topic.objects.create(name='Tópico XSS', subject=cls.materia)
        cls.pregunta = Question.objects.create(
            user=cls.user, topic=cls.topic, question_text='¿Qué?', answer_text='r',
            options_json=json.dumps([CIERRE_SCRIPT, 'opción B']),
        )
        cls.pregunta.subjects.add(cls.materia)

    def setUp(self):
        self.client = Client()
        self.client.login(username='xss_user', password='testpass123')

    def test_editar_pregunta_no_deja_cerrar_el_script(self):
        resp = self.client.get(reverse('material:editar_pregunta', args=[self.pregunta.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('<script>window.__xss', resp.content.decode())

    def test_el_helper_de_escape_se_carga_en_todas_las_paginas(self):
        resp = self.client.get(reverse('material:lista_preguntas'))
        self.assertContains(resp, 'html_escape')

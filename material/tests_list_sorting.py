"""Orden por columna en los listados (?sort=<columna>&dir=asc|desc): el
registro declara qué columnas ordenan, el servidor ordena TODO el listado
(no solo la página) y la URL con el orden sobrevive a paginar y a filtrar."""
import re

from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse

from .list_columns import LIST_REGISTRY, get_sort, resolve_config, sort_items, text_key
from .models import (
    CampusV2, Career, CareerSubject, Exam, ExamTemplate, ExamVersionBatch, Favorite, FacultyV2,
    FormatoImpresion, InstitutionV2, OralExamSet, Question, Rubric, Subject, Subtopic, Topic,
)
from .tests_catalogo_qa import make_user
from .tests_list_columns import _ready

# Listado -> nombre de la URL. 'contenidos' se prueba aparte (necesita un archivo).
URLS = {
    'preguntas': 'material:lista_preguntas',
    'mis_examenes': 'material:mis_examenes',
    'plantillas': 'material:list_exam_templates',
    'orales': 'material:list_oral_exams',
    'instituciones': 'material:institution_v2_list',
    'materias': 'material:subject_list',
    'carreras': 'material:career_list',
    'favoritos': 'material:favoritos_list',
    'rubricas': 'material:rubric_list',
    'formatos': 'material:formato_impresion_list',
    'espacio_personal': 'material:espacio_personal_list',
    'usuarios': 'material:user_list',
}


class RegistroTests(TestCase):
    def test_todo_listado_tiene_alguna_columna_ordenable(self):
        for key, spec in LIST_REGISTRY.items():
            self.assertTrue(any(c['sort'] for c in spec['columns']), key)

    def test_la_configuracion_avisa_que_columnas_ordenan(self):
        cfg = resolve_config(None, 'instituciones')
        por_clave = {c['key']: c['sortable'] for c in cfg['columns']}
        self.assertTrue(por_clave['nombre'])
        self.assertFalse(por_clave['logo'])

    def test_get_sort_solo_acepta_claves_del_registro(self):
        class Req:
            def __init__(self, **get):
                self.GET = get
        self.assertEqual(get_sort(Req(sort='nombre', dir='desc'), 'materias'), ('nombre', 'desc'))
        self.assertEqual(get_sort(Req(sort='nombre', dir='raro'), 'materias'), ('nombre', 'asc'))
        # 'resultados' existe pero no ordena; 'password' no existe.
        self.assertEqual(get_sort(Req(sort='resultados'), 'materias'), (None, None))
        self.assertEqual(get_sort(Req(sort='password'), 'materias'), (None, None))
        self.assertEqual(get_sort(Req(), 'materias'), (None, None))

    def test_sort_items_deja_los_vacios_al_final_en_cualquier_sentido(self):
        class Req:
            def __init__(self, direction):
                self.GET = {'sort': 'nombre', 'dir': direction}
        items = [{'n': 'beta'}, {'n': ''}, {'n': 'Álfa'}, {'n': None}]
        getters = {'nombre': lambda i: text_key(i['n'])}
        asc = [i['n'] for i in sort_items(Req('asc'), 'espacio_personal', items, getters)]
        desc = [i['n'] for i in sort_items(Req('desc'), 'espacio_personal', items, getters)]
        self.assertEqual(asc, ['Álfa', 'beta', '', None])
        self.assertEqual(desc, ['beta', 'Álfa', '', None])


class OrdenEnLosListadosTests(TestCase):
    """Cada columna ordenable, en los dos sentidos, tiene que dar 200 en su
    listado (la mayoría son consultas con DISTINCT y relaciones: ahí es donde
    un orden mal armado rompe en PostgreSQL), y el orden tiene que ser el pedido."""

    @classmethod
    def setUpTestData(cls):
        cls.user = _ready(make_user('so_user'))
        cls.admin = _ready(make_user('so_admin', role='admin'))
        u = cls.user
        cls.inst_a = InstitutionV2.objects.create(name='Zeta Institución', created_by=u, es_catalogo_institucional=False)
        cls.inst_b = InstitutionV2.objects.create(name='alfa Institución', created_by=u, es_catalogo_institucional=False)
        CampusV2.objects.create(institution=cls.inst_a, name='Sede Norte')
        CampusV2.objects.create(institution=cls.inst_a, name='Sede Sur')
        cls.fac = FacultyV2.objects.create(
            name='Facultad SO', institution=cls.inst_a, created_by=u, es_catalogo_institucional=False,
        )
        cls.carrera_a = Career.objects.create(name='Carrera Zeta', created_by=u, es_catalogo_institucional=False)
        cls.carrera_b = Career.objects.create(name='Carrera Alfa', created_by=u, es_catalogo_institucional=False)
        cls.carrera_a.faculties.add(cls.fac)
        cls.mat_a = Subject.objects.create(name='Zoología', created_by=u, es_catalogo_institucional=False)
        cls.mat_b = Subject.objects.create(name='Álgebra', created_by=u, es_catalogo_institucional=False)
        CareerSubject.objects.create(career=cls.carrera_a, subject=cls.mat_a)
        CareerSubject.objects.create(career=cls.carrera_b, subject=cls.mat_a)
        CareerSubject.objects.create(career=cls.carrera_b, subject=cls.mat_b)
        topic = Topic.objects.create(name='Tópico SO', subject=cls.mat_a)
        subtopic = Subtopic.objects.create(name='Sub SO', topic=topic)
        for texto, bloom, ia in (('Zorro pregunta', 3, False), ('Abeja pregunta', 1, True), ('Mono pregunta', None, False)):
            q = Question.objects.create(
                user=u, topic=topic, subtopic=subtopic, question_text=texto, answer_text='r',
                bloom_level=bloom, generated_by_ai=ia,
            )
            q.subjects.add(cls.mat_a, cls.mat_b)
        exam = Exam.objects.create(created_by=u, title='Parcial Zeta', subject=cls.mat_a)
        Exam.objects.create(created_by=u, title='Final alfa', subject=cls.mat_b)
        ExamVersionBatch.objects.create(name='Lote Mono', created_by=u, subject=cls.mat_a, version_count=3)
        ExamTemplate.objects.create(
            created_by=u, name='Plantilla Zeta', institution=cls.inst_a, faculty=cls.fac,
            career=cls.carrera_a, subject=cls.mat_a, institution_name_snapshot='Zeta Institución',
        )
        ExamTemplate.objects.create(
            created_by=u, name='Plantilla alfa', institution=cls.inst_b, faculty=cls.fac,
            career=cls.carrera_a, subject=cls.mat_b,
        )
        OralExamSet.objects.create(
            user=u, name='Oral Zeta', subject=cls.mat_a, num_groups=2, students_per_group=3,
            questions_per_student=2, total_students=6,
        )
        OralExamSet.objects.create(
            user=u, name='Oral alfa', subject=cls.mat_b, num_groups=1, students_per_group=1,
            questions_per_student=1, total_students=1,
        )
        Rubric.objects.create(title='Rúbrica Zeta', created_by=u)
        Rubric.objects.create(title='Rúbrica alfa', created_by=u)
        FormatoImpresion.objects.create(nombre='Formato Zeta', user=u)
        FormatoImpresion.objects.create(nombre='Formato alfa', user=u)
        for model, pk in ((Subject, cls.mat_a.pk), (Exam, exam.pk)):
            Favorite.objects.create(user=u, content_type=ContentType.objects.get_for_model(model), object_id=pk)

    def _get(self, username, key, **params):
        client = Client()
        client.login(username=username, password='testpass123')
        return client.get(reverse(URLS[key]), params)

    def test_toda_columna_ordenable_responde_en_los_dos_sentidos(self):
        for key, spec in LIST_REGISTRY.items():
            if key not in URLS:
                continue
            username = 'so_admin' if key == 'usuarios' else 'so_user'
            for col in spec['columns']:
                if not col['sort']:
                    continue
                for direction in ('asc', 'desc'):
                    resp = self._get(username, key, sort=col['key'], dir=direction)
                    self.assertEqual(resp.status_code, 200, '%s / %s / %s' % (key, col['key'], direction))

    def test_columna_inexistente_o_no_ordenable_se_ignora(self):
        for sort in ('nope', 'resultados', '__class__', 'pk; DROP TABLE'):
            resp = self._get('so_user', 'materias', sort=sort)
            self.assertEqual(resp.status_code, 200, sort)

    @staticmethod
    def _posiciones(html, textos):
        return [html.index(t) for t in textos]

    def test_preguntas_ordena_por_texto_en_los_dos_sentidos(self):
        textos = ['Abeja pregunta', 'Mono pregunta', 'Zorro pregunta']
        html = self._get('so_user', 'preguntas', sort='pregunta', dir='asc').content.decode()
        self.assertEqual(self._posiciones(html, textos), sorted(self._posiciones(html, textos)))
        html = self._get('so_user', 'preguntas', sort='pregunta', dir='desc').content.decode()
        self.assertEqual(self._posiciones(html, textos), sorted(self._posiciones(html, textos), reverse=True))

    def test_preguntas_con_materias_multiples_no_repite_filas(self):
        # Cada pregunta tiene dos materias: ordenar por materia no puede duplicarla.
        html = self._get('so_user', 'preguntas', sort='materia').content.decode()
        self.assertEqual(html.count('Abeja pregunta'), 1)

    def test_materias_ordena_sin_distinguir_tildes_ni_mayusculas(self):
        html = self._get('so_user', 'materias', sort='nombre', dir='asc').content.decode()
        self.assertLess(html.index('Álgebra'), html.index('Zoología'))
        html = self._get('so_user', 'materias', sort='nombre', dir='desc').content.decode()
        self.assertLess(html.index('Zoología'), html.index('Álgebra'))

    def test_materias_con_varias_carreras_no_se_repite(self):
        html = self._get('so_user', 'materias', sort='carreras').content.decode()
        self.assertEqual(html.count('Zoología'), 1)

    def test_instituciones_ordena_ignorando_mayusculas(self):
        html = self._get('so_user', 'instituciones', sort='nombre', dir='asc').content.decode()
        self.assertLess(html.index('alfa Institución'), html.index('Zeta Institución'))

    def test_instituciones_ordenar_por_sedes_no_duplica(self):
        html = self._get('so_user', 'instituciones', sort='sedes').content.decode()
        self.assertEqual(html.count('Zeta Institución'), 1)

    def test_plantillas_ordena_por_nombre_de_institucion_guardado_o_de_la_relacion(self):
        html = self._get('so_user', 'plantillas', sort='institucion', dir='asc').content.decode()
        self.assertLess(html.index('Plantilla alfa'), html.index('Plantilla Zeta'))

    def test_orales_ordena_por_total_de_estudiantes(self):
        html = self._get('so_user', 'orales', sort='total', dir='desc').content.decode()
        self.assertLess(html.index('Oral Zeta'), html.index('Oral alfa'))

    def test_mis_examenes_mezcla_lotes_y_examenes_y_ordena_por_nombre(self):
        html = self._get('so_user', 'mis_examenes', sort='nombre', dir='asc').content.decode()
        orden = [html.index(n) for n in ('Final alfa', 'Lote Mono', 'Parcial Zeta')]
        self.assertEqual(orden, sorted(orden))

    def test_favoritos_ordena_por_tipo(self):
        html = self._get('so_user', 'favoritos', sort='tipo', dir='asc').content.decode()
        self.assertLess(html.index('Examen</span>'), html.index('Materia</span>'))

    def test_rubricas_formatos_y_espacio_personal(self):
        html = self._get('so_user', 'rubricas', sort='titulo', dir='asc').content.decode()
        self.assertLess(html.index('Rúbrica alfa'), html.index('Rúbrica Zeta'))
        html = self._get('so_user', 'formatos', sort='nombre', dir='desc').content.decode()
        self.assertLess(html.index('Formato Zeta'), html.index('Formato alfa'))
        html = self._get('so_user', 'espacio_personal', sort='nombre', dir='asc').content.decode()
        self.assertLess(html.index('alfa Institución'), html.index('Zeta Institución'))

    def test_usuarios_ordena_por_nombre_de_usuario(self):
        html = self._get('so_admin', 'usuarios', sort='usuario', dir='asc').content.decode()
        self.assertLess(html.index('so_admin'), html.index('so_user'))

    def test_el_orden_se_conserva_al_paginar(self):
        for i in range(30):
            Question.objects.create(user=self.user, question_text='Pregunta relleno %02d' % i, answer_text='r')
        html = self._get('so_user', 'preguntas', sort='pregunta', dir='desc').content.decode()
        enlaces = re.findall(r'href="(\?page=2[^"]*)"', html)
        self.assertTrue(enlaces)
        self.assertIn('sort=pregunta', enlaces[0])
        self.assertIn('dir=desc', enlaces[0])

    def test_la_pantalla_trae_el_selector_de_orden(self):
        html = self._get('so_user', 'materias').content.decode()
        self.assertIn('id="listSortSelect"', html)
        self.assertIn('"sortable": true', html)

"""Estado del cuestionario oral dentro del Asistente paso a paso (2026-10-25).

O4: con una sola pregunta el oral tiene que ofrecer su tópico, y el host necesita poder detectar que
cambió el contenido de la materia (firma preguntas-tópicos-unidades de full_wizard_subject_progress)
para recargar el marco. D16: guardar un oral embebido crea el OralExamSet y la pantalla de guardado
solo existe para su dueño. Corre contra una base descartable."""
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import OralExamSet, Question, Subject, Topic

User = get_user_model()


def make_user(username):
    user = User.objects.create_user(username=username, password='testpass123')
    user.profile.security_question = 'comida_favorita'
    user.profile.save()
    return user


class OralConPocasPreguntasTests(TestCase):
    def setUp(self):
        self.ana = make_user('oe_ana')
        self.beto = make_user('oe_beto')
        self.materia = Subject.objects.create(name='Una sola', created_by=self.ana, es_catalogo_institucional=False)
        self.topico = Topic.objects.create(
            name='Unico', subject=self.materia, es_catalogo_institucional=False, created_by=self.ana)
        self.client = Client()
        self.client.force_login(self.ana)

    def _pregunta(self, texto, topico=None):
        q = Question.objects.create(user=self.ana, question_text=texto, answer_text='r', topic=topico)
        q.subjects.add(self.materia)
        return q

    def _topicos_del_oral(self):
        r = self.client.get(reverse('material:get_topics'), {
            'subject_id': self.materia.pk, 'for_exam': '1', 'include_no_topic': '1'})
        return [t['name'] for t in r.json()]

    def _progreso(self):
        return self.client.get(reverse('material:full_wizard_subject_progress'), {'subject_id': self.materia.pk}).json()

    def test_con_una_sola_pregunta_el_oral_ofrece_su_topico(self):
        self.assertEqual(self._topicos_del_oral(), [])
        self._pregunta('Única', self.topico)
        self.assertEqual(self._topicos_del_oral(), ['Unico'])

    def test_la_firma_de_progreso_cambia_al_sumar_preguntas_y_topicos(self):
        # El host (full_wizard.js) recarga el marco del paso Examen cuando esta firma cambia.
        def firma():
            d = self._progreso()
            return (d['question_count'], d['topic_count'], d['oral_units'])
        self._pregunta('Una', self.topico)
        antes = firma()
        self._pregunta('Dos', self.topico)
        despues_misma_unidad = firma()
        self.assertNotEqual(antes, despues_misma_unidad)
        otro = Topic.objects.create(name='Otro', subject=self.materia, es_catalogo_institucional=False, created_by=self.ana)
        self._pregunta('Tres', otro)
        self.assertNotEqual(despues_misma_unidad, firma())
        self.assertEqual(firma(), (3, 2, 2))

    def test_el_host_compara_la_firma_antes_de_reutilizar_el_marco(self):
        from pathlib import Path
        js = (Path(__file__).parent / 'static' / 'material' / 'js' / 'full_wizard.js').read_text(encoding='utf-8')
        self.assertIn("exam.sig !== sig", js)
        self.assertIn("exam.url = null; // cambió el contenido", js)


class GuardadoDelOralEmbebidoTests(TestCase):
    def setUp(self):
        self.ana = make_user('og_ana')
        self.beto = make_user('og_beto')
        self.materia = Subject.objects.create(name='Historia', created_by=self.ana, es_catalogo_institucional=False)
        self.topico = Topic.objects.create(
            name='Siglo XX', subject=self.materia, es_catalogo_institucional=False, created_by=self.ana)
        for i in range(4):
            q = Question.objects.create(user=self.ana, question_text=f'P{i}', answer_text='r', topic=self.topico)
            q.subjects.add(self.materia)
        self.client = Client()
        self.client.force_login(self.ana)

    def _crear(self):
        return self.client.post(reverse('material:create_oral_exam'), {
            'name': 'Oral', 'subject': self.materia.pk, 'topics': [self.topico.pk],
            'total_students': 2, 'questions_per_student': 1, 'num_groups': 1, 'students_per_group': 2, 'fw': '1',
        })

    def test_dos_orales_seguidos_se_crean_los_dos_y_cada_pantalla_de_guardado_apunta_al_suyo(self):
        # Mismo recorrido que "Armar otro cuestionario": el segundo no pisa ni reutiliza el primero.
        primero = self._crear()
        segundo = self._crear()
        self.assertEqual(OralExamSet.objects.filter(user=self.ana).count(), 2)
        ids = list(OralExamSet.objects.filter(user=self.ana).order_by('id').values_list('id', flat=True))
        self.assertIn(f'guardado={ids[0]}', primero['Location'])
        self.assertIn(f'guardado={ids[1]}', segundo['Location'])
        pantalla = self.client.get(segundo['Location'])
        self.assertEqual(pantalla.status_code, 200)
        self.assertEqual(json.loads(pantalla.context['oral_saved_json'])['view_url'],
                         reverse('material:view_oral_exam', kwargs={'exam_id': ids[1]}))

    def test_la_pantalla_de_guardado_no_existe_para_otra_cuenta(self):
        self._crear()
        guardado = OralExamSet.objects.get(user=self.ana)
        otro = Client()
        otro.force_login(self.beto)
        resp = otro.get(reverse('material:create_oral_exam_wizard'), {'fw': '1', 'guardado': guardado.pk})
        self.assertEqual(resp.context['oral_saved_json'], 'null')

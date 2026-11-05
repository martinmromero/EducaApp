"""Cuestionario oral dentro del Asistente paso a paso (iframe, ?fw=1).

El asistente oral se enmarca con la materia ya fijada, el guardado vuelve a una
pantalla propia (el cuestionario y el formulario clásico no se pueden enmarcar) y
los errores y avisos viajan por la sesión en vez de quedar encolados como mensajes
para otra pantalla. Corre contra una base descartable."""
import json

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from .models import OralExamSet, Question, Subject, Subtopic, Topic

User = get_user_model()


def make_user(username):
    user = User.objects.create_user(username=username, password='testpass123')
    user.profile.security_question = 'comida_favorita'
    user.profile.save()
    return user


def login(username):
    client = Client()
    client.login(username=username, password='testpass123')
    return client


class OralEnElAsistenteTests(TestCase):
    def setUp(self):
        self.ana = make_user('oa_ana')
        self.beto = make_user('oa_beto')
        self.materia = Subject.objects.create(name='Historia', created_by=self.ana, es_catalogo_institucional=False)
        self.otra = Subject.objects.create(name='Geografía', created_by=self.ana, es_catalogo_institucional=False)
        self.topic = Topic.objects.create(name='Siglo XX', subject=self.materia, es_catalogo_institucional=False, created_by=self.ana)
        self.sub = Subtopic.objects.create(name='Guerras', topic=self.topic, es_catalogo_institucional=False, created_by=self.ana)
        for materia in (self.materia, self.otra):
            for i in range(3):
                q = Question.objects.create(
                    user=self.ana, question_text=f'{materia.name} {i}', answer_text='r',
                    topic=self.topic if materia == self.materia else None,
                    subtopic=self.sub if materia == self.materia else None,
                )
                q.subjects.add(materia)
        self.client_ana = login('oa_ana')

    def wizard(self, **params):
        base = {'fw': '1'}
        base.update(params)
        return self.client_ana.get(reverse('material:create_oral_exam_wizard'), base)

    def datos(self, **extra):
        data = {
            'name': 'Oral QA', 'subject': self.materia.pk, 'topics': [self.topic.pk],
            'total_students': 2, 'questions_per_student': 1, 'num_groups': 1, 'students_per_group': 2, 'fw': '1',
        }
        data.update(extra)
        return data

    def test_se_puede_enmarcar_y_fija_la_materia(self):
        resp = self.wizard(subject_id=self.materia.pk)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['X-Frame-Options'], 'SAMEORIGIN')
        self.assertTrue(resp.context['is_embedded'])
        self.assertEqual(resp.context['fw_subject'], self.materia)
        self.assertEqual(list(resp.context['materias']), [self.materia])
        self.assertContains(resp, 'name="fw" value="1"')
        self.assertContains(resp, 'type="hidden" name="subject"')
        self.assertNotContains(resp, 'Usar la pantalla completa de siempre')

    def test_sin_fw_sigue_siendo_el_asistente_de_siempre(self):
        resp = self.client_ana.get(reverse('material:create_oral_exam_wizard'))
        self.assertFalse(resp.context['is_embedded'])
        self.assertContains(resp, 'Usar la pantalla completa de siempre')
        self.assertEqual({m.pk for m in resp.context['materias']}, {self.materia.pk, self.otra.pk})

    def test_el_envio_avisa_que_esta_creando_y_los_topes_se_validan_al_cargar(self):
        resp = self.client_ana.get(reverse('material:create_oral_exam_wizard'))
        # el botón final dice qué pasa mientras el servidor trabaja (submit_guard.js), no un «Guardando…» genérico
        self.assertContains(resp, 'data-texto-espera="Creando el cuestionario…"')
        # los topes (alumnos, grupos, preguntas) los lee el JS del atributo max de cada campo: siguen estando en el HTML
        for campo, tope in (('id_total_students', '100'), ('id_num_groups', '10'), ('id_questions_per_student', '10')):
            self.assertRegex(resp.content.decode(), r'max="%s"[^>]*id="%s"' % (tope, campo))

    def test_una_materia_ajena_o_invisible_no_se_fija(self):
        resp = login('oa_beto').get(reverse('material:create_oral_exam_wizard'), {'fw': '1', 'subject_id': self.materia.pk})
        self.assertIsNone(resp.context['fw_subject'])

    def test_guardar_vuelve_al_asistente_sin_mensajes_encolados(self):
        resp = self.client_ana.post(reverse('material:create_oral_exam'), self.datos())
        oral = OralExamSet.objects.get(name='Oral QA')
        self.assertRedirects(
            resp, reverse('material:create_oral_exam_wizard') + f'?fw=1&guardado={oral.pk}',
            fetch_redirect_response=False,
        )
        self.assertEqual(list(get_messages(resp.wsgi_request)), [])

    def test_la_pantalla_de_guardado_trae_el_enlace_y_los_avisos(self):
        self.client_ana.post(reverse('material:create_oral_exam'), self.datos())
        oral = OralExamSet.objects.get(name='Oral QA')
        resp = self.wizard(guardado=oral.pk)
        saved = resp.context['oral_saved']
        self.assertEqual(saved['name'], 'Oral QA')
        self.assertEqual(saved['view_url'], reverse('material:view_oral_exam', kwargs={'exam_id': oral.pk}))
        self.assertContains(resp, 'Cuestionario oral guardado')
        payload = json.loads(resp.context['oral_saved_json'])
        self.assertEqual(payload['view_url'], saved['view_url'])
        # los avisos se muestran una sola vez
        self.assertEqual(self.wizard(guardado=oral.pk).context['oral_saved']['warnings'], [])

    def test_el_cuestionario_de_otro_usuario_no_se_muestra(self):
        self.client_ana.post(reverse('material:create_oral_exam'), self.datos())
        oral = OralExamSet.objects.get(name='Oral QA')
        resp = login('oa_beto').get(reverse('material:create_oral_exam_wizard'), {'fw': '1', 'guardado': oral.pk})
        self.assertIsNone(resp.context['oral_saved'])

    def test_un_error_vuelve_al_asistente_y_se_muestra_una_vez(self):
        resp = self.client_ana.post(reverse('material:create_oral_exam'), self.datos(num_groups=5))  # más grupos que alumnos
        self.assertRedirects(
            resp, reverse('material:create_oral_exam_wizard') + f'?fw=1&subject_id={self.materia.pk}',
            fetch_redirect_response=False,
        )
        self.assertFalse(OralExamSet.objects.filter(name='Oral QA').exists())
        self.assertEqual(list(get_messages(resp.wsgi_request)), [])
        con_error = self.wizard(subject_id=self.materia.pk)
        self.assertIn('grupos', con_error.context['oral_fw_error'])
        self.assertContains(con_error, 'alert-danger')
        self.assertEqual(self.wizard(subject_id=self.materia.pk).context['oral_fw_error'], '')

    def test_sin_fw_el_comportamiento_clasico_no_cambia(self):
        datos = self.datos()
        datos.pop('fw')
        resp = self.client_ana.post(reverse('material:create_oral_exam'), datos)
        oral = OralExamSet.objects.get(name='Oral QA')
        self.assertRedirects(resp, reverse('material:view_oral_exam', kwargs={'exam_id': oral.pk}), fetch_redirect_response=False)
        self.assertTrue(any('creado' in str(m) for m in get_messages(resp.wsgi_request)))

    def test_el_progreso_cuenta_las_unidades_del_oral(self):
        data = self.client_ana.get(reverse('material:full_wizard_subject_progress'), {'subject_id': self.materia.pk}).json()
        self.assertEqual(data['oral_units'], 1)  # un solo sub-tópico con preguntas
        sin_tema = self.client_ana.get(reverse('material:full_wizard_subject_progress'), {'subject_id': self.otra.pk}).json()
        self.assertEqual(sin_tema['oral_units'], 1)  # preguntas sin tópico: una sola unidad "sin tópico"


class OralConMuchosAlumnosTests(TestCase):
    """Cuestionario oral grande (2026-11-05): crear y ver 30 alumnos con una materia de 120 preguntas tarda pocas consultas.

    Antes la creación hacía una consulta por alumno y por pregunta (144) y la pantalla del cuestionario más de 500
    (cinco consultas por cada conteo de evaluaciones, tres conteos por alumno): con una base remota eran segundos de espera."""

    def setUp(self):
        self.user = make_user('oral_grande')
        self.materia = Subject.objects.create(name='Materia grande', created_by=self.user)
        self.temas = [Topic.objects.create(name=f'Tema {i}', subject=self.materia) for i in range(30)]
        subtemas = [Subtopic.objects.create(name=f'Sub {i}', topic=self.temas[i % 30]) for i in range(60)]
        for i in range(120):
            q = Question.objects.create(
                user=self.user, question_text=f'Pregunta {i}', answer_text='r', topic=self.temas[i % 30],
                subtopic=subtemas[i % 60], question_type='desarrollo',
            )
            q.subjects.add(self.materia)
        self.client = login('oral_grande')

    def _crear(self):
        return self.client.post(reverse('material:create_oral_exam'), {
            'name': 'Oral grande', 'subject': self.materia.pk, 'topics': [t.pk for t in self.temas],
            'total_students': 30, 'num_groups': 2, 'students_per_group': 15, 'questions_per_student': 3,
        })

    def test_crear_y_ver_30_alumnos_usa_pocas_consultas(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as creacion:
            resp = self._crear()
        self.assertEqual(resp.status_code, 302)
        oral = OralExamSet.objects.get(name='Oral grande')
        self.assertEqual(oral.groups.count(), 2)
        self.assertEqual(sum(g.students.count() for g in oral.groups.all()), 30)
        asignadas = sum(s.oralexamstudentquestion_set.count() for g in oral.groups.all() for s in g.students.all())
        self.assertEqual(asignadas, 90)
        self.assertLess(len(creacion), 60, f'{len(creacion)} consultas al crear')
        with CaptureQueriesContext(connection) as pantalla:
            vista = self.client.get(reverse('material:view_oral_exam', args=[oral.pk]))
        self.assertEqual(vista.status_code, 200)
        self.assertLess(len(pantalla), 25, f'{len(pantalla)} consultas al ver el cuestionario')

    def test_los_conteos_de_evaluacion_siguen_bien(self):
        self._crear()
        oral = OralExamSet.objects.get(name='Oral grande')
        alumno = oral.groups.first().students.first()
        asignaciones = list(alumno.oralexamstudentquestion_set.all())
        asignaciones[0].evaluation = 'bien'
        asignaciones[1].evaluation = 'regular'
        for a in asignaciones[:2]:
            a.save()
        self.assertEqual(alumno.get_evaluation_counts(), {'bien': 1, 'regular': 1, 'mal': 0, 'pendiente': 1, 'total': 3})
        self.assertEqual(alumno.get_progress_percentage(), 66.7)
        self.assertEqual(alumno.get_score_percentage(), 75.0)

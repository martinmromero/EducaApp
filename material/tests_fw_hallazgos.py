"""Regresiones de los hallazgos de la revisión del Asistente completo (2026-10-05):

D1/D2  entrar al Asistente completo cuenta como haber hecho el recorrido
       inicial (OnboardingGateMiddleware ya no rebota a /comenzar/).
D3     la vista previa, dentro del <iframe> del asistente, vuelve al asistente
       de examen (enmarcable) y no al formulario clásico (X-Frame-Options: DENY).
D4     sin "Preguntas por tema", el examen lleva todas las preguntas de los
       tópicos elegidos (antes: una por tópico).
Corre contra una base descartable."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Question, Subject, Topic

User = get_user_model()


def make_user(username):
    user = User.objects.create_user(username=username, password='testpass123')
    user.profile.security_question = 'comida_favorita'  # sin esto el gate pide configurarla antes
    user.profile.save()
    return user


class FullWizardOnboardingGateTests(TestCase):
    def setUp(self):
        self.user = make_user('fw_gate')
        self.client = Client()
        self.client.login(username='fw_gate', password='testpass123')

    def test_usuario_nuevo_sin_recorrido_va_a_comenzar(self):
        # Línea base: el gate sigue funcionando para quien no entró al asistente.
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('material:onboarding_v2_page'), resp['Location'])

    def test_entrar_al_asistente_completo_libera_el_gate(self):
        self.assertFalse(self.user.profile.onboarding_completed)
        self.assertEqual(self.client.get(reverse('material:full_wizard')).status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.onboarding_completed)
        # "Terminar" lleva a Inicio: ya no rebota al asistente viejo.
        self.assertEqual(self.client.get('/').status_code, 200)


class PreviewExamEmbeddedRedirectTests(TestCase):
    def setUp(self):
        self.user = make_user('fw_preview')
        self.client = Client()
        self.client.login(username='fw_preview', password='testpass123')

    def test_sin_datos_en_sesion_fuera_de_iframe_vuelve_al_formulario_clasico(self):
        resp = self.client.get(reverse('material:preview_exam'))
        self.assertRedirects(resp, reverse('material:create_exam'), fetch_redirect_response=False)

    def test_sin_datos_en_sesion_dentro_de_iframe_vuelve_al_asistente(self):
        resp = self.client.get(reverse('material:preview_exam'), HTTP_SEC_FETCH_DEST='iframe')
        self.assertRedirects(
            resp, reverse('material:create_exam_wizard') + '?fw=1', fetch_redirect_response=False,
        )

    def test_sin_preguntas_dentro_de_iframe_vuelve_al_asistente(self):
        materia = Subject.objects.create(name='Materia vacía', created_by=self.user, es_catalogo_institucional=False)
        topic = Topic.objects.create(name='Tópico vacío', subject=materia)
        session = self.client.session
        session['preview_exam'] = {'subject': str(materia.pk), 'topics': [str(topic.pk)], 'num_versions': '1'}
        session.save()
        resp = self.client.get(reverse('material:preview_exam'), HTTP_SEC_FETCH_DEST='iframe')
        self.assertRedirects(
            resp, reverse('material:create_exam_wizard') + '?fw=1', fetch_redirect_response=False,
        )

    def test_el_destino_del_iframe_se_puede_enmarcar(self):
        resp = self.client.get(reverse('material:create_exam_wizard') + '?fw=1')
        self.assertEqual(resp['X-Frame-Options'], 'SAMEORIGIN')


class DefaultQuestionsPerVersionTests(TestCase):
    def setUp(self):
        self.user = make_user('fw_default')
        self.client = Client()
        self.client.login(username='fw_default', password='testpass123')
        self.materia = Subject.objects.create(name='Materia default', created_by=self.user, es_catalogo_institucional=False)
        self.topic = Topic.objects.create(name='T1', subject=self.materia)
        self.otro_topic = Topic.objects.create(name='T2', subject=self.materia)
        for i in range(4):
            q = Question.objects.create(user=self.user, question_text=f'P{i}', answer_text='r', topic=self.topic)
            q.subjects.add(self.materia)
        # Un tópico NO elegido no suma preguntas.
        q = Question.objects.create(user=self.user, question_text='Ajena', answer_text='r', topic=self.otro_topic)
        q.subjects.add(self.materia)

    def preview(self, **exam):
        data = {'subject': str(self.materia.pk), 'topics': [str(self.topic.pk)], 'num_versions': '1'}
        data.update(exam)
        session = self.client.session
        session['preview_exam'] = data
        session.save()
        return self.client.get(reverse('material:preview_exam'))

    def test_sin_cantidad_usa_todas_las_del_topico_elegido(self):
        resp = self.preview()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['total_exam_questions'], 4)

    def test_sin_cantidad_con_dos_temas_las_reparte(self):
        resp = self.preview(num_versions='2')
        self.assertEqual(resp.status_code, 200)
        # 4 preguntas entre 2 temas: 2 por tema (total_exam_questions solo cuenta
        # el caso de un único tema, por eso se miran las versiones).
        self.assertEqual([len(v['question_ids']) for v in resp.context['versions_preview']], [2, 2])

    def test_cantidad_explicita_se_respeta(self):
        resp = self.preview(questions_per_version='2')
        self.assertEqual(resp.context['total_exam_questions'], 2)

    def test_preguntas_elegidas_a_mano_se_respetan(self):
        ids = [str(q.pk) for q in Question.objects.filter(topic=self.topic)[:3]]
        resp = self.preview(questions=ids)
        self.assertEqual(resp.context['total_exam_questions'], 3)

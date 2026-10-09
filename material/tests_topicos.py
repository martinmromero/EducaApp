"""Tópicos por carrera-materia, con el criterio de espacio personal vs. catálogo,
y cuestionario oral con preguntas compartidas.

Cubre la visibilidad (get_visible_topics / get_visible_subtopics), la creación
según el alcance, el ABM de la ficha de la materia, la propuesta al catálogo
(aprobar y fusionar desde la bandeja), el relleno de la migración y que el oral
use las preguntas compartidas con sus tópicos. Corre contra una base descartable."""
import importlib

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from . import content_visibility as cv
from .models import (
    Career, CareerSubject, CatalogRequest, ContentShare, Exam, GroupMembership, OralExamSet,
    Question, SharingGroup, Subject, Subtopic, Topic,
)
from .views import resolve_catalog_request, resolve_catalog_request_fusion

User = get_user_model()


def make_user(username, admin=False):
    user = User.objects.create_user(username=username, password='testpass123')
    user.profile.security_question = 'comida_favorita'
    if admin:
        user.profile.role = 'admin'
    user.profile.save()
    return user


def login(username):
    client = Client()
    client.login(username=username, password='testpass123')
    return client


class BaseTopicos(TestCase):
    def setUp(self):
        self.admin = make_user('t_admin', admin=True)
        self.ana = make_user('t_ana')
        self.beto = make_user('t_beto')
        self.arq = Career.objects.create(name='Arquitectura', es_catalogo_institucional=True)
        self.sis = Career.objects.create(name='Sistemas', es_catalogo_institucional=True)
        self.ingles = Subject.objects.create(name='Inglés I', es_catalogo_institucional=True)
        self.cs_arq = CareerSubject.objects.create(career=self.arq, subject=self.ingles)
        self.cs_sis = CareerSubject.objects.create(career=self.sis, subject=self.ingles)
        # Tópico del catálogo de Arquitectura y otro de Sistemas
        self.t_arq = Topic.objects.create(
            name='Vocabulario de obra', subject=self.ingles, career_subject=self.cs_arq,
            es_catalogo_institucional=True, created_by=self.admin,
        )
        self.t_sis = Topic.objects.create(
            name='Technical writing', subject=self.ingles, career_subject=self.cs_sis,
            es_catalogo_institucional=True, created_by=self.admin,
        )


class VisibilidadTests(BaseTopicos):
    def test_el_catalogo_lo_ven_todos_y_lo_personal_solo_su_dueno(self):
        personal = Topic.objects.create(
            name='Mis frases', subject=self.ingles, career_subject=self.cs_arq,
            es_catalogo_institucional=False, created_by=self.ana,
        )
        self.assertIn(personal, cv.get_visible_topics(self.ana))
        self.assertNotIn(personal, cv.get_visible_topics(self.beto))
        self.assertIn(self.t_arq, cv.get_visible_topics(self.beto))

    def test_con_carrera_solo_los_de_esa_carrera_y_los_sin_carrera(self):
        comun = Topic.objects.create(
            name='Gramática básica', subject=self.ingles, career_subject=None,
            es_catalogo_institucional=True, created_by=self.admin,
        )
        nombres = set(cv.get_visible_topics(self.ana, subject=self.ingles, career_subject=self.cs_arq).values_list('name', flat=True))
        self.assertEqual(nombres, {'Vocabulario de obra', 'Gramática básica'})
        sin_dato = set(cv.get_visible_topics(self.ana, subject=self.ingles).values_list('name', flat=True))
        self.assertEqual(sin_dato, {'Vocabulario de obra', 'Technical writing', 'Gramática básica'})
        self.assertIn(comun, cv.get_visible_topics(self.beto, career_subject=self.cs_sis))

    def test_resolve_career_subject_con_una_sola_carrera_la_usa(self):
        sola = Subject.objects.create(name='Álgebra', es_catalogo_institucional=True)
        cs = CareerSubject.objects.create(career=self.sis, subject=sola)
        self.assertEqual(cv.resolve_career_subject(sola), cs)
        self.assertIsNone(cv.resolve_career_subject(self.ingles))  # en dos carreras: no se sabe cuál
        self.assertEqual(cv.resolve_career_subject(self.ingles, self.arq.pk), self.cs_arq)

    def test_los_topicos_de_un_docente_con_materia_compartida_llegan_al_destinatario(self):
        materia = Subject.objects.create(name='Física', created_by=self.ana, es_catalogo_institucional=False)
        propio = Topic.objects.create(
            name='Cinemática', subject=materia, es_catalogo_institucional=False, created_by=self.ana,
        )
        sub = Subtopic.objects.create(name='MRU', topic=propio, es_catalogo_institucional=False, created_by=self.ana)
        self.assertNotIn(propio, cv.get_visible_topics(self.beto))
        grupo = SharingGroup.objects.create(name='Cátedra', created_by=self.ana)
        GroupMembership.objects.create(group=grupo, user=self.ana, status='accepted')
        GroupMembership.objects.create(group=grupo, user=self.beto, status='accepted')
        ContentShare.objects.create(group=grupo, shared_by=self.ana, kind='materia', subject=materia, is_active=True)
        self.assertIn(propio, cv.get_visible_topics(self.beto))
        self.assertIn(sub, cv.get_visible_subtopics(self.beto))

    def test_los_subtopicos_personales_no_se_ven_en_un_topico_del_catalogo(self):
        sub = Subtopic.objects.create(name='Solo mío', topic=self.t_arq, es_catalogo_institucional=False, created_by=self.ana)
        self.assertIn(sub, cv.get_visible_subtopics(self.ana))
        self.assertNotIn(sub, cv.get_visible_subtopics(self.beto))


class CreacionTests(BaseTopicos):
    def test_un_docente_sobre_materia_del_catalogo_crea_uno_personal(self):
        client = login('t_ana')
        resp = client.post(reverse('material:add_topic'), {
            'name': 'Mi tópico', 'subject_id': self.ingles.pk, 'career_id': self.arq.pk,
        })
        self.assertTrue(resp.json()['success'])
        topic = Topic.objects.get(name='Mi tópico')
        self.assertFalse(topic.es_catalogo_institucional)
        self.assertEqual((topic.created_by, topic.career_subject), (self.ana, self.cs_arq))

    def test_un_admin_sobre_materia_del_catalogo_crea_uno_del_catalogo(self):
        client = login('t_admin')
        client.post(reverse('material:add_topic'), {'name': 'Del catálogo', 'subject_id': self.ingles.pk, 'career_id': self.sis.pk})
        self.assertTrue(Topic.objects.get(name='Del catálogo').es_catalogo_institucional)

    def test_duplicado_dentro_de_lo_que_el_usuario_ve(self):
        client = login('t_ana')
        resp = client.post(reverse('material:add_topic'), {
            'name': 'vocabulario de obra', 'subject_id': self.ingles.pk, 'career_id': self.arq.pk,
        })
        self.assertEqual(resp.status_code, 400)

    def test_el_mismo_nombre_en_otra_carrera_si_se_puede(self):
        client = login('t_ana')
        resp = client.post(reverse('material:add_topic'), {
            'name': 'Vocabulario de obra', 'subject_id': self.ingles.pk, 'career_id': self.sis.pk,
        })
        self.assertTrue(resp.json()['success'])

    def test_get_topics_oculta_lo_personal_ajeno_y_pide_login(self):
        Topic.objects.create(name='Secreto', subject=self.ingles, career_subject=self.cs_arq, es_catalogo_institucional=False, created_by=self.ana)
        beto = login('t_beto')
        nombres = {t['name'] for t in beto.get('/get-topics/', {'subject_id': self.ingles.pk, 'career_id': self.arq.pk}).json()}
        self.assertEqual(nombres, {'Vocabulario de obra'})
        self.assertEqual(Client().get('/get-topics/', {'subject_id': self.ingles.pk}).status_code, 302)

    def test_get_or_create_topic_reutiliza_el_visible_y_crea_personal_si_falta(self):
        existente, creado = cv.get_or_create_topic(self.ana, self.ingles, 'VOCABULARIO DE OBRA', career_subject=self.cs_arq)
        self.assertEqual((existente, creado), (self.t_arq, False))
        nuevo, creado = cv.get_or_create_topic(self.ana, self.ingles, 'Otro', career_subject=self.cs_arq)
        self.assertTrue(creado)
        self.assertFalse(nuevo.es_catalogo_institucional)


class AbmFichaTests(BaseTopicos):
    def test_la_ficha_muestra_los_topicos_por_carrera(self):
        resp = login('t_ana').get(reverse('material:subject_detail', kwargs={'pk': self.ingles.pk}))
        self.assertContains(resp, 'Vocabulario de obra')
        self.assertContains(resp, 'Technical writing')
        self.assertContains(resp, 'Tópicos y sub-tópicos')

    def test_un_docente_no_edita_ni_borra_un_topico_del_catalogo(self):
        client = login('t_ana')
        client.post(reverse('material:topic_update', kwargs={'pk': self.t_arq.pk}), {'name': 'Cambiado'})
        client.post(reverse('material:topic_delete', kwargs={'pk': self.t_arq.pk}))
        self.t_arq.refresh_from_db()
        self.assertEqual(self.t_arq.name, 'Vocabulario de obra')

    def test_un_admin_edita_y_reasigna_un_topico_del_catalogo(self):
        client = login('t_admin')
        client.post(reverse('material:topic_update', kwargs={'pk': self.t_arq.pk}), {
            'name': 'Vocabulario técnico', 'career_subject_id': self.cs_sis.pk,
        })
        self.t_arq.refresh_from_db()
        self.assertEqual((self.t_arq.name, self.t_arq.career_subject_id), ('Vocabulario técnico', self.cs_sis.pk))

    def test_el_docente_agrega_edita_y_borra_los_suyos(self):
        client = login('t_ana')
        client.post(reverse('material:topic_create', kwargs={'subject_id': self.ingles.pk}), {
            'name': 'Mío', 'career_subject_id': self.cs_arq.pk,
        })
        topic = Topic.objects.get(name='Mío')
        self.assertFalse(topic.es_catalogo_institucional)
        client.post(reverse('material:topic_update', kwargs={'pk': topic.pk}), {'name': 'Mío 2', 'career_subject_id': self.cs_arq.pk})
        topic.refresh_from_db()
        self.assertEqual(topic.name, 'Mío 2')
        q = Question.objects.create(user=self.ana, question_text='P', answer_text='r', topic=topic)
        client.post(reverse('material:topic_delete', kwargs={'pk': topic.pk}))
        self.assertFalse(Topic.objects.filter(pk=topic.pk).exists())
        q.refresh_from_db()
        self.assertIsNone(q.topic)

    def test_un_docente_no_toca_el_topico_personal_de_otro(self):
        ajeno = Topic.objects.create(name='De Ana', subject=self.ingles, es_catalogo_institucional=False, created_by=self.ana)
        resp = login('t_beto').post(reverse('material:topic_delete', kwargs={'pk': ajeno.pk}))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Topic.objects.filter(pk=ajeno.pk).exists())

    def test_subtopicos_el_docente_en_un_topico_del_catalogo_crea_uno_personal(self):
        client = login('t_ana')
        client.post(reverse('material:subtopic_create', kwargs={'topic_id': self.t_arq.pk}), {'name': 'Mi sub'})
        sub = Subtopic.objects.get(name='Mi sub')
        self.assertFalse(sub.es_catalogo_institucional)
        self.assertEqual(sub.created_by, self.ana)
        client.post(reverse('material:subtopic_delete', kwargs={'pk': sub.pk}))
        self.assertFalse(Subtopic.objects.filter(pk=sub.pk).exists())


class PropuestaAlCatalogoTests(BaseTopicos):
    def setUp(self):
        super().setUp()
        self.personal = Topic.objects.create(
            name='Frases de cierre', subject=self.ingles, career_subject=self.cs_arq,
            es_catalogo_institucional=False, created_by=self.ana,
        )
        self.sub = Subtopic.objects.create(name='Mails', topic=self.personal, es_catalogo_institucional=False, created_by=self.ana)

    def proponer(self):
        return login('t_ana').post(reverse('material:topic_propose', kwargs={'pk': self.personal.pk}))

    def test_proponer_crea_la_solicitud_una_sola_vez(self):
        self.proponer()
        self.proponer()
        solicitudes = CatalogRequest.objects.filter(tipo='topico', topico=self.personal)
        self.assertEqual(solicitudes.count(), 1)
        self.assertEqual((solicitudes[0].materia, solicitudes[0].carrera, solicitudes[0].estado), (self.ingles, self.arq, 'pendiente'))

    def test_no_se_propone_un_topico_de_una_materia_personal(self):
        materia = Subject.objects.create(name='Mía', created_by=self.ana, es_catalogo_institucional=False)
        topic = Topic.objects.create(name='X', subject=materia, es_catalogo_institucional=False, created_by=self.ana)
        login('t_ana').post(reverse('material:topic_propose', kwargs={'pk': topic.pk}))
        self.assertFalse(CatalogRequest.objects.filter(topico=topic).exists())

    def test_no_se_propone_lo_ajeno_ni_lo_que_ya_es_del_catalogo(self):
        login('t_beto').post(reverse('material:topic_propose', kwargs={'pk': self.t_arq.pk}))
        self.assertFalse(CatalogRequest.objects.filter(topico=self.t_arq).exists())

    def test_aprobar_lo_suma_al_catalogo_con_sus_subtopicos(self):
        self.proponer()
        solicitud = CatalogRequest.objects.get(topico=self.personal)
        ok, _msg = resolve_catalog_request(solicitud, admin_user=self.admin, aprobar=True)
        self.assertTrue(ok)
        self.personal.refresh_from_db()
        self.sub.refresh_from_db()
        self.assertTrue(self.personal.es_catalogo_institucional)
        self.assertTrue(self.sub.es_catalogo_institucional)
        # y ahora lo ve cualquier docente de esa carrera
        self.assertIn(self.personal, cv.get_visible_topics(self.beto, career_subject=self.cs_arq))

    def test_rechazar_lo_deja_personal(self):
        self.proponer()
        solicitud = CatalogRequest.objects.get(topico=self.personal)
        resolve_catalog_request(solicitud, admin_user=self.admin, aprobar=False, nota_admin='ya existe algo parecido')
        self.personal.refresh_from_db()
        self.assertFalse(self.personal.es_catalogo_institucional)

    def test_fusionar_pasa_preguntas_subtopicos_y_examenes_al_destino(self):
        pregunta = Question.objects.create(user=self.ana, question_text='P', answer_text='r', topic=self.personal, subtopic=self.sub)
        examen = Exam.objects.create(title='Parcial', created_by=self.ana, subject=self.ingles)
        examen.topics.add(self.personal)
        self.proponer()
        solicitud = CatalogRequest.objects.get(topico=self.personal)
        ok, _msg = resolve_catalog_request_fusion(solicitud, admin_user=self.admin, destino_id=self.t_arq.pk)
        self.assertTrue(ok)
        pregunta.refresh_from_db()
        self.assertEqual(pregunta.topic, self.t_arq)
        self.assertEqual(pregunta.subtopic.topic, self.t_arq)
        self.assertEqual(list(examen.topics.all()), [self.t_arq])
        self.assertFalse(Topic.objects.filter(pk=self.personal.pk).exists())

    def test_el_formulario_de_solicitar_alta_no_ofrece_topico(self):
        from .forms import CatalogRequestForm
        tipos = [valor for valor, _ in CatalogRequestForm(user=self.ana).fields['tipo'].choices]
        self.assertNotIn('topico', tipos)

    def test_fusionar_materias_reapunta_los_topicos_a_la_carrera_materia_destino(self):
        origen = Subject.objects.create(name='Inglés 1 (borrador)', created_by=self.ana, es_catalogo_institucional=False)
        cs_origen = CareerSubject.objects.create(career=self.arq, subject=origen)
        topic = Topic.objects.create(name='Propio', subject=origen, career_subject=cs_origen, es_catalogo_institucional=False, created_by=self.ana)
        from .views import _fusionar_en_destino
        _fusionar_en_destino('materia', origen, self.ingles)
        topic.refresh_from_db()
        self.assertEqual((topic.subject, topic.career_subject), (self.ingles, self.cs_arq))


class MigracionTests(TestCase):
    def test_relleno_de_alcance(self):
        migracion = importlib.import_module('material.migrations.0103_topico_por_carrera_materia')
        dueno = make_user('mig_dueno')
        personal = Subject.objects.create(name='Personal', created_by=dueno, es_catalogo_institucional=False)
        una = Subject.objects.create(name='Una carrera', es_catalogo_institucional=True)
        varias = Subject.objects.create(name='Varias carreras', es_catalogo_institucional=True)
        c1 = Career.objects.create(name='C1')
        c2 = Career.objects.create(name='C2')
        cs_una = CareerSubject.objects.create(career=c1, subject=una)
        CareerSubject.objects.create(career=c1, subject=varias)
        CareerSubject.objects.create(career=c2, subject=varias)
        t_personal = Topic.objects.create(name='a', subject=personal)
        sub_personal = Subtopic.objects.create(name='s', topic=t_personal)
        t_una = Topic.objects.create(name='b', subject=una)
        t_varias = Topic.objects.create(name='c', subject=varias)

        migracion.asignar_alcance_a_topicos(apps, None)

        for obj in (t_personal, sub_personal, t_una, t_varias):
            obj.refresh_from_db()
        self.assertFalse(t_personal.es_catalogo_institucional)
        self.assertEqual(t_personal.created_by, dueno)
        self.assertFalse(sub_personal.es_catalogo_institucional)
        self.assertEqual(sub_personal.created_by, dueno)
        self.assertEqual((t_una.career_subject, t_una.es_catalogo_institucional), (cs_una, True))
        self.assertIsNone(t_varias.career_subject)


class OralConPreguntasCompartidasTests(TestCase):
    def setUp(self):
        self.ana = make_user('o_ana')
        self.beto = make_user('o_beto')
        self.materia = Subject.objects.create(name='Historia', created_by=self.ana, es_catalogo_institucional=False)
        self.topic = Topic.objects.create(name='Siglo XX', subject=self.materia, es_catalogo_institucional=False, created_by=self.ana)
        self.sub = Subtopic.objects.create(name='Guerras', topic=self.topic, es_catalogo_institucional=False, created_by=self.ana)
        self.preguntas = []
        for i in range(3):
            q = Question.objects.create(user=self.ana, question_text=f'P{i}', answer_text='r', topic=self.topic, subtopic=self.sub)
            q.subjects.add(self.materia)
            self.preguntas.append(q)
        # Una generada por IA y sin aprobar no se ofrece (igual que en el examen escrito).
        sin_aprobar = Question.objects.create(
            user=self.ana, question_text='IA', answer_text='r', topic=self.topic, generated_by_ai=True, ai_approved=False,
        )
        sin_aprobar.subjects.add(self.materia)

    def compartir(self):
        grupo = SharingGroup.objects.create(name='Cátedra', created_by=self.ana)
        GroupMembership.objects.create(group=grupo, user=self.ana, status='accepted')
        GroupMembership.objects.create(group=grupo, user=self.beto, status='accepted')
        ContentShare.objects.create(group=grupo, shared_by=self.ana, kind='materia', subject=self.materia, is_active=True)

    def test_sin_compartir_el_destinatario_no_tiene_preguntas(self):
        self.assertEqual(cv.get_oral_questions(self.beto, self.materia).count(), 0)

    def test_compartidas_si_y_solo_las_aprobadas(self):
        self.compartir()
        self.assertEqual(set(cv.get_oral_questions(self.beto, self.materia)), set(self.preguntas))

    def test_el_oral_ofrece_la_materia_compartida_con_sus_topicos(self):
        self.compartir()
        client = login('o_beto')
        wizard = client.get(reverse('material:create_oral_exam_wizard'))
        self.assertIn(self.materia, wizard.context['materias'])
        topicos = client.get('/get-topics/', {'subject_id': self.materia.pk, 'for_exam': '1'}).json()
        self.assertEqual([t['name'] for t in topicos], ['Siglo XX'])
        subtopicos = client.get('/get-subtopics/', {'topic_id': self.topic.pk}).json()
        self.assertEqual([s['name'] for s in subtopicos], ['Guerras'])

    def test_validar_y_crear_con_preguntas_compartidas(self):
        self.compartir()
        client = login('o_beto')
        resp = client.post(
            reverse('material:validate_oral_exam'),
            data={'subject_id': self.materia.pk, 'topic_ids': [self.topic.pk], 'total_students': 2, 'questions_per_student': 1},
            content_type='application/json',
        )
        self.assertTrue(resp.json().get('success'), resp.json())
        crear = client.post(reverse('material:create_oral_exam'), {
            'name': 'Oral compartido', 'subject': self.materia.pk, 'topics': [self.topic.pk],
            'total_students': 2, 'questions_per_student': 1, 'num_groups': 1, 'students_per_group': 2,
        })
        self.assertEqual(crear.status_code, 302, getattr(crear, 'context', None) and crear.context['form'].errors)
        oral = OralExamSet.objects.get(name='Oral compartido')
        usadas = set(oral.groups.first().students.first().questions.values_list('pk', flat=True))
        self.assertTrue(usadas <= {q.pk for q in self.preguntas})

    def test_sin_compartir_no_puede_armar_el_oral(self):
        client = login('o_beto')
        wizard = client.get(reverse('material:create_oral_exam_wizard'))
        self.assertNotIn(self.materia, wizard.context['materias'])

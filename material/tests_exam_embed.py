"""Paso Examen del Asistente completo: el asistente "Nuevo examen" se monta en
un <iframe> same-origin (?fw=1) con lo ya elegido precargado. Cubre la
validación de ese precargado, el acotado de materia/plantillas, que las
pantallas enmarcadas puedan enmarcarse (y las demás no), y la respuesta del
guardado que consume el host. Corre contra una base descartable."""
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import (
    Career, CareerSubject, ExamTemplate, FacultyV2, InstitutionV2,
    LearningOutcome, Question, Subject, Topic,
)

User = get_user_model()


def make_user(username):
    return User.objects.create_user(username=username, password='testpass123')


class FwExamPrefillTests(TestCase):
    def setUp(self):
        self.user = make_user('fw_docente')
        self.client = Client()
        self.client.login(username='fw_docente', password='testpass123')

        self.inst = InstitutionV2.objects.create(name='Inst QA', es_catalogo_institucional=True)
        self.fac = FacultyV2.objects.create(name='Fac QA', institution=self.inst, es_catalogo_institucional=True)
        self.career = Career.objects.create(name='Carrera QA', es_catalogo_institucional=True)
        self.career.faculties.add(self.fac)

        self.materia = Subject.objects.create(name='Materia QA', created_by=self.user, es_catalogo_institucional=False)
        self.otra = Subject.objects.create(name='Otra QA', created_by=self.user, es_catalogo_institucional=False)
        for materia in (self.materia, self.otra):
            topic = Topic.objects.create(name=f'T {materia.name}', subject=materia)
            q = Question.objects.create(user=self.user, question_text=f'P {materia.name}', answer_text='r', topic=topic)
            q.subjects.add(materia)

        cs = CareerSubject.objects.create(career=self.career, subject=self.materia)
        self.ra = LearningOutcome.objects.create(
            career_subject=cs, description='RA QA', created_by=self.user, es_catalogo_institucional=False,
        )

    def url(self, **params):
        base = {'fw': '1'}
        base.update({k: v for k, v in params.items() if v is not None})
        return reverse('material:create_exam_wizard') + '?' + '&'.join(f'{k}={v}' for k, v in base.items())

    def config(self, resp):
        """fwPrefill embebido en la página, ya como dict."""
        html = resp.content.decode()
        marker = 'fwPrefill: '
        start = html.index(marker) + len(marker)
        end = html.index('\n};', start)
        return json.loads(html[start:end].rstrip())

    def test_sin_fw_no_hay_modo_embebido(self):
        resp = self.client.get(reverse('material:create_exam_wizard'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['is_embedded'])
        self.assertContains(resp, 'Usar la pantalla completa de siempre')
        # El asistente suelto sigue ofreciendo todas las materias con preguntas.
        self.assertEqual({m.pk for m in resp.context['materias']}, {self.materia.pk, self.otra.pk})

    def test_fw_precarga_lo_elegido_y_acota_la_materia(self):
        resp = self.client.get(self.url(
            subject_id=self.materia.pk, institucion_id=self.inst.pk, facultad_id=self.fac.pk,
            carrera_id=self.career.pk, outcome_ids=self.ra.pk,
        ))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context['is_embedded'])
        self.assertNotContains(resp, 'Usar la pantalla completa de siempre')
        self.assertEqual([m.pk for m in resp.context['materias']], [self.materia.pk])
        prefill = self.config(resp)
        self.assertEqual(prefill['subject_id'], self.materia.pk)
        self.assertEqual((prefill['institucion_id'], prefill['institucion_name']), (self.inst.pk, 'Inst QA'))
        self.assertEqual((prefill['facultad_id'], prefill['facultad_name']), (self.fac.pk, 'Fac QA'))
        self.assertEqual((prefill['carrera_id'], prefill['carrera_name']), (self.career.pk, 'Carrera QA'))
        self.assertEqual(prefill['outcome_ids'], [self.ra.pk])

    def test_ids_ajenos_o_inventados_no_se_precargan(self):
        otro = make_user('fw_otro')
        ajena = Subject.objects.create(name='Ajena QA', created_by=otro, es_catalogo_institucional=False)
        ra_ajeno = LearningOutcome.objects.create(
            career_subject=CareerSubject.objects.create(career=self.career, subject=ajena),
            description='RA ajeno', created_by=otro, es_catalogo_institucional=False,
        )
        resp = self.client.get(self.url(subject_id=ajena.pk, institucion_id=999999, outcome_ids=f'{ra_ajeno.pk},xx'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.config(resp), {})
        # Sin materia válida no se acota nada: el asistente funciona como suelto.
        self.assertEqual({m.pk for m in resp.context['materias']}, {self.materia.pk, self.otra.pk})

    def test_plantillas_solo_de_la_materia_elegida(self):
        propia = ExamTemplate.objects.create(
            name='Plantilla de la materia', created_by=self.user, institution=self.inst,
            faculty=self.fac, career=self.career, subject=self.materia,
        )
        ExamTemplate.objects.create(
            name='Plantilla de otra', created_by=self.user, institution=self.inst,
            faculty=self.fac, career=self.career, subject=self.otra,
        )
        resp = self.client.get(self.url(subject_id=self.materia.pk))
        self.assertEqual([t.pk for t in resp.context['templates']], [propia.pk])

    def test_pagina_se_puede_enmarcar_en_el_mismo_origen(self):
        resp = self.client.get(self.url(subject_id=self.materia.pk))
        self.assertEqual(resp['X-Frame-Options'], 'SAMEORIGIN')

    def test_otras_pantallas_siguen_sin_poder_enmarcarse(self):
        resp = self.client.get(reverse('material:create_exam'))
        self.assertEqual(resp['X-Frame-Options'], 'DENY')


class FwExamSaveResponseTests(TestCase):
    """save_exam_from_session devuelve view_url para la pantalla final del
    Asistente completo (no la redirección al listado)."""

    def setUp(self):
        self.user = make_user('fw_guarda')
        self.client = Client()
        self.client.login(username='fw_guarda', password='testpass123')
        self.materia = Subject.objects.create(name='Materia guardar', created_by=self.user, es_catalogo_institucional=False)
        self.topic = Topic.objects.create(name='T', subject=self.materia)
        self.questions = []
        for i in range(3):
            q = Question.objects.create(user=self.user, question_text=f'P{i}', answer_text='r', topic=self.topic)
            q.subjects.add(self.materia)
            self.questions.append(q)

    def save(self, **exam):
        data = {'subject': str(self.materia.pk), 'topics': [str(self.topic.pk)],
                'questions': [str(q.pk) for q in self.questions], 'num_versions': '1'}
        data.update(exam)
        session = self.client.session
        session['preview_exam'] = data
        session.save()
        return self.client.post(reverse('material:save_exam_from_session'), HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def test_un_examen_devuelve_su_url(self):
        resp = self.save()
        data = resp.json()
        self.assertTrue(data['success'], data)
        self.assertEqual(data['view_url'], reverse('material:ver_examen', kwargs={'pk': data['created_exam_ids'][0]}))

    def test_varios_temas_devuelven_la_url_del_lote(self):
        resp = self.save(num_versions='2', questions_per_version='1')
        data = resp.json()
        self.assertTrue(data['success'], data)
        self.assertIn('/examenes/lotes/', data['view_url'])

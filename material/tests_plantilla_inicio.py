"""Partir de una plantilla al comienzo del Asistente completo.

Una plantilla guarda institución, facultad, carrera, materia y resultados de
aprendizaje: el asistente la ofrece en el paso 1, completa los pasos 1 a 5 y le
pasa la plantilla al examen embebido. Cubre qué plantillas se ofrecen, el
contexto que se devuelve (validado como visible) y el parámetro plantilla_id del
examen embebido. Corre contra una base descartable."""
import json

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse

from .models import (
    Career, CareerSubject, ContentShare, ExamTemplate, FacultyV2, GroupMembership, InstitutionV2,
    LearningOutcome, Question, SharingGroup, Subject, Topic,
)

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


class PlantillaAlComienzoTests(TestCase):
    def setUp(self):
        self.ana = make_user('p_ana')
        self.beto = make_user('p_beto')
        self.inst = InstitutionV2.objects.create(name='Inst P', es_catalogo_institucional=True)
        self.fac = FacultyV2.objects.create(name='Fac P', institution=self.inst, es_catalogo_institucional=True)
        self.career = Career.objects.create(name='Carrera P', es_catalogo_institucional=True)
        self.career.faculties.add(self.fac)
        self.materia = Subject.objects.create(name='Materia P', created_by=self.ana, es_catalogo_institucional=False)
        self.cs = CareerSubject.objects.create(career=self.career, subject=self.materia)
        self.ra = LearningOutcome.objects.create(
            career_subject=self.cs, description='RA P', created_by=self.ana, es_catalogo_institucional=False,
        )
        topic = Topic.objects.create(name='T', subject=self.materia, es_catalogo_institucional=False, created_by=self.ana)
        for i in range(2):
            q = Question.objects.create(user=self.ana, question_text=f'P{i}', answer_text='r', topic=topic)
            q.subjects.add(self.materia)
        self.plantilla = ExamTemplate.objects.create(
            name='Parcial tipo', created_by=self.ana, institution=self.inst, faculty=self.fac,
            career=self.career, subject=self.materia,
        )
        self.plantilla.learning_outcomes.add(self.ra)

    def compartir_con_beto(self):
        grupo = SharingGroup.objects.create(name='Cátedra', created_by=self.ana)
        GroupMembership.objects.create(group=grupo, user=self.ana, status='accepted')
        GroupMembership.objects.create(group=grupo, user=self.beto, status='accepted')
        ContentShare.objects.create(
            group=grupo, shared_by=self.ana, kind='plantilla', is_active=True,
            content_type=ContentType.objects.get_for_model(ExamTemplate),
            object_id=self.plantilla.pk,
        )

    def test_se_ofrecen_las_propias_y_no_las_ajenas(self):
        propias = login('p_ana').get(reverse('material:full_wizard_templates')).json()['templates']
        self.assertEqual([t['name'] for t in propias], ['Parcial tipo'])
        self.assertEqual(propias[0]['subject'], 'Materia P')
        ajenas = login('p_beto').get(reverse('material:full_wizard_templates')).json()['templates']
        self.assertEqual(ajenas, [])

    def test_el_contexto_trae_la_cadena_los_resultados_y_las_preguntas(self):
        data = login('p_ana').get(
            reverse('material:full_wizard_template_context', kwargs={'template_id': self.plantilla.pk})
        ).json()
        self.assertTrue(data['ok'])
        self.assertEqual(
            {k: v['id'] for k, v in data['chain'].items()},
            {'institucion': self.inst.pk, 'facultad': self.fac.pk, 'carrera': self.career.pk, 'materia': self.materia.pk},
        )
        self.assertEqual([o['id'] for o in data['outcomes']], [self.ra.pk])
        self.assertEqual(data['question_count'], 2)
        self.assertEqual(data['template']['id'], self.plantilla.pk)

    def test_una_plantilla_ajena_no_se_puede_pedir(self):
        resp = login('p_beto').get(
            reverse('material:full_wizard_template_context', kwargs={'template_id': self.plantilla.pk})
        )
        self.assertEqual(resp.status_code, 404)

    def test_compartida_pero_apoyada_en_una_materia_personal_se_explica(self):
        # La materia es personal de Ana: Beto ve la plantilla compartida pero no la materia.
        self.compartir_con_beto()
        resp = login('p_beto').get(
            reverse('material:full_wizard_template_context', kwargs={'template_id': self.plantilla.pk})
        )
        self.assertEqual(resp.status_code, 409)
        self.assertFalse(resp.json()['ok'])
        self.assertIn('materia', resp.json()['error'])

    def test_el_examen_embebido_recibe_la_plantilla_de_la_misma_materia(self):
        url = reverse('material:create_exam_wizard') + (
            f'?fw=1&subject_id={self.materia.pk}&plantilla_id={self.plantilla.pk}'
        )
        resp = login('p_ana').get(url)
        html = resp.content.decode()
        marcador = 'fwPrefill: '
        inicio = html.index(marcador) + len(marcador)
        prefill = json.loads(html[inicio:html.index('\n};', inicio)].rstrip())
        self.assertEqual(prefill['plantilla_id'], self.plantilla.pk)

    def test_la_plantilla_de_otra_materia_o_ajena_se_ignora(self):
        otra = Subject.objects.create(name='Otra', created_by=self.ana, es_catalogo_institucional=False)
        q = Question.objects.create(user=self.ana, question_text='X', answer_text='r')
        q.subjects.add(otra)
        url = reverse('material:create_exam_wizard') + f'?fw=1&subject_id={otra.pk}&plantilla_id={self.plantilla.pk}'
        html = login('p_ana').get(url).content.decode()
        inicio = html.index('fwPrefill: ') + len('fwPrefill: ')
        self.assertNotIn('plantilla_id', json.loads(html[inicio:html.index('\n};', inicio)].rstrip()))

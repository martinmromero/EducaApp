"""Asistente "Subir preguntas" (/upload-questions/asistente/): endpoints JSON
(materias, guardar una pregunta, vista previa e importación de lotes) y el
refactor del parseo CSV/TXT que ahora comparten la vista previa y la
importación real. Corre contra una base descartable (manage.py test)."""
import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from .models import Question, Subject, Topic, Subtopic

User = get_user_model()

CSV_OK = (
    "pregunta,respuesta,tema,subtema,pagina,tipo,opciones,dificultad,nivel_bloom\n"
    "¿Cuánto es 2+2?,4,Álgebra,,12,opcion_multiple,1|2|3|4,2,1\n"
    "¿San Martín cruzó los Andes?,Verdadero,Historia,Argentina,34,verdadero_falso,,1,2\n"
    "Explicar la fotosíntesis,Proceso de las plantas,Biología,,,desarrollo,,3,\n"
)

TXT_OK = (
    "pregunta: ¿Capital de Francia?\n"
    "respuesta: París\n"
    "tema: Geografía\n"
    "\n"
    "pregunta: ¿Sin tema?\n"
    "respuesta: Sí\n"
)


def make_user(username):
    return User.objects.create_user(username=username, password='testpass123')


def csv_file(content, name='lote.csv'):
    return SimpleUploadedFile(name, content.encode('utf-8'), content_type='text/csv')


class UploadWizardBase(TestCase):
    def setUp(self):
        self.user = make_user('uqw_docente')
        self.client = Client()
        self.client.login(username='uqw_docente', password='testpass123')
        # Materia propia (espacio personal) — visible para este usuario.
        self.materia = Subject.objects.create(
            name='Materia de prueba', created_by=self.user, es_catalogo_institucional=False,
        )


class PageAndSubjectsTests(UploadWizardBase):
    def test_pagina_requiere_login(self):
        resp = Client().get(reverse('material:upload_questions_wizard'))
        self.assertEqual(resp.status_code, 302)

    def test_pagina_renderiza_con_materia_inicial(self):
        resp = self.client.get(reverse('material:upload_questions_wizard'), {'materia': self.materia.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'data-uqw')
        self.assertContains(resp, 'Materia de prueba')

    def test_materia_inicial_ajena_se_ignora(self):
        otro = make_user('otro')
        ajena = Subject.objects.create(name='Materia ajena', created_by=otro, es_catalogo_institucional=False)
        resp = self.client.get(reverse('material:upload_questions_wizard'), {'materia': ajena.pk})
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'Materia ajena')

    def test_busqueda_de_materias_sin_acentos_y_solo_visibles(self):
        Subject.objects.create(name='Matemática Discreta', created_by=self.user, es_catalogo_institucional=False)
        otro = make_user('otro2')
        Subject.objects.create(name='Matemática Secreta', created_by=otro, es_catalogo_institucional=False)
        resp = self.client.get(reverse('material:upload_questions_wizard_subjects'), {'q': 'matematica'})
        nombres = [s['name'] for s in resp.json()['subjects']]
        self.assertIn('Matemática Discreta', nombres)
        self.assertNotIn('Matemática Secreta', nombres)

    def test_sin_busqueda_solo_trae_las_propias_con_contenido(self):
        vacia = Subject.objects.create(name='Sin contenido', created_by=self.user, es_catalogo_institucional=False)
        q = Question.objects.create(user=self.user, question_text='x', answer_text='y')
        q.subjects.add(self.materia)
        resp = self.client.get(reverse('material:upload_questions_wizard_subjects'))
        nombres = [s['name'] for s in resp.json()['subjects']]
        self.assertIn('Materia de prueba', nombres)
        self.assertNotIn(vacia.name, nombres)


class SaveSingleTests(UploadWizardBase):
    def post(self, **extra):
        data = {
            'subjects': self.materia.pk,
            'question_type': 'desarrollo',
            'question_text': 'Explicar X',
            'answer_text': 'Porque Y',
            'difficulty': '2',
            'bloom_level': '',
            'source_page': '',
            'contenido': '',
            'options_json': '',
        }
        data.update(extra)
        return self.client.post(reverse('material:upload_questions_wizard_save'), data)

    def test_guarda_una_pregunta_con_su_materia(self):
        resp = self.post()
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()['ok'])
        q = Question.objects.get(pk=resp.json()['id'])
        self.assertEqual(q.user, self.user)
        self.assertEqual(list(q.subjects.all()), [self.materia])
        self.assertEqual(q.difficulty, 2)
        self.assertIsNone(q.bloom_level)

    def test_guarda_topico_y_subtopico(self):
        topic = Topic.objects.create(name='T1', subject=self.materia)
        sub = Subtopic.objects.create(name='S1', topic=topic)
        resp = self.post(topic=topic.pk, subtopic=sub.pk)
        self.assertEqual(resp.status_code, 200, resp.content)
        q = Question.objects.get(pk=resp.json()['id'])
        self.assertEqual((q.topic, q.subtopic), (topic, sub))

    def test_opcion_multiple_guarda_las_opciones(self):
        resp = self.post(question_type='opcion_multiple', answer_text='4', options_json=json.dumps(['3', '4']))
        q = Question.objects.get(pk=resp.json()['id'])
        self.assertEqual(json.loads(q.options_json), ['3', '4'])

    def test_enunciado_vacio_devuelve_error_json(self):
        resp = self.post(question_text='')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()['ok'])
        self.assertIn('question_text', resp.json()['errors'])
        self.assertEqual(Question.objects.count(), 0)

    def test_materia_ajena_se_rechaza(self):
        otro = make_user('otro3')
        ajena = Subject.objects.create(name='Ajena', created_by=otro, es_catalogo_institucional=False)
        resp = self.post(subjects=ajena.pk)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Question.objects.count(), 0)

    def test_solo_post(self):
        resp = self.client.get(reverse('material:upload_questions_wizard_save'))
        self.assertEqual(resp.status_code, 405)


class BatchTests(UploadWizardBase):
    def preview(self, content, name='lote.csv', subject=None):
        return self.client.post(reverse('material:upload_questions_wizard_preview'), {
            'file': csv_file(content, name), 'subject_id': (subject or self.materia).pk,
        })

    def do_import(self, content, name='lote.csv', **extra):
        data = {'file': csv_file(content, name), 'subject_id': self.materia.pk}
        data.update(extra)
        return self.client.post(reverse('material:upload_questions_wizard_import'), data)

    def test_vista_previa_no_guarda_nada(self):
        resp = self.preview(CSV_OK)
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertEqual(data['valid'], 3)
        self.assertEqual(data['error_count'], 0)
        self.assertEqual(Question.objects.count(), 0)
        self.assertEqual(Topic.objects.count(), 0)

    def test_vista_previa_marca_topicos_nuevos_y_existentes(self):
        Topic.objects.create(name='álgebra', subject=self.materia)
        data = self.preview(CSV_OK).json()
        por_nombre = {t['name']: t['is_new'] for t in data['topics']}
        # "álgebra" ya existe (distinta capitalización): no se vuelve a crear.
        self.assertFalse(por_nombre['Álgebra'])
        self.assertIn('Historia', por_nombre)
        self.assertTrue(por_nombre['Historia'])
        self.assertTrue(por_nombre['Biología'])

    def test_vista_previa_informa_filas_invalidas(self):
        csv = "pregunta,respuesta,tema\n¿Ok?,Sí,T\n,sin pregunta,T\n¿Sin respuesta?,,T\n"
        data = self.preview(csv).json()
        self.assertEqual(data['valid'], 1)
        self.assertEqual(data['error_count'], 2)
        self.assertIn('Fila 3', data['errors'][0])

    def test_encabezados_en_mayuscula_se_aceptan(self):
        csv = "Pregunta,Respuesta,Tema\n¿Ok?,Sí,T\n"
        self.assertEqual(self.preview(csv).json()['valid'], 1)

    def test_vista_previa_avisa_opcion_multiple_sin_opciones(self):
        csv = "pregunta,respuesta,tema,tipo\n¿Ok?,Sí,T,opcion_multiple\n"
        data = self.preview(csv).json()
        self.assertEqual(data['valid'], 1)
        self.assertEqual(data['warning_count'], 1)

    def test_vista_previa_detecta_duplicadas(self):
        q = Question.objects.create(user=self.user, question_text='¿Cuánto es 2+2?', answer_text='4')
        q.subjects.add(self.materia)
        self.assertEqual(self.preview(CSV_OK).json()['duplicates'], 1)

    def test_txt_funciona_y_tema_vacio_cae_a_general(self):
        data = self.preview(TXT_OK, 'lote.txt').json()
        self.assertEqual(data['valid'], 2)
        self.assertIn('General', {t['name'] for t in data['topics']})

    def test_txt_sin_pregunta_se_descarta(self):
        data = self.preview("respuesta: x\ntema: T\n", 'lote.txt').json()
        self.assertEqual(data['valid'], 0)
        self.assertEqual(data['error_count'], 1)

    def test_importa_con_materia_topicos_y_tipos(self):
        resp = self.do_import(CSV_OK)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()['created'], 3)
        self.assertEqual(Question.objects.filter(subjects=self.materia, user=self.user).count(), 3)
        self.assertEqual(set(Topic.objects.filter(subject=self.materia).values_list('name', flat=True)),
                         {'Álgebra', 'Historia', 'Biología'})
        mc = Question.objects.get(question_text='¿Cuánto es 2+2?')
        self.assertEqual(mc.question_type, 'opcion_multiple')
        self.assertEqual(json.loads(mc.options_json), ['1', '2', '3', '4'])
        self.assertEqual(mc.bloom_level, 1)
        vf = Question.objects.get(question_text='¿San Martín cruzó los Andes?')
        self.assertEqual(vf.answer_text, 'Verdadero')
        self.assertEqual(vf.subtopic.name, 'Argentina')

    def test_importar_omitiendo_duplicadas(self):
        q = Question.objects.create(user=self.user, question_text='¿Cuánto es 2+2?', answer_text='4')
        q.subjects.add(self.materia)
        resp = self.do_import(CSV_OK, skip_duplicates='1')
        self.assertEqual(resp.json()['created'], 2)
        self.assertEqual(resp.json()['skipped'], 1)
        self.assertEqual(Question.objects.filter(question_text='¿Cuánto es 2+2?').count(), 1)

    def test_importar_sin_omitir_duplica(self):
        q = Question.objects.create(user=self.user, question_text='¿Cuánto es 2+2?', answer_text='4')
        q.subjects.add(self.materia)
        self.assertEqual(self.do_import(CSV_OK).json()['created'], 3)
        self.assertEqual(Question.objects.filter(question_text='¿Cuánto es 2+2?').count(), 2)

    def test_importar_archivo_sin_filas_validas_es_error(self):
        resp = self.do_import("pregunta,respuesta,tema\n,,\n")
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()['ok'])
        self.assertEqual(Question.objects.count(), 0)

    def test_filas_invalidas_no_impiden_importar_las_buenas(self):
        csv = "pregunta,respuesta,tema\n¿Ok?,Sí,T\n,roto,T\n"
        data = self.do_import(csv).json()
        self.assertEqual(data['created'], 1)
        self.assertEqual(data['error_count'], 1)

    def test_extension_no_soportada(self):
        resp = self.preview(CSV_OK, 'lote.xlsx')
        self.assertEqual(resp.status_code, 400)

    def test_materia_ajena_se_rechaza_en_ambos_endpoints(self):
        otro = make_user('otro4')
        ajena = Subject.objects.create(name='Ajena', created_by=otro, es_catalogo_institucional=False)
        self.assertEqual(self.preview(CSV_OK, subject=ajena).status_code, 400)
        resp = self.client.post(reverse('material:upload_questions_wizard_import'), {
            'file': csv_file(CSV_OK), 'subject_id': ajena.pk,
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Question.objects.count(), 0)

    def test_archivo_demasiado_grande(self):
        from . import views
        original = views.UPLOAD_WIZARD_MAX_FILE_BYTES
        views.UPLOAD_WIZARD_MAX_FILE_BYTES = 50
        try:
            resp = self.preview(CSV_OK)
        finally:
            views.UPLOAD_WIZARD_MAX_FILE_BYTES = original
        self.assertEqual(resp.status_code, 400)

    def test_endpoints_requieren_login(self):
        anon = Client()
        for name in ('upload_questions_wizard_save', 'upload_questions_wizard_preview', 'upload_questions_wizard_import'):
            self.assertEqual(anon.post(reverse(f'material:{name}')).status_code, 302)


class LegacyUploadStillWorksTests(UploadWizardBase):
    """El formulario clásico (/upload-questions/, pestaña Lote) comparte
    parseo con el asistente tras el refactor: no debe haber cambiado."""

    def test_lote_clasico_sigue_importando(self):
        resp = self.client.post(reverse('material:upload_questions'), {
            'file': csv_file(CSV_OK), 'subject_id': self.materia.pk,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Question.objects.filter(subjects=self.materia).count(), 3)

    def test_txt_clasico_sigue_importando(self):
        resp = self.client.post(reverse('material:upload_questions'), {
            'file': csv_file(TXT_OK, 'lote.txt'), 'subject_id': self.materia.pk,
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Question.objects.filter(subjects=self.materia).count(), 2)

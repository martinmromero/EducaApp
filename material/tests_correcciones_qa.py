"""Correcciones que salieron de la ronda de pruebas del 2026-10-16.

- Fusionar materias/carreras con tópicos de igual nombre del mismo docente.
- Exportar a PDF con logos SVG (escudos de ejemplo o logos .svg subidos).
- Editar un examen: la fecha en formato dd/mm/aaaa pasa a ISO y se mandan los
  nombres en bruto para no perder institución/facultad/carrera/sede.
- Importar CSV separado por punto y coma (Excel en español).
Corre contra una base descartable."""
import base64
import io

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Career, CareerSubject, Exam, Question, Subject, Topic
from .views import _build_preview_exam_payload_from_exam, _fusionar_en_destino, _iter_csv_rows

User = get_user_model()

SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120">'
    '<circle cx="60" cy="60" r="50" fill="#1f6f5c"/><rect x="40" y="40" width="40" height="40" fill="#fff"/></svg>'
)


def make_user(username):
    user = User.objects.create_user(username=username, password='testpass123')
    user.profile.security_question = 'comida_favorita'
    user.profile.save()
    return user


class FusionConTopicosDuplicadosTests(TestCase):
    def setUp(self):
        self.ana = make_user('q_ana')
        self.carrera = Career.objects.create(name='Sistemas', es_catalogo_institucional=True)
        self.origen = Subject.objects.create(name='Inglés personal', created_by=self.ana, es_catalogo_institucional=False)
        self.destino = Subject.objects.create(name='Inglés I', es_catalogo_institucional=True)
        self.cs_origen = CareerSubject.objects.create(career=self.carrera, subject=self.origen)
        self.cs_destino = CareerSubject.objects.create(career=self.carrera, subject=self.destino)

    def _topico(self, nombre, subject, cs):
        return Topic.objects.create(name=nombre, subject=subject, career_subject=cs, created_by=self.ana)

    def test_fusionar_materia_con_topico_del_mismo_nombre_no_falla(self):
        t_origen = self._topico('Colisión', self.origen, self.cs_origen)
        t_destino = self._topico('Colisión', self.destino, self.cs_destino)
        suelto = self._topico('Sin carrera', self.origen, None)
        pregunta = Question.objects.create(
            question_text='¿Cuál es el término?', answer_text='x', user=self.ana, topic=t_origen)
        pregunta.subjects.add(self.origen)

        _fusionar_en_destino('materia', self.origen, self.destino)

        self.assertFalse(Subject.objects.filter(pk=self.origen.pk).exists())
        self.assertEqual(Topic.objects.filter(name='Colisión', subject=self.destino).count(), 1)
        pregunta.refresh_from_db()
        self.assertEqual(pregunta.topic_id, t_destino.pk)
        suelto.refresh_from_db()
        self.assertEqual(suelto.subject_id, self.destino.pk)

    def test_fusionar_carrera_con_topico_del_mismo_nombre_no_falla(self):
        otra = Career.objects.create(name='Sistemas personal', created_by=self.ana, es_catalogo_institucional=False)
        materia = Subject.objects.create(name='Matemática', es_catalogo_institucional=True)
        cs_origen = CareerSubject.objects.create(career=otra, subject=materia)
        cs_destino = CareerSubject.objects.create(career=self.carrera, subject=materia)
        t_origen = self._topico('Límites', materia, cs_origen)
        t_destino = self._topico('Límites', materia, cs_destino)
        pregunta = Question.objects.create(
            question_text='¿Qué es un límite?', answer_text='x', user=self.ana, topic=t_origen)

        _fusionar_en_destino('carrera', otra, self.carrera)

        self.assertFalse(Career.objects.filter(pk=otra.pk).exists())
        self.assertEqual(Topic.objects.filter(name='Límites', career_subject=cs_destino).count(), 1)
        pregunta.refresh_from_db()
        self.assertEqual(pregunta.topic_id, t_destino.pk)

    def test_los_topicos_sin_colision_se_mudan_a_la_carrera_materia_destino(self):
        t = self._topico('Único', self.origen, self.cs_origen)
        _fusionar_en_destino('materia', self.origen, self.destino)
        t.refresh_from_db()
        self.assertEqual((t.subject_id, t.career_subject_id), (self.destino.pk, self.cs_destino.pk))


class PdfConLogoSvgTests(TestCase):
    def test_un_logo_svg_se_rasteriza_en_vez_de_romper(self):
        from .renderers.pdf_renderer import _to_raster_png
        png = _to_raster_png(SVG.encode())
        self.assertIsNotNone(png)
        self.assertTrue(png.startswith(b'\x89PNG'))

    def test_un_png_se_deja_como_esta_y_basura_da_none(self):
        from PIL import Image as PILImage
        from .renderers.pdf_renderer import _to_raster_png
        buf = io.BytesIO()
        PILImage.new('RGB', (4, 4), 'red').save(buf, 'PNG')
        self.assertEqual(_to_raster_png(buf.getvalue()), buf.getvalue())
        self.assertIsNone(_to_raster_png(b'esto no es una imagen'))

    def test_el_encabezado_con_logo_svg_devuelve_una_imagen(self):
        from reportlab.platypus import Image
        from .renderers.pdf_renderer import _build_logo_flowable
        uri = 'data:image/svg+xml;base64,' + base64.b64encode(SVG.encode()).decode()
        self.assertIsInstance(_build_logo_flowable({'logo_b64': uri}), Image)

    def test_un_logo_ilegible_no_rompe_el_encabezado(self):
        from .renderers.pdf_renderer import _build_logo_flowable
        uri = 'data:image/svg+xml;base64,' + base64.b64encode(b'no es svg').decode()
        _build_logo_flowable({'logo_b64': uri})  # no debe lanzar


class EditarExamenPrefillTests(TestCase):
    def setUp(self):
        self.user = make_user('q_edit')
        self.subject = Subject.objects.create(name='Bases de Datos', created_by=self.user)

    def _examen(self, **kw):
        return Exam.objects.create(
            title='Parcial', subject=self.subject, created_by=self.user,
            institution_name=kw.pop('institution_name', 'Universidad Ajena'),
            faculty_name='Facultad Ajena', career_name='Carrera Ajena', campus_name='Sede Ajena',
            date_str=kw.pop('date_str', '15/06/2026'), catedra='Cátedra QA', **kw)

    def test_la_fecha_dd_mm_aaaa_pasa_a_iso_para_el_input_date(self):
        payload = _build_preview_exam_payload_from_exam(self._examen())
        self.assertEqual(payload['fecha'], '2026-06-15')

    def test_una_fecha_ya_iso_no_cambia(self):
        payload = _build_preview_exam_payload_from_exam(self._examen(date_str='2026-11-20'))
        self.assertEqual(payload['fecha'], '2026-11-20')

    def test_se_mandan_los_nombres_en_bruto_y_la_catedra(self):
        payload = _build_preview_exam_payload_from_exam(self._examen())
        self.assertEqual(payload['institucion_name'], 'Universidad Ajena')
        self.assertEqual(payload['facultad_name'], 'Facultad Ajena')
        self.assertEqual(payload['carrera_name'], 'Carrera Ajena')
        self.assertEqual(payload['sede_name'], 'Sede Ajena')
        self.assertEqual(payload['catedra'], 'Cátedra QA')


class CsvConPuntoYComaTests(TestCase):
    def _filas(self, texto):
        return list(_iter_csv_rows(texto.splitlines(keepends=True)))

    def test_csv_con_comas_sigue_andando(self):
        filas = self._filas('pregunta,respuesta,tema\n¿A?,B,T1\n')
        self.assertEqual(filas[0][1]['pregunta'], '¿A?')
        self.assertEqual(filas[0][1]['tema'], 'T1')

    def test_csv_de_excel_con_punto_y_coma_y_bom(self):
        filas = self._filas('﻿pregunta;respuesta;tema\n¿A, con coma?;B;T1\n')
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0][1]['pregunta'], '¿A, con coma?')
        self.assertEqual(filas[0][1]['respuesta'], 'B')

    def test_csv_con_tabuladores(self):
        filas = self._filas('pregunta\trespuesta\ttema\n¿A?\tB\tT1\n')
        self.assertEqual(filas[0][1]['tema'], 'T1')

    def test_archivo_vacio_no_rompe(self):
        self.assertEqual(self._filas(''), [])

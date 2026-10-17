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
import json

from django.test import Client, TestCase
from django.urls import reverse

from .models import (
    Career, CareerSubject, ContentShare, Exam, GroupMembership, Question, SharingGroup, Subject, Topic,
)
from .views import (
    _build_preview_exam_payload_from_exam, _fusionar_en_destino, _iter_csv_rows, _iter_txt_blocks,
    _leer_plan_de_estudios,
)

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


class MateriaCompartidaEnAsistenteTests(TestCase):
    """Un docente al que le compartieron una materia (grupo de confianza) puede
    armarle un examen o un oral desde el Asistente completo, sin que esa materia
    pase a ser "visible" para administrarla."""

    def setUp(self):
        self.ana = make_user('c_ana')
        self.beto = make_user('c_beto')
        self.cleo = make_user('c_cleo')
        self.carrera_ana = Career.objects.create(name='Carrera de Ana', created_by=self.ana, es_catalogo_institucional=False)
        self.materia = Subject.objects.create(name='Historia compartida', created_by=self.ana, es_catalogo_institucional=False)
        self.cs = CareerSubject.objects.create(career=self.carrera_ana, subject=self.materia)
        self.tema = Topic.objects.create(name='Tema 1', subject=self.materia, career_subject=self.cs, created_by=self.ana)
        for i in range(3):
            q = Question.objects.create(
                question_text=f'Pregunta {i}', answer_text='r', user=self.ana, topic=self.tema, bloom_level=1)
            q.subjects.add(self.materia)
        grupo = SharingGroup.objects.create(name='Cátedra', created_by=self.ana)
        GroupMembership.objects.create(group=grupo, user=self.ana, status='accepted')
        GroupMembership.objects.create(group=grupo, user=self.beto, status='accepted')
        ContentShare.objects.create(group=grupo, shared_by=self.ana, kind='materia', subject=self.materia, is_active=True)
        self.carrera_beto = Career.objects.create(name='Carrera de Beto', created_by=self.beto, es_catalogo_institucional=False)

    def _cliente(self, user):
        c = Client()
        c.force_login(user)
        return c

    def test_helpers_de_visibilidad(self):
        from . import content_visibility as cv
        self.assertIn(self.materia, cv.get_shared_subjects(self.beto))
        self.assertIn(self.materia, cv.get_usable_subjects(self.beto))
        # Compartida no es "visible": no se administra ni se lista como propia.
        self.assertNotIn(self.materia, cv.get_visible_subjects(self.beto))
        # Quien no está en el grupo no la ve de ninguna forma.
        self.assertNotIn(self.materia, cv.get_usable_subjects(self.cleo))
        # La dueña no se la ve como "compartida conmigo".
        self.assertNotIn(self.materia, cv.get_shared_subjects(self.ana))

    def test_el_paso_materia_lista_las_compartidas(self):
        r = self._cliente(self.beto).get(reverse('material:full_wizard_shared_subjects'))
        nombres = [m['name'] for m in r.json()['subjects']]
        self.assertEqual(nombres, ['Historia compartida'])
        self.assertTrue(r.json()['subjects'][0]['compartida'])
        r2 = self._cliente(self.cleo).get(reverse('material:full_wizard_shared_subjects'))
        self.assertEqual(r2.json()['subjects'], [])

    def test_el_buscador_las_ofrece_solo_si_se_pide(self):
        c = self._cliente(self.beto)
        url = reverse('material:check_catalog_duplicate')
        self.assertEqual(c.get(url, {'nivel': 'materia', 'q': 'Historia'}).json(), [])
        r = c.get(url, {'nivel': 'materia', 'q': 'Historia', 'incluir_compartidas': '1'}).json()
        self.assertEqual([m['name'] for m in r], ['Historia compartida'])
        self.assertTrue(r[0]['compartida'])

    def test_elegirla_no_la_vincula_a_la_carrera_de_quien_la_usa(self):
        c = self._cliente(self.beto)
        r = c.post(reverse('material:full_wizard_save_step'), json.dumps({
            'step': 'materia', 'action': 'existente', 'existing_id': self.materia.pk,
            'carrera_id': self.carrera_beto.pk,
        }), content_type='application/json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()['ok'])
        self.assertFalse(CareerSubject.objects.filter(career=self.carrera_beto, subject=self.materia).exists())

    def test_quien_no_esta_en_el_grupo_no_puede_elegirla(self):
        r = self._cliente(self.cleo).post(reverse('material:full_wizard_save_step'), json.dumps({
            'step': 'materia', 'action': 'existente', 'existing_id': self.materia.pk,
        }), content_type='application/json')
        self.assertEqual(r.status_code, 400)

    def test_el_progreso_cuenta_las_preguntas_compartidas(self):
        r = self._cliente(self.beto).get(reverse('material:full_wizard_subject_progress'), {'subject_id': self.materia.pk})
        self.assertEqual(r.json()['question_count'], 3)
        self.assertEqual(r.json()['own_question_count'], 0)
        r2 = self._cliente(self.cleo).get(reverse('material:full_wizard_subject_progress'), {'subject_id': self.materia.pk})
        self.assertEqual(r2.json()['question_count'], 0)

    def test_el_asistente_de_examen_embebido_precarga_la_materia_compartida(self):
        r = self._cliente(self.beto).get(reverse('material:create_exam_wizard'), {'fw': '1', 'subject_id': self.materia.pk})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Historia compartida')


class TxtConLineasDeContinuacionTests(TestCase):
    def _bloques(self, texto):
        return list(_iter_txt_blocks(texto.splitlines(keepends=True)))

    def test_los_dos_puntos_dentro_del_texto_no_cortan_el_campo(self):
        bloques = self._bloques(
            'pregunta: Defina el término: "átomo". Ejemplo: H2O\nrespuesta: Unidad básica: la menor parte\ntema: Química: general\n')
        datos = bloques[0][1]
        self.assertEqual(datos['pregunta'], 'Defina el término: "átomo". Ejemplo: H2O')
        self.assertEqual(datos['tema'], 'Química: general')

    def test_una_linea_de_continuacion_se_suma_a_la_pregunta(self):
        bloques = self._bloques('pregunta: Explique la hora 10:30\ncon detalle en otra línea: aquí\nrespuesta: x\ntema: T\n')
        self.assertEqual(bloques[0][1]['pregunta'], 'Explique la hora 10:30 con detalle en otra línea: aquí')

    def test_la_introduccion_con_dos_puntos_antes_del_primer_bloque_se_ignora(self):
        bloques = self._bloques('Ejemplo de archivo: copiar el bloque.\n\npregunta: A\nrespuesta: B\ntema: T\n')
        self.assertEqual(len(bloques), 1)
        self.assertEqual(set(bloques[0][1]), {'pregunta', 'respuesta', 'tema'})


class PlanDeEstudiosAnioInvalidoTests(TestCase):
    def test_un_anio_invalido_conserva_el_numero_y_el_cuatrimestre(self):
        class FakeSubject:
            name = 'Álgebra'
        class FakeCS:
            pk = 7
            subject = FakeSubject()
        post = {'plan_numero_7': '12', 'plan_anio_7': '99', 'plan_cuatri_7': '1.º'}
        cambios, errores = _leer_plan_de_estudios(post, [FakeCS()])
        self.assertEqual(cambios[7], {'numero_materia': '12', 'cuatrimestre_cursada': '1.º'})
        self.assertNotIn('anio_cursada', cambios[7])
        self.assertEqual(len(errores), 1)

    def test_un_anio_valido_se_guarda_completo(self):
        class FakeSubject:
            name = 'Álgebra'
        class FakeCS:
            pk = 7
            subject = FakeSubject()
        cambios, errores = _leer_plan_de_estudios({'plan_numero_7': '1', 'plan_anio_7': '2', 'plan_cuatri_7': ''}, [FakeCS()])
        self.assertEqual(cambios[7]['anio_cursada'], 2)
        self.assertEqual(errores, [])


class MensajeDeFusionTests(TestCase):
    def test_la_solicitud_fusionada_lo_dice(self):
        from .models import CatalogRequest
        solicitud = CatalogRequest(
            tipo='topico', estado='aprobada', nombre_propuesto='Vocab. de obra',
            nota_admin='Fusionado con "Vocabulario de obra", ya existente en el catálogo institucional.')
        mensaje = solicitud.resultado_mensaje()
        self.assertIn('se fusionó con "Vocabulario de obra"', mensaje)
        self.assertNotIn('ya se sumó', mensaje)

    def test_la_aprobada_normal_sigue_igual(self):
        from .models import CatalogRequest
        solicitud = CatalogRequest(tipo='topico', estado='aprobada', nombre_propuesto='Frases', nota_admin='')
        self.assertIn('ya se sumó al catálogo institucional', solicitud.resultado_mensaje())


class ExchangeQuestionInvalidaTests(TestCase):
    def test_una_pregunta_que_no_corresponde_da_404_en_espanol(self):
        user = make_user('q_oral')
        c = Client()
        c.force_login(user)
        r = c.post(reverse('material:exchange_question'), {'student_question_id': '999999', 'new_question_id': '1'})
        self.assertEqual(r.status_code, 404)
        self.assertFalse(r.json()['success'])
        self.assertNotIn('matches', r.json()['error'])


class TipoDeExamenTests(TestCase):
    def test_los_tipos_del_formulario_tienen_nombre_legible(self):
        for valor, texto in (('1er_parcial', '1er. Parcial'), ('recuperatorio', 'Recuperatorio'),
                             ('practico', 'Práctico'), ('final', 'Final'), ('parcial', 'Parcial')):
            self.assertEqual(Exam(exam_type=valor).get_exam_type_display(), texto)


class TopicosDeIAConCarreraTests(TestCase):
    def test_con_la_carrera_elegida_el_topico_queda_en_esa_carrera(self):
        from .content_visibility import resolve_career_subject
        ana = make_user('ia_ana')
        a = Career.objects.create(name='Carrera A', es_catalogo_institucional=True)
        b = Career.objects.create(name='Carrera B', es_catalogo_institucional=True)
        materia = Subject.objects.create(name='Inglés I', es_catalogo_institucional=True)
        cs_a = CareerSubject.objects.create(career=a, subject=materia)
        CareerSubject.objects.create(career=b, subject=materia)
        self.assertIsNone(resolve_career_subject(materia))            # varias carreras: sin carrera
        self.assertEqual(resolve_career_subject(materia, a.pk), cs_a)  # con la carrera elegida


class RutasQueDabanErrorTests(TestCase):
    def test_los_resultados_de_aprendizaje_sin_sesion_redirigen_al_login(self):
        r = Client().get('/carrera-materia/1/outcomes/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('login', r['Location'])

    def test_unidades_con_materia_vacia_devuelve_lista_vacia(self):
        user = make_user('u_unidades')
        c = Client()
        c.force_login(user)
        r = c.get('/get-unidades/', {'subject_id': ''})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])

    def test_el_admin_de_django_permite_agregar_una_materia(self):
        admin = User.objects.create_superuser('adm_django', 'a@b.com', 'pass-12345')
        c = Client()
        c.force_login(admin)
        self.assertEqual(c.get('/admin/material/subject/add/').status_code, 200)


class LimpiezaRonda2Tests(TestCase):
    """Lo que quedó tras eliminar el código marcado "CANDIDATO A BORRAR" (2026-10-17)."""

    def setUp(self):
        self.user = make_user('l_ana')
        self.client = Client()
        self.client.force_login(self.user)

    def test_las_rutas_eliminadas_ya_no_existen(self):
        from django.urls import NoReverseMatch
        for nombre, kwargs in (('institution_v2_logs', {'pk': 1}), ('download_template', {'format': 'csv'})):
            with self.assertRaises(NoReverseMatch):
                reverse('material:' + nombre, kwargs=kwargs)
        self.assertEqual(self.client.get('/instituciones-v2/logs/1/').status_code, 404)
        self.assertEqual(self.client.get('/download-template/csv/').status_code, 404)

    def test_la_ruta_de_resultados_de_aprendizaje_sigue_viva(self):
        self.assertEqual(self.client.get(reverse('material:get_learning_outcomes')).status_code, 200)

    def test_editar_plantilla_abre_y_un_post_directo_no_guarda(self):
        from .models import ExamTemplate
        from .models import FacultyV2, InstitutionV2
        materia = Subject.objects.create(name='Álgebra', created_by=self.user)
        inst = InstitutionV2.objects.create(name='Inst L', created_by=self.user)
        fac = FacultyV2.objects.create(name='Fac L', institution=inst, created_by=self.user)
        carrera = Career.objects.create(name='Carrera L', created_by=self.user, es_catalogo_institucional=False)
        plantilla = ExamTemplate.objects.create(
            name='Mi plantilla', created_by=self.user, subject=materia,
            institution=inst, faculty=fac, career=carrera)
        url = reverse('material:edit_exam_template', args=[plantilla.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        r = self.client.post(url, {'name': 'Cambiado por POST directo'})
        self.assertEqual(r.status_code, 302)
        plantilla.refresh_from_db()
        self.assertEqual(plantilla.name, 'Mi plantilla')


class CacheDeOpcionesDeFiltroTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.ana = make_user('f_ana')
        self.beto = make_user('f_beto')
        self.materia = Subject.objects.create(name='Historia', created_by=self.ana)
        self.tema = Topic.objects.create(name='Tema 1', subject=self.materia, created_by=self.ana)
        self.q = Question.objects.create(question_text='P1', answer_text='r', user=self.ana, topic=self.tema, bloom_level=1)
        self.q.subjects.add(self.materia)

    def _opciones(self, user, query=''):
        from django.test import RequestFactory
        from .column_filters import get_filter_options, get_selected_filters
        from .views import QUESTION_FILTER_FIELDS
        request = RequestFactory().get('/lista-preguntas/' + query)
        request.user = user
        selected = get_selected_filters(request, QUESTION_FILTER_FIELDS)
        return get_filter_options(Question.objects.filter(user=user), QUESTION_FILTER_FIELDS, selected, request=request)

    def test_la_segunda_llamada_no_toca_la_base(self):
        primera = self._opciones(self.ana)
        with self.assertNumQueries(0):
            segunda = self._opciones(self.ana)
        self.assertEqual(primera, segunda)

    def test_un_tema_nuevo_aparece_enseguida(self):
        antes = {o['label'] for o in self._opciones(self.ana)['topic']}
        nuevo = Topic.objects.create(name='Tema 2', subject=self.materia, created_by=self.ana)
        Question.objects.create(question_text='P2', answer_text='r', user=self.ana, topic=nuevo, bloom_level=2)
        despues = {o['label'] for o in self._opciones(self.ana)['topic']}
        self.assertNotIn('Tema 2', antes)
        self.assertIn('Tema 2', despues)

    def test_cada_usuario_y_cada_url_tienen_su_entrada(self):
        self._opciones(self.ana)
        # Otro usuario: no reutiliza lo de Ana (y no ve sus temas).
        self.assertEqual([o['label'] for o in self._opciones(self.beto)['topic'] if o['value'] != '__none__'], [])
        # Misma persona con otros parámetros: calcula de nuevo, no devuelve lo anterior.
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            self._opciones(self.ana, '?bloom_level=1')
        self.assertGreater(len(ctx), 0)

    def test_borrar_invalida(self):
        self._opciones(self.ana)
        self.q.delete()
        topicos = [o for o in self._opciones(self.ana)['topic'] if o['value'] != '__none__']
        self.assertEqual(topicos, [])

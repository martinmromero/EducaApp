"""Generar con IA (2026-10-31): motivo de descarte de preguntas, panel de privacidad y niveles de Bloom a priorizar."""
import json

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse

from .models import Question, Subject
from .views_document_processor import _parse_bloom_levels, _privacy_info

User = get_user_model()


def _docente(nombre):
    u = User.objects.create_user(username=nombre, password='testpass123')
    u.profile.security_question = 'comida_favorita'
    u.profile.onboarding_completed = True
    u.profile.interface_mode = 'avanzado'
    u.profile.save()
    return u


def _pregunta(texto, **extra):
    base = {'pregunta': texto, 'respuesta': 'R', 'tipo': 'desarrollo', 'dificultad': 3, 'bloom_nivel': 2}
    base.update(extra)
    return base


class MotivoDescarteTests(TestCase):
    def setUp(self):
        self.user = _docente('md_docente')
        self.materia = Subject.objects.create(name='Materia de prueba', created_by=self.user)
        self.c = Client()
        self.c.force_login(self.user)

    def _guardar(self, aprobadas=(), rechazadas=()):
        resp = self.c.post(
            reverse('material:save_generated_questions'),
            data=json.dumps({
                'approved': list(aprobadas), 'rejected': list(rechazadas),
                'filename': 'doc.pdf', 'subject_ids': [self.materia.id],
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()

    def test_el_motivo_queda_en_la_pregunta_rechazada(self):
        self._guardar(rechazadas=[_pregunta('Rechazada 1', motivo_descarte='demasiado_simple')])
        q = Question.objects.get(question_text='Rechazada 1')
        self.assertFalse(q.ai_approved)
        self.assertEqual(q.discard_reason, 'demasiado_simple')
        self.assertEqual(q.discard_note, '')

    def test_el_detalle_solo_se_guarda_con_otro_y_se_recorta(self):
        self._guardar(rechazadas=[
            _pregunta('Con detalle', motivo_descarte='otro', motivo_detalle='x' * 500),
            _pregunta('Detalle ignorado', motivo_descarte='repetida', motivo_detalle='no debe guardarse'),
        ])
        self.assertEqual(len(Question.objects.get(question_text='Con detalle').discard_note), 300)
        self.assertEqual(Question.objects.get(question_text='Detalle ignorado').discard_note, '')

    def test_un_motivo_desconocido_se_ignora_y_descartar_sin_motivo_sigue_andando(self):
        self._guardar(rechazadas=[
            _pregunta('Motivo inventado', motivo_descarte='<script>'),
            _pregunta('Sin motivo'),
        ])
        for texto in ('Motivo inventado', 'Sin motivo'):
            q = Question.objects.get(question_text=texto)
            self.assertFalse(q.ai_approved)
            self.assertEqual(q.discard_reason, '')

    def test_las_aprobadas_no_guardan_motivo(self):
        self._guardar(aprobadas=[_pregunta('Aprobada', motivo_descarte='demasiado_simple')])
        q = Question.objects.get(question_text='Aprobada')
        self.assertTrue(q.ai_approved)
        self.assertEqual(q.discard_reason, '')

    def test_el_listado_muestra_el_motivo(self):
        self._guardar(rechazadas=[_pregunta('Listada', motivo_descarte='fuera_del_texto')])
        html = self.c.get(reverse('material:lista_preguntas')).content.decode()
        self.assertIn('No se desprende del texto', html)

    def test_el_listado_muestra_solo_el_motivo_y_el_detalle_va_en_el_tooltip(self):
        self._guardar(rechazadas=[_pregunta('Con nota', motivo_descarte='otro', motivo_detalle='detalle largo de prueba')])
        html = self.c.get(reverse('material:lista_preguntas')).content.decode()
        self.assertIn('>Otro motivo</div>', html)
        self.assertIn('title="Otro (detallar): detalle largo de prueba"', html)
        self.assertNotIn('>Otro (detallar): detalle largo de prueba<', html)

    def test_las_opciones_incluyen_las_pedidas(self):
        etiquetas = [e for _, e in Question.DISCARD_REASON_CHOICES]
        for esperado in ('Demasiado simple', 'No es relevante', 'Muy parecida a otras preguntas', 'Otro (detallar)'):
            self.assertTrue(any(e.startswith(esperado) for e in etiquetas), esperado)


class PantallaGenerarConIATests(TestCase):
    def setUp(self):
        self.c = Client()
        self.c.force_login(_docente('gen_docente'))

    def test_la_pantalla_trae_panel_de_privacidad_niveles_de_bloom_y_motivos(self):
        html = self.c.get(reverse('material:document_processor_dashboard')).content.decode()
        self.assertIn('id="privacyPanel"', html)
        self.assertIn('¿Qué se envía a la IA y adónde?', html)
        for n in range(1, 7):
            self.assertIn(f'id="bl_{n}"', html)
        self.assertIn('id="bloomModeHint"', html)
        # opciones del descarte disponibles para el JS
        self.assertIn('muy parecida a otras preguntas'.lower(), html.lower())

    def test_el_texto_del_panel_no_usa_voseo(self):
        html = self.c.get(reverse('material:document_processor_dashboard')).content.decode()
        panel = html.split('id="privacyPanel"')[1].split('</details>')[0]
        for prohibido in ('podés', 'tenés', 'elegí', 'tildá'):
            self.assertNotIn(prohibido, panel.lower())


class PrivacidadYBloomUnitTests(SimpleTestCase):
    def test_privacy_info_distingue_publica_propia_y_externa(self):
        self.assertEqual(_privacy_info({}, True)['kind'], 'shared')
        self.assertEqual(_privacy_info({'backend': 'ollama_local'}, False)['kind'], 'local')
        externa = _privacy_info({'backend': 'openai_compatible', 'provider': 'groq'}, False)
        self.assertEqual((externa['kind'], externa['provider']), ('external', 'Groq'))
        self.assertEqual(_privacy_info({'backend': 'gemini', 'provider': 'gemini'}, False)['provider'], 'Google (Gemini)')

    def test_parse_bloom_levels(self):
        self.assertEqual(_parse_bloom_levels(None), [])
        self.assertEqual(_parse_bloom_levels(['5', 4, 4, 'x', 0, 7, None, 6]), [4, 5, 6])


class _BackendFalso:
    def __init__(self):
        self.prompt = ''

    def generate(self, prompt, **kwargs):
        self.prompt = prompt
        return {'success': True, 'text': '{"preguntas": []}'}


class NivelesDeBloomEnElPromptTests(TestCase):
    def _prompt(self, **kw):
        from .views_document_processor import _generate_questions_for_chunk
        b = _BackendFalso()
        _generate_questions_for_chunk('Texto de prueba suficientemente largo.', 'Cap', 3, 0, 1, backend=b, **kw)
        return b.prompt

    def test_sin_seleccion_el_prompt_no_menciona_prioridad(self):
        self.assertNotIn('priorizar estos niveles', self._prompt())

    def test_con_seleccion_el_prompt_lista_los_niveles_elegidos(self):
        prompt = self._prompt(bloom_levels=[4, 5])
        self.assertIn('priorizar estos niveles: 4=Analizar, 5=Evaluar', prompt)
        self.assertNotIn('3=Aplicar,', prompt.split('priorizar estos niveles')[1][:60])


class SinRecursosExternosTests(TestCase):
    """Bootstrap, iconos, fuentes y librerías se sirven desde el propio servidor (2026-10-31): nada se pide a un CDN."""

    PROHIBIDOS = ('googleapis', 'gstatic', 'jsdelivr', 'cdnjs', 'unpkg', 'code.jquery.com', 'bootstrapcdn')

    def _html(self, url_name, tema='default', **kw):
        u = _docente(f'sre_{tema}_{url_name}')
        u.profile.visual_theme = tema
        u.profile.save()
        c = Client()
        c.force_login(u)
        return c.get(reverse(url_name, **kw)).content.decode()

    def test_las_pantallas_principales_no_piden_nada_a_un_cdn(self):
        for nombre in ('material:index', 'material:lista_preguntas', 'material:document_processor_dashboard'):
            html = self._html(nombre)
            for dominio in self.PROHIBIDOS:
                self.assertNotIn(dominio, html, f'{nombre}: {dominio}')
            self.assertIn('vendor/bootstrap/css/bootstrap.min.', html)
            self.assertIn('vendor/fonts/fonts.', html)

    def test_las_pantallas_de_acceso_tampoco(self):
        c = Client()
        for url in ('/accounts/login/', '/404-prueba-inexistente/'):
            html = c.get(url).content.decode()
            for dominio in self.PROHIBIDOS:
                self.assertNotIn(dominio, html, f'{url}: {dominio}')

    def test_las_fuentes_de_todos_los_temas_estan_en_la_hoja_local(self):
        from pathlib import Path
        css = (Path(__file__).resolve().parent.parent / 'static' / 'vendor' / 'fonts' / 'fonts.css').read_text(encoding='utf-8')
        for familia in ('Inter', 'Montserrat', 'Public Sans', 'Bricolage Grotesque'):
            self.assertIn(f'font-family: "{familia}"', css)
        carpeta = Path(__file__).resolve().parent.parent / 'static' / 'vendor' / 'fonts'
        for archivo in carpeta.glob('*.woff2'):
            self.assertIn(archivo.name, css)

    def test_el_visor_de_documentos_usa_las_copias_locales(self):
        html = self._html('material:document_processor_dashboard')
        for ruta in ('vendor/pdfjs/pdf.min.', 'vendor/pdfjs/pdf.worker.min.', 'vendor/jszip/jszip.min.', 'vendor/docx-preview/docx-preview.min.'):  # el archivo lleva un hash en el nombre
            self.assertIn(ruta, html)


class RecorridoDeGenerarConIATests(TestCase):
    """El recorrido de Generar con IA no apunta a elementos ocultos (2026-10-31)."""

    def test_el_recorrido_muestra_el_encabezado_oculto_y_salta_lo_que_no_se_ve(self):
        from pathlib import Path
        js = (Path(__file__).resolve().parent.parent / 'static' / 'js' / 'page_tours' / 'doc_processor_tour.js').read_text(encoding='utf-8')
        self.assertIn('revealStatusHeader', js)
        self.assertIn('getBoundingClientRect', js)
        self.assertIn("'docStatusHeader'", js)


class AsistentesRetomarSinAvisosTests(TestCase):
    """Al retomar un borrador los asistentes avanzan sin avisos apilados ni mover la página (2026-10-31)."""

    def _js(self, nombre):
        from pathlib import Path
        return (Path(__file__).resolve().parent / 'static' / 'material' / 'js' / nombre).read_text(encoding='utf-8')

    def test_el_motor_ofrece_runSilently_y_goNext_devuelve_si_avanzo(self):
        js = self._js('wizard_engine.js')
        self.assertIn('runSilently: runSilently', js)
        self.assertIn('return false;', js)
        self.assertIn('if (!silencio) scrollToStepper();', js)

    def test_los_asistentes_retoman_con_runSilently_y_cortan_en_el_primer_paso_que_no_valida(self):
        for nombre in ('create_exam_wizard.js', 'create_exam_template_wizard.js', 'create_institution_v2_wizard.js',
                       'create_oral_exam_wizard.js', 'full_wizard.js'):
            js = self._js(nombre)
            self.assertIn('runSilently', js, nombre)
        # ya no quedan cadenas de goNext() sueltas al retomar el borrador del examen
        self.assertNotIn('wizardCtrl.goNext();\n                wizardCtrl.goNext();\n                wizardCtrl.goNext();', self._js('create_exam_wizard.js').replace('\r\n', '\n'))

    def test_el_asistente_completo_ajusta_el_marco_al_alto_visible_en_celular(self):
        js = self._js('full_wizard.js')
        self.assertIn('function fitExamFrame', js)
        self.assertIn('scrollToStepper', js)


class VerExamenAccionesTests(TestCase):
    """Pantalla del examen guardado (2026-10-31): hoja sola, botón «Acciones» y Bloom como pirámide."""

    def setUp(self):
        from .models import Exam, Topic
        self.user = _docente('vex_docente')
        materia = Subject.objects.create(name='Materia VEX', created_by=self.user)
        tema = Topic.objects.create(name='T', subject=materia)
        self.exam = Exam.objects.create(title='Examen VEX', subject=materia, created_by=self.user)
        for nivel in (1, 1, 4):
            q = Question.objects.create(user=self.user, question_text=f'P{nivel}', answer_text='r', topic=tema, bloom_level=nivel)
            q.subjects.add(materia)
            self.exam.questions.add(q)
        self.c = Client()
        self.c.force_login(self.user)

    def test_la_pantalla_trae_el_boton_acciones_con_ver_descargar_y_bloom(self):
        html = self.c.get(reverse('material:ver_examen', kwargs={'pk': self.exam.pk})).content.decode()
        for esperado in ('id="examActionsBtn"', 'id="accionesPanel"', 'id="viewShowAnswers"', 'id="exportIncludeAnswers"',
                         'id="examRubricsBtn"', 'bloom-pirami', 'Ajustar'):
            self.assertIn(esperado, html)
        # los tres botones de descarga y la pirámide con seis escalones
        self.assertEqual(html.count('class="bloom-escalon'), 6)
        self.assertIn('doDownload(\'pdf\', this)', html)

    def test_la_piramide_cuenta_las_preguntas_por_nivel(self):
        html = self.c.get(reverse('material:ver_examen', kwargs={'pk': self.exam.pk})).content.decode()
        recordar = html.split('Recordar</span>')[1][:80]
        self.assertIn('>2<', recordar)
        analizar = html.split('Analizar</span>')[1][:80]
        self.assertIn('>1<', analizar)

    def test_el_icono_de_pantalla_completa_ya_no_esta(self):
        html = self.c.get(reverse('material:ver_examen', kwargs={'pk': self.exam.pk})).content.decode()
        self.assertNotIn('bi-arrows-fullscreen', html)


class VistaPreviaAntesDeGuardarTests(TestCase):
    """Vista previa del examen antes de guardar (2026-11-01): a la vista queda solo «Guardar Examen»; lo demás va en «Acciones»."""

    def setUp(self):
        from .models import Topic
        self.user = _docente('vp_docente')
        self.materia = Subject.objects.create(name='Materia VP', created_by=self.user)
        tema = Topic.objects.create(name='T', subject=self.materia)
        q = Question.objects.create(user=self.user, question_text='PreguntaVP', answer_text='r', topic=tema, bloom_level=2)
        q.subjects.add(self.materia)
        self.c = Client()
        self.c.force_login(self.user)
        session = self.c.session
        session['preview_exam'] = {'subject': str(self.materia.id), 'topics': [str(tema.id)], 'questions': [str(q.id)], 'num_versions': '1'}
        session.save()

    def test_a_la_vista_solo_guardar_y_el_resto_en_acciones(self):
        html = self.c.get(reverse('material:preview_exam')).content.decode()
        zona = html[html.index('class="print-button no-print"'):]
        zona = zona[:zona.index('</div>')]
        self.assertIn('id="examSaveBtn"', zona)
        for fuera in ('Imprimir', 'Mostrar respuestas', 'Editar', 'Volver'):
            self.assertNotIn(fuera, zona)
        self.assertIn('id="examActionsBtn"', html)
        self.assertIn('css/skins', html)  # la forma de los botones sale del tema visual elegido
        panel = html[html.index('id="accionesPanel"'):]
        for dentro in ('Mostrar respuestas', 'Imprimir', 'Editar', 'Volver', 'Distribución cognitiva'):
            self.assertIn(dentro, panel)

    def test_varios_temas_dejan_guardar_a_la_vista_y_el_resto_en_acciones(self):
        from .models import Topic
        tema2 = Topic.objects.create(name='T2', subject=self.materia)
        q2 = Question.objects.create(user=self.user, question_text='PreguntaVP2', answer_text='r', topic=tema2, bloom_level=1)
        q2.subjects.add(self.materia)
        q1 = Question.objects.get(question_text='PreguntaVP')
        session = self.c.session
        session['preview_exam'] = {
            'subject': str(self.materia.id), 'topics': [str(q1.topic_id), str(tema2.id)],
            'questions': [str(q1.id), str(q2.id)], 'num_versions': '2', 'questions_per_version': '1', 'balance_by_topic': '1',
        }
        session.save()
        html = self.c.get(reverse('material:preview_exam')).content.decode()
        self.assertIn('id="saveExamVersionsBtn"', html)
        self.assertIn('id="examActionsBtn"', html)
        menu = html[html.index('id="examActionsBtn"'):]
        menu = menu[:menu.index('</ul>')]
        for dentro in ('Vista previa de impresión', 'Editar selección', 'Volver'):
            self.assertIn(dentro, menu)


class AccionesUnificadasTests(TestCase):
    """Panel «Acciones» (2026-11-01): «Incluir respuestas/rúbricas» son interruptores como «Mostrar respuestas», y los botones de la vista previa siguen la forma del tema."""

    def test_incluir_respuestas_es_un_interruptor_no_una_casilla(self):
        from .models import Exam
        user = _docente('acc_docente')
        materia = Subject.objects.create(name='Materia ACC', created_by=user)
        exam = Exam.objects.create(title='Examen ACC', subject=materia, created_by=user)
        c = Client()
        c.force_login(user)
        html = c.get(reverse('material:ver_examen', args=[exam.pk])).content.decode()
        bloque = html[html.index('id="accExport"'):]
        bloque = bloque[:bloque.index('</section>')]
        self.assertIn('view-toggle', bloque)
        self.assertIn('Incluir respuestas', bloque)
        self.assertNotIn('acc-checks', bloque)


class VerPreguntaMotivoTests(TestCase):
    """Detalle de una pregunta rechazada (2026-11-02): muestra el motivo del descarte y su detalle."""

    def setUp(self):
        from .models import Topic
        self.user = _docente('vpm_docente')
        self.materia = Subject.objects.create(name='Materia VPM', created_by=self.user)
        self.tema = Topic.objects.create(name='T', subject=self.materia)
        self.c = Client()
        self.c.force_login(self.user)

    def _pregunta(self, **kw):
        q = Question.objects.create(user=self.user, question_text='PreguntaVPM', answer_text='r', topic=self.tema,
                                    generated_by_ai=True, ai_approved=False, **kw)
        q.subjects.add(self.materia)
        return q

    def test_muestra_motivo_y_detalle(self):
        q = self._pregunta(discard_reason='otro', discard_note='no sirve para la unidad 3')
        html = self.c.get(reverse('material:ver_pregunta', args=[q.pk])).content.decode()
        self.assertIn('id="motivoRechazo"', html)
        self.assertIn('Otro (detallar)', html)
        self.assertIn('no sirve para la unidad 3', html)

    def test_rechazada_sin_motivo_lo_aclara(self):
        q = self._pregunta()
        html = self.c.get(reverse('material:ver_pregunta', args=[q.pk])).content.decode()
        self.assertIn('No se indicó un motivo', html)

    def test_aprobada_no_muestra_el_aviso(self):
        q = self._pregunta()
        Question.objects.filter(pk=q.pk).update(ai_approved=True)
        html = self.c.get(reverse('material:ver_pregunta', args=[q.pk])).content.decode()
        self.assertNotIn('id="motivoRechazo"', html)

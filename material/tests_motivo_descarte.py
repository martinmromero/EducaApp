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


class FuentesPorTemaTests(TestCase):
    """Las fuentes de Google que no usa el tema activo no se piden (2026-10-31)."""

    def _head(self, tema):
        u = _docente(f'ft_{tema}')
        u.profile.visual_theme = tema
        u.profile.save()
        c = Client()
        c.force_login(u)
        return c.get(reverse('material:index')).content.decode().split('</head>')[0]

    def test_tema_comun_pide_solo_inter(self):
        head = self._head('default')
        self.assertIn('family=Inter', head)
        for otra in ('Montserrat', 'Public+Sans', 'Bricolage'):
            self.assertNotIn('family=' + otra, head)

    def test_tema_uai_suma_montserrat(self):
        head = self._head('uai')
        self.assertIn('family=Montserrat', head)
        self.assertNotIn('Public+Sans', head)

    def test_tema_lapiz_rojo_suma_public_sans_y_bricolage(self):
        head = self._head('lapiz_rojo')
        self.assertIn('Public+Sans', head)
        self.assertIn('Bricolage', head)
        self.assertNotIn('family=Montserrat', head)


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

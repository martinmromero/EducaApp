"""Elegir páginas con gráficos y generar preguntas con IA (2026-10-26).

Antes: elegir solo páginas sin texto daba "No se pudo extraer texto de las unidades seleccionadas"; en una selección
mixta las páginas sin texto se descartaban (sus imágenes nunca llegaban al modelo) y, con el tope de preguntas, las
del texto desplazaban a las de las imágenes. Los pedidos a la IA se reemplazan por una función falsa."""
import json
import time
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from . import views_document_processor as vdp
from .tests_imagenes_pdf import _pdf_de_prueba

User = get_user_model()


def _usuario(nombre):
    u = User.objects.create_user(username=nombre, password='testpass123')
    u.profile.security_question = 'comida_favorita'
    u.profile.onboarding_completed = True
    u.profile.save()
    return u


class PaginasConGraficosTests(TestCase):
    def setUp(self):
        self.ruta = _pdf_de_prueba()
        self.user = _usuario('img_ana')
        self.client = Client()
        self.client.force_login(self.user)
        sesion = self.client.session
        sesion['doc_processor'] = {'file_path': self.ruta, 'filename': 'prueba.pdf'}
        sesion.save()

    def _pedir_texto(self, paginas):
        return self.client.post(reverse('material:get_pages_text'), data=json.dumps({'pages': paginas}),
                                content_type='application/json')

    def test_elegir_solo_paginas_sin_texto_ya_no_da_error(self):
        r = self._pedir_texto([3])
        self.assertEqual(r.status_code, 200, r.content)
        datos = r.json()
        self.assertTrue(datos['solo_sin_texto'])
        self.assertEqual([c['pages'] for c in datos['chapters']], [[3]])
        self.assertEqual(datos['chapters'][0]['content'], '')

    def test_en_una_seleccion_mixta_las_paginas_sin_texto_se_conservan(self):
        datos = self._pedir_texto([1, 2, 3]).json()
        self.assertEqual([c['pages'][0] for c in datos['chapters']], [1, 2, 3])
        self.assertEqual([c['sin_texto'] for c in datos['chapters']], [False, False, True])
        self.assertFalse(datos['solo_sin_texto'])

    def _capitulos(self):
        texto1 = 'Esta página tiene bastante texto corrido para no parecer un escaneo. ' * 3
        return [
            {'title': 'Página 1', 'content': texto1, 'tokens': 40, 'pages': [1]},
            {'title': 'Página 2', 'content': 'Figura 1. Ventas por trimestre. Texto de epígrafe que acompaña el gráfico de barras.',
             'tokens': 20, 'pages': [2]},
            {'title': 'Página 3', 'content': '', 'tokens': 0, 'pages': [3], 'sin_texto': True},
        ]

    def _correr(self, capitulos, con_imagenes, total=6, falla_imagenes=False):
        job_id = 'job-prueba-%s' % time.time()
        with vdp._jobs_lock:
            vdp._jobs[job_id] = {
                'chapter_indices': [], 'chapters_from_request': capitulos, 'filename': 'prueba.pdf',
                'question_types': [], 'total_questions': total, 'questions_per_block': 0,
                'doc_session': {'file_path': self.ruta, 'filename': 'prueba.pdf'}, 'user_id': self.user.id,
                'created_at': time.time(), 'existing_questions_list': [], 'existing_texts_set': set(),
                'include_images': con_imagenes,
            }
        llamadas = []

        def falso(texto, titulo, cantidad, i, n, **kw):
            imgs = kw.get('images')
            llamadas.append({'texto': texto, 'imagenes': [x['page'] for x in imgs] if imgs else None})
            if imgs and falla_imagenes:
                raise RuntimeError('El modelo no acepta imágenes')
            prefijo = 'IMG' if imgs else 'TXT'
            return [{'pregunta': f'{prefijo} {titulo} {k}', 'respuesta': 'r', 'tipo': 'desarrollo'} for k in range(4)]

        with mock.patch.object(vdp, '_generate_questions_for_chunk', side_effect=falso), \
                mock.patch('material.ai_router.get_backend_for_user', return_value=mock.MagicMock()), \
                mock.patch.object(vdp.time, 'sleep', lambda s: None):
            respuesta = self.client.get(reverse('material:stream_questions', args=[job_id]))
            crudo = b''.join(respuesta.streaming_content).decode('utf8')
        eventos = [json.loads(linea[6:]) for linea in crudo.split('\n') if linea.startswith('data: ')]
        return eventos, llamadas

    def test_con_imagenes_llegan_las_paginas_con_grafico_y_no_se_pierden_las_preguntas_de_las_imagenes(self):
        eventos, llamadas = self._correr(self._capitulos(), True, total=30)
        paginas = sorted(p for c in llamadas if c['imagenes'] for p in c['imagenes'])
        self.assertEqual(paginas, [2, 3])
        # Con un tope justo (6: 4 del primer capítulo y 2 del segundo) y las del texto primero, antes no entraba
        # ninguna de las imágenes.
        eventos, _ = self._correr(self._capitulos(), True, total=6)
        preguntas = [q['pregunta'] for e in eventos if e['type'] == 'questions' for q in e['questions']]
        self.assertTrue(any(p.startswith('IMG') for p in preguntas), preguntas)
        self.assertTrue(any(p.startswith('TXT') for p in preguntas), preguntas)
        self.assertLessEqual(len(preguntas), 6)

    def test_una_pagina_sin_texto_con_imagenes_genera_aunque_no_haya_texto(self):
        eventos, llamadas = self._correr([self._capitulos()[2]], True)
        self.assertEqual(llamadas, [{'texto': '', 'imagenes': [3]}])
        self.assertTrue(any(e['type'] == 'questions' and e['questions'] for e in eventos))

    def test_sin_imagenes_se_omiten_las_paginas_sin_texto_y_se_avisa(self):
        eventos, llamadas = self._correr(self._capitulos(), False)
        self.assertTrue(all(c['imagenes'] is None for c in llamadas))
        avisos = [e['message'] for e in eventos if e['type'] == 'aviso']
        self.assertTrue(any('Incluir imágenes' in a for a in avisos), avisos)

    def test_sin_imagenes_y_solo_paginas_sin_texto_da_un_error_que_dice_que_hacer(self):
        eventos, llamadas = self._correr([self._capitulos()[2]], False)
        errores = [e['message'] for e in eventos if e['type'] == 'error']
        self.assertEqual(llamadas, [])
        self.assertTrue(errores and 'Incluir imágenes' in errores[0], errores)

    def test_si_falla_la_llamada_de_imagenes_se_avisa_el_motivo_y_se_conserva_lo_del_texto(self):
        eventos, _ = self._correr(self._capitulos()[:2], True, falla_imagenes=True)
        mensajes = [e['message'] for e in eventos if e['type'] == 'chunk_error']
        self.assertTrue(any('El modelo no acepta imágenes' in m for m in mensajes), mensajes)
        self.assertTrue(any(e['type'] == 'questions' and e['questions'] for e in eventos))

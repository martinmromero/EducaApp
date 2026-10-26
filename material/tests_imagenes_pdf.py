"""Análisis de imágenes al generar preguntas con IA (2026-10-26): los gráficos dibujados como vectores y los
escaneos también llegan al modelo, solo de las páginas elegidas. Corre contra archivos temporales."""
import os
import tempfile

import fitz
from django.test import SimpleTestCase

from .ia_processor import extract_page_images, extract_visual_pages


def _pdf_de_prueba():
    doc = fitz.open()
    # 1: solo texto
    p = doc.new_page()
    p.insert_text((72, 100), 'Esta página tiene bastante texto corrido para no parecer un escaneo. ' * 3, fontsize=10)
    # 2: texto corto y un gráfico hecho con vectores (sin ninguna imagen incrustada)
    p = doc.new_page()
    p.insert_text((72, 60), 'Figura 1. Ventas por trimestre. Texto de epígrafe que acompaña el gráfico de barras.', fontsize=10)
    for i in range(15):
        p.draw_rect(fitz.Rect(80 + i * 20, 300 - i * 8, 94 + i * 20, 300), color=(0, 0, 1), fill=(0.2, 0.4, 0.9))
    # 3: página sin texto (como un escaneo)
    doc.new_page()
    # 4: otra de solo texto
    p = doc.new_page()
    p.insert_text((72, 100), 'Otra página de texto largo que no necesita imagen alguna para entenderse bien. ' * 3, fontsize=10)
    ruta = os.path.join(tempfile.mkdtemp(), 'prueba.pdf')
    doc.save(ruta)
    doc.close()
    return ruta


class ExtraerPaginasVisualesTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ruta = _pdf_de_prueba()

    def test_el_grafico_vectorial_y_la_pagina_sin_texto_se_dibujan_y_las_de_texto_no(self):
        paginas = [i['page'] for i in extract_visual_pages(self.ruta, [1, 2, 3, 4])]
        self.assertEqual(paginas, [2, 3])

    def test_la_extraccion_vieja_no_veia_el_grafico_vectorial(self):
        self.assertEqual(extract_page_images(self.ruta), [])

    def test_solo_mira_las_paginas_pedidas(self):
        self.assertEqual([i['page'] for i in extract_visual_pages(self.ruta, [3])], [3])
        self.assertEqual(extract_visual_pages(self.ruta, [1, 4]), [])

    def test_devuelve_jpeg_en_data_uri_y_respeta_el_tope(self):
        imagenes = extract_visual_pages(self.ruta, [2, 3], max_images=1)
        self.assertEqual(len(imagenes), 1)
        self.assertTrue(imagenes[0]['data_uri'].startswith('data:image/jpeg;base64,'))
        self.assertEqual(imagenes[0]['mime'], 'image/jpeg')

    def test_no_levanta_excepciones_con_archivos_que_no_sirven(self):
        self.assertEqual(extract_visual_pages('/no/existe.pdf', [1]), [])
        self.assertEqual(extract_visual_pages(self.ruta, []), [])
        self.assertEqual(extract_visual_pages(self.ruta, [99]), [])
        self.assertEqual(extract_visual_pages(self.ruta.replace('.pdf', '.docx'), [1]), [])

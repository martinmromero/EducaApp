"""La semilla del checklist de Modo Testing corre en el build de Render: un texto demasiado largo para la columna
tiró abajo un despliegue entero (2026-10-30, "value too long for type character varying(300)")."""
from django.core.management import call_command
from django.test import TestCase

from .management.commands import seed_test_checklist as semilla
from .models import TestChecklistItem


class SemillaChecklistTests(TestCase):
    def test_ningun_texto_supera_el_maximo_de_la_columna(self):
        maximo = TestChecklistItem._meta.get_field('text').max_length
        self.assertEqual(maximo, semilla.TEXTO_MAX)
        largos = [(len(i[2]), i[2][:60]) for i in semilla.ITEMS if len(i[2]) > maximo]
        self.assertEqual(largos, [])
        maximo_area = TestChecklistItem._meta.get_field('area_name').max_length
        self.assertEqual([i[1] for i in semilla.ITEMS if len(i[1]) > maximo_area], [])

    def test_los_textos_anteriores_apuntan_a_items_que_existen(self):
        claves = {(i[0], i[2]) for i in semilla.ITEMS}
        for clave in semilla.TEXTOS_ANTERIORES:
            self.assertIn(clave, claves)

    def test_el_comando_corre_completo_y_es_idempotente(self):
        call_command('seed_test_checklist')
        cantidad = TestChecklistItem.objects.count()
        call_command('seed_test_checklist')
        self.assertEqual(TestChecklistItem.objects.count(), cantidad)
        self.assertEqual(cantidad, len(semilla.ITEMS))

    def test_el_renombrado_del_asistente_conserva_el_item_y_sus_resultados(self):
        item = next(i for i in semilla.ITEMS if 'Asistente paso a paso' in i[2])
        viejo = item[2].replace('Asistente paso a paso', 'Asistente completo')
        existente = TestChecklistItem.objects.create(area_number=item[0], area_name=item[1], text=viejo, order=1)
        call_command('seed_test_checklist')
        existente.refresh_from_db()
        self.assertEqual(existente.text, item[2])

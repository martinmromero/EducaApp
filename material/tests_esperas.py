"""Avisos de espera (2026-10-29): script de actividad en todas las páginas y estado de la IA pública en caché."""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from .ai_router import GlobalFallbackBackend

User = get_user_model()


class _Interno:
    def __init__(self, estados):
        self.estados = list(estados)
        self.llamadas = 0

    def get_status(self):
        self.llamadas += 1
        return self.estados.pop(0) if self.estados else self.estados_ultimo

    def is_available(self):
        return True


class EstadoIAEnCacheTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_un_estado_conectado_se_reusa_sin_volver_a_preguntarle_al_proveedor(self):
        interno = _Interno([{'connected': True, 'model': 'm'}])
        interno.estados_ultimo = {'connected': False}
        backend = GlobalFallbackBackend(interno, config_id=101)
        self.assertTrue(backend.get_status()['connected'])
        self.assertTrue(backend.get_status()['connected'])
        self.assertEqual(interno.llamadas, 1)

    def test_un_estado_desconectado_no_se_guarda(self):
        interno = _Interno([{'connected': False}, {'connected': True}])
        interno.estados_ultimo = {'connected': True}
        backend = GlobalFallbackBackend(interno, config_id=102)
        self.assertFalse(backend.get_status()['connected'])
        self.assertTrue(backend.get_status()['connected'])
        self.assertEqual(interno.llamadas, 2)

    def test_cada_configuracion_tiene_su_propio_estado(self):
        a = _Interno([{'connected': True, 'model': 'a'}])
        a.estados_ultimo = {'connected': False}
        b = _Interno([{'connected': True, 'model': 'b'}])
        b.estados_ultimo = {'connected': False}
        self.assertEqual(GlobalFallbackBackend(a, config_id=201).get_status()['model'], 'a')
        self.assertEqual(GlobalFallbackBackend(b, config_id=202).get_status()['model'], 'b')


class ScriptDeActividadTests(TestCase):
    def test_las_paginas_con_menu_cargan_el_script_de_actividad(self):
        u = User.objects.create_user(username='es_docente', password='testpass123')
        u.profile.security_question = 'comida_favorita'
        u.profile.onboarding_completed = True
        u.profile.save()
        c = Client()
        c.force_login(u)
        html = c.get(reverse('material:index')).content.decode()
        self.assertIn('js/actividad', html)

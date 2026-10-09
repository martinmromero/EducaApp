"""La IA pública gratuita es la fuente principal; Ollama es una opción más.

Cubre el default de cada usuario, la migración de datos que pasa a la IA pública
a quien nunca eligió nada, los mensajes cuando no hay IA pública o se agotó el
cupo, y que ya no se cae a un Ollama inexistente. Corre contra una base
descartable."""
import importlib

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from . import ai_router
from .models import UserAIConfig

User = get_user_model()


def make_user(username):
    user = User.objects.create_user(username=username, password='testpass123')
    user.profile.security_question = 'comida_favorita'
    user.profile.save()
    return user


class DefaultSourceTests(TestCase):
    def test_un_usuario_nuevo_arranca_con_la_ia_publica(self):
        user = make_user('ia_nuevo')
        config, _ = UserAIConfig.objects.get_or_create(user=user)
        self.assertEqual(config.source, 'shared_demo')

    def test_el_formulario_sin_fuente_guarda_la_ia_publica(self):
        user = make_user('ia_form')
        client = Client()
        client.login(username='ia_form', password='testpass123')
        client.post(reverse('material:ai_config'), {})
        self.assertEqual(UserAIConfig.objects.get(user=user).source, 'shared_demo')


class MigracionDeDatosTests(TestCase):
    def setUp(self):
        migracion = importlib.import_module('material.migrations.0102_ia_publica_por_defecto')
        self.migrar = migracion.ollama_sin_url_a_ia_publica

    def test_ollama_sin_url_pasa_a_ia_publica(self):
        sin_url = UserAIConfig.objects.create(user=make_user('mig_a'), source='ollama_local', ollama_url=None)
        vacia = UserAIConfig.objects.create(user=make_user('mig_b'), source='ollama_local', ollama_url='')
        self.migrar(apps, None)
        sin_url.refresh_from_db()
        vacia.refresh_from_db()
        self.assertEqual((sin_url.source, vacia.source), ('shared_demo', 'shared_demo'))

    def test_ollama_con_url_propia_se_respeta(self):
        propia = UserAIConfig.objects.create(
            user=make_user('mig_c'), source='ollama_local', ollama_url='http://servidor:11434',
        )
        self.migrar(apps, None)
        propia.refresh_from_db()
        self.assertEqual(propia.source, 'ollama_local')

    def test_otras_fuentes_no_se_tocan(self):
        byok = UserAIConfig.objects.create(user=make_user('mig_d'), source='byok')
        self.migrar(apps, None)
        byok.refresh_from_db()
        self.assertEqual(byok.source, 'byok')


class SinIAPublicaTests(TestCase):
    """En la base de pruebas no hay ninguna GlobalAIConfig activa."""

    def setUp(self):
        self.user = make_user('ia_sin')
        self.client = Client()
        self.client.login(username='ia_sin', password='testpass123')

    def test_no_se_cae_a_ollama(self):
        backend = ai_router.get_backend_for_user(self.user)
        self.assertIsInstance(backend, ai_router.PublicAIUnavailableBackend)
        self.assertNotIsInstance(backend, ai_router.OllamaBackend)

    def test_generar_explica_que_hacer(self):
        result = ai_router.get_backend_for_user(self.user).generate('hola')
        self.assertFalse(result['success'])
        self.assertIn('Ollama', result['error'])
        self.assertIn('administrador', result['error'])

    def test_el_estado_dice_que_no_esta_disponible(self):
        data = self.client.get(reverse('material:ai_config_status')).json()
        self.assertFalse(data['connected'])
        self.assertEqual(data['source'], 'shared_demo')
        self.assertIn('IA pública', data['error'])


class CupoAgotadoTests(TestCase):
    def test_un_error_de_cupo_se_explica(self):
        crudo = {'success': False, 'error': 'Límite de solicitudes de groq alcanzado (429) tras reintentar.', 'text': None}
        result = ai_router._quota_friendly(crudo)
        self.assertEqual(result['error'], ai_router.SHARED_QUOTA_EXHAUSTED_MESSAGE)
        self.assertTrue(result['quota_exhausted'])

    def test_otros_errores_y_los_exitos_no_se_tocan(self):
        otro = {'success': False, 'error': 'JSON inválido', 'text': None}
        ok = {'success': True, 'text': 'hola'}
        self.assertEqual(ai_router._quota_friendly(otro), otro)
        self.assertEqual(ai_router._quota_friendly(ok), ok)

    def test_el_mensaje_ofrece_conexion_propia_y_ollama_de_la_institucion(self):
        msg = ai_router.SHARED_QUOTA_EXHAUSTED_MESSAGE
        self.assertIn('conexión propia', msg)
        self.assertIn('Ollama', msg)
        self.assertIn('administrador', msg)

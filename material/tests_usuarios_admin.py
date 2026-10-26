"""Pantalla /users/ (2026-10-26): Área de Pruebas como tilde/cruz y "Restablecer" dentro de Editar."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import TrainingAccountLink

User = get_user_model()


def _crear(nombre, admin=False):
    u = User.objects.create_user(username=nombre, password='testpass123')
    u.profile.security_question = 'comida_favorita'
    u.profile.onboarding_completed = True
    u.profile.role = 'admin' if admin else 'user'
    u.profile.save()
    if admin:
        u.is_superuser = True
        u.is_staff = True
        u.save()
    return u


class UsuariosAdminTests(TestCase):
    def setUp(self):
        self.admin = _crear('usr_admin', admin=True)
        self.docente = _crear('usr_docente')
        self.c = Client()
        self.c.force_login(self.admin)

    def test_la_lista_no_trae_el_boton_restablecer_y_muestra_cruz_si_no_hay_area(self):
        html = self.c.get(reverse('material:user_list')).content.decode()
        self.assertNotIn('Restablecer', html.split('usr-actions')[0].rsplit('<tbody>', 1)[-1])
        self.assertIn('bi-x-circle-fill', html)
        self.assertNotIn('area-pruebas/restablecer', html)

    def test_con_area_creada_la_lista_muestra_tilde_y_editar_ofrece_restablecer(self):
        espejo = _crear('usr_docente_espejo')
        espejo.profile.is_training_account = True
        espejo.profile.save()
        TrainingAccountLink.objects.create(real_user=self.docente, training_user=espejo)
        html = self.c.get(reverse('material:user_list')).content.decode()
        self.assertIn('bi-check-circle-fill', html)
        self.assertNotIn('area-pruebas/restablecer', html)
        editar = self.c.get(reverse('material:edit_user', args=[self.docente.id])).content.decode()
        self.assertIn(reverse('material:admin_restablecer_area_pruebas', args=[self.docente.id]), editar)

    def test_editar_sin_area_no_ofrece_el_boton(self):
        editar = self.c.get(reverse('material:edit_user', args=[self.docente.id])).content.decode()
        self.assertNotIn('area-pruebas/restablecer', editar)
        self.assertIn('Todavía no creó su Área de Pruebas', editar)

    def test_restablecer_vuelve_a_la_ficha_del_usuario(self):
        r = self.c.post(reverse('material:admin_restablecer_area_pruebas', args=[self.docente.id]))
        self.assertRedirects(r, reverse('material:edit_user', args=[self.docente.id]), fetch_redirect_response=False)

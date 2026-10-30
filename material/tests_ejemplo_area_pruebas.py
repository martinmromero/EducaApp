"""Ejemplo paso a paso dentro del Área de Pruebas (2026-10-30): reemplaza al "Probar con un esquema ya armado" del
tutorial de inicio, que quedó oculto."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Question, Subject
from .training_accounts import get_or_create_training_account

User = get_user_model()


def _docente(nombre):
    u = User.objects.create_user(username=nombre, password='testpass123')
    u.profile.security_question = 'comida_favorita'
    u.profile.onboarding_completed = True
    u.profile.save()
    return u


class EjemploEnAreaDePruebasTests(TestCase):
    def setUp(self):
        self.seed, _ = User.objects.get_or_create(username=settings.SEED_CONTENT_USERNAME)
        self.docente = _docente('ej_ana')
        self.c = Client()
        self.c.force_login(self.docente)

    def _materia_de_ejemplo(self, nombre):
        m = Subject.objects.create(name=nombre, created_by=self.seed)
        q = Question.objects.create(user=self.seed, question_text='¿Qué es ' + nombre + '?', answer_text='r', ai_approved=True)
        q.subjects.add(m)
        return m

    def _entrar(self):
        self.c.post(reverse('material:entrar_area_pruebas'))

    def test_fuera_del_area_de_pruebas_vuelve_al_inicio_con_aviso(self):
        r = self.c.get(reverse('material:ejemplo_paso_a_paso'))
        self.assertRedirects(r, reverse('material:index'), fetch_redirect_response=False)

    def test_el_banner_ofrece_el_ejemplo(self):
        self._entrar()
        html = self.c.get(reverse('material:index')).content.decode()
        self.assertIn(reverse('material:ejemplo_paso_a_paso'), html)
        self.assertIn('Ver el ejemplo paso a paso', html)

    def test_con_una_sola_materia_entra_directo_al_resumen(self):
        m = self._materia_de_ejemplo('Algebra de ejemplo')
        self._entrar()
        r = self.c.get(reverse('material:ejemplo_paso_a_paso'))
        self.assertRedirects(r, reverse('material:onboarding_v2_demo_scheme') + f'?subject_id={m.id}',
                             fetch_redirect_response=False)
        r2 = self.c.get(reverse('material:onboarding_v2_demo_scheme'), {'subject_id': m.id}, follow=True)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.redirect_chain[-1][0], reverse('material:onboarding_v2_demo_recap'))

    def test_con_varias_deja_elegir(self):
        a = self._materia_de_ejemplo('Algebra de ejemplo')
        b = self._materia_de_ejemplo('Biologia de ejemplo')
        self._entrar()
        html = self.c.get(reverse('material:ejemplo_paso_a_paso')).content.decode()
        self.assertIn(f'subject_id={a.id}', html)
        self.assertIn(f'subject_id={b.id}', html)

    def test_sin_materias_de_ejemplo_avisa(self):
        self._entrar()
        r = self.c.get(reverse('material:ejemplo_paso_a_paso'))
        self.assertRedirects(r, reverse('material:index'), fetch_redirect_response=False)

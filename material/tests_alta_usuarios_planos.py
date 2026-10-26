"""Alta de elementos por docentes (cuentas planas), 2026-10-26: la institución propia ofrece "Agregar facultad" y
"Mis agregados" lleva a ver/editar lo creado."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import InstitutionV2

User = get_user_model()


def _docente(nombre):
    u = User.objects.create_user(username=nombre, password='testpass123')
    u.profile.security_question = 'comida_favorita'
    u.profile.onboarding_completed = True
    u.profile.save()
    return u


class AltaDeUsuariosPlanosTests(TestCase):
    def setUp(self):
        self.ana = _docente('alta_ana')
        self.beto = _docente('alta_beto')
        self.c = Client()
        self.c.force_login(self.ana)
        self.c.post(reverse('material:catalog_request_create'), {
            'tipo': 'institucion', 'nombre_propuesto': 'Instituto Propio', 'institucion_nueva': 'Instituto Propio',
        })
        self.inst = InstitutionV2.objects.get(name='Instituto Propio')

    def test_la_institucion_propia_queda_en_el_espacio_personal_de_quien_la_crea(self):
        self.assertEqual(self.inst.created_by_id, self.ana.id)
        self.assertFalse(self.inst.es_catalogo_institucional)

    def test_la_ficha_ofrece_agregar_facultad_solo_a_quien_la_creo(self):
        url = reverse('material:institution_v2_detail', args=[self.inst.pk])
        self.assertContains(self.c.get(url), 'Agregar facultad')
        self.assertContains(self.c.get(url), reverse('material:edit_institution_v2', args=[self.inst.pk]))
        otro = Client()
        otro.force_login(self.beto)
        self.assertNotContains(otro.get(url), 'Agregar facultad')

    def test_el_formulario_llega_con_la_institucion_elegida(self):
        r = self.c.get(reverse('material:catalog_request_create'), {'tipo': 'facultad', 'institucion': self.inst.pk})
        self.assertEqual(r.context['form'].initial.get('institucion'), self.inst.pk)

    def test_una_institucion_ajena_no_se_precarga(self):
        otro = Client()
        otro.force_login(self.beto)
        r = otro.get(reverse('material:catalog_request_create'), {'tipo': 'facultad', 'institucion': self.inst.pk})
        self.assertNotIn('institucion', r.context['form'].initial)

    def test_mis_agregados_lleva_a_ver_lo_creado(self):
        r = self.c.get(reverse('material:mis_solicitudes_catalogo'))
        self.assertContains(r, reverse('material:institution_v2_detail', args=[self.inst.pk]))

    def test_el_dueno_puede_ponerle_sigla(self):
        r = self.c.post(reverse('material:edit_institution_v2', args=[self.inst.pk]), {'name': 'Instituto Propio', 'sigla': 'IP'})
        self.assertEqual(r.status_code, 302)
        self.inst.refresh_from_db()
        self.assertEqual(self.inst.sigla, 'IP')

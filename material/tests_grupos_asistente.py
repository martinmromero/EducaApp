"""Asistente de grupos de confianza (2026-10-25): crear el grupo, invitar y compartir en un solo recorrido;
estado del grupo visible; detalle de lo compartido para quien recibe la invitación; acceso al grupo al aceptar.
Corre contra una base descartable."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import (
    ContentShare, ExamTemplate, FormatoImpresion, GroupMembership, Question, Rubric, SharingGroup, Subject,
)

User = get_user_model()


def make_user(username):
    user = User.objects.create_user(username=username, password='testpass123')
    user.profile.security_question = 'comida_favorita'
    user.profile.save()
    return user


class GrupoAsistenteTests(TestCase):
    def setUp(self):
        self.ana = make_user('g_ana')
        self.beto = make_user('g_beto')
        self.carla = make_user('g_carla')
        self.client = Client()
        self.client.force_login(self.ana)
        self.materia = Subject.objects.create(name='Álgebra G', created_by=self.ana, es_catalogo_institucional=False)
        Question.objects.create(question_text='P', answer_text='r', user=self.ana, bloom_level=1).subjects.add(self.materia)
        self.rubrica = Rubric.objects.create(title='Rúbrica G', created_by=self.ana)
        self.formato = FormatoImpresion.objects.create(nombre='Formato G', user=self.ana)

    def _crear(self, **extra):
        datos = {'name': 'Cátedra G', 'invitar': [self.beto.pk], 'materias': [self.materia.pk],
                 'rubricas': [self.rubrica.pk], 'formatos': [self.formato.pk]}
        datos.update(extra)
        return self.client.post(reverse('material:grupo_asistente_nuevo'), datos)

    def test_el_asistente_abre_para_un_grupo_nuevo_y_para_uno_existente(self):
        r = self.client.get(reverse('material:grupo_asistente_nuevo'))
        self.assertContains(r, 'id="id_grupo_name"')
        self.assertContains(r, 'g_beto')
        self.assertNotContains(r, 'value="%d" id="inv_%d"' % (self.ana.pk, self.ana.pk))
        self._crear()
        grupo = SharingGroup.objects.get(name='Cátedra G')
        r = self.client.get(reverse('material:grupo_asistente', args=[grupo.pk]))
        self.assertNotContains(r, 'id="id_grupo_name"')
        # lo ya compartido llega tildado, y quien ya fue invitado no se ofrece de nuevo
        self.assertContains(r, 'data-inicial="1"')
        self.assertNotContains(r, 'id="inv_%d"' % self.beto.pk)

    def test_un_solo_envio_crea_el_grupo_invita_y_comparte(self):
        r = self._crear()
        grupo = SharingGroup.objects.get(name='Cátedra G')
        self.assertRedirects(r, reverse('material:grupo_detalle', args=[grupo.pk]))
        self.assertEqual(grupo.created_by, self.ana)
        self.assertEqual(GroupMembership.objects.get(group=grupo, user=self.ana).status, 'accepted')
        self.assertEqual(GroupMembership.objects.get(group=grupo, user=self.beto).status, 'pending')
        self.assertTrue(ContentShare.objects.filter(group=grupo, kind='materia', subject=self.materia, is_active=True).exists())
        self.assertTrue(ContentShare.objects.filter(group=grupo, kind='rubrica', object_id=self.rubrica.pk, is_active=True).exists())
        self.assertTrue(ContentShare.objects.filter(group=grupo, kind='formato', object_id=self.formato.pk, is_active=True).exists())

    def test_un_grupo_nuevo_exige_nombre_y_no_crea_nada_sin_el(self):
        self._crear(name='  ')
        self.assertEqual(SharingGroup.objects.count(), 0)

    def test_destildar_deja_de_compartir_y_lo_ajeno_se_ignora(self):
        self._crear()
        grupo = SharingGroup.objects.get(name='Cátedra G')
        ajena = Rubric.objects.create(title='Ajena', created_by=self.beto)
        self.client.post(reverse('material:grupo_asistente', args=[grupo.pk]), {
            'materias': [self.materia.pk], 'rubricas': [ajena.pk],
        })
        self.assertFalse(ContentShare.objects.get(group=grupo, kind='rubrica', object_id=self.rubrica.pk).is_active)
        self.assertFalse(ContentShare.objects.get(group=grupo, kind='formato', object_id=self.formato.pk).is_active)
        self.assertTrue(ContentShare.objects.get(group=grupo, kind='materia').is_active)
        self.assertFalse(ContentShare.objects.filter(object_id=ajena.pk).exists())

    def test_quien_no_es_miembro_no_puede_usar_el_asistente_de_un_grupo(self):
        self._crear()
        grupo = SharingGroup.objects.get(name='Cátedra G')
        ajeno = Client()
        ajeno.force_login(self.carla)
        r = ajeno.post(reverse('material:grupo_asistente', args=[grupo.pk]), {'invitar': [self.carla.pk]})
        self.assertRedirects(r, reverse('material:grupos_list'))
        self.assertFalse(GroupMembership.objects.filter(group=grupo, user=self.carla).exists())

    def test_el_grupo_muestra_el_estado_de_lo_compartido(self):
        self._crear()
        grupo = SharingGroup.objects.get(name='Cátedra G')
        r = self.client.get(reverse('material:grupo_detalle', args=[grupo.pk]))
        self.assertContains(r, 'id="grupoEstadoCompartido"')
        self.assertContains(r, 'Álgebra G')
        self.assertContains(r, 'Rúbrica G')
        self.assertContains(r, 'de g_ana')
        self.assertContains(r, 'grupoAsistenteBtn')

    def test_quien_recibe_la_invitacion_ve_el_detalle_y_al_aceptar_puede_ir_al_grupo(self):
        self._crear()
        grupo = SharingGroup.objects.get(name='Cátedra G')
        beto = Client()
        beto.force_login(self.beto)
        r = beto.get(reverse('material:invitaciones_pendientes'))
        self.assertContains(r, 'Cátedra G')
        self.assertContains(r, 'Álgebra G')
        self.assertContains(r, 'Formato G')
        self.assertContains(r, 'g_ana')
        membresia = GroupMembership.objects.get(group=grupo, user=self.beto)
        r = beto.post(reverse('material:invitaciones_pendientes'), {'membership_id': membresia.pk, 'action': 'accept'}, follow=True)
        self.assertContains(r, 'id="invitacionAceptada"')
        self.assertContains(r, reverse('material:grupo_detalle', args=[grupo.pk]))
        membresia.refresh_from_db()
        self.assertEqual(membresia.status, 'accepted')

    def test_el_parametro_aceptada_no_muestra_grupos_ajenos(self):
        self._crear()
        grupo = SharingGroup.objects.get(name='Cátedra G')
        carla = Client()
        carla.force_login(self.carla)
        r = carla.get(reverse('material:invitaciones_pendientes') + f'?aceptada={grupo.pk}')
        self.assertNotContains(r, 'id="invitacionAceptada"')

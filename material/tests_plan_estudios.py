"""Plan de estudios: N° de materia, año y cuatrimestre de cada materia dentro de
una carrera, editables desde "Editar carrera" (Asociaciones de Carrera).

Cubre el permiso (administrador en el catálogo, dueño en su carrera personal,
nadie más), que la fila carrera-materia se actualiza y no se recrea (de ella
cuelgan tópicos y resultados de aprendizaje), y la validación. Corre contra una
base descartable."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Career, CareerSubject, LearningOutcome, Subject, Topic

User = get_user_model()


def make_user(username, admin=False):
    user = User.objects.create_user(username=username, password='testpass123')
    user.profile.security_question = 'comida_favorita'
    if admin:
        user.profile.role = 'admin'
    user.profile.save()
    return user


def login(username):
    client = Client()
    client.login(username=username, password='testpass123')
    return client


class PlanDeEstudiosTests(TestCase):
    def setUp(self):
        self.admin = make_user('p_admin', admin=True)
        self.ana = make_user('p_ana')
        self.beto = make_user('p_beto')
        self.catalogo = Career.objects.create(name='Carrera catálogo', es_catalogo_institucional=True, created_by=self.admin)
        self.personal = Career.objects.create(name='Carrera de Ana', es_catalogo_institucional=False, created_by=self.ana)
        self.alg = Subject.objects.create(name='Álgebra', es_catalogo_institucional=True, created_by=self.admin)
        self.fis = Subject.objects.create(name='Física', es_catalogo_institucional=True, created_by=self.admin)
        self.cs_cat = CareerSubject.objects.create(career=self.catalogo, subject=self.alg)
        self.cs_per = CareerSubject.objects.create(career=self.personal, subject=self.alg)
        # Lo que cuelga de la fila carrera-materia y no se puede perder.
        self.topico = Topic.objects.create(
            name='Matrices', subject=self.alg, career_subject=self.cs_cat,
            es_catalogo_institucional=True, created_by=self.admin,
        )
        self.ra = LearningOutcome.objects.create(
            career_subject=self.cs_cat, description='RA 1', created_by=self.admin, es_catalogo_institucional=True,
        )

    def url(self, career):
        return reverse('material:career_associations', kwargs={'pk': career.pk})

    def post(self, client, career, cs, **plan):
        data = {'name': career.name, 'subjects': [cs.subject_id]}
        for campo, valor in plan.items():
            data[f'plan_{campo}_{cs.pk}'] = valor
        return client.post(self.url(career), data)

    def test_el_admin_carga_el_plan_en_una_carrera_del_catalogo(self):
        resp = self.post(login('p_admin'), self.catalogo, self.cs_cat, numero='12', anio='2', cuatri='1.º')
        self.assertRedirects(resp, reverse('material:career_detail', kwargs={'pk': self.catalogo.pk}))
        self.cs_cat.refresh_from_db()
        self.assertEqual((self.cs_cat.numero_materia, self.cs_cat.anio_cursada, self.cs_cat.cuatrimestre_cursada), ('12', 2, '1.º'))

    def test_guardar_el_plan_no_recrea_la_fila_ni_pierde_topicos_ni_resultados(self):
        pk_antes = self.cs_cat.pk
        self.post(login('p_admin'), self.catalogo, self.cs_cat, numero='7', anio='1', cuatri='anual')
        self.assertTrue(CareerSubject.objects.filter(pk=pk_antes, career=self.catalogo).exists())
        self.topico.refresh_from_db()
        self.ra.refresh_from_db()
        self.assertEqual(self.topico.career_subject_id, pk_antes)
        self.assertEqual(self.ra.career_subject_id, pk_antes)

    def test_el_dueno_carga_el_plan_en_su_carrera_personal(self):
        self.post(login('p_ana'), self.personal, self.cs_per, numero='3', anio='4', cuatri='2.º')
        self.cs_per.refresh_from_db()
        self.assertEqual((self.cs_per.numero_materia, self.cs_per.anio_cursada, self.cs_per.cuatrimestre_cursada), ('3', 4, '2.º'))
        # No toca la misma materia en la carrera del catálogo.
        self.cs_cat.refresh_from_db()
        self.assertEqual((self.cs_cat.numero_materia, self.cs_cat.anio_cursada), ('', None))

    def test_un_docente_no_edita_el_plan_de_una_carrera_del_catalogo(self):
        resp = self.post(login('p_ana'), self.catalogo, self.cs_cat, numero='99', anio='9', cuatri='x')
        self.assertRedirects(resp, reverse('material:career_detail', kwargs={'pk': self.catalogo.pk}))
        self.cs_cat.refresh_from_db()
        self.assertEqual((self.cs_cat.numero_materia, self.cs_cat.anio_cursada, self.cs_cat.cuatrimestre_cursada), ('', None, ''))

    def test_otro_docente_no_edita_la_carrera_personal_de_alguien_mas(self):
        self.post(login('p_beto'), self.personal, self.cs_per, numero='99', anio='9', cuatri='x')
        self.cs_per.refresh_from_db()
        self.assertEqual((self.cs_per.numero_materia, self.cs_per.anio_cursada), ('', None))

    def test_un_dato_invalido_avisa_y_no_frena_los_demas(self):
        otra = CareerSubject.objects.create(career=self.catalogo, subject=self.fis)
        client = login('p_admin')
        resp = client.post(self.url(self.catalogo), {
            'name': self.catalogo.name, 'subjects': [self.alg.pk, self.fis.pk],
            f'plan_anio_{self.cs_cat.pk}': '99',           # fuera de rango
            f'plan_anio_{otra.pk}': '3', f'plan_numero_{otra.pk}': '5',
        })
        self.assertEqual(resp.status_code, 302)
        self.cs_cat.refresh_from_db()
        otra.refresh_from_db()
        self.assertIsNone(self.cs_cat.anio_cursada)
        self.assertEqual((otra.anio_cursada, otra.numero_materia), (3, '5'))
        follow = client.get(resp['Location'])
        self.assertContains(follow, 'el año tiene que ser un número entre 1 y 12')

    def test_vaciar_un_campo_lo_deja_sin_dato(self):
        self.cs_cat.numero_materia, self.cs_cat.anio_cursada, self.cs_cat.cuatrimestre_cursada = '4', 2, '1.º'
        self.cs_cat.save()
        self.post(login('p_admin'), self.catalogo, self.cs_cat, numero='', anio='', cuatri='')
        self.cs_cat.refresh_from_db()
        self.assertEqual((self.cs_cat.numero_materia, self.cs_cat.anio_cursada, self.cs_cat.cuatrimestre_cursada), ('', None, ''))

    def test_un_post_sin_campos_del_plan_no_borra_lo_cargado(self):
        self.cs_cat.numero_materia, self.cs_cat.anio_cursada = '4', 2
        self.cs_cat.save()
        login('p_admin').post(self.url(self.catalogo), {'name': self.catalogo.name, 'subjects': [self.alg.pk]})
        self.cs_cat.refresh_from_db()
        self.assertEqual((self.cs_cat.numero_materia, self.cs_cat.anio_cursada), ('4', 2))

    def test_la_pantalla_muestra_una_fila_por_materia_con_lo_ya_cargado(self):
        self.cs_cat.anio_cursada = 3
        self.cs_cat.save()
        resp = login('p_admin').get(self.url(self.catalogo))
        self.assertContains(resp, f'name="plan_anio_{self.cs_cat.pk}"')
        self.assertContains(resp, 'Plan de estudios')
        self.assertEqual([cs.pk for cs in resp.context['plan_rows']], [self.cs_cat.pk])
        self.assertContains(resp, 'value="3"')

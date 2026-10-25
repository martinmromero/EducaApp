"""Selectores de materia con relevancia y búsqueda, y listas que ya no exponen lo de otras cuentas (2026-10-26).
Corre contra una base descartable."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .content_visibility import anotar_materias, count_relevant_subjects, order_subjects_by_relevance
from .models import Career, CareerSubject, Favorite, InstitutionV2, Question, Subject
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


def make_user(username, **extra):
    user = User.objects.create_user(username=username, password='testpass123', **extra)
    user.profile.security_question = 'comida_favorita'
    user.profile.save()
    return user


class AnotarMateriasTests(TestCase):
    def setUp(self):
        self.ana = make_user('s_ana')
        self.carrera = Career.objects.create(name='Sistemas', es_catalogo_institucional=True)
        self.otra_carrera = Career.objects.create(name='Biología', es_catalogo_institucional=True)

    def _materia(self, nombre, **kw):
        kw.setdefault('es_catalogo_institucional', True)
        return Subject.objects.create(name=nombre, **kw)

    def test_la_materia_creada_por_uno_cuenta_como_propia_aunque_no_tenga_preguntas(self):
        propia = self._materia('Mi primera materia', created_by=self.ana, es_catalogo_institucional=False)
        ajena = self._materia('Álgebra')
        lista = anotar_materias(self.ana, Subject.objects.all())
        self.assertEqual([s.name for s in lista], ['Mi primera materia', 'Álgebra'])
        self.assertEqual(propia.tier if hasattr(propia, 'tier') else lista[0].tier, 'mias')
        self.assertEqual(lista[1].tier, 'resto')

    def test_niveles_propias_de_la_carrera_y_resto_en_ese_orden(self):
        con_preguntas = self._materia('Zoología')
        Question.objects.create(question_text='P', answer_text='r', user=self.ana, bloom_level=1).subjects.add(con_preguntas)
        favorita = self._materia('Yoga')
        Favorite.objects.create(user=self.ana, content_type=ContentType.objects.get_for_model(Subject), object_id=favorita.pk)
        de_carrera = self._materia('Programación')
        CareerSubject.objects.create(career=self.carrera, subject=de_carrera)
        de_otra = self._materia('Citología')
        CareerSubject.objects.create(career=self.otra_carrera, subject=de_otra)
        lista = anotar_materias(self.ana, Subject.objects.all(), career_id=self.carrera.pk)
        self.assertEqual([(s.name, s.tier) for s in lista], [
            ('Yoga', 'mias'), ('Zoología', 'mias'), ('Programación', 'carrera'), ('Citología', 'resto'),
        ])

    def test_nombres_repetidos_se_distinguen_por_carrera_y_origen(self):
        a = self._materia('Programación I')
        CareerSubject.objects.create(career=self.carrera, subject=a)
        b = self._materia('Programación I', created_by=self.ana, es_catalogo_institucional=False)
        c = self._materia('Única')
        lista = {s.pk: s for s in anotar_materias(self.ana, Subject.objects.all())}
        self.assertEqual(lista[a.pk].etiqueta, 'Programación I (Sistemas · Catálogo)')
        self.assertEqual(lista[b.pk].etiqueta, 'Programación I (sin carrera · Personal)')
        self.assertEqual(lista[c.pk].etiqueta, 'Única')

    def test_materia_en_dos_carreras_las_nombra_a_las_dos(self):
        m = self._materia('Inglés I')
        CareerSubject.objects.create(career=self.carrera, subject=m)
        CareerSubject.objects.create(career=self.otra_carrera, subject=m)
        otra = self._materia('Inglés I', es_catalogo_institucional=False, created_by=self.ana)
        lista = {s.pk: s for s in anotar_materias(self.ana, Subject.objects.all())}
        self.assertIn('Biología / Sistemas', lista[m.pk].etiqueta)

    def test_las_carreras_personales_de_otra_cuenta_no_se_nombran(self):
        beto = make_user('s_beto')
        privada = Career.objects.create(name='Carrera secreta', created_by=beto, es_catalogo_institucional=False)
        m = self._materia('Ética')
        CareerSubject.objects.create(career=privada, subject=m)
        lista = anotar_materias(self.ana, Subject.objects.filter(pk=m.pk))
        self.assertEqual(lista[0].carreras_txt, '')

    def test_con_el_interruptor_apagado_todo_es_resto_y_alfabetico(self):
        self._materia('Zeta', created_by=self.ana, es_catalogo_institucional=False)
        self._materia('Alfa')
        with override_settings(SELECTORES_INTELIGENTES=False):
            lista = anotar_materias(self.ana, Subject.objects.all())
        self.assertEqual([(s.name, s.tier) for s in lista], [('Alfa', 'resto'), ('Zeta', 'resto')])

    def test_el_orden_por_relevancia_de_los_checklists_cuenta_lo_creado(self):
        propia = self._materia('Zeta propia', created_by=self.ana, es_catalogo_institucional=False)
        self._materia('Alfa')
        qs = Subject.objects.all()
        self.assertEqual(count_relevant_subjects(self.ana, qs), 1)
        self.assertEqual(order_subjects_by_relevance(self.ana, qs).first().pk, propia.pk)
        with override_settings(SELECTORES_INTELIGENTES=False):
            self.assertEqual(count_relevant_subjects(self.ana, qs), 0)


class PantallasConSelectorTests(TestCase):
    def setUp(self):
        self.ana = make_user('p_ana')
        self.beto = make_user('p_beto')
        self.client = Client()
        self.client.force_login(self.ana)

    def test_crear_examen_no_lista_instituciones_ni_carreras_personales_de_otra_cuenta(self):
        InstitutionV2.objects.create(name='Institución de todos', es_catalogo_institucional=True)
        InstitutionV2.objects.create(name='Institución personal de Ana', created_by=self.ana, es_catalogo_institucional=False)
        InstitutionV2.objects.create(name='Institución secreta de Beto', created_by=self.beto, es_catalogo_institucional=False)
        Career.objects.create(name='Carrera de todos', es_catalogo_institucional=True)
        Career.objects.create(name='Carrera secreta de Beto', created_by=self.beto, es_catalogo_institucional=False)
        r = self.client.get(reverse('material:create_exam'))
        self.assertContains(r, 'Institución de todos')
        self.assertContains(r, 'Institución personal de Ana')
        self.assertNotContains(r, 'Institución secreta de Beto')
        self.assertContains(r, 'Carrera de todos')
        self.assertNotContains(r, 'Carrera secreta de Beto')

    def test_el_asistente_de_plantilla_no_lista_a_todas_las_cuentas_como_docente(self):
        r = self.client.get(reverse('material:create_exam_template_wizard'))
        self.assertNotContains(r, 'p_beto')

    def test_las_pantallas_con_listas_de_materias_traen_el_selector_inteligente(self):
        for nombre in ('create_exam_template', 'create_exam_template_wizard', 'create_exam_wizard',
                       'create_oral_exam_wizard', 'upload_questions', 'create_oral_exam'):
            r = self.client.get(reverse('material:' + nombre))
            self.assertContains(r, 'data-smart-select="materia"', msg_prefix=nombre)
            self.assertContains(r, 'smart_select', msg_prefix=nombre)

    def test_con_el_interruptor_apagado_no_se_carga_el_script_pero_el_select_sigue(self):
        with override_settings(SELECTORES_INTELIGENTES=False):
            r = self.client.get(reverse('material:create_exam_template_wizard'))
        self.assertNotContains(r, 'js/smart_select')
        self.assertContains(r, 'id="id_subject"')

    def test_las_opciones_del_formulario_de_plantilla_llevan_nivel_y_rotulo(self):
        mia = Subject.objects.create(name='Mi materia', created_by=self.ana, es_catalogo_institucional=False)
        dup1 = Subject.objects.create(name='Repetida', es_catalogo_institucional=True)
        dup2 = Subject.objects.create(name='Repetida', created_by=self.ana, es_catalogo_institucional=False)
        r = self.client.get(reverse('material:create_exam_template'))
        html = r.content.decode()
        self.assertIn('value="%d" data-tier="mias"' % mia.pk, html)
        self.assertIn('Repetida (sin carrera · Catálogo)', html)
        self.assertIn('Repetida (sin carrera · Personal)', html)

    def test_enviar_un_formulario_con_una_materia_sigue_validando(self):
        from .forms import ExamTemplateForm
        m = Subject.objects.create(name='Válida', created_by=self.ana, es_catalogo_institucional=False)
        form = ExamTemplateForm(user=self.ana)
        self.assertIn(m, form.fields['subject'].queryset)
        self.assertEqual(form.fields['subject'].widget.attrs.get('data-smart-select'), 'materia')

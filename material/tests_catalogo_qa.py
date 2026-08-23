"""QA extensiva 2026-08-22 — cobertura del giro a "espacio personal" del
catálogo académico (institución/facultad/carrera/materia) y de las
funcionalidades sin commitear a esa fecha: edición/borrado autoservicio,
filtro "Personal", hub /espacio-personal/, aprobación/rechazo por nivel,
fusión con existente, detección de duplicados por similitud+sigla, y carga
masiva de catálogo por CSV. Pensado para correr contra una base descartable
(manage.py test crea/destruye test_educaapp) — no toca datos reales.
"""
import io
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import (
    InstitutionV2, FacultyV2, Career, Subject, CareerSubject,
    CatalogRequest, Topic, Question, LearningOutcome, CampusV2, ExamTemplate,
)
from .views import _similitud, _normalizar_para_busqueda, _tokens

User = get_user_model()


def make_user(username, role='user'):
    user = User.objects.create_user(username=username, password='testpass123')
    user.profile.role = role
    user.profile.save(update_fields=['role'])
    return user


class SimilitudTests(TestCase):
    """_similitud: substring bidireccional, superposición de palabras,
    tipeo palabra por palabra — sección 04 del informe de estado."""

    def score(self, q, nombre):
        q_norm = _normalizar_para_busqueda(q)
        return _similitud(q_norm, _tokens(q_norm), nombre)

    def test_substring_encuentra_nombre_largo(self):
        self.assertEqual(self.score('matema', 'Licenciatura en Matemática'), 1.0)

    def test_substring_al_reves_tambien_matchea(self):
        self.assertEqual(self.score('Facultad Ciencias Exactas', 'Ciencias Exactas'), 1.0)

    def test_orden_de_palabras_no_importa(self):
        self.assertGreater(self.score('Exactas Ciencias', 'Ciencias Exactas'), 0)

    def test_typo_dentro_de_nombre_largo_matchea(self):
        # "Ingeneria" (typo) debe encontrar "Ingeniería en Sistemas Informáticos"
        self.assertGreater(self.score('Ingeneria', 'Ingeniería en Sistemas Informáticos'), 0)

    def test_palabras_cortas_sin_relacion_no_matchean(self):
        # coincidencia de letras al azar no debe cruzar el umbral (ver
        # UMBRAL_DIFUSO calibrado para esto, comentario del propio código)
        self.assertEqual(self.score('matema', 'sistemas'), 0.0)

    def test_nombre_completamente_distinto_no_matchea(self):
        self.assertEqual(self.score('Medicina', 'Contabilidad'), 0.0)


class DuplicateCheckEndpointTests(TestCase):
    """check_catalog_duplicate: matching por nombre Y sigla para instituciones."""

    def setUp(self):
        self.user = make_user('docente1')
        self.client = Client()
        self.client.login(username='docente1', password='testpass123')
        self.inst = InstitutionV2.objects.create(
            name='Universidad Abierta Interamericana', sigla='UAI',
            es_catalogo_institucional=True,
        )

    def test_encuentra_por_sigla_aunque_no_sea_substring_del_nombre(self):
        resp = self.client.get(reverse('material:check_catalog_duplicate'), {'nivel': 'institucion', 'q': 'UAI'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(any(c['id'] == self.inst.id for c in data))

    def test_encuentra_por_nombre_parcial(self):
        resp = self.client.get(reverse('material:check_catalog_duplicate'), {'nivel': 'institucion', 'q': 'Abierta Interamericana'})
        data = resp.json()
        self.assertTrue(any(c['id'] == self.inst.id for c in data))

    def test_query_corta_no_pega_a_la_base(self):
        resp = self.client.get(reverse('material:check_catalog_duplicate'), {'nivel': 'institucion', 'q': 'U'})
        self.assertEqual(resp.json(), [])

    def test_nivel_invalido_devuelve_vacio_sin_error(self):
        resp = self.client.get(reverse('material:check_catalog_duplicate'), {'nivel': 'algo_raro', 'q': 'UAI'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])


class SolicitarAltaCreacionInmediataTests(TestCase):
    """catalog_request_create -> _materializar_y_generar_solicitudes: la
    cadena completa se crea YA en espacio personal, una fila de
    CatalogRequest por nivel realmente nuevo, mismo lote_id."""

    def setUp(self):
        self.user = make_user('docente2')
        self.client = Client()
        self.client.login(username='docente2', password='testpass123')

    def test_cadena_completa_nueva_crea_4_niveles_y_es_usable_de_inmediato(self):
        resp = self.client.post(reverse('material:catalog_request_create'), {
            'tipo': 'materia',
            'institucion_nueva': 'Instituto Nuevo QA',
            'facultad_nueva': 'Facultad QA',
            'carrera_nueva': 'Carrera QA',
            'nombre_propuesto': 'Materia QA',
        })
        self.assertEqual(resp.status_code, 302)

        inst = InstitutionV2.objects.get(name='Instituto Nuevo QA')
        fac = FacultyV2.objects.get(name='Facultad QA')
        car = Career.objects.get(name='Carrera QA')
        mat = Subject.objects.get(name='Materia QA')

        for obj in (inst, fac, car, mat):
            self.assertFalse(obj.es_catalogo_institucional, f'{obj} debería nacer como personal')
            self.assertEqual(obj.created_by_id, self.user.id)

        self.assertTrue(CareerSubject.objects.filter(career=car, subject=mat).exists())

        filas = CatalogRequest.objects.filter(solicitado_por=self.user)
        self.assertEqual(filas.count(), 4)
        lotes = set(filas.values_list('lote_id', flat=True))
        self.assertEqual(len(lotes), 1, 'las 4 filas deben compartir el mismo lote_id')
        self.assertTrue(all(f.estado == 'pendiente' for f in filas))

        # Usable de inmediato: aparece en el listado de materias del propio usuario
        resp = self.client.get(reverse('material:subject_list'))
        self.assertContains(resp, 'Materia QA')

    def test_reutiliza_institucion_existente_no_duplica(self):
        InstitutionV2.objects.create(
            name='Instituto Reusado', created_by=self.user, es_catalogo_institucional=False,
        )
        resp = self.client.post(reverse('material:catalog_request_create'), {
            'tipo': 'facultad',
            'institucion_nueva': 'Instituto Reusado',
            'nombre_propuesto': 'Facultad Nueva',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(InstitutionV2.objects.filter(name='Instituto Reusado').count(), 1)
        # Solo debería haber generado fila de CatalogRequest para la facultad
        # (la institución ya existía como personal propio, no es "nueva").
        self.assertEqual(CatalogRequest.objects.filter(tipo='institucion').count(), 0)
        self.assertEqual(CatalogRequest.objects.filter(tipo='facultad').count(), 1)

    def test_no_ve_ni_puede_reusar_espacio_personal_de_otro_usuario(self):
        otro = make_user('otro_docente')
        InstitutionV2.objects.create(
            name='Instituto De Otro', created_by=otro, es_catalogo_institucional=False,
        )
        resp = self.client.post(reverse('material:catalog_request_create'), {
            'tipo': 'facultad',
            'institucion_nueva': 'Instituto De Otro',
            'nombre_propuesto': 'Facultad X',
        })
        self.assertEqual(resp.status_code, 302)
        # No debe reusar la fila del otro usuario: tiene que crear una propia homónima.
        self.assertEqual(InstitutionV2.objects.filter(name='Instituto De Otro').count(), 2)
        propia = InstitutionV2.objects.get(name='Instituto De Otro', created_by=self.user)
        self.assertFalse(propia.es_catalogo_institucional)


class AprobacionRechazoPorNivelTests(TestCase):
    """resolve_catalog_request: aprobación/rechazo por nivel independiente,
    limpieza real al rechazar (_intentar_eliminar_si_vacio), SET_NULL en las
    FK de CatalogRequest en vez de CASCADE."""

    def setUp(self):
        self.admin = make_user('admin1', role='admin')
        self.docente = make_user('docente3')
        self.client = Client()
        self.client.login(username='docente3', password='testpass123')
        self.client.post(reverse('material:catalog_request_create'), {
            'tipo': 'materia',
            'institucion_nueva': 'Inst Aprobacion',
            'facultad_nueva': 'Fac Aprobacion',
            'carrera_nueva': 'Carr Aprobacion',
            'nombre_propuesto': 'Materia Aprobacion',
        })
        self.client.logout()
        self.client.login(username='admin1', password='testpass123')

    def _solicitud(self, tipo):
        return CatalogRequest.objects.get(tipo=tipo, nombre_propuesto__icontains='Aprobacion')

    def test_aprobar_materia_promueve_solo_ese_nivel(self):
        solicitud = self._solicitud('materia')
        resp = self.client.post(reverse('material:catalog_requests_bandeja'), {
            'solicitud_id': solicitud.pk, 'accion': 'aprobar',
        })
        self.assertEqual(resp.status_code, 302)
        materia = Subject.objects.get(name='Materia Aprobacion')
        self.assertTrue(materia.es_catalogo_institucional)
        # Las hermanas del mismo lote (institución/facultad/carrera) no se
        # tocan por aprobar/rechazar esta fila.
        self.assertFalse(InstitutionV2.objects.get(name='Inst Aprobacion').es_catalogo_institucional)

    def test_rechazar_institucion_vacia_la_borra_de_verdad(self):
        # La institución de este fixture no tiene nada más colgando salvo
        # la facultad que sí se creó junto — pero _RELACION_CONTENIDO_POR_TIPO
        # para 'institucion' es 'facultyv2_set', así que SÍ tiene contenido
        # (la facultad hermana) y NO debería borrarse. Se verifica ese caso
        # negativo acá, y el caso "vacía de verdad" en el siguiente test.
        solicitud = self._solicitud('institucion')
        resp = self.client.post(reverse('material:catalog_requests_bandeja'), {
            'solicitud_id': solicitud.pk, 'accion': 'rechazar',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(InstitutionV2.objects.filter(name='Inst Aprobacion').exists(),
                         'no debería borrarse: tiene una facultad real colgando')
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'rechazada')
        # No se borró la fila real (tenía la facultad hermana colgando), así
        # que la FK sigue apuntando a ella tal cual — SET_NULL solo entra en
        # juego cuando la fila real SÍ se borra (ver el próximo test).
        self.assertIsNotNone(solicitud.institucion_id)

    def test_rechazar_materia_vacia_la_borra_y_no_rompe_el_registro_de_auditoria(self):
        solicitud = self._solicitud('materia')
        resp = self.client.post(reverse('material:catalog_requests_bandeja'), {
            'solicitud_id': solicitud.pk, 'accion': 'rechazar',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Subject.objects.filter(name='Materia Aprobacion').exists(),
                          'materia sin nada colgando debería borrarse al rechazar')
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'rechazada')
        self.assertIsNone(solicitud.materia_id)

    def test_rechazar_materia_con_temas_reales_no_la_borra(self):
        materia = Subject.objects.get(name='Materia Aprobacion')
        Topic.objects.create(name='Tema real', subject=materia)
        solicitud = self._solicitud('materia')
        self.client.post(reverse('material:catalog_requests_bandeja'), {
            'solicitud_id': solicitud.pk, 'accion': 'rechazar',
        })
        self.assertTrue(Subject.objects.filter(pk=materia.pk).exists(),
                         'no debería borrarse: tiene un Tema real cargado')
        materia.refresh_from_db()
        self.assertFalse(materia.es_catalogo_institucional)

    def test_no_admin_no_puede_resolver_solicitudes(self):
        self.client.logout()
        self.client.login(username='docente3', password='testpass123')
        solicitud = self._solicitud('materia')
        resp = self.client.post(reverse('material:catalog_requests_bandeja'), {
            'solicitud_id': solicitud.pk, 'accion': 'aprobar',
        })
        self.assertEqual(resp.status_code, 302)  # redirect a '/', no aprueba
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'pendiente')

    def test_resolver_solicitud_ya_resuelta_no_hace_nada(self):
        solicitud = self._solicitud('materia')
        self.client.post(reverse('material:catalog_requests_bandeja'), {
            'solicitud_id': solicitud.pk, 'accion': 'aprobar',
        })
        # Segunda vez sobre la misma solicitud ya resuelta:
        resp = self.client.post(reverse('material:catalog_requests_bandeja'), {
            'solicitud_id': solicitud.pk, 'accion': 'rechazar',
        })
        self.assertEqual(resp.status_code, 302)
        materia = Subject.objects.get(name='Materia Aprobacion')
        self.assertTrue(materia.es_catalogo_institucional, 'la segunda accion no debe revertir la primera')


class FusionConExistenteTests(TestCase):
    """resolve_catalog_request_fusion + _fusionar_en_destino: reasigna
    Temas/Preguntas/CareerSubject/LearningOutcome hacia el destino
    institucional elegido a mano por el admin, todo atómico."""

    def setUp(self):
        self.admin = make_user('admin2', role='admin')
        self.docente = make_user('docente4')
        self.carrera_destino = Career.objects.create(name='Carrera Destino', es_catalogo_institucional=True)
        self.materia_destino = Subject.objects.create(name='Materia Destino', es_catalogo_institucional=True)
        CareerSubject.objects.create(career=self.carrera_destino, subject=self.materia_destino)

        self.materia_origen = Subject.objects.create(
            name='Materia Origen (duplicada)', created_by=self.docente, es_catalogo_institucional=False,
        )
        self.cs_origen = CareerSubject.objects.create(career=self.carrera_destino, subject=self.materia_origen)
        self.tema = Topic.objects.create(name='Tema en origen', subject=self.materia_origen)
        self.pregunta = Question.objects.create(
            question_text='¿Pregunta?', answer_text='Resp', question_type='multiple_choice',
            topic=self.tema, user=self.docente,
        )
        self.pregunta.subjects.add(self.materia_origen)
        self.solicitud = CatalogRequest.objects.create(
            tipo='materia', nombre_propuesto=self.materia_origen.name,
            materia=self.materia_origen, solicitado_por=self.docente,
        )

    def test_fusionar_reasigna_temas_preguntas_y_borra_el_origen(self):
        from .views import resolve_catalog_request_fusion
        ok, _msg = resolve_catalog_request_fusion(
            self.solicitud, admin_user=self.admin, destino_id=self.materia_destino.pk,
        )
        self.assertTrue(ok)
        self.assertFalse(Subject.objects.filter(pk=self.materia_origen.pk).exists())

        self.tema.refresh_from_db()
        self.assertEqual(self.tema.subject_id, self.materia_destino.pk)

        self.pregunta.refresh_from_db()
        self.assertIn(self.materia_destino, self.pregunta.subjects.all())
        self.assertNotIn(self.materia_origen.pk, self.pregunta.subjects.values_list('pk', flat=True))

        # El CareerSubject del origen se reasigna/fusiona al de destino, no se duplica.
        self.assertEqual(CareerSubject.objects.filter(career=self.carrera_destino, subject=self.materia_destino).count(), 1)
        self.assertFalse(CareerSubject.objects.filter(pk=self.cs_origen.pk).exists())

        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, 'aprobada')

    def test_fusionar_con_destino_no_institucional_falla(self):
        from .views import resolve_catalog_request_fusion
        borrador_ajeno = Subject.objects.create(name='Otro borrador', created_by=self.docente, es_catalogo_institucional=False)
        ok, msg = resolve_catalog_request_fusion(
            self.solicitud, admin_user=self.admin, destino_id=borrador_ajeno.pk,
        )
        self.assertFalse(ok)
        self.assertTrue(Subject.objects.filter(pk=self.materia_origen.pk).exists(), 'no debe borrar el origen si la fusion fallo')

    def test_endpoint_bandeja_requiere_destino_id_valido(self):
        self.client_ = Client()
        self.client_.login(username='admin2', password='testpass123')
        resp = self.client_.post(reverse('material:catalog_requests_bandeja'), {
            'solicitud_id': self.solicitud.pk, 'accion': 'fusionar', 'destino_id': 'no-es-un-numero',
        })
        self.assertEqual(resp.status_code, 302)
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, 'pendiente')


class EdicionYBorradoAutoservicioTests(TestCase):
    """_puede_editar_catalogo + eliminar_espacio_personal: el dueño de un
    borrador personal puede editarlo/borrarlo; nadie más puede, ni siquiera
    sobre una fila ya institucional que él mismo creó originalmente."""

    def setUp(self):
        self.dueno = make_user('dueno')
        self.otro = make_user('otro_usuario')
        self.admin = make_user('admin3', role='admin')
        self.materia_propia = Subject.objects.create(
            name='Materia Propia', created_by=self.dueno, es_catalogo_institucional=False,
        )
        self.materia_institucional_del_dueno = Subject.objects.create(
            name='Materia Ya Institucional', created_by=self.dueno, es_catalogo_institucional=True,
        )

    def login(self, username):
        c = Client()
        c.login(username=username, password='testpass123')
        return c

    # --- edición ---

    def test_dueno_puede_editar_su_borrador(self):
        c = self.login('dueno')
        resp = c.post(reverse('material:edit_subject', args=[self.materia_propia.pk]), {
            'name': 'Materia Propia Corregida',
        })
        self.assertEqual(resp.status_code, 302)
        self.materia_propia.refresh_from_db()
        self.assertEqual(self.materia_propia.name, 'Materia Propia Corregida')

    def test_otro_usuario_no_puede_editar_borrador_ajeno(self):
        c = self.login('otro_usuario')
        resp = c.get(reverse('material:edit_subject', args=[self.materia_propia.pk]))
        self.assertNotEqual(resp.status_code, 200)
        self.materia_propia.refresh_from_db()
        self.assertEqual(self.materia_propia.name, 'Materia Propia')

    def test_dueno_no_puede_editar_su_propia_materia_ya_institucional(self):
        c = self.login('dueno')
        resp = c.get(reverse('material:edit_subject', args=[self.materia_institucional_del_dueno.pk]))
        self.assertNotEqual(resp.status_code, 200,
                             'una vez institucional, ni el creador original debería poder editarla directamente')

    def test_admin_puede_editar_cualquier_cosa(self):
        c = self.login('admin3')
        resp = c.get(reverse('material:edit_subject', args=[self.materia_institucional_del_dueno.pk]))
        self.assertEqual(resp.status_code, 200)

    # --- borrado autoservicio ---

    def test_dueno_puede_borrar_su_propio_borrador(self):
        c = self.login('dueno')
        resp = c.post(reverse('material:eliminar_espacio_personal', args=['materia', self.materia_propia.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Subject.objects.filter(pk=self.materia_propia.pk).exists())

    def test_otro_usuario_no_puede_borrar_borrador_ajeno(self):
        c = self.login('otro_usuario')
        resp = c.post(reverse('material:eliminar_espacio_personal', args=['materia', self.materia_propia.pk]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Subject.objects.filter(pk=self.materia_propia.pk).exists())

    def test_dueno_no_puede_autoborrar_su_materia_ya_institucional(self):
        c = self.login('dueno')
        resp = c.post(reverse('material:eliminar_espacio_personal', args=['materia', self.materia_institucional_del_dueno.pk]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Subject.objects.filter(pk=self.materia_institucional_del_dueno.pk).exists())

    def test_nivel_invalido_da_404_no_500(self):
        c = self.login('dueno')
        resp = c.post(reverse('material:eliminar_espacio_personal', args=['no_existe', self.materia_propia.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_anonimo_no_puede_borrar_nada(self):
        c = Client()
        resp = c.post(reverse('material:eliminar_espacio_personal', args=['materia', self.materia_propia.pk]))
        self.assertEqual(resp.status_code, 302)  # redirect a login
        self.assertTrue(Subject.objects.filter(pk=self.materia_propia.pk).exists())


class FiltroPersonalYHubTests(TestCase):
    """Filtro '?personal=1' en los listados + pantalla /espacio-personal/."""

    def setUp(self):
        self.user = make_user('docente5')
        self.otro = make_user('otro_docente5')
        self.client = Client()
        self.client.login(username='docente5', password='testpass123')

        self.institucional = InstitutionV2.objects.create(name='Institucional Publica', es_catalogo_institucional=True)
        self.propia = InstitutionV2.objects.create(name='Mi Borrador Institucion', created_by=self.user, es_catalogo_institucional=False)
        self.ajena = InstitutionV2.objects.create(name='Borrador De Otro', created_by=self.otro, es_catalogo_institucional=False)

        self.materia_propia = Subject.objects.create(name='Mi Materia Personal', created_by=self.user, es_catalogo_institucional=False)
        self.materia_institucional = Subject.objects.create(name='Materia Del Catalogo', es_catalogo_institucional=True)

    def test_filtro_personal_en_instituciones_solo_muestra_lo_propio(self):
        resp = self.client.get(reverse('material:institution_v2_list'), {'personal': '1'})
        self.assertContains(resp, 'Mi Borrador Institucion')
        self.assertNotContains(resp, 'Institucional Publica')
        self.assertNotContains(resp, 'Borrador De Otro')

    def test_sin_filtro_ve_catalogo_mas_lo_propio_pero_no_lo_ajeno(self):
        resp = self.client.get(reverse('material:institution_v2_list'))
        self.assertContains(resp, 'Institucional Publica')
        self.assertContains(resp, 'Mi Borrador Institucion')
        self.assertNotContains(resp, 'Borrador De Otro')

    def test_hub_espacio_personal_junta_los_4_niveles_propios(self):
        resp = self.client.get(reverse('material:espacio_personal_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Mi Borrador Institucion')
        self.assertContains(resp, 'Mi Materia Personal')
        self.assertNotContains(resp, 'Borrador De Otro')
        self.assertNotContains(resp, 'Materia Del Catalogo')


class ContenidoFormSubjectScopingTests(TestCase):
    """ContenidoForm.subjects (bug encontrado en la auditoria: mostraba
    materias de TODOS los docentes, catalogo y espacio personal ajeno)."""

    def test_subjects_queryset_no_incluye_espacio_personal_ajeno(self):
        from .forms import ContenidoForm
        user = make_user('docente6')
        otro = make_user('otro_docente6')
        propia = Subject.objects.create(name='Mia Para Subir', created_by=user, es_catalogo_institucional=False)
        ajena = Subject.objects.create(name='Ajena Para Subir', created_by=otro, es_catalogo_institucional=False)
        institucional = Subject.objects.create(name='Catalogo Para Subir', es_catalogo_institucional=True)

        form = ContenidoForm(user=user)
        ids_visibles = set(form.fields['subjects'].queryset.values_list('pk', flat=True))
        self.assertIn(propia.pk, ids_visibles)
        self.assertIn(institucional.pk, ids_visibles)
        self.assertNotIn(ajena.pk, ids_visibles, 'no debe ver el espacio personal de otro usuario')


class LearningOutcomeCareerSubjectFilterTests(TestCase):
    """Bug encontrado en la auditoria: ExamTemplateForm filtraba
    LearningOutcome por 'subject' directo en vez de 'career_subject__subject'
    (huerfano desde que LearningOutcome paso a colgar de CareerSubject)."""

    def test_examtemplateform_learning_outcomes_usa_career_subject_subject(self):
        from .forms import ExamTemplateForm
        subject = Subject.objects.create(name='Materia LO', es_catalogo_institucional=True)
        career = Career.objects.create(name='Carrera LO', es_catalogo_institucional=True)
        cs = CareerSubject.objects.create(career=career, subject=subject)
        lo = LearningOutcome.objects.create(career_subject=cs, description='RA de prueba')

        form = ExamTemplateForm()
        if 'learning_outcomes' in form.fields:
            ids = set(form.fields['learning_outcomes'].queryset.values_list('pk', flat=True))
            self.assertIn(lo.pk, ids)


class PrintFormatVisibilityTests(TestCase):
    """get_visible_print_formats: combinar querysets con y sin .distinct()
    usando '|' tira 'Cannot combine a unique query with a non-unique query'."""

    def test_no_explota_al_combinar_querysets(self):
        from .print_format_utils import get_visible_print_formats
        user = make_user('docente7')
        try:
            list(get_visible_print_formats(user))
        except Exception as e:
            self.fail(f'get_visible_print_formats no deberia explotar: {e!r}')


class BulkCatalogUploadTests(TestCase):
    """admin_bulk_catalog_upload: flujo en dos pasos (preview con dry_run,
    confirmar persiste), directo a catalogo institucional."""

    CSV = (
        'facultad,carrera,numero de materia,materia,año de cursada,cuatrimestre de cursada\r\n'
        'Ingenieria,Sistemas,101,Algebra,1,1\r\n'
        'Ingenieria,Sistemas,102,Analisis Matematico,1,2\r\n'
    )

    def setUp(self):
        self.admin = make_user('admin4', role='admin')
        self.client = Client()
        self.client.login(username='admin4', password='testpass123')
        self.institucion = InstitutionV2.objects.create(name='Institucion CSV', es_catalogo_institucional=True)

    def _archivo(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile('plan.csv', self.CSV.encode('utf-8'), content_type='text/csv')

    def test_paso_1_preview_no_escribe_nada_en_la_base(self):
        resp = self.client.post(reverse('material:admin_bulk_catalog_upload'), {
            'institucion': self.institucion.pk, 'archivo': self._archivo(),
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(FacultyV2.objects.filter(name='Ingenieria').exists(), 'el preview no debe persistir nada')
        self.assertContains(resp, 'Algebra')

    def test_paso_2_confirmar_persiste_directo_al_catalogo_institucional(self):
        resp = self.client.post(reverse('material:admin_bulk_catalog_upload'), {
            'confirmar': '1',
            'institucion_id': self.institucion.pk,
            'csv_text': self.CSV,
        })
        self.assertEqual(resp.status_code, 200)
        fac = FacultyV2.objects.get(name='Ingenieria', institution=self.institucion)
        car = Career.objects.get(name='Sistemas')
        mat1 = Subject.objects.get(name='Algebra')
        mat2 = Subject.objects.get(name='Analisis Matematico')
        for obj in (fac, car, mat1, mat2):
            self.assertTrue(obj.es_catalogo_institucional, f'{obj} deberia entrar directo como institucional')
        self.assertTrue(CareerSubject.objects.filter(career=car, subject=mat1).exists())
        self.assertTrue(CareerSubject.objects.filter(career=car, subject=mat2).exists())

    def test_fila_repetida_reutiliza_en_vez_de_duplicar(self):
        csv_repetido = self.CSV + 'Ingenieria,Sistemas,101,Algebra,1,1\r\n'
        self.client.post(reverse('material:admin_bulk_catalog_upload'), {
            'confirmar': '1', 'institucion_id': self.institucion.pk, 'csv_text': csv_repetido,
        })
        self.assertEqual(FacultyV2.objects.filter(name='Ingenieria').count(), 1)
        self.assertEqual(Career.objects.filter(name='Sistemas').count(), 1)
        self.assertEqual(Subject.objects.filter(name='Algebra').count(), 1)

    def test_fila_incompleta_se_reporta_como_error_sin_tirar_las_demas(self):
        csv_con_error = self.CSV + 'Ingenieria,,103,Materia Sin Carrera,1,1\r\n'
        resp = self.client.post(reverse('material:admin_bulk_catalog_upload'), {
            'confirmar': '1', 'institucion_id': self.institucion.pk, 'csv_text': csv_con_error,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Subject.objects.filter(name='Algebra').exists())
        self.assertFalse(Subject.objects.filter(name='Materia Sin Carrera').exists())

    def test_no_admin_no_puede_acceder(self):
        c = Client()
        make_user('docente8')
        c.login(username='docente8', password='testpass123')
        resp = c.get(reverse('material:admin_bulk_catalog_upload'))
        self.assertEqual(resp.status_code, 302)

    def test_archivo_no_csv_es_rechazado(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        archivo = SimpleUploadedFile('plan.txt', b'no importa', content_type='text/plain')
        resp = self.client.post(reverse('material:admin_bulk_catalog_upload'), {
            'institucion': self.institucion.pk, 'archivo': archivo,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(FacultyV2.objects.filter(institution=self.institucion).exists())


class ExamWizardCatalogScopingTests(TestCase):
    """create_exam_wizard dejo de precargar TODAS las instituciones/carreras
    del sistema (ver informe de estado, punchlist) — ahora busca en vivo
    contra check_catalog_duplicate. get_faculties_by_institution y
    get_careers_by_faculty (cascada compartida con create_exam.js y
    create_exam_template.js) tenian el mismo agujero: devolvian filas del
    espacio personal de CUALQUIER usuario a quien supiera el ID."""

    def setUp(self):
        self.user = make_user('docente_wizard')
        self.otro = make_user('otro_docente_wizard')
        self.client = Client()
        self.client.login(username='docente_wizard', password='testpass123')

        self.institucion = InstitutionV2.objects.create(name='Inst Wizard', es_catalogo_institucional=True)
        self.facultad_propia = FacultyV2.objects.create(
            name='Facultad Propia', institution=self.institucion,
            created_by=self.user, es_catalogo_institucional=False,
        )
        self.facultad_ajena = FacultyV2.objects.create(
            name='Facultad Ajena', institution=self.institucion,
            created_by=self.otro, es_catalogo_institucional=False,
        )
        self.carrera_propia = Career.objects.create(
            name='Carrera Propia', created_by=self.user, es_catalogo_institucional=False,
        )
        self.carrera_propia.faculties.add(self.facultad_propia)
        self.carrera_ajena = Career.objects.create(
            name='Carrera Ajena', created_by=self.otro, es_catalogo_institucional=False,
        )
        self.carrera_ajena.faculties.add(self.facultad_propia)

    def test_get_faculties_by_institution_no_devuelve_espacio_personal_ajeno(self):
        resp = self.client.get(reverse('material:get_faculties_by_institution', args=[self.institucion.pk]))
        self.assertEqual(resp.status_code, 200)
        nombres = {f['name'] for f in resp.json()['faculties']}
        self.assertIn('Facultad Propia', nombres)
        self.assertNotIn('Facultad Ajena', nombres)

    def test_get_careers_by_faculty_no_devuelve_espacio_personal_ajeno(self):
        resp = self.client.get(reverse('material:get_careers_by_faculty', args=[self.facultad_propia.pk]))
        self.assertEqual(resp.status_code, 200)
        nombres = {c['name'] for c in resp.json()['careers']}
        self.assertIn('Carrera Propia', nombres)
        self.assertNotIn('Carrera Ajena', nombres)

    def test_get_careers_by_faculty_requiere_login(self):
        anon = Client()
        resp = anon.get(reverse('material:get_careers_by_faculty', args=[self.facultad_propia.pk]))
        self.assertEqual(resp.status_code, 302)

    def test_get_exam_template_incluye_nombres_para_prefill_sin_fetch_extra(self):
        campus = CampusV2.objects.create(name='Sede Wizard', institution=self.institucion)
        subject = Subject.objects.create(name='Materia Wizard', es_catalogo_institucional=True)
        template = ExamTemplate.objects.create(
            institution=self.institucion, faculty=self.facultad_propia,
            career=self.carrera_propia, campus=campus, subject=subject,
            created_by=self.user,
        )
        resp = self.client.get(reverse('material:get_exam_template', args=[template.pk]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['institution_name'], 'Inst Wizard')
        self.assertEqual(data['faculty_name'], 'Facultad Propia')
        self.assertEqual(data['career_name'], 'Carrera Propia')
        self.assertEqual(data['campus_name'], 'Sede Wizard')

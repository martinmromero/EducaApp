"""Hablar con el autor (2026-10-29): formulario para cualquier usuario + bandeja solo para admin."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import AuthorMessage

User = get_user_model()


def _crear(nombre, admin=False):
    u = User.objects.create_user(username=nombre, password='testpass123', email=f'{nombre}@ejemplo.com')
    u.profile.security_question = 'comida_favorita'
    u.profile.onboarding_completed = True
    u.profile.role = 'admin' if admin else 'user'
    u.profile.save()
    if admin:
        u.is_superuser = True
        u.is_staff = True
        u.save()
    return u


class ContactoAutorTests(TestCase):
    def setUp(self):
        self.admin = _crear('ca_admin', admin=True)
        self.docente = _crear('ca_docente')
        self.c = Client()
        self.c.force_login(self.docente)

    def test_requiere_login(self):
        r = Client().get(reverse('material:contacto_autor'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('login', r['Location'])

    def test_usuario_comun_ve_el_formulario_y_el_link_en_el_menu(self):
        r = self.c.get(reverse('material:contacto_autor'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Hablar con el autor')
        home = self.c.get(reverse('material:index')).content.decode()
        self.assertIn(reverse('material:contacto_autor'), home)
        self.assertNotIn(reverse('material:contacto_bandeja'), home)

    def test_el_enlace_vive_en_el_menu_de_ayuda_y_no_en_el_menu_lateral(self):
        html = self.c.get(reverse('material:index')).content.decode()
        self.assertEqual(html.count('id="tourContactoAutor"'), 1)
        self.assertGreater(html.index('id="tourContactoAutor"'), html.index('id="tourHelpMenu"'))
        # orden del menú "?": recorrido general, probar con un ejemplo, Área de Pruebas, hablar con el autor
        orden = [html.index(x) for x in ('id="tourChoiceGeneralItem"', 'id="tourProbarEjemploItem"', 'id="tourAreaPruebasItem"', 'id="tourContactoAutor"')]
        self.assertEqual(orden, sorted(orden))
        # el menú lateral (antes del menú de ayuda) ya no lo trae
        lateral = html.split('id="tourHelpMenu"')[0]
        self.assertNotIn('Hablar con el autor', lateral)

    def test_modo_testing_oculto_por_defecto_aunque_la_cuenta_sea_tester(self):
        self.docente.profile.is_tester = True
        self.docente.profile.save()
        html = self.c.get(reverse('material:index')).content.decode()
        self.assertNotIn('Modo Testing', html)

    @override_settings(MODO_TESTING_VISIBLE=True)
    def test_modo_testing_vuelve_con_el_interruptor_encendido(self):
        self.docente.profile.is_tester = True
        self.docente.profile.save()
        html = self.c.get(reverse('material:index')).content.decode()
        self.assertIn('Modo Testing', html)

    def test_el_formulario_muestra_el_contacto_directo(self):
        html = self.c.get(reverse('material:contacto_autor')).content.decode()
        self.assertIn('mailto:martin.romero@uai.edu.ar', html)
        self.assertIn('https://wa.me/5491160490784', html)

    def test_enviar_guarda_el_mensaje(self):
        r = self.c.post(reverse('material:contacto_autor'), {
            'tipo': 'error', 'mensaje': '  No carga el PDF  ', 'pagina_origen': '/exams/',
        })
        self.assertEqual(r.status_code, 302)
        m = AuthorMessage.objects.get()
        self.assertEqual((m.user, m.tipo, m.mensaje, m.pagina_origen, m.leido), (self.docente, 'error', 'No carga el PDF', '/exams/', False))

    def test_mensaje_vacio_no_guarda(self):
        r = self.c.post(reverse('material:contacto_autor'), {'tipo': 'consulta', 'mensaje': '   '})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(AuthorMessage.objects.count(), 0)

    def test_tipo_invalido_cae_en_consulta(self):
        self.c.post(reverse('material:contacto_autor'), {'tipo': 'hack', 'mensaje': 'hola'})
        self.assertEqual(AuthorMessage.objects.get().tipo, 'consulta')

    def test_origen_externo_se_descarta(self):
        self.c.post(reverse('material:contacto_autor'), {
            'mensaje': 'hola', 'pagina_origen': 'https://malo.example.com/x',
        })
        self.assertEqual(AuthorMessage.objects.get().pagina_origen, '')

    def test_bandeja_solo_admin(self):
        r = self.c.get(reverse('material:contacto_bandeja'))
        self.assertEqual(r.status_code, 302)

    def test_admin_ve_mensajes_badge_y_marca_leido(self):
        AuthorMessage.objects.create(user=self.docente, tipo='sugerencia', mensaje='Más letra grande')
        adm = Client()
        adm.force_login(self.admin)
        html = adm.get(reverse('material:contacto_bandeja')).content.decode()
        self.assertIn('Más letra grande', html)
        self.assertIn('ca_docente@ejemplo.com', html)
        self.assertIn('badge bg-danger ms-1">1<', adm.get(reverse('material:index')).content.decode())
        m = AuthorMessage.objects.get()
        adm.post(reverse('material:contacto_bandeja'), {'mensaje_id': m.pk, 'accion': 'leido'})
        m.refresh_from_db()
        self.assertTrue(m.leido)

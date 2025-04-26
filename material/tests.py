import os
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from .models import Institution, Campus, Faculty
from .forms import InstitutionForm

User = get_user_model()

class InstitutionModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        cls.institution = Institution.objects.create(
            name='Universidad Test',
            owner=cls.user,
            logo=SimpleUploadedFile(
                name='test_logo.jpg',
                content=b'',
                content_type='image/jpeg'
            )
        )

    def test_institution_creation(self):
        """Verifica que las instituciones se crean correctamente"""
        self.assertEqual(self.institution.name, 'Universidad Test')
        self.assertTrue(self.institution.id)  # Asegura que tenga ID
        self.assertEqual(self.institution.owner, self.user)

    def test_institution_str(self):
        """Prueba el método __str__"""
        self.assertEqual(str(self.institution), 'Universidad Test')

    def test_institution_logo_upload(self):
        """Verifica la subida de logos"""
        self.assertTrue(self.institution.logo.name.startswith('institution_logos/'))

    def test_institution_constraints(self):
        """Prueba constraints del modelo"""
        with self.assertRaises(Exception):
            Institution.objects.create(name='', owner=self.user)  # Nombre vacío
        with self.assertRaises(Exception):
            Institution.objects.create(name='Universidad Test', owner=self.user)  # Duplicado


class InstitutionViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='viewuser',
            password='testpass123'
        )
        self.institution = Institution.objects.create(
            name='Test View',
            owner=self.user
        )
        self.client.login(username='viewuser', password='testpass123')

    def test_manage_institutions_view(self):
        """Prueba acceso a la vista principal"""
        response = self.client.get(reverse('material:manage_institutions'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test View')

    def test_edit_institution_view(self):
        """Prueba edición de institución"""
        url = reverse('material:edit_institution', kwargs={'pk': self.institution.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_delete_institution_view(self):
        """Prueba eliminación de institución"""
        url = reverse('material:delete_institution', kwargs={'pk': self.institution.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)  # Redirect after delete
        self.assertEqual(Institution.objects.count(), 0)


class InstitutionFormTests(TestCase):
    def test_valid_form(self):
        """Prueba formulario válido"""
        user = User.objects.create_user(username='formuser', password='test123')
        form_data = {
            'name': 'Universidad Form',
            'owner': user.id
        }
        form = InstitutionForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_form(self):
        """Prueba formulario inválido"""
        form_data = {'name': ''}  # Nombre vacío
        form = InstitutionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)


class RelatedModelsTests(TestCase):
    """Pruebas para modelos relacionados (Campus, Faculty)"""
    def setUp(self):
        self.user = User.objects.create_user(username='relateduser', password='test123')
        self.institution = Institution.objects.create(
            name='Parent Institution',
            owner=self.user
        )

    def test_campus_creation(self):
        """Prueba creación de Campus"""
        campus = Campus.objects.create(
            name='Campus Central',
            institution=self.institution
        )
        self.assertEqual(campus.institution, self.institution)
        self.assertIn(campus, self.institution.campus_set.all())

    def test_faculty_creation(self):
        """Prueba creación de Faculty"""
        faculty = Faculty.objects.create(
            name='Ingeniería',
            code='ING',
            institution=self.institution
        )
        self.assertEqual(faculty.institution, self.institution)
        self.assertEqual(faculty.code, 'ING')


class SecurityTests(TestCase):
    """Pruebas de seguridad y permisos"""
    def test_unauthorized_access(self):
        """Usuario no autorizado no puede editar"""
        user1 = User.objects.create_user(username='user1', password='pass123')
        user2 = User.objects.create_user(username='user2', password='pass123')
        institution = Institution.objects.create(
            name='Segura',
            owner=user1
        )
        
        self.client.login(username='user2', password='pass123')
        url = reverse('material:edit_institution', kwargs={'pk': institution.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)  # Forbidden
import os
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from .models import Institution, Campus, Faculty,InstitutionV2, UserInstitution,CampusV2,FacultyV2,InstitutionLog 
from .forms import InstitutionForm
from .models import Subject, Topic, Question

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


class CreateExamPreviewSelectionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='examuser', password='testpass123')
        self.client.login(username='examuser', password='testpass123')

        self.subject = Subject.objects.create(name='Matematica')
        self.topic_a = Topic.objects.create(name='Tema A', subject=self.subject)
        self.topic_b = Topic.objects.create(name='Tema B', subject=self.subject)

        self.selected_a = self._create_question('Aprobada A', self.topic_a, approved=True)
        self.selected_b = self._create_question('Aprobada B', self.topic_b, approved=True)
        self._create_question('Rechazada A', self.topic_a, approved=False)
        self._create_question('Rechazada B', self.topic_b, approved=False)

    def _create_question(self, text, topic, approved):
        question = Question.objects.create(
            question_text=text,
            answer_text='Respuesta',
            question_type='multiple_choice',
            topic=topic,
            user=self.user,
            generated_by_ai=True,
            ai_approved=approved,
        )
        question.subjects.add(self.subject)
        return question

    def test_preview_multiversion_uses_only_selected_questions(self):
        session = self.client.session
        session['preview_exam'] = {
            'subject': str(self.subject.id),
            'topics': [str(self.topic_a.id), str(self.topic_b.id)],
            'questions': [str(self.selected_a.id), str(self.selected_b.id)],
            'num_versions': '2',
            'questions_per_version': '1',
            'balance_by_topic': '1',
        }
        session.save()

        response = self.client.get(reverse('material:preview_exam'))

        self.assertEqual(response.status_code, 200)
        generated = self.client.session.get('preview_generated_versions_ids') or []
        generated_ids = {question_id for version in generated for question_id in version}

        self.assertTrue(generated_ids)
        self.assertTrue(generated_ids.issubset({self.selected_a.id, self.selected_b.id}))

    def test_preview_generation_excludes_rejected_questions(self):
        session = self.client.session
        session['preview_exam'] = {
            'subject': str(self.subject.id),
            'topics': [str(self.topic_a.id)],
            'questions': [],
            'num_versions': '1',
            'questions_per_version': '2',
            'balance_by_topic': '1',
        }
        session.save()

        response = self.client.get(reverse('material:preview_exam'))

        self.assertEqual(response.status_code, 200)
        generated = self.client.session.get('preview_generated_versions_ids') or []
        generated_ids = {question_id for version in generated for question_id in version}

        self.assertEqual(generated_ids, {self.selected_a.id})
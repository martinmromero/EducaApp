import os
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from .models import InstitutionV2, UserInstitution, CampusV2, FacultyV2, InstitutionLog
from .models import Subject, Topic, Question

User = get_user_model()

# Institution/Campus/Faculty (v1) y sus tests se eliminaron junto con el
# stack v1 — ver informe de rediseño del catálogo académico. Ya estaban
# rotos antes de este cambio: `from .forms import InstitutionForm` fallaba
# al importar (esa clase no existe en forms.py), así que este archivo
# entero no podía cargarse — `manage_institutions`/`edit_institution`/
# `delete_institution` tampoco tenían URL registrada.


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
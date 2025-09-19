from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from material.models import Subject, Topic, Question, OralExamSet
from material.views import generate_oral_exam_questions
from collections import defaultdict


class Command(BaseCommand):
    help = 'Prueba el algoritmo de asignación de preguntas orales'

    def handle(self, *args, **options):
        # Buscar un usuario existente
        try:
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR('No hay usuarios en la base de datos'))
                return
                
            # Buscar una materia con preguntas
            subjects_with_questions = []
            for subject in Subject.objects.all():
                question_count = Question.objects.filter(topic__subject=subject, user=user).count()
                if question_count > 0:
                    subjects_with_questions.append((subject, question_count))
            
            if not subjects_with_questions:
                self.stdout.write(self.style.ERROR('No hay materias con preguntas en la base de datos'))
                return
            
            # Ordenar por cantidad de preguntas (descendente)
            subjects_with_questions.sort(key=lambda x: x[1], reverse=True)
            subject, question_count = subjects_with_questions[0]
            
            self.stdout.write(f'Materia seleccionada: {subject.name} ({question_count} preguntas)')
                
            # Obtener topics de la materia que tienen preguntas
            topics = Topic.objects.filter(
                subject=subject, 
                question__user=user
            ).distinct()[:10]  # Tomar máximo 10 topics
            if not topics:
                self.stdout.write(self.style.ERROR('No hay topics en la materia'))
                return
                
            self.stdout.write(f'Usuario: {user.username}')
            self.stdout.write(f'Materia: {subject.name}')
            self.stdout.write(f'Topics: {[t.name for t in topics]}')
            
            # Crear un examen oral de prueba
            oral_exam = OralExamSet.objects.create(
                user=user,
                name="Prueba Algoritmo",
                subject=subject,
                num_groups=7,
                students_per_group=4,  # Será ajustado automáticamente
                questions_per_student=2,
                total_students=25
            )
            
            # Agregar topics
            oral_exam.topics.set(topics)
            
            self.stdout.write(f'Examen creado: {oral_exam.name}')
            self.stdout.write(f'Configuración: {oral_exam.num_groups} grupos, {oral_exam.total_students} estudiantes totales, {oral_exam.questions_per_student} preguntas por estudiante')
            
            # Contar preguntas disponibles
            available_questions = Question.objects.filter(
                subject=subject,
                topic__in=topics,
                user=user
            )
            self.stdout.write(f'Preguntas disponibles: {available_questions.count()}')
            
            # Agrupar por subtemas para mostrar distribución
            questions_by_subtopic = defaultdict(list)
            for question in available_questions:
                key = question.subtopic.name if question.subtopic else f"Sin subtema ({question.topic.name})"
                questions_by_subtopic[key].append(question)
            
            self.stdout.write(f'Distribución por subtema:')
            for subtopic, questions in questions_by_subtopic.items():
                self.stdout.write(f'  - {subtopic}: {len(questions)} preguntas')
            
            # Generar preguntas
            self.stdout.write('\n--- GENERANDO PREGUNTAS ---')
            generate_oral_exam_questions(oral_exam)
            
            # Analizar resultados
            self.stdout.write('\n--- ANÁLISIS DE RESULTADOS ---')
            
            groups = oral_exam.groups.all()
            for group in groups:
                self.stdout.write(f'\nGrupo {group.group_number}:')
                students = group.students.all()
                
                # Analizar por ronda
                for round_num in range(1, oral_exam.questions_per_student + 1):
                    self.stdout.write(f'  Ronda {round_num}:')
                    subtopics_in_round = []
                    
                    for student in students:
                        question_in_round = student.questions.filter(
                            oralexamstudentquestion__order=round_num
                        ).first()
                        
                        if question_in_round:
                            subtopic_name = question_in_round.subtopic.name if question_in_round.subtopic else f"Sin subtema ({question_in_round.topic.name})"
                            subtopics_in_round.append(subtopic_name)
                            self.stdout.write(f'    Estudiante {student.student_number}: {subtopic_name}')
                    
                    # Verificar repeticiones en la ronda
                    unique_subtopics = set(subtopics_in_round)
                    if len(unique_subtopics) != len(subtopics_in_round):
                        self.stdout.write(self.style.ERROR(f'    ¡REPETICIÓN DETECTADA EN RONDA {round_num}!'))
                    else:
                        self.stdout.write(self.style.SUCCESS(f'    ✓ No hay repeticiones en ronda {round_num}'))
            
            # Limpiar
            oral_exam.delete()
            self.stdout.write(f'\nExamen de prueba eliminado')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))

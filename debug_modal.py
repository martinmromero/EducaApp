#!/usr/bin/env python
"""
Script para hacer pruebas específicas de debug del modal
"""
import os
import sys
import django

# Setup Django environment
sys.path.append('C:/Users/marti/OneDrive/tesis/educaapp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'educaapp.settings')
django.setup()

from django.contrib.auth.models import User
from material.models import OralExamSet, OralExamGroup, OralExamStudent, OralExamStudentQuestion

def debug_oral_exam_structure():
    """Debug the structure of oral exams"""
    print("=== DEBUGGING ORAL EXAM STRUCTURE ===")
    
    # Find the most recent exam
    exams = OralExamSet.objects.all().order_by('-created_at')
    print(f"Total exams in database: {exams.count()}")
    
    if exams.exists():
        exam = exams.first()
        print(f"Most recent exam: ID={exam.id}, created by {exam.user.username}")
        print(f"  Subject: {exam.subject.name}")
        print(f"  Topics: {[t.name for t in exam.topics.all()]}")
        
        # Get groups
        groups = exam.groups.all()
        print(f"  Groups: {groups.count()}")
        
        for group in groups:
            print(f"\n  Group {group.id}:")
            students = group.students.all()
            print(f"    Students: {students.count()}")
            
            for student in students:
                print(f"      Student ID {student.id}: {student.student_name if student.student_name else 'No name'}")
                questions = student.questions.all()
                print(f"        Questions: {questions.count()}")
                
                for sq in questions:
                    try:
                        eval_status = getattr(sq, 'evaluation', None) or 'No evaluation'
                        q_order = getattr(sq, 'question_order', 'N/A')
                        q_text = sq.question.question_text[:50] if hasattr(sq, 'question') else 'No question text'
                        print(f"          Q{q_order}: {q_text}... [{eval_status}]")
                    except Exception as e:
                        print(f"          Error accessing question: {e}")
                        print(f"          Object type: {type(sq)}, attributes: {dir(sq)}")
        
        print(f"\n=== TESTING CHANGE BUTTON DATA ===")
        
        # Find a student question to test the change button data
        student_questions = OralExamStudentQuestion.objects.filter(
            student__group__exam_set=exam
        ).select_related('student__group', 'question')
        
        if student_questions.exists():
            sq = student_questions.first()
            print(f"Test Student Question:")
            print(f"  ID: {sq.id}")
            print(f"  Group ID: {sq.student.group.id}")
            print(f"  Question ID: {sq.question.id}")
            print(f"  Question Text: {sq.question.question_text[:100]}...")
            
            # This is the data that would be in the change button
            print(f"\nChange button should have:")
            print(f"  data-student-question-id='{sq.id}'")
            print(f"  data-group-id='{sq.student.group.id}'")
            print(f"  data-current-question-id='{sq.question.id}'")
            
            # Check if there are available questions for exchange
            from material.models import Question
            used_in_group = OralExamStudentQuestion.objects.filter(
                student__group=sq.student.group
            ).values_list('question_id', flat=True)
            
            available = Question.objects.filter(
                user=exam.user,
                subject=exam.subject,
                active=True
            ).exclude(id__in=used_in_group)
            
            print(f"\nAvailable questions for exchange: {available.count()}")
            if available.exists():
                print(f"  Example: {available.first().question_text[:50]}...")
            else:
                print("  No available questions for exchange!")
        
    else:
        print("No exams found in database!")

if __name__ == '__main__':
    debug_oral_exam_structure()
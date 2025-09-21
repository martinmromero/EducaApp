#!/usr/bin/env python
"""
Script para probar la funcionalidad del modal de cambio de preguntas
"""
import os
import sys
import django

# Setup Django environment
sys.path.append('C:/Users/marti/OneDrive/tesis/educaapp')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'educaapp.settings')
django.setup()

from django.contrib.auth.models import User
from material.models import Subject, Question, OralExamSet, OralExamGroup, OralExamStudent, OralExamStudentQuestion
import requests
import json

def test_available_questions_endpoint():
    """Test the available questions AJAX endpoint"""
    print("=== Testing Available Questions Endpoint ===")
    
    # First, let's check if we have any users, subjects, and questions
    users = User.objects.all()
    subjects = Subject.objects.all()
    questions = Question.objects.all()
    
    print(f"Users in database: {users.count()}")
    print(f"Subjects in database: {subjects.count()}")
    print(f"Questions in database: {questions.count()}")
    
    if not users.exists():
        print("No users found. Creating test user...")
        user = User.objects.create_user('testuser', 'test@example.com', 'testpass')
        print(f"Created user: {user.username}")
    else:
        user = users.first()
        print(f"Using existing user: {user.username}")
    
    if not subjects.exists():
        print("No subjects found. Please create subjects first.")
        return
    
    subject = subjects.first()
    print(f"Using subject: {subject.name}")
    
    # Check for oral exam groups
    groups = OralExamGroup.objects.filter(exam_set__user=user)
    print(f"Oral exam groups for user: {groups.count()}")
    
    if groups.exists():
        group = groups.first()
        print(f"Testing with group ID: {group.id}")
        
        # Test the endpoint URL construction
        test_url = f"http://127.0.0.1:8000/material/oral-exams/available-questions/?group_id={group.id}"
        print(f"Test URL: {test_url}")
        
        try:
            # Note: This will fail because we need authentication, but we can check the URL structure
            response = requests.get(test_url)
            print(f"Response status: {response.status_code}")
            if response.status_code != 200:
                print(f"Response content: {response.text[:500]}")
        except Exception as e:
            print(f"Request error (expected due to no auth): {e}")
    else:
        print("No oral exam groups found. Please create an oral exam first.")
    
    print("\n=== URL Pattern Check ===")
    # Let's verify the URL pattern exists
    try:
        from django.urls import reverse
        url = reverse('material:get_available_questions')
        print(f"URL pattern exists: {url}")
    except Exception as e:
        print(f"URL pattern error: {e}")

def check_javascript_syntax():
    """Check if the template has proper JavaScript syntax"""
    print("\n=== Checking Template JavaScript ===")
    
    template_path = 'C:/Users/marti/OneDrive/tesis/educaapp/material/templates/material/oral_exams/view.html'
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for common JavaScript syntax issues
        issues = []
        
        # Count braces
        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces != close_braces:
            issues.append(f"Brace mismatch: {open_braces} open vs {close_braces} close")
        
        # Check for orphaned });
        if '});' in content:
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if line.strip() == '});':
                    # Check if this }); has a matching opening
                    context_start = max(0, i-10)
                    context_lines = lines[context_start:i+5]
                    print(f"Found '}});' at line {i}. Context:")
                    for j, ctx_line in enumerate(context_lines):
                        marker = " --> " if j == (i - context_start - 1) else "     "
                        print(f"{context_start + j + 1:4d}{marker}{ctx_line}")
                    print()
        
        # Check for modal references
        if 'changeQuestionModal' in content:
            print("✓ Modal 'changeQuestionModal' is referenced in template")
        else:
            issues.append("Modal 'changeQuestionModal' not found in template")
        
        # Check for event listeners
        if 'DOMContentLoaded' in content:
            print("✓ DOMContentLoaded listener found")
        else:
            issues.append("No DOMContentLoaded listener found")
        
        if issues:
            print("Issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✓ No obvious JavaScript syntax issues detected")
            
    except Exception as e:
        print(f"Error reading template: {e}")

if __name__ == '__main__':
    test_available_questions_endpoint()
    check_javascript_syntax()
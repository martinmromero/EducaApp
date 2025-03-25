from django.contrib import admin
from .models import Subject, Material, Question, Exam, ExamTemplate, Profile

# Registra los modelos
admin.site.register(Subject)
admin.site.register(Material)
admin.site.register(Question)
admin.site.register(Exam)
admin.site.register(ExamTemplate)
admin.site.register(Profile)
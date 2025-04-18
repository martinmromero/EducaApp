from django.contrib import admin
from .models import (
    Subject, Contenido, Question, Exam, ExamTemplate, Profile,
    Topic, Subtopic, Institution, Faculty, LearningOutcome
)

class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'website')
    search_fields = ('name', 'address')

class FacultyAdmin(admin.ModelAdmin):
    list_display = ('name', 'institution')
    list_filter = ('institution',)
    search_fields = ('name', 'institution__name')

class LearningOutcomeAdmin(admin.ModelAdmin):
    list_display = ('code', 'subject', 'level')
    list_filter = ('subject', 'level')
    search_fields = ('code', 'description')

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ('question_text', 'difficulty', 'topic', 'subtopic')
    show_change_link = True

class TopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'importance')
    list_filter = ('subject', 'importance')
    search_fields = ('name', 'subject__name')
    inlines = [QuestionInline]

class SubtopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'topic')
    list_filter = ('topic__subject', 'topic')
    search_fields = ('name', 'topic__name')

class ContenidoAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'uploaded_by', 'uploaded_at')
    list_filter = ('subject', 'uploaded_by')
    search_fields = ('title', 'subject__name', 'isbn')
    readonly_fields = ('uploaded_at',)

class QuestionAdmin(admin.ModelAdmin):
    list_display = ('short_question_text', 'subject', 'difficulty', 'topic')
    list_filter = ('subject', 'topic', 'difficulty')
    search_fields = ('question_text', 'subject__name', 'topic__name')
    filter_horizontal = ('exams',)

    def short_question_text(self, obj):
        return obj.question_text[:50] + '...' if len(obj.question_text) > 50 else obj.question_text
    short_question_text.short_description = 'Pregunta'

class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'created_by', 'created_at', 'is_published')
    list_filter = ('subject', 'created_at', 'is_published')
    search_fields = ('title', 'subject__name')
    filter_horizontal = ('topics', 'questions', 'learning_outcomes')
    fieldsets = (
        (None, {
            'fields': ('title', 'subject', 'topics', 'questions', 'learning_outcomes')
        }),
        ('Configuración', {
            'fields': ('instructions', 'duration_minutes', 'is_published'),
            'classes': ('collapse',)
        }),
    )

class ExamTemplateAdmin(admin.ModelAdmin):
    list_display = ('subject', 'exam_type_display', 'year', 'created_by')
    list_filter = ('exam_type', 'exam_mode', 'year', 'subject')
    search_fields = ('subject__name', 'career_name', 'professor__username')
    filter_horizontal = ('learning_outcomes',)
    
    def exam_type_display(self, obj):
        display = obj.get_exam_type_display()
        if obj.exam_type == 'parcial' and obj.partial_number:
            display += f" ({obj.get_partial_number_display()})"
        return display
    exam_type_display.short_description = 'Tipo de Examen'

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role_display', 'institutions_list')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')
    filter_horizontal = ('institutions', 'faculties')

    def role_display(self, obj):
        return obj.get_role_display()
    role_display.short_description = 'Rol'

    def institutions_list(self, obj):
        return ", ".join([i.name for i in obj.institutions.all()])
    institutions_list.short_description = 'Instituciones'

# Registros
admin.site.register(Institution, InstitutionAdmin)
admin.site.register(Faculty, FacultyAdmin)
admin.site.register(LearningOutcome, LearningOutcomeAdmin)
admin.site.register(Subject)
admin.site.register(Topic, TopicAdmin)
admin.site.register(Subtopic, SubtopicAdmin)
admin.site.register(Contenido, ContenidoAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Exam, ExamAdmin)
admin.site.register(ExamTemplate, ExamTemplateAdmin)
admin.site.register(Profile, ProfileAdmin)
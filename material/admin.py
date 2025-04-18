from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Subject, Contenido, Question, Exam, ExamTemplate, Profile,
    Topic, Subtopic, Institution, LearningOutcome
)

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'logo_preview', 'campuses_short')
    search_fields = ('name', 'campuses', 'owner__username')
    list_filter = ('owner',)
    fields = ('name', 'logo', 'logo_preview', 'campuses', 'faculties', 'owner')
    readonly_fields = ('logo_preview',)
    raw_id_fields = ('owner',)  # Para mejor rendimiento con muchos usuarios

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(owner=request.user)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            # Para usuarios normales, establecer el owner automáticamente
            form.base_fields['owner'].disabled = True
            form.base_fields['owner'].initial = request.user
        return form

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.logo.url)
        return "No logo disponible"
    logo_preview.short_description = 'Vista previa'

    def campuses_short(self, obj):
        if obj.campuses:
            campuses = [c.strip() for c in obj.campuses.split(',') if c.strip()]
            if len(campuses) > 3:
                return f"{', '.join(campuses[:3])}... (+{len(campuses)-3})"
            return ', '.join(campuses)
        return "No especificado"
    campuses_short.short_description = 'Sedes'

    def save_model(self, request, obj, form, change):
        if not obj.owner_id:  # Si es nueva institución
            obj.owner = request.user
        super().save_model(request, obj, form, change)
        

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'learning_outcomes_count')
    search_fields = ('name',)

    def learning_outcomes_count(self, obj):
        return obj.outcomes.count()
    learning_outcomes_count.short_description = 'Resultados'

@admin.register(Contenido)
class ContenidoAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'uploaded_by', 'uploaded_at')
    list_filter = ('subject', 'uploaded_by')
    search_fields = ('title', 'subject__name')
    date_hierarchy = 'uploaded_at'
    raw_id_fields = ('uploaded_by', 'subject')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_short', 'subject', 'difficulty', 'question_type')
    list_filter = ('subject', 'difficulty', 'question_type')
    search_fields = ('question_text', 'answer_text')
    raw_id_fields = ('contenido', 'subject', 'topic', 'subtopic', 'user')

    def question_short(self, obj):
        return f"{obj.question_text[:50]}..."
    question_short.short_description = 'Pregunta'

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'created_by', 'created_at')
    filter_horizontal = ('questions', 'topics', 'learning_outcomes')
    raw_id_fields = ('created_by', 'subject')

@admin.register(ExamTemplate)
class ExamTemplateAdmin(admin.ModelAdmin):
    list_display = ('subject', 'exam_type', 'year', 'created_by')
    list_filter = ('exam_type', 'year', 'subject')
    search_fields = ('subject__name', 'career_name')
    raw_id_fields = ('institution', 'subject', 'professor', 'created_by')  # Eliminado 'faculty'

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'institutions_list')
    list_filter = ('role',)
    filter_horizontal = ('institutions',)  # Eliminado 'faculties'

    def institutions_list(self, obj):
        return ", ".join([i.name for i in obj.institutions.all()])
    institutions_list.short_description = 'Instituciones'

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'importance')
    list_filter = ('subject', 'importance')
    search_fields = ('name', 'subject__name')

@admin.register(Subtopic)
class SubtopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'topic', 'subject')
    list_filter = ('topic',)
    search_fields = ('name', 'topic__name')

    def subject(self, obj):
        return obj.topic.subject
    subject.short_description = 'Asignatura'

@admin.register(LearningOutcome)
class LearningOutcomeAdmin(admin.ModelAdmin):
    list_display = ('code', 'subject', 'level', 'description_short')
    list_filter = ('subject', 'level')
    search_fields = ('code', 'description')

    def description_short(self, obj):
        return f"{obj.description[:50]}..."
    description_short.short_description = 'Descripción'
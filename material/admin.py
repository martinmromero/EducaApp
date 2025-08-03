from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Subject, Contenido, Question, Exam, ExamTemplate, Profile,
    Topic, Subtopic, Institution, InstitutionV2, LearningOutcome, Career
)
from .forms import SubjectForm
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

# --- Institution Admin ---
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
# --- End Institution Admin ---

# --- InstitutionV2 Admin ---
@admin.register(InstitutionV2)
class InstitutionV2Admin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at', 'updated_at')
    search_fields = ('name',)
    list_filter = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('name', 'logo', 'is_active')}),
    )
# --- End InstitutionV2 Admin ---

@admin.register(Career)
class CareerAdmin(admin.ModelAdmin):
    list_display = ('name', 'faculties_list', 'subjects_list')
    search_fields = ('name',)
    filter_horizontal = ('faculties', 'subjects', 'campus')

    def faculties_list(self, obj):
        return ", ".join([f.name for f in obj.faculties.all()])
    faculties_list.short_description = 'Facultades'

    def subjects_list(self, obj):
        return ", ".join([s.name for s in obj.subjects.all()])
    subjects_list.short_description = 'Materias'

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    form = SubjectForm  # Usando el form mejorado que definimos antes
    list_display = ('name', 'learning_outcomes_short', 'careers_list')
    search_fields = ('name',)
    list_filter = ('careers',)  # Añadido para mejor filtrado
    filter_horizontal = ('careers',)  # Para selección más fácil de carreras
    
    fieldsets = (
        (None, {
            'fields': ('name', 'careers')
        }),
        ('Resultados de Aprendizaje', {
            'fields': ('learning_outcomes',),
            'description': '''<div class="help">
                <p>Formato recomendado: <code>CÓDIGO: Descripción - Nivel X</code></p>
                <p>Ejemplo: <code>MATH-101: Resolver ecuaciones - Nivel 2</code></p>
            </div>'''
        }),
    )

    def learning_outcomes_short(self, obj):
        if not obj.learning_outcomes:
            return ""
        # Versión mejorada que muestra el primer código encontrado
        first_line = obj.learning_outcomes.split('\n')[0].strip()
        if ':' in first_line:
            return f"{first_line.split(':')[0].strip()}..."
        return f"{first_line[:50]}..." if first_line else ""
    learning_outcomes_short.short_description = 'Resultados'

    def careers_list(self, obj):
        return ", ".join([c.name for c in obj.careers.all()[:3]]) + ("..." if obj.careers.count() > 3 else "")
    careers_list.short_description = 'Carreras'
    
    class Media:
        css = {
            'all': ('admin/css/subject_admin.css',)
        }
        js = ('admin/js/subject_admin.js',)

@admin.register(Contenido)
class ContenidoAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'uploaded_by', 'uploaded_at', 'chapter')
    list_filter = ('subject', 'uploaded_by')
    search_fields = ('title', 'subject__name')
    date_hierarchy = 'uploaded_at'
    raw_id_fields = ('uploaded_by', 'subject')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_short', 'subject', 'difficulty', 'question_type', 'contenido', 'source_page')
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
    raw_id_fields = ('institution', 'subject', 'professor', 'created_by')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'institutions_list')
    list_filter = ('role',)
    filter_horizontal = ('institutions',)

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
    list_display = ('id', 'short_description', 'subject_name', 'created_at')
    list_select_related = ('subject',)
    search_fields = ('description', 'subject__name')
    list_filter = ('subject__name', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    fields = ('subject', 'description', 'created_at', 'updated_at')
    ordering = ('-created_at',)

    def short_description(self, obj):
        return obj.description[:80] + ('...' if len(obj.description) > 80 else '')
    short_description.short_description = 'Descripción'

    def subject_name(self, obj):
        return obj.subject.name
    subject_name.short_description = 'Materia'
    subject_name.admin_order_field = 'subject__name'
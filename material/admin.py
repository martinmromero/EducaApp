from django.contrib import admin
from .models import Subject, Contenido, Question, Exam, ExamTemplate, Profile, Topic, Subtopic

class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'created_by', 'created_at', 'is_published')
    list_filter = ('subject', 'created_at', 'is_published')
    search_fields = ('title', 'subject__Nombre')
    filter_horizontal = ('topics', 'questions')  # Para relaciones ManyToMany
    fieldsets = (
        (None, {
            'fields': ('title', 'subject', 'topics', 'questions')
        }),
        ('Configuración avanzada', {
            'fields': ('instructions', 'duration_minutes', 'is_published'),
            'classes': ('collapse',)
        }),
    )

admin.site.register(Subject)
admin.site.register(Contenido)
admin.site.register(Question)
admin.site.register(Exam, ExamAdmin)  # Registro con configuración personalizada
admin.site.register(ExamTemplate)
admin.site.register(Profile)
admin.site.register(Topic)
admin.site.register(Subtopic)
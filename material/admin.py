from django import forms
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Subject, Contenido, Question, Exam, ExamTemplate, Profile,
    Topic, Subtopic, Unidad, InstitutionV2, LearningOutcome, Career, CareerSubject,
    InstitutionAIConfig, UserAIConfig, GlobalAIConfig, encrypt_api_key,
    SharingGroup, GroupMembership, ContentShare, CatalogRequest,
)
from .forms import SubjectForm
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User


def _superuser_only_has_permission(request):
    """El panel /admin/ de Django es solo para superusers.

    Los "admin" de la app (Profile.role == 'admin') tienen sus propios
    permisos elevados dentro de la app (gestión de usuarios, config. de IA,
    etc. vía is_admin()), pero eso es intencionalmente independiente de
    is_staff/acceso a /admin/: ese panel expone edición directa y sin
    scoping de todos los modelos, así que se restringe a superusers.
    """
    return bool(request.user and request.user.is_active and request.user.is_superuser)


admin.site.has_permission = _superuser_only_has_permission


class OwnerScopedAdminMixin:
    """Scoping por propietario dentro de /admin/, como defensa adicional.

    /admin/ ya está restringido a superusers (ver _superuser_only_has_permission
    arriba), que de por sí ven todo. Este mixin es un resguardo extra por si
    alguna vez se relaja esa restricción: evita que un staff no-superuser
    vea/edite Contenidos, Preguntas o Exámenes de otros usuarios.
    """
    owner_field = None

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or not self.owner_field:
            return qs
        return qs.filter(**{self.owner_field: request.user})


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

class CareerSubjectInline(admin.TabularInline):
    # Career.subjects tiene through=CareerSubject (numero_materia/anio_
    # cursada/cuatrimestre_cursada) — un M2M con through no admite
    # filter_horizontal, se edita con un inline como este.
    model = CareerSubject
    extra = 0
    autocomplete_fields = ('subject',)


@admin.register(Career)
class CareerAdmin(admin.ModelAdmin):
    list_display = ('name', 'faculties_list', 'subjects_list')
    search_fields = ('name',)
    filter_horizontal = ('faculties', 'campus')
    inlines = [CareerSubjectInline]

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
class ContenidoAdmin(OwnerScopedAdminMixin, admin.ModelAdmin):
    owner_field = 'uploaded_by'
    list_display = ('title', 'subjects_list', 'uploaded_by', 'uploaded_at', 'chapter')
    list_filter = ('uploaded_by',)
    search_fields = ('title', 'subjects__name')
    date_hierarchy = 'uploaded_at'
    raw_id_fields = ('uploaded_by',)
    filter_horizontal = ('subjects',)

    def subjects_list(self, obj):
        return ', '.join(s.name for s in obj.subjects.all()) or '-'
    subjects_list.short_description = 'Materias'

@admin.register(Question)
class QuestionAdmin(OwnerScopedAdminMixin, admin.ModelAdmin):
    owner_field = 'user'
    list_display = ('question_short', 'subjects_list', 'difficulty', 'question_type', 'contenido', 'source_page')
    list_filter = ('difficulty', 'question_type')
    search_fields = ('question_text', 'answer_text')
    raw_id_fields = ('contenido', 'topic', 'subtopic', 'user')
    filter_horizontal = ('subjects',)

    def question_short(self, obj):
        return f"{obj.question_text[:50]}..."
    question_short.short_description = 'Pregunta'

    def subjects_list(self, obj):
        return ', '.join(s.name for s in obj.subjects.all()) or '-'
    subjects_list.short_description = 'Materias'

@admin.register(Exam)
class ExamAdmin(OwnerScopedAdminMixin, admin.ModelAdmin):
    owner_field = 'created_by'
    list_display = ('title', 'subject', 'created_by', 'created_at')
    filter_horizontal = ('questions', 'topics', 'learning_outcomes')
    raw_id_fields = ('created_by', 'subject')

@admin.register(ExamTemplate)
class ExamTemplateAdmin(OwnerScopedAdminMixin, admin.ModelAdmin):
    owner_field = 'created_by'
    list_display = ('subject', 'exam_type', 'year', 'created_by')
    list_filter = ('exam_type', 'year', 'subject')
    search_fields = ('subject__name', 'career_name')
    raw_id_fields = ('institution', 'subject', 'professor', 'created_by')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    # Cambiar 'role' acá equivale a promover/degradar administradores,
    # saltandose las protecciones de auto-degradación y "último admin" que
    # tiene la vista material:edit_user. Se restringe a superusers para que
    # ese único camino siga siendo el punto de control real.
    list_display = ('user', 'role', 'security_question', 'security_answer')
    list_filter = ('role',)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'importance', 'created_by', 'unidad')
    list_filter = ('subject', 'importance')
    search_fields = ('name', 'subject__name')
    raw_id_fields = ('created_by', 'unidad')


@admin.register(Unidad)
class UnidadAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'created_by', 'order')
    list_filter = ('subject',)
    search_fields = ('name', 'subject__name')
    raw_id_fields = ('created_by',)


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
    list_display = ('id', 'short_description', 'subject_name', 'career_name', 'created_at')
    list_select_related = ('career_subject', 'career_subject__subject', 'career_subject__career')
    search_fields = ('description', 'career_subject__subject__name', 'career_subject__career__name')
    list_filter = ('career_subject__career', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    fields = ('career_subject', 'description', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    raw_id_fields = ('career_subject',)

    def short_description(self, obj):
        return obj.description[:80] + ('...' if len(obj.description) > 80 else '')
    short_description.short_description = 'Descripción'

    def subject_name(self, obj):
        return obj.career_subject.subject.name if obj.career_subject else '—'
    subject_name.short_description = 'Materia'
    subject_name.admin_order_field = 'career_subject__subject__name'

    def career_name(self, obj):
        return obj.career_subject.career.name if obj.career_subject else '—'
    career_name.short_description = 'Carrera'
    career_name.admin_order_field = 'career_subject__career__name'


# ---------------------------------------------------------------------------
# Admin de configuración IA
# ---------------------------------------------------------------------------
class InstitutionAIConfigAdminForm(forms.ModelForm):
    """Form personalizado para manejar el campo api_key sin exponer el texto cifrado."""
    api_key = forms.CharField(
        label='API Key',
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text='Dejar vacío para no modificar la key existente.',
    )

    class Meta:
        model = InstitutionAIConfig
        exclude = ('api_key_encrypted',)

    def save(self, commit=True):
        instance = super().save(commit=False)
        raw_key = self.cleaned_data.get('api_key', '').strip()
        if raw_key:
            instance.api_key_encrypted = encrypt_api_key(raw_key)
        if commit:
            instance.save()
        return instance


@admin.register(InstitutionAIConfig)
class InstitutionAIConfigAdmin(admin.ModelAdmin):
    form = InstitutionAIConfigAdminForm
    list_display = ('institution', 'provider', 'model', 'is_active', 'updated_at')
    list_filter = ('provider', 'is_active')
    search_fields = ('institution__name',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('institution', 'provider', 'model', 'base_url', 'api_key', 'is_active')}),
        ('Auditoría', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


class UserAIConfigAdminForm(forms.ModelForm):
    api_key = forms.CharField(
        label='API Key',
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text='Dejar vacío para no modificar.',
    )

    class Meta:
        model = UserAIConfig
        exclude = ('api_key_encrypted',)

    def save(self, commit=True):
        instance = super().save(commit=False)
        raw_key = self.cleaned_data.get('api_key', '').strip()
        if raw_key:
            instance.api_key_encrypted = encrypt_api_key(raw_key)
        if commit:
            instance.save()
        return instance


@admin.register(UserAIConfig)
class UserAIConfigAdmin(admin.ModelAdmin):
    form = UserAIConfigAdminForm
    list_display = ('user', 'source', 'provider', 'model', 'institution')
    list_filter = ('source', 'provider')
    search_fields = ('user__username', 'user__email')
    raw_id_fields = ('user', 'institution')
    fieldsets = (
        (None, {'fields': ('user', 'source')}),
        ('BYOK', {'fields': ('provider', 'model', 'base_url', 'api_key'), 'classes': ('collapse',)}),
        ('Institucional', {'fields': ('institution',), 'classes': ('collapse',)}),
    )


class GlobalAIConfigAdminForm(forms.ModelForm):
    """Form personalizado para manejar el campo api_key sin exponer el texto cifrado."""
    api_key = forms.CharField(
        label='API Key',
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text='Dejar vacío para no modificar la key existente. Esta key se usa como fallback '
                   'automático de demo para cualquier usuario sin proveedor propio configurado.',
    )

    class Meta:
        model = GlobalAIConfig
        exclude = ('api_key_encrypted',)

    def save(self, commit=True):
        instance = super().save(commit=False)
        raw_key = self.cleaned_data.get('api_key', '').strip()
        if raw_key:
            instance.api_key_encrypted = encrypt_api_key(raw_key)
        if commit:
            instance.save()
        return instance


@admin.register(GlobalAIConfig)
class GlobalAIConfigAdmin(admin.ModelAdmin):
    form = GlobalAIConfigAdminForm
    list_display = ('provider', 'model', 'is_active', 'updated_at')
    fieldsets = (
        (None, {'fields': ('provider', 'model', 'api_key', 'is_active')}),
    )


# --- Grupos de confianza (compartir preguntas) ---
class GroupMembershipInline(admin.TabularInline):
    model = GroupMembership
    extra = 0
    fields = ('user', 'status', 'invited_by', 'created_at', 'responded_at')
    readonly_fields = ('created_at',)


class ContentShareInline(admin.TabularInline):
    model = ContentShare
    extra = 0
    fields = ('kind', 'subject', 'content_type', 'object_id', 'shared_by', 'is_active', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(SharingGroup)
class SharingGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_at', 'members_count')
    search_fields = ('name', 'created_by__username')
    inlines = [GroupMembershipInline, ContentShareInline]

    def members_count(self, obj):
        return obj.memberships.filter(status='accepted').count()
    members_count.short_description = 'Miembros aceptados'


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ('group', 'user', 'status', 'invited_by', 'created_at', 'responded_at')
    list_filter = ('status',)
    search_fields = ('group__name', 'user__username')


@admin.register(ContentShare)
class ContentShareAdmin(admin.ModelAdmin):
    list_display = ('group', 'kind', 'subject', 'shared_object', 'shared_by', 'is_active', 'created_at')
    list_filter = ('kind', 'is_active')
    search_fields = ('group__name', 'subject__name', 'shared_by__username')


@admin.register(CatalogRequest)
class CatalogRequestAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'nombre_propuesto', 'estado', 'solicitado_por', 'created_at')
    list_filter = ('tipo', 'estado')
    search_fields = ('nombre_propuesto', 'solicitado_por__username')
    raw_id_fields = ('institucion', 'facultad', 'carrera', 'solicitado_por', 'resuelto_por')
    actions = ['aprobar_y_crear', 'rechazar']

    @admin.action(description='Aprobar y crear en el catálogo')
    def aprobar_y_crear(self, request, queryset):
        from .views import resolve_catalog_request
        creadas, saltadas = 0, 0
        for solicitud in queryset.filter(estado='pendiente'):
            ok, _ = resolve_catalog_request(solicitud, admin_user=request.user, aprobar=True)
            creadas += ok
            saltadas += (not ok)
        if creadas:
            self.message_user(request, f'{creadas} solicitud(es) aprobadas y creadas en el catálogo.')
        if saltadas:
            self.message_user(
                request,
                f'{saltadas} solicitud(es) salteadas por falta de contexto (institución/facultad/carrera) — hay que completarlas y reintentar.',
                level='WARNING',
            )

    @admin.action(description='Rechazar')
    def rechazar(self, request, queryset):
        from .views import resolve_catalog_request
        count = 0
        for solicitud in queryset.filter(estado='pendiente'):
            ok, _ = resolve_catalog_request(solicitud, admin_user=request.user, aprobar=False)
            count += ok
        self.message_user(request, f'{count} solicitud(es) rechazadas.')


@admin.register(CareerSubject)
class CareerSubjectAdmin(admin.ModelAdmin):
    list_display = ('career', 'subject', 'numero_materia', 'anio_cursada', 'cuatrimestre_cursada')
    list_filter = ('career', 'anio_cursada')
    search_fields = ('career__name', 'subject__name')
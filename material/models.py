from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import json

# --- MODELOS V2 PRIMERO (para evitar referencias circulares) ---

from django.db import models
from django.core.exceptions import ValidationError

class InstitutionV2(models.Model):
    name = models.CharField(
        max_length=255,
        verbose_name="Nombre",
        help_text="Nombre completo de la institución"
    )
    logo = models.ImageField(
        upload_to='institution_logos_v2/',
        null=True,
        blank=True,
        verbose_name="Logo",
        help_text="Subir imagen del logo institucional"
    )
    # Búsqueda por sigla ("UAI" → "Universidad Abierta Interamericana") —
    # no alcanza con acento/mayúsculas-insensible sobre el nombre porque la
    # sigla no es necesariamente una subcadena del nombre completo.
    sigla = models.CharField(
        max_length=20, blank=True, default='', verbose_name="Sigla",
        help_text="Opcional — permite encontrarla al buscar por sigla además de por nombre completo",
    )
    logo_b64 = models.TextField(
        null=True,
        blank=True,
        verbose_name="Logo (Base64)",
        help_text="Copia del logo en Base64 para producción sin filesystem persistente"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa",
        help_text="Indica si la institución está activa en el sistema"
    )
    # Institución del contenido semilla (ver seed_demo_content) — solo debe
    # aparecer en el esquema de ejemplo del asistente de onboarding, nunca
    # en los selectores de uso normal (Crear Examen, Formatos de Impresión,
    # etc.). Ver [[project_include_seed_missing_across_endpoints]].
    is_seed_demo = models.BooleanField(default=False)
    # Espacio personal vs. catálogo institucional (ver "personal space"
    # acordado con el usuario): una fila creada por un usuario raso nace
    # con esto en False — usable de inmediato solo para quien la creó (y
    # quien comparta con ella), invisible en los selectores públicos hasta
    # que un admin la suma al catálogo institucional (o la fusiona con una
    # ya existente). Todo lo cargado por el admin, o lo ya migrado antes de
    # este campo, queda en True.
    es_catalogo_institucional = models.BooleanField(
        default=True, verbose_name="En el catálogo institucional",
    )
    # Nullable porque las filas cargadas por el admin (o migradas antes de
    # este campo) no tienen "creador personal" en este sentido.
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='institutions_created', verbose_name="Creado por",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización"
    )

    class Meta:
        verbose_name = "Institución V2"
        verbose_name_plural = "Instituciones V2"
        ordering = ['name']
        constraints = [
            # Alcance acotado al catálogo institucional a propósito — dos
            # usuarios distintos pueden tener cada uno un espacio personal
            # con el mismo nombre sin chocar entre sí (la desambiguación de
            # esos casos queda para el admin al momento de fusionar, no
            # para una restricción de base de datos). Mismo criterio que ya
            # se usa en Career.name (ver informe de rediseño del catálogo).
            models.UniqueConstraint(
                fields=['name'],
                condition=models.Q(is_active=True, es_catalogo_institucional=True),
                name='unique_active_institutional_institution_name'
            )
        ]

    def __str__(self):
        return self.name

    @property
    def logo_src(self):
        # En producción puede existir drift de esquema (columna logo_b64 faltante temporalmente).
        # Este fallback evita 500 y prioriza Base64 cuando está disponible.
        try:
            if self.logo_b64:
                return self.logo_b64
        except Exception:
            pass

        try:
            if self.logo:
                return self.logo.url
        except Exception:
            pass

        return ''

# UserInstitution DEBE estar inmediatamente después
class UserInstitution(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    institution = models.ForeignKey('material.InstitutionV2', on_delete=models.CASCADE)  # Usar string reference
    is_favorite = models.BooleanField(default=False)
    
    class Meta:
        app_label = 'material'
        unique_together = ('user', 'institution')

class CampusV2(models.Model):
    institution = models.ForeignKey(
        InstitutionV2,
        on_delete=models.CASCADE,
        related_name='campusv2_set',
        verbose_name="Institución"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Nombre de la Sede",
        help_text="Nombre de la sede"
    )
    address = models.TextField(
        verbose_name="Dirección",
        help_text="Dirección completa de la sede",
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa",
        help_text="Indica si la sede está activa"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sede V2"
        verbose_name_plural = "Sedes V2"
        constraints = [
            # Condicionado a is_active=True: una sede desactivada (soft-delete
            # vía is_active=False) no debe bloquear la creación de una sede
            # nueva con el mismo nombre.
            models.UniqueConstraint(
                fields=['institution', 'name'],
                condition=models.Q(is_active=True),
                name='unique_active_campus_name_per_institution'
            )
        ]

    def clean(self):
        if not self.name or not self.name.strip():
            raise ValidationError("El nombre de la sede no puede estar vacío")

        if self.institution_id and CampusV2.objects.filter(
            institution=self.institution,
            name__iexact=self.name.strip(),
            is_active=True
        ).exclude(id=self.id).exists():
            raise ValidationError("Ya existe una sede activa con este nombre en la institución")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.institution})"

class FacultyV2(models.Model):
    institution = models.ForeignKey(
        InstitutionV2,
        on_delete=models.CASCADE,
        related_name='facultyv2_set',
        verbose_name="Institución"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Nombre de la Facultad",
        help_text="Nombre de la facultad"
    )
    # Elimina esta línea:
    # code = models.CharField(...)
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa",
        help_text="Indica si la facultad está activa"
    )
    # Ver InstitutionV2.es_catalogo_institucional — mismo mecanismo de
    # espacio personal vs. catálogo institucional.
    es_catalogo_institucional = models.BooleanField(
        default=True, verbose_name="En el catálogo institucional",
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='faculties_created', verbose_name="Creado por",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Facultad"
        verbose_name_plural = "Facultades"
        ordering = ['name']
        constraints = [
            # Igual criterio que CampusV2: una facultad desactivada (soft-
            # delete vía is_active=False) no debe bloquear crear una facultad
            # nueva con el mismo nombre. Acotado al catálogo institucional
            # por el mismo motivo que InstitutionV2 — ver ahí.
            models.UniqueConstraint(
                fields=['institution', 'name'],
                condition=models.Q(is_active=True, es_catalogo_institucional=True),
                name='unique_active_faculty_name_per_institution'
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.institution.name}"

class InstitutionLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Creación'),
        ('update', 'Actualización'),
        ('delete', 'Eliminación'),
        ('favorite', 'Favorito'),
    ]

    institution = models.ForeignKey(InstitutionV2, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Log de Institución"
        verbose_name_plural = "Logs de Instituciones"

# Institution/Campus/Faculty (v1) fueron eliminados — ver rediseño del
# catálogo académico público (informe "Catálogo Académico"). Reemplazados
# en toda la app por InstitutionV2/CampusV2/FacultyV2 desde hace tiempo;
# eran código muerto e inalcanzable (sin URL, sin form, NameError si se
# invocaban) salvo Profile.institutions, que ya estaba desconectado del
# form real por un bug de tipos. Ver git history si hace falta consultar
# el modelo viejo.

class Subject(models.Model):
    # OJO: name NO es unique=True todavía a propósito. get_or_create_real_subject()
    # (más abajo) matchea materias por (nombre, created_by) y crea una fila
    # nueva por usuario cuando hace falta — agregar unique=True acá rompería
    # esa función (IntegrityError) para cualquier docente que tipee un nombre
    # de materia que ya usó otro. Volverlo único al catálogo público requiere
    # primero cerrar la creación libre de materias (Fase 3: bloquear
    # get_or_create_real_subject/"Nueva materia" para usuarios rasos y
    # ofrecer el flujo de solicitud) — se hace en un paso aparte, no acá.
    name = models.CharField(max_length=100)
    # La M2M real vive del lado de Career (ver Career.subjects, through=
    # CareerSubject) — acá no se declara una segunda M2M aparte. Antes había
    # dos M2M independientes entre Subject y Career (Subject.careers y
    # Career.subjects, cada una con su propia tabla puente, sincronizadas a
    # mano en seed_demo_content.py) — se consolidó en una sola relación:
    # `subject.careers` sigue andando igual, ahora como accessor inverso de
    # Career.subjects.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Materia de ejemplo sembrada por seed_demo_content (ver
    # SEED_CONTENT_USERNAME) — usada SOLO por el flujo del asistente de
    # configuración (wizard) para mostrar un examen de ejemplo. No es un
    # dato real de ningún docente. Antes se mezclaba con las materias reales
    # en todos los selectores del sitio (Subir Preguntas, Crear Examen,
    # "Nueva materia") porque Subject se matchea por nombre sin dueño — un
    # docente que tipeaba "Programación I" para su propio curso terminaba
    # reusando esta misma fila semilla sin saberlo. Ver
    # [[project_subject_topic_global_sharing_bug]]. get_or_create_real_subject()
    # (más abajo) es el punto único para crear/matchear materias reales sin
    # pisar esto.
    is_seed_demo = models.BooleanField(
        default=False,
        verbose_name="Materia semilla del sistema (demo)",
        help_text="Sembrada por seed_demo_content para el asistente de configuración — no es una materia real de ningún docente.",
    )
    # Dueño real de la materia. Antes Subject no tenía dueño y se matcheaba
    # solo por nombre (ver comentario de is_seed_demo más arriba y
    # [[project_subject_topic_global_sharing_bug]]): dos docentes que
    # escribían "Programación I" terminaban compartiendo la misma fila sin
    # saberlo, y /materias/ mostraba TODAS las materias del sistema a
    # cualquier usuario. get_or_create_real_subject() ahora matchea por
    # (nombre, usuario) — cada docente tiene su propia fila incluso con
    # nombres iguales. Nullable porque las filas históricas sin ningún
    # Question/Contenido asociado no tienen forma de inferir un dueño.
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='owned_subjects', verbose_name="Creada por",
    )
    # Ver InstitutionV2.es_catalogo_institucional — mismo mecanismo de
    # espacio personal vs. catálogo institucional. A diferencia de los
    # otros tres niveles, acá conviven filas viejas de antes de este campo
    # (get_or_create_real_subject de un docente) con las del catálogo
    # curado — el backfill de la migración distingue por si están
    # vinculadas a alguna Carrera (CareerSubject), no asume True a secas.
    es_catalogo_institucional = models.BooleanField(
        default=True, verbose_name="En el catálogo institucional",
    )

    class Meta:
        db_table = 'material_subjects'
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_all_outcomes(self):
        """Resultados de aprendizaje de TODAS las carreras que usan esta
        materia (LearningOutcome cuelga de CareerSubject, no de Subject
        directo — ver informe de rediseño). Para el detalle por carrera, ver
        SubjectDetailView."""
        return list(
            LearningOutcome.objects.filter(career_subject__subject=self)
            .values('id', 'description')
        )

    def clean(self):
        if not self.name.strip():
            raise ValidationError("El nombre no puede estar vacío")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


def get_or_create_real_subject(name, user):
    """
    Punto único para crear/matchear una materia REAL por nombre (CSV/TXT,
    "Nueva materia", generador de IA, paso 3 del wizard cuando el docente
    tipea un nombre nuevo). A diferencia de Subject.objects.get_or_create,
    nunca reutiliza una fila con is_seed_demo=True: si un docente tipea
    "Programación I" y solo existe la materia semilla con ese nombre, se
    crea una fila real aparte en vez de mezclar su contenido con el
    ejemplo del asistente (ver Subject.is_seed_demo).

    Matchea por (nombre, user) y no por nombre a secas: antes, dos docentes
    que tipeaban el mismo nombre de materia terminaban compartiendo la misma
    fila (y por lo tanto sus temas, resultados de aprendizaje y visibilidad
    en /materias/) sin saberlo. Ver [[project_subject_topic_global_sharing_bug]].
    """
    subject = Subject.objects.filter(name=name, is_seed_demo=False, created_by=user).first()
    if subject:
        return subject, False
    return Subject.objects.create(name=name, is_seed_demo=False, created_by=user), True




class LearningOutcome(models.Model):
    # Unívoco a (materia, carrera), no solo a la materia — confirmado
    # explícitamente como requisito no opcional (ver informe de rediseño):
    # la misma Materia puede representar programas distintos en carreras
    # distintas (confirmado con datos reales: "Inglés I" se repite en 4
    # carreras de UAI-FTI), así que sus resultados de aprendizaje no pueden
    # quedar pegados a la Materia en abstracto. Obligatorio desde la Fase 4
    # (reset de datos, tabla vacía — se verificó que el único call site que
    # crea filas ya lo pasa siempre, ver seed_demo_content.py).
    career_subject = models.ForeignKey(
        'CareerSubject',
        on_delete=models.CASCADE,
        related_name="outcome_relations",
        verbose_name="Materia en la carrera"
    )
    description = models.TextField(
        verbose_name="Contenido",
        help_text="Texto completo del resultado de aprendizaje"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Resultado de Aprendizaje"
        verbose_name_plural = "Resultados de Aprendizaje"
        ordering = ['created_at']


class Unidad(models.Model):
    """
    Agrupa Temas de una Materia para elegir contenido más rápido al crear
    examen (por unidad completa, o por tema suelto como hoy — ver informe
    de rediseño). Privada por usuario, igual que Topic: cada docente arma
    sus propias unidades sobre sus propios temas, no es catálogo público.
    """
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unidades')
    name = models.CharField(max_length=255, verbose_name="Nombre de la unidad")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Orden")

    class Meta:
        verbose_name = "Unidad"
        verbose_name_plural = "Unidades"
        unique_together = ('subject', 'created_by', 'name')
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} ({self.subject.name})"


class Topic(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nombre del Tópico")
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        verbose_name="Asignatura relacionada"
    )
    importance = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Importancia (1-5)"
    )
    # Sigue nullable a propósito, a diferencia de LearningOutcome.career_
    # subject (que sí se endureció en la Fase 4): hay ~10 call sites que
    # crean Topic sin pasar created_by (document processor, wizard paso 3,
    # add_topic, clean_seed_subjects, tests) — volverlo obligatorio ahora
    # rompería esos flujos en cadena. Requiere una revisión propia de cada
    # uno, no un cambio de un renglón. unique_together de abajo trata
    # múltiples NULL como distintos (comportamiento normal de SQL), así que
    # no bloquea nada mientras tanto.
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True,
        related_name='owned_topics', verbose_name="Creado por",
    )
    unidad = models.ForeignKey(
        Unidad, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='topics', verbose_name="Unidad",
    )

    def __str__(self):
        return f"{self.subject.name} - {self.name}"

    class Meta:
        verbose_name = "Tópico"
        verbose_name_plural = "Tópicos"
        unique_together = ('name', 'subject', 'created_by')

class Subtopic(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nombre del Sub-tópico")
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        verbose_name="Tópico relacionado"
    )

    def __str__(self):
        return f"{self.topic} → {self.name}"

    class Meta:
        verbose_name = "Sub-tópico"
        verbose_name_plural = "Sub-tópicos"
        unique_together = ('name', 'topic')

class Contenido(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='contenidos/', blank=True, null=True, max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    subjects = models.ManyToManyField(
        Subject,
        blank=True,
        verbose_name='Materias',
        related_name='contenidos'
    )
    author = models.CharField(max_length=255, blank=True, null=True, verbose_name='Autor(es)')
    isbn = models.CharField(max_length=20, blank=True, null=True)
    edition = models.CharField(max_length=50, blank=True, null=True)
    pages = models.PositiveIntegerField(blank=True, null=True)
    publisher = models.CharField(max_length=100, blank=True, null=True)
    year = models.PositiveIntegerField(blank=True, null=True)
    chapter = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Capítulo (opcional)'
    )
    file_deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Archivo eliminado el',
        help_text='Fecha en que el archivo físico fue eliminado automáticamente (7 días tras la subida). Los metadatos se conservan.'
    )
    file_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        verbose_name='Hash SHA-256 del archivo',
        help_text='Huella digital del archivo para detectar duplicados. Se calcula al subir.'
    )

    @property
    def file_available(self):
        return bool(self.file) and self.file_deleted_at is None

    def file_actually_exists(self):
        """
        Chequea contra el storage si el archivo sigue físicamente presente.
        A diferencia de file_available, no confía en file_deleted_at: ese campo
        solo se actualiza al cerrar sesión o al detectar sesiones inactivas, así
        que si el archivo desaparece por otro motivo (reinicio/redeploy del
        servidor, storage efímero, etc.) mientras la sesión sigue abierta,
        file_deleted_at queda desactualizado y esta es la única forma confiable
        de saberlo.
        """
        if not self.file or not self.file.name:
            return False
        from django.core.files.storage import default_storage
        try:
            return default_storage.exists(self.file.name)
        except Exception:
            return False

    def __str__(self):
        subjects = ', '.join(str(s) for s in self.subjects.all()) or 'Sin materia'
        return f"{subjects} - {self.title}"

class Question(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('opcion_multiple', 'Opción múltiple'),
        ('verdadero_falso', 'Verdadero/Falso'),
        ('completar_blank', 'Completar el espacio'),
        ('desarrollo', 'Desarrollo'),
    ]

    BLOOM_LEVEL_CHOICES = [
        (1, 'Recordar'),
        (2, 'Comprender'),
        (3, 'Aplicar'),
        (4, 'Analizar'),
        (5, 'Evaluar'),
        (6, 'Crear'),
    ]

    contenido = models.ForeignKey(
        'Contenido',
        on_delete=models.CASCADE,
        verbose_name='Contenido relacionado',
        null=True,
        blank=True,
        related_name='preguntas'
    )
    subjects = models.ManyToManyField(
        'Subject',
        blank=True,
        verbose_name='Materias',
        related_name='questions'
    )
    topic = models.ForeignKey(
        'Topic',
        on_delete=models.SET_NULL,
        null=True,
        blank=False,
        verbose_name='Tema principal'
    )
    subtopic = models.ForeignKey(
        'Subtopic',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Subtema (opcional)'
    )
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPE_CHOICES,
        default='opcion_multiple',
        verbose_name='Tipo de pregunta'
    )
    question_text = models.TextField(verbose_name='Texto de la pregunta')
    answer_text = models.TextField(verbose_name='Texto de la respuesta')
    question_image = models.ImageField(
        upload_to='questions/images/',
        null=True,
        blank=True,
        verbose_name='Imagen de la pregunta (opcional)'
    )
    answer_image = models.ImageField(
        upload_to='answers/images/',
        null=True,
        blank=True,
        verbose_name='Imagen de la respuesta (opcional)'
    )
    # Imágenes codificadas en Base64 — compatibles con SQLite (dev) y
    # PostgreSQL/Neon (prod) sin depender del filesystem del servidor.
    # El campo ImageField equivalente se vacía siempre tras la conversión.
    question_image_b64 = models.TextField(
        null=True,
        blank=True,
        verbose_name='Imagen de pregunta (Base64)',
    )
    answer_image_b64 = models.TextField(
        null=True,
        blank=True,
        verbose_name='Imagen de respuesta (Base64)',
    )
    options_json = models.TextField(
        blank=True,
        null=True,
        verbose_name='Opciones (JSON)'
    )
    difficulty = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Dificultad (1-5)'
    )
    bloom_level = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=BLOOM_LEVEL_CHOICES,
        verbose_name='Nivel Bloom',
        help_text='Nivel cognitivo según taxonomía de Bloom (1=Recordar … 6=Crear). Solo visible para el docente.'
    )
    source_page = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Página de referencia'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Usuario',
        null=True,
        blank=True
    )
    # Campos para preguntas generadas por IA
    generated_by_ai = models.BooleanField(
        default=False,
        verbose_name='Generada por IA',
        help_text='Indica si esta pregunta fue generada automáticamente por IA'
    )
    ai_approved = models.BooleanField(
        null=True,
        blank=True,
        verbose_name='Aprobada por usuario',
        help_text='True=Aprobada, False=Rechazada, NULL=Sin revisar'
    )
    source_chapters_json = models.TextField(
        blank=True,
        null=True,
        verbose_name='Capítulos fuente (JSON)',
        help_text='JSON con información de los capítulos de donde se generó'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['topic', 'subtopic', 'difficulty']
        verbose_name = 'Pregunta'
        verbose_name_plural = 'Preguntas'

    @property
    def options(self):
        if self.options_json:
            try:
                return json.loads(self.options_json)
            except json.JSONDecodeError:
                return None
        return None

    @options.setter
    def options(self, value):
        self.options_json = json.dumps(value) if value else None
    
    @property
    def source_chapters(self):
        """Retorna los capítulos fuente como objeto Python"""
        if self.source_chapters_json:
            try:
                return json.loads(self.source_chapters_json)
            except json.JSONDecodeError:
                return None
        return None
    
    @source_chapters.setter
    def source_chapters(self, value):
        """Guarda los capítulos fuente como JSON"""
        self.source_chapters_json = json.dumps(value, ensure_ascii=False) if value else None

    @property
    def bibliographic_reference(self):
        """Referencia bibliográfica de origen (libro + capítulo + página),
        para preguntas cargadas a mano o generadas por IA."""
        if not self.contenido_id:
            return None

        book_parts = [self.contenido.title]
        if self.contenido.author:
            book_parts.append(self.contenido.author)
        if self.contenido.edition:
            book_parts.append(f"{self.contenido.edition}ª ed.")
        if self.contenido.publisher:
            book_parts.append(self.contenido.publisher)
        if self.contenido.year:
            book_parts.append(str(self.contenido.year))
        book = ', '.join(book_parts)

        chapters = self.source_chapters
        if chapters:
            chapter_parts = []
            for ch in chapters:
                title = ch.get('title')
                pages = ch.get('pages') or []
                if title and pages:
                    chapter_parts.append(f"{title} (pág. {pages[0]}{'–' + str(pages[-1]) if len(pages) > 1 else ''})")
                elif title:
                    chapter_parts.append(title)
            if chapter_parts:
                return f"{book} — {'; '.join(chapter_parts)}"

        if self.contenido.chapter or self.source_page:
            location = ', '.join(filter(None, [
                self.contenido.chapter,
                f"pág. {self.source_page}" if self.source_page else None,
            ]))
            return f"{book} — {location}" if location else book

        return book

    def clean(self):
        super().clean()
        for field_name in ['question_image', 'answer_image']:
            image = getattr(self, field_name)
            if image and not image.name.lower().endswith(('.jpg', '.jpeg', '.png', '.svg')):
                raise ValidationError(f'Formato no válido para {field_name}. Use JPG, PNG o SVG.')

    def __str__(self):
        first_subject = self.subjects.first()
        subject_name = first_subject.name if first_subject else 'Sin materia'
        return f"{subject_name} - {self.question_text[:50]}..."

class Exam(models.Model):
    title = models.CharField(
        max_length=255,
        verbose_name="Título del examen",
        help_text="Ej: Parcial 1 - Matemáticas"
    )

    topics = models.ManyToManyField(
        Topic,
        verbose_name="Temas evaluados",
        blank=True,
        related_name="exams"
    )

    questions = models.ManyToManyField(
        Question,
        verbose_name="Preguntas",
        related_name="exams"
    )

    # Único campo de texto libre de Exam — Exam.notes_and_recommendations
    # existió en paralelo (sin ningún control real en Crear Examen) y
    # producía secciones duplicadas en la vista previa cuando ambos se
    # poblaban con el mismo texto (ver [[project_examtemplate_vs_exam_field_audit_parking_lot]]);
    # se eliminó el campo entero en vez de solo dejar de usarlo, para que la
    # duplicación sea imposible en vez de estar solo parcheada. El
    # verbose_name es "Notas y recomendaciones" (no "Instrucciones
    # generales" como originalmente) para que coincida con lo que en la
    # práctica siempre termina siendo: tipeado a mano o traído de una
    # plantilla.
    instructions = models.TextField(
        verbose_name="Notas y recomendaciones",
        blank=True,
        null=True
    )

    duration_minutes = models.PositiveIntegerField(
        verbose_name="Duración (minutos)",
        default=60
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )

    version_batch = models.ForeignKey(
        'ExamVersionBatch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versions',
        verbose_name='Lote de versiones'
    )

    version_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Numero de version'
    )
    
    is_published = models.BooleanField(
        default=False,
        verbose_name="Publicado"
    )
    
    def get_questions_by_topic(self):
        return {
            topic: self.questions.filter(topic=topic)
            for topic in self.topics.all()
        }

    def total_points(self):
        return sum(q.difficulty for q in self.questions.all())


    EXAM_TYPE_CHOICES = [  
        ('final', 'Final'),  
        ('parcial', 'Parcial'),  
    ]  
    EXAM_MODE_CHOICES = [  
        ('oral', 'Oral'),  
        ('escrito', 'Escrito'),  
    ]  
    EXAM_PARTIAL_CHOICES = [  
        ('1ro', 'Primer Parcial'),  
        ('2do', 'Segundo Parcial'),  
        ('3ro', 'Tercer Parcial'),  
        ('4to', 'Cuarto Parcial'),  
    ]  
    EXAM_GROUP_CHOICES = [  
        ('individual', 'Individual'),  
        ('grupal', 'Grupal'),  
    ]  
    SHIFT_CHOICES = [  
        ('mañana', 'Mañana'),  
        ('tarde', 'Tarde'),  
        ('noche', 'Noche'),  
    ]  

    # institution/faculty/campus (FKs a Institution/Faculty/Campus v1) se
    # quitaron junto con el stack v1 — nunca se poblaban, el guardado de
    # examen siempre usó institution_name/faculty_name/campus_name (texto).
    career_name = models.CharField(max_length=255, verbose_name="Carrera", blank=True, default='')  
    subject = models.ForeignKey(  
        'Subject',  
        on_delete=models.SET_NULL,  
        null=True,  
        blank=True,  
        verbose_name="Materia"  
    )  
    professor = models.ForeignKey(  
        User,  
        on_delete=models.SET_NULL,  
        null=True,  
        blank=True,  
        verbose_name="Profesor"  
    )  
    year = models.IntegerField(verbose_name="Año", null=True, blank=True)
    exam_type = models.CharField(
        max_length=40,
        choices=EXAM_TYPE_CHOICES,
        verbose_name="Tipo de examen",
        blank=True,
        null=True,  
    )  
    partial_number = models.CharField(  
        max_length=10,  
        choices=EXAM_PARTIAL_CHOICES,  
        blank=True,  
        null=True,  
        verbose_name="Número de parcial"  
    )  
    exam_mode = models.CharField(  
        max_length=10,  
        choices=EXAM_MODE_CHOICES,  
        verbose_name="Modalidad de examen",  
        blank=True,  
        null=True,  
    )  
    exam_group = models.CharField(  
        max_length=10,  
        choices=EXAM_GROUP_CHOICES,  
        default='individual',  
        verbose_name="Modalidad grupal"  
    )  
    shift = models.CharField(  
        max_length=10,  
        choices=SHIFT_CHOICES,  
        blank=True,  
        null=True,  
        verbose_name="Turno"  
    )  
    resolution_time = models.CharField(  
        max_length=50,  
        blank=True,  
        null=True,  
        verbose_name="Tiempo de resolución"  
    )  
    topics_to_evaluate = models.TextField(
        blank=True,
        null=True,
        verbose_name="Tópicos a evaluar"
    )
    institution_name = models.CharField(max_length=255, blank=True, default='', verbose_name="Institución (texto)")
    faculty_name = models.CharField(max_length=255, blank=True, default='', verbose_name="Facultad (texto)")
    campus_name = models.CharField(max_length=255, blank=True, default='', verbose_name="Sede (texto)")
    subject_name = models.CharField(max_length=255, blank=True, default='', verbose_name="Materia (texto)")
    topics_snapshot = models.JSONField(default=list, blank=True, verbose_name="Temas (snapshot)")
    outcomes_snapshot = models.JSONField(default=list, blank=True, verbose_name="Resultados de aprendizaje (snapshot)")
    date_str = models.CharField(max_length=50, blank=True, default='', verbose_name="Fecha (texto)")
    alumno = models.CharField(max_length=255, blank=True, default='', verbose_name="Alumno/a")
    curso = models.CharField(max_length=100, blank=True, default='', verbose_name="Curso")
    # Texto libre a propósito, mismo criterio que curso/turno_text: distintas
    # cátedras de la misma materia (misma carrera, mismo plan de estudios)
    # pueden diferir en profesor, bibliografía y hasta contenido — no hay
    # catálogo de cátedras (ver parking lot de modelado estructural), esto
    # solo imprime en el encabezado del examen.
    catedra = models.CharField(max_length=255, blank=True, default='', verbose_name="Cátedra")

    @property
    def turno(self):
        """Alias for 'shift' so templates using session-dict keys also work."""
        return self.shift

    @property
    def sede(self):
        """Alias for 'campus_name'."""
        return self.campus_name

    @property
    def modalidad_resolucion(self):
        """Return resolution_time as a list (mirrors session dict format)."""
        if not self.resolution_time:
            return []
        return [m.strip() for m in self.resolution_time.split(',') if m.strip()]

    learning_outcomes = models.ManyToManyField(
        'LearningOutcome',
        blank=True,
        verbose_name="Resultados de aprendizaje"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_exams',
        verbose_name="Creado por"
    )

    def __str__(self):
        exam_name = f"{self.get_exam_type_display()}"
        if self.exam_type == 'parcial' and self.partial_number:
            exam_name += f" {self.get_partial_number_display()}"
        return f"{self.subject} - {exam_name} ({self.year})"

    class Meta:
        verbose_name = "Examen"
        verbose_name_plural = "Exámenes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["exam_type", "year"]),
            models.Index(fields=["subject"]),
        ]

TEST_STAGE_CHOICES = [
    (1, 'Etapa 1 — Contenido e IA'),
    (2, 'Etapa 2 — Exámenes y evaluación'),
    (3, 'Etapa 3 — Organización y colaboración'),
]


class Profile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('user', 'Usuario'),
    ]

    VISUAL_THEME_CHOICES = [
        ('default', 'EducaApp'),
        ('slack', 'Slack'),
        ('linear', 'Linear'),
        ('figma', 'Figma'),
        ('miro', 'Miro'),
        ('pinterest', 'Pinterest'),
        ('replicate', 'Replicate'),
        ('starbucks', 'Starbucks'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    # ONBOARDING WIZARD — ROLLBACK: eliminar este campo y revertir migración 0020
    onboarding_completed = models.BooleanField(
        default=False,
        verbose_name='Onboarding completado',
        help_text='Indica si el usuario completó o saltó el wizard de configuración inicial.',
    )
    visual_theme = models.CharField(
        max_length=20,
        choices=VISUAL_THEME_CHOICES,
        default='default',
        verbose_name='Tema visual',
        help_text='Skin de colores/tipografía elegido por el usuario para la interfaz.',
    )
    SECURITY_QUESTION_CHOICES = [
        ('primera_mascota', 'Nombre de la primera mascota'),
        ('apellido_soltera_materno', 'Apellido de soltera materno'),
        ('ciudad_nacimiento', 'Ciudad de nacimiento'),
        ('comida_favorita', 'Comida favorita'),
        ('segundo_nombre_padre', 'Segundo nombre del padre'),
        ('marca_primer_auto', 'Marca del primer auto'),
        ('calle_donde_crecio', 'Nombre de la calle donde creció'),
        ('equipo_futbol', 'Equipo de fútbol preferido'),
    ]
    # Recuperación de contraseña sin email: se le pide al usuario en el
    # primer login (ver OnboardingGateMiddleware) y se usa después para
    # validar identidad en /accounts/recuperar/. La respuesta se guarda en
    # texto plano (no hasheada) a propósito: el administrador tiene que
    # poder verla desde el Django Admin para asistir a un docente que se
    # olvidó tanto la contraseña como su propia respuesta.
    security_question = models.CharField(
        max_length=50,
        choices=SECURITY_QUESTION_CHOICES,
        blank=True,
        verbose_name='Pregunta de seguridad',
    )
    security_answer = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Respuesta de seguridad',
    )
    # Cuenta espejo del Área de Pruebas (ver TrainingAccountLink más abajo)
    # — nunca una cuenta real de un docente. Se chequea con un booleano
    # propio en vez de resolver siempre por join contra TrainingAccountLink
    # porque esto se filtra en cada listado de "todos los usuarios activos"
    # (profesor de plantilla/examen, invitar a grupo de confianza).
    is_training_account = models.BooleanField(
        default=False,
        verbose_name='Es cuenta del Área de Pruebas',
        help_text='Cuenta espejo automática, nunca un docente real — se excluye de selectores de usuario.',
    )
    is_tester = models.BooleanField(
        default=False,
        verbose_name='Es tester (UAT)',
        help_text='Ve el panel de Modo Testing dentro de la app, para ir marcando el checklist de pruebas.',
    )
    test_stage = models.PositiveSmallIntegerField(
        null=True, blank=True, choices=TEST_STAGE_CHOICES, verbose_name='Etapa de testing asignada',
        help_text='Vacío = ve el checklist completo. Se completa solo al aceptar una invitación de testing con etapa asignada — no hace falta tocarlo a mano.',
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class TrainingAccountLink(models.Model):
    """
    Empareja a un docente real con su cuenta espejo del Área de Pruebas.
    "Entrar" al Área de Pruebas es un login() real como training_user (ver
    material/training_accounts.py) — no una bandera de sesión que cambie el
    dueño de cada consulta, así todas las vistas existentes (ya scopeadas
    por request.user en todos lados) funcionan sin tocarlas. Esta tabla es
    la única fuente de verdad de qué cuenta espejo pertenece a qué docente
    real — salir_area_pruebas la revalida siempre, nunca confía solo en el
    ID guardado en sesión.
    """
    real_user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='training_link',
        verbose_name='Docente real',
    )
    training_user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='real_account_link',
        verbose_name='Cuenta del Área de Pruebas',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Vínculo de Área de Pruebas'
        verbose_name_plural = 'Vínculos de Área de Pruebas'

    def __str__(self):
        return f'{self.real_user.username} ↔ {self.training_user.username}'


# ---------------------------------------------------------------------------
# Modo Testing (panel de UAT dentro de la app)
# ---------------------------------------------------------------------------
class TestChecklistItem(models.Model):
    """
    Un paso del checklist de testing (ver Plan de Pruebas). Se semillan de una
    sola vez con el comando `seed_test_checklist` — no se editan a mano vía
    UI, si el alcance del testing cambia se re-corre el comando.
    """
    area_number = models.PositiveSmallIntegerField(verbose_name='Número de área')
    area_name = models.CharField(max_length=100, verbose_name='Área')
    order = models.PositiveSmallIntegerField(verbose_name='Orden')
    text = models.CharField(max_length=300, verbose_name='Qué probar')
    target_url_name = models.CharField(
        max_length=100, blank=True, verbose_name='Ruta relacionada',
        help_text='Nombre de URL (namespace material:) al que apunta el link "Ir a esta pantalla". Vacío si no aplica.',
    )
    admin_only = models.BooleanField(default=False, verbose_name='Solo testers admin')
    stage = models.PositiveSmallIntegerField(
        null=True, blank=True, choices=TEST_STAGE_CHOICES, verbose_name='Etapa',
        help_text='Vacío = aparece para cualquier tester sin importar la etapa que tenga asignada (ítems transversales como Alta y primer acceso o Apariencia).',
    )

    class Meta:
        ordering = ['order']
        verbose_name = 'Ítem de checklist de testing'
        verbose_name_plural = 'Ítems de checklist de testing'

    def __str__(self):
        return f'{self.area_number:02d} · {self.text[:60]}'


class TestResult(models.Model):
    STATUS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('ok', 'Funcionó bien'),
        ('problemas', 'Funcionó con problemas'),
        ('no_ok', 'No funcionó'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_results', verbose_name='Tester')
    item = models.ForeignKey(TestChecklistItem, on_delete=models.CASCADE, related_name='results', verbose_name='Ítem')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='pendiente', verbose_name='Resultado')
    comment = models.TextField(blank=True, verbose_name='Comentario')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('user', 'item')]
        verbose_name = 'Resultado de testing'
        verbose_name_plural = 'Resultados de testing'

    def __str__(self):
        return f'{self.user.username} → {self.item} → {self.get_status_display()}'


class Invitation(models.Model):
    """
    Invitación para dar de alta una cuenta nueva vía link compartible.
    El token se genera al crear la invitación; el User recién se crea
    cuando la persona invitada completa el formulario en invitacion_aceptar.
    Un link es de un solo uso: una vez reclamado (used_at seteado) queda
    inválido.
    """
    token = models.CharField(max_length=64, unique=True, editable=False)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='invitaciones_creadas',
        verbose_name='Creada por',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='invitacion_aceptada', verbose_name='Aceptada por',
    )
    is_tester = models.BooleanField(
        default=False, verbose_name='Es invitación de testing (UAT)',
        help_text='La cuenta que se crea con este link nace con profile.is_tester=True — resuelve que no hay usuario a quien marcar como tester antes de que exista.',
    )
    test_stage = models.PositiveSmallIntegerField(
        null=True, blank=True, choices=TEST_STAGE_CHOICES, verbose_name='Etapa de testing asignada',
    )

    class Meta:
        verbose_name = 'Invitación'
        verbose_name_plural = 'Invitaciones'
        ordering = ['-created_at']

    def __str__(self):
        estado = f'usada por {self.used_by.username}' if self.used_by_id else 'pendiente'
        return f'Invitación de {self.created_by.username} ({estado})'

    def is_used(self):
        return self.used_at is not None

    def save(self, *args, **kwargs):
        if not self.token:
            import secrets
            self.token = secrets.token_urlsafe(6)
        super().save(*args, **kwargs)


class Career(models.Model):
    # Ya no es unique=True: con más de una institución cargada (ver informe
    # de rediseño del catálogo), dos instituciones distintas pueden tener
    # cada una una carrera con el mismo nombre (ej. "Licenciatura en
    # Sistemas de Información") — antes esto tiraba IntegrityError apenas
    # se cargaba la segunda institución. La desambiguación de nombres
    # "iguales pero distintos" queda en manos de quien carga el catálogo
    # (ver clean(), más abajo, que ya no bloquea duplicados).
    name = models.CharField(
        max_length=255,
        verbose_name="Nombre de la Carrera",
        help_text="Nombre completo de la carrera"
    )
    faculties = models.ManyToManyField(
        FacultyV2,
        blank=True,
        verbose_name="Facultades",
        related_name="career_faculties"  # related_name único
    )
    subjects = models.ManyToManyField(
        Subject,
        through='CareerSubject',
        blank=True,
        verbose_name="Materias",
        related_name="careers"
    )
    campus = models.ManyToManyField(
        CampusV2,
        blank=True,
        verbose_name="Campus",
        related_name="career_campuses"  # related_name único
    )
    # Carrera del contenido semilla (ver seed_demo_content) — mismo criterio
    # que InstitutionV2.is_seed_demo: solo debe verse en el esquema de
    # ejemplo del asistente, nunca en los selectores de uso normal.
    is_seed_demo = models.BooleanField(default=False)
    # Ver InstitutionV2.es_catalogo_institucional — mismo mecanismo de
    # espacio personal vs. catálogo institucional.
    es_catalogo_institucional = models.BooleanField(
        default=True, verbose_name="En el catálogo institucional",
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='careers_created', verbose_name="Creado por",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización"
    )

    class Meta:
        verbose_name = "Carrera"
        verbose_name_plural = "Carreras"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        """Validación adicional"""
        if not self.name.strip():
            raise ValidationError("El nombre no puede estar vacío")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class CareerSubject(models.Model):
    """
    Through explícito de Career.subjects — cada fila es "esta Materia, tal
    como se cursa dentro de esta Carrera puntual". numero_materia/anio_
    cursada/cuatrimestre_cursada son datos del PLAN DE ESTUDIOS de esa
    carrera, no de la Materia en sí (la misma "Álgebra I" puede ser 1er año
    en una carrera y 3er año en otra) — por eso viven acá y no en Subject.

    Los tres campos son blank=True/default='' (no obligatorios) a propósito:
    así career.subjects.add(subject)/.set(...) sigue funcionando sin pasar
    valores extra (ver seed_demo_content.py), para altas rápidas donde
    todavía no se cargó el detalle del plan de estudios.
    """
    career = models.ForeignKey(Career, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    numero_materia = models.CharField(max_length=20, blank=True, default='', verbose_name="N° de materia")
    anio_cursada = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Año de cursada")
    cuatrimestre_cursada = models.CharField(max_length=20, blank=True, default='', verbose_name="Cuatrimestre de cursada")

    class Meta:
        verbose_name = "Materia de la carrera"
        verbose_name_plural = "Materias de la carrera"
        unique_together = ('career', 'subject')
        ordering = ['anio_cursada', 'numero_materia']

    def __str__(self):
        return f"{self.subject.name} ({self.career.name})"


#nuevas clases para relacionar instituciones con carreras y materias.  falta ajustar carreras, materias e instituciones
class InstitutionCareer(models.Model):
    institution = models.ForeignKey(
        InstitutionV2,
        on_delete=models.CASCADE,
        verbose_name="Institución",
        related_name='institution_careers'
    )
    career = models.ForeignKey(
        'Career',
        on_delete=models.CASCADE,
        verbose_name="Carrera",
        related_name='career_institutions'
    )
    date_created = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )

    class Meta:
        unique_together = ('institution', 'career')
        verbose_name = "Relación Institución-Carrera"
        verbose_name_plural = "Relaciones Institución-Carreras"
        ordering = ['-date_created']

    def __str__(self):
        return f"{self.institution.name} - {self.career.name}"

class InstitutionSubject(models.Model):
    institution = models.ForeignKey(
        InstitutionV2,
        on_delete=models.CASCADE,
        verbose_name="Institución",
        related_name='institution_subjects'
    )
    subject = models.ForeignKey(
        'Subject',
        on_delete=models.CASCADE,
        verbose_name="Materia",
        related_name='subject_institutions'
    )
    date_created = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    is_core = models.BooleanField(
        default=True,
        verbose_name="Materia troncal",
        help_text="Indica si es una materia troncal/obligatoria"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )

    class Meta:
        unique_together = ('institution', 'subject')
        verbose_name = "Relación Institución-Materia"
        verbose_name_plural = "Relaciones Institución-Materias"
        ordering = ['-date_created']

    def __str__(self):
        return f"{self.institution.name} - {self.subject.name}"


class CatalogRequest(models.Model):
    """
    Solicitud de un usuario para agregar algo al catálogo público
    (Institución/Facultad/Carrera/Materia, ver informe de rediseño). El
    catálogo pasa a ser de alta exclusiva de admin — esta es la vía para
    que un usuario pida algo que falta, en vez de crearlo él mismo.

    institucion/facultad/carrera son FKs reales al catálogo YA EXISTENTE
    (no texto libre): el formulario arma el contexto con dropdowns en
    cascada, así el admin no tiene que interpretar qué quiso decir el
    usuario. Solo `nombre_propuesto` es texto libre — lo nuevo que falta.
    """
    TIPO_CHOICES = [
        ('institucion', 'Institución'),
        ('facultad', 'Facultad'),
        ('carrera', 'Carrera'),
        ('materia', 'Materia'),
        ('resultado_aprendizaje', 'Resultado de aprendizaje'),
    ]
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    ]

    tipo = models.CharField(max_length=25, choices=TIPO_CHOICES, verbose_name="Tipo")
    # TextField (no CharField) porque para tipo='resultado_aprendizaje' este
    # campo pasa a ser el texto del resultado propuesto, no solo un nombre
    # corto — puede ser una oración larga.
    nombre_propuesto = models.TextField(verbose_name="Nombre propuesto")

    # Cuando una sola solicitud crea varios niveles nuevos a la vez (ej.
    # institución+facultad+carrera+materia, todas nuevas), se generan
    # VARIAS filas de CatalogRequest — una por nivel realmente creado, no
    # una por solicitud — para que el admin apruebe/rechace cada nivel por
    # separado. Antes se resolvía en una sola fila y aprobar o rechazar
    # decidía TODA la cadena junta, lo que dejaba sin forma de rechazar
    # solo la materia (por ejemplo, un nombre placeholder/de prueba) sin
    # arrastrar a institución/facultad/carrera igual de válidas. Este
    # campo agrupa esas filas — mismo valor para todas las que salieron
    # de un mismo envío — para que la bandeja las muestre juntas.
    lote_id = models.UUIDField(null=True, blank=True, editable=False, db_index=True, verbose_name="Lote")

    # Contexto — solo se completa lo que corresponda según `tipo` (una
    # Institución nueva no tiene contexto; una Materia nueva completa los 3).
    # Cada nivel admite DOS formas, mutuamente excluyentes: elegir una fila
    # YA EXISTENTE del catálogo (el FK) o proponer un nombre NUEVO (el
    # "_nueva" de al lado) cuando ese nivel tampoco existe todavía — así se
    # puede pedir la cadena completa institución+facultad+carrera+materia
    # de una sola solicitud en vez de una por vez esperando aprobación en
    # el medio.
    # on_delete=SET_NULL (no CASCADE) en las cuatro FK de acá abajo a
    # propósito: al rechazar un nivel, _intentar_eliminar_si_vacio puede
    # borrar la fila real detrás (institución/facultad/carrera/materia)
    # para no acumular basura en la base — pero la SOLICITUD tiene que
    # sobrevivir a eso como registro de auditoría (nombre_propuesto ya
    # guarda el texto). Con CASCADE, borrar la fila real se llevaba puesta
    # a la CatalogRequest en el mismo golpe, y el resto del código (que
    # sigue usando `solicitud` después de borrar) rompía con "unsaved
    # related object".
    institucion = models.ForeignKey(
        InstitutionV2, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='catalog_requests', verbose_name="Institución",
    )
    institucion_nueva = models.CharField(max_length=255, blank=True, default='', verbose_name="Institución (nueva)")
    institucion_sigla_nueva = models.CharField(
        max_length=20, blank=True, default='', verbose_name="Sigla de la institución (nueva)",
    )
    facultad = models.ForeignKey(
        FacultyV2, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='catalog_requests', verbose_name="Facultad",
    )
    facultad_nueva = models.CharField(max_length=255, blank=True, default='', verbose_name="Facultad (nueva)")
    carrera = models.ForeignKey(
        Career, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='catalog_requests', verbose_name="Carrera",
    )
    carrera_nueva = models.CharField(max_length=255, blank=True, default='', verbose_name="Carrera (nueva)")

    # Solo para tipo='resultado_aprendizaje' — a diferencia de los otros
    # niveles, acá NO hay variante "_nueva": un resultado de aprendizaje
    # solo tiene sentido sobre una Materia que ya está en el catálogo Y ya
    # vinculada a la Carrera elegida (una fila de CareerSubject real). Si
    # esa Materia todavía no existe, primero hay que pedirla con
    # tipo='materia' y recién después pedir el resultado.
    materia = models.ForeignKey(
        Subject, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='catalog_requests', verbose_name="Materia",
    )

    # Solo tiene efecto cuando la solicitud da de alta una institución nueva
    # (tipo='institucion' o institucion_nueva completado en un nivel más
    # profundo) — se copia al InstitutionV2 recién creado al aprobar.
    logo_propuesto = models.ImageField(
        upload_to='catalog_request_logos/', null=True, blank=True,
        verbose_name="Logo propuesto",
        help_text="Solo si se está proponiendo una institución nueva",
    )

    justificacion = models.TextField(blank=True, default='', verbose_name="Justificación")
    solicitado_por = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='catalog_requests',
        verbose_name="Solicitado por",
    )
    estado = models.CharField(
        max_length=10, choices=ESTADO_CHOICES, default='pendiente', verbose_name="Estado",
    )
    nota_admin = models.TextField(blank=True, default='', verbose_name="Nota del admin")
    resuelto_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='resolved_catalog_requests', verbose_name="Resuelto por",
    )
    resuelto_en = models.DateTimeField(null=True, blank=True, verbose_name="Resuelto el")
    created_at = models.DateTimeField(auto_now_add=True)
    # Aviso al solicitante: distingue "ya resuelta" de "ya se lo mostré" —
    # sostiene el badge de notificación en el menú (se apaga al visitar
    # "Mis solicitudes", ver mis_solicitudes_catalogo).
    visto_por_solicitante = models.BooleanField(default=False, verbose_name="Visto por el solicitante")

    class Meta:
        verbose_name = "Solicitud de catálogo"
        verbose_name_plural = "Solicitudes de catálogo"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.nombre_propuesto} ({self.get_estado_display()})"

    # "el resultado de aprendizaje" es masculino, el resto de los tipos son
    # femeninos — usado por resultado_mensaje() para el artículo correcto.
    _ARTICULO_POR_TIPO = {
        'institucion': 'la', 'facultad': 'la', 'carrera': 'la', 'materia': 'la',
        'resultado_aprendizaje': 'el',
    }

    def entidad_propia(self):
        """La fila real (InstitutionV2/FacultyV2/Career/Subject) que este
        `tipo` representa — la que se creó/eligió para ESTE nivel puntual,
        no el contexto de arriba. None para resultado_aprendizaje (no crea
        nada propio, ver clean() en CatalogRequestForm) o si esa fila ya
        no existe (fusionada o borrada). Usado para decidir si mostrar
        "Borrar" en Mis solicitudes — ver eliminar_espacio_personal."""
        return {
            'institucion': self.institucion,
            'facultad': self.facultad,
            'carrera': self.carrera,
            'materia': self.materia,
        }.get(self.tipo)

    def contexto_display(self):
        """Cadena institución / facultad / carrera (/ materia) para mostrar
        en las tablas de la bandeja y "Mis solicitudes". Desde que
        _materializar_espacio_personal crea todo de una al enviar la
        solicitud, el FK de cada nivel queda poblado de entrada — por eso
        acá NO alcanza con "hay FK, mostrar el nombre y listo": un FK
        puede apuntar a una fila ya institucional o a un borrador recién
        creado en el espacio personal de esta misma solicitud, y esa
        distinción es justamente lo que el admin necesita ver de un
        vistazo (una solicitud de Materia puede traer colgada una
        Institución/Facultad/Carrera nuevas, todas sin catalogar
        todavía)."""
        partes = []
        for fk_attr, nueva_attr in (
            ('institucion', 'institucion_nueva'),
            ('facultad', 'facultad_nueva'),
            ('carrera', 'carrera_nueva'),
        ):
            fk = getattr(self, fk_attr)
            nueva = getattr(self, nueva_attr)
            if fk:
                etiqueta = fk.name if fk.es_catalogo_institucional else f'{fk.name} (espacio personal)'
                partes.append(etiqueta)
            elif nueva:
                partes.append(f'{nueva} (espacio personal)')
        if self.materia_id:
            m = self.materia
            etiqueta = m.name if m.es_catalogo_institucional else f'{m.name} (espacio personal)'
            partes.append(etiqueta)
        return ' / '.join(partes)

    def resultado_mensaje(self):
        """Texto del aviso para quien lo agregó, adaptado a los 5 tipos
        posibles (institución/facultad/carrera/materia/resultado de
        aprendizaje) y a si se sumó o no al catálogo institucional. Vacío
        si todavía está pendiente. Tono "agregar", no "solicitar": lo que
        se agrega ya es usable de inmediato en el espacio personal — esto
        avisa si además pasó a ser del catálogo institucional (compartido)
        o no, no si "se permitió" hacerlo."""
        if self.estado == 'pendiente':
            return ''
        institucion_nombre = self.institucion.name if self.institucion_id else self.institucion_nueva
        facultad_nombre = self.facultad.name if self.facultad_id else self.facultad_nueva
        carrera_nombre = self.carrera.name if self.carrera_id else self.carrera_nueva
        materia_nombre = self.materia.name if self.materia_id else ''
        contexto_por_tipo = {
            'institucion': '',
            'facultad': f' en {institucion_nombre}' if institucion_nombre else '',
            'carrera': f' en {facultad_nombre}' if facultad_nombre else '',
            'materia': f' en {carrera_nombre}' if carrera_nombre else '',
            'resultado_aprendizaje': f' en {materia_nombre} ({carrera_nombre})' if materia_nombre else '',
        }
        contexto = contexto_por_tipo.get(self.tipo, '')
        tipo_label = self.get_tipo_display().lower()
        articulo = self._ARTICULO_POR_TIPO.get(self.tipo, 'la').capitalize()
        if self.estado == 'aprobada':
            return (
                f'{articulo} {tipo_label} "{self.nombre_propuesto}"{contexto} ya se sumó al catálogo institucional.'
            )
        motivo = f' Motivo: {self.nota_admin}' if self.nota_admin else ''
        return (
            f'{articulo} {tipo_label} "{self.nombre_propuesto}"{contexto} no se sumó al catálogo institucional.{motivo}'
        )


class ExamVersionBatch(models.Model):
    name = models.CharField(max_length=255, verbose_name='Nombre del lote')
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='exam_version_batches',
        verbose_name='Creado por'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Materia'
    )
    institution_name = models.CharField(max_length=255, blank=True, default='')
    exam_type = models.CharField(max_length=50, blank=True, default='')
    semester = models.CharField(max_length=50, blank=True, default='')
    year = models.IntegerField(null=True, blank=True)
    version_count = models.PositiveIntegerField(default=1)
    questions_per_version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Lote de versiones de examen'
        verbose_name_plural = 'Lotes de versiones de examen'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class ExamTemplate(models.Model):
    # Opciones de modalidad
    EXAM_MODE_CHOICES = [
        ('presencial', 'Presencial'),
        ('virtual', 'Virtual'),
        ('domiciliario', 'Domiciliario'),
        ('hibrido', 'Híbrido'),
        ('otro', 'Otro')
    ]
    
    # Opciones de tipo de examen
    EXAM_TYPE_CHOICES = [
        ('1er_parcial', '1er. Parcial'),
        ('2do_parcial', '2do. Parcial'), 
        ('3er_parcial', '3er. Parcial'),
        ('final', 'Final'),
        ('recuperatorio', 'Recuperatorio'),
        ('practico', 'Práctico')
    ]
    
    # Opciones de turno
    SHIFT_CHOICES = [
        ('manana', 'Mañana'),
        ('tarde', 'Tarde'),
        ('noche', 'Noche')
    ]

    # Nombre elegido por el usuario (opcional). Si se deja vacío, __str__
    # sigue armando uno automático a partir de Materia/Tipo/Año, como antes.
    name = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name="Nombre de la plantilla"
    )

    # Relaciones institucionales
    institution = models.ForeignKey(
        InstitutionV2,
        on_delete=models.PROTECT,
        verbose_name="Institución"
    )
   
    faculty = models.ForeignKey(
        FacultyV2,
        on_delete=models.PROTECT,
        verbose_name="Facultad"
    )
  
    career = models.ForeignKey(
        Career,
        on_delete=models.PROTECT,
        verbose_name="Carrera"
    )
  
    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        verbose_name="Materia"
    )
   
    campus = models.ForeignKey(
        CampusV2,
        on_delete=models.PROTECT,
        verbose_name="Sede/Campus",
        null=True,
        blank=True
    )
  
    professor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='professor_exam_templates',
        verbose_name="Profesor",
        null=True,
        blank=True
    )

    # Texto libre a propósito, mismo criterio que Exam.catedra — ver ese
    # comentario para el contexto completo.
    catedra = models.CharField(max_length=255, blank=True, default='', verbose_name="Cátedra")

    # Configuración del examen
    year = models.PositiveIntegerField(
        verbose_name="Año académico",
        default=timezone.now().year
    )
   
    exam_type = models.CharField(
        max_length=20,
        choices=EXAM_TYPE_CHOICES,
        verbose_name="Tipo de examen",
        blank=True,
        null=True,  # Permitir NULL en la base de datos
        default=None
    )
   
    exam_mode = models.CharField(
        max_length=20,
        choices=EXAM_MODE_CHOICES,
        verbose_name="Modalidad de examen",
        blank=True,
        null=True,  # Permitir NULL en la base de datos
        default=None
    )
   
    shift = models.CharField(
        max_length=20,
        choices=SHIFT_CHOICES,
        verbose_name="Turno",
        blank=True,
        null=True
    )
    
    # Contenido evaluativo
    learning_outcomes = models.ManyToManyField(
        LearningOutcome,
        verbose_name="Resultados de aprendizaje",
        blank=True
    )

    # Rubric se define más abajo en este mismo archivo — referencia por
    # nombre porque ExamTemplate se declara antes en el módulo.
    rubrics = models.ManyToManyField(
        'Rubric',
        verbose_name="Rúbricas",
        related_name='exam_templates',
        blank=True
    )

    notes_and_recommendations = models.TextField(
        verbose_name="Notas y recomendaciones",
        blank=True
    )
    
    # Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_exam_templates',
        verbose_name="Creado por"
    )

    # Snapshot fields — conservan los nombres en el momento de creación del examen
    institution_name_snapshot = models.CharField(max_length=255, blank=True, default='', verbose_name="Institución (snapshot)")
    faculty_name_snapshot = models.CharField(max_length=255, blank=True, default='', verbose_name="Facultad (snapshot)")
    campus_name_snapshot = models.CharField(max_length=255, blank=True, default='', verbose_name="Sede (snapshot)")
    career_name_snapshot = models.CharField(max_length=255, blank=True, default='', verbose_name="Carrera (snapshot)")
    subject_name_snapshot = models.CharField(max_length=255, blank=True, default='', verbose_name="Materia (snapshot)")
    outcomes_snapshot = models.JSONField(default=list, blank=True, verbose_name="Resultados de aprendizaje (snapshot)")

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )
    
    # Diseño
    institution_logo = models.ImageField(
        upload_to='exam_templates/logos/',
        null=True,
        blank=True,
        verbose_name="Logo institucional"
    )

    custom_css = models.TextField(
        blank=True,
        help_text="CSS personalizado para la plantilla",
        verbose_name="Estilos CSS"
    )

    # El formato es parte de la plantilla, no solo un dato de contenido: dos
    # plantillas de la misma institución pueden querer imprimirse distinto
    # (ej. "Final" vs "Trabajo Práctico"). Si no se elige ninguno acá, sigue
    # aplicando la cadena de resolución de siempre (institución → usuario →
    # global, ver print_format_utils.resolve_print_format_for_context) — este
    # campo es un nivel más específico que se inserta ANTES de esa cadena,
    # no la reemplaza.
    print_format = models.ForeignKey(
        'FormatoImpresion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exam_templates',
        verbose_name="Formato de impresión",
    )

    class Meta:
        verbose_name = "Plantilla de examen"
        verbose_name_plural = "Plantillas de examen"
        ordering = ['-created_at']
        permissions = [
            ('can_share_template', 'Puede compartir plantillas'),
        ]
        indexes = [
            models.Index(fields=['exam_type', 'year']),
            models.Index(fields=['subject']),
        ]
    
    def __str__(self):
        if self.name:
            return self.name
        exam_name = f"{self.get_exam_type_display()}"
        if self.exam_type == 'parcial' and self.partial_number:
            exam_name += f" {self.get_partial_number_display()}"
        return f"{self.subject} - {exam_name} ({self.year})"
    
    def save(self, *args, **kwargs):
        # skip_validation existe porque save_exam_template arma la plantilla
        # a mano desde POST (no pasa por ExamTemplateForm) y ya hace su
        # propia validación mínima de campos requeridos antes de llegar acá.
        skip_validation = kwargs.pop('skip_validation', False)
        if not skip_validation:
            self.full_clean()
        super().save(*args, **kwargs)

# Modelo para Cuestionarios Orales
class OralExamSet(models.Model):
    name = models.CharField(
        max_length=255,
        verbose_name='Nombre del conjunto de examen oral'
    )
    subject = models.ForeignKey(
        'Subject',
        on_delete=models.CASCADE,
        verbose_name='Materia'
    )
    topics = models.ManyToManyField(
        'Topic',
        verbose_name='Temas a evaluar',
        help_text='Seleccione los temas que se incluirán en el examen oral'
    )
    num_groups = models.PositiveIntegerField(
        verbose_name='Número de grupos',
        help_text='Cantidad de grupos de estudiantes'
    )
    students_per_group = models.PositiveIntegerField(
        verbose_name='Estudiantes por grupo',
        help_text='Número de estudiantes en cada grupo'
    )
    questions_per_student = models.PositiveIntegerField(
        default=3,
        verbose_name='Preguntas por estudiante',
        help_text='Cantidad de preguntas que recibirá cada estudiante'
    )
    total_students = models.PositiveIntegerField(
        verbose_name='Total de estudiantes',
        help_text='Cantidad total de estudiantes que rendirán el examen'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Creador'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Conjunto de Examen Oral'
        verbose_name_plural = 'Conjuntos de Exámenes Orales'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.subject.name}"

class OralExamGroup(models.Model):
    exam_set = models.ForeignKey(
        OralExamSet,
        on_delete=models.CASCADE,
        related_name='groups'
    )
    group_number = models.PositiveIntegerField(
        verbose_name='Número de grupo'
    )
    
    class Meta:
        verbose_name = 'Grupo de Examen Oral'
        verbose_name_plural = 'Grupos de Examen Oral'
        ordering = ['exam_set', 'group_number']
    
    def __str__(self):
        return f"Grupo {self.group_number} - {self.exam_set.name}"

class OralExamStudent(models.Model):
    group = models.ForeignKey(
        OralExamGroup,
        on_delete=models.CASCADE,
        related_name='students'
    )
    student_number = models.PositiveIntegerField(
        verbose_name='Número de estudiante'
    )
    student_name = models.CharField(
        max_length=255,
        verbose_name='Nombre del estudiante',
        blank=True,
        null=True,
        help_text='Nombre completo del estudiante'
    )
    questions = models.ManyToManyField(
        Question,
        through='OralExamStudentQuestion',
        verbose_name='Preguntas asignadas'
    )
    
    class Meta:
        verbose_name = 'Estudiante de Examen Oral'
        verbose_name_plural = 'Estudiantes de Examen Oral'
        ordering = ['group', 'student_number']
    
    def __str__(self):
        if self.student_name:
            return f"{self.student_name} - Grupo {self.group.group_number}"
        return f"Estudiante {self.student_number} - {self.group}"
    
    def get_evaluation_counts(self):
        """Retorna un diccionario con las evaluaciones del estudiante"""
        evaluations = self.oralexamstudentquestion_set.all()
        counts = {
            'bien': evaluations.filter(evaluation='bien').count(),
            'regular': evaluations.filter(evaluation='regular').count(),
            'mal': evaluations.filter(evaluation='mal').count(),
            'pendiente': evaluations.filter(evaluation='pendiente').count(),
            'total': evaluations.count()
        }
        return counts
    
    def get_progress_percentage(self):
        """Retorna el porcentaje de progreso (preguntas evaluadas)"""
        counts = self.get_evaluation_counts()
        if counts['total'] == 0:
            return 0
        evaluated = counts['total'] - counts['pendiente']
        return round((evaluated / counts['total']) * 100, 1)
    
    def get_score_percentage(self):
        """
        Retorna el porcentaje de puntuación basado en:
        - 'bien': 100% (1.0 punto)
        - 'regular': 50% (0.5 puntos)  
        - 'mal': 0% (0.0 puntos)
        - 'pendiente': no se cuenta
        """
        counts = self.get_evaluation_counts()
        evaluated = counts['total'] - counts['pendiente']
        if evaluated == 0:
            return 0
        
        # Calcular puntuación total
        total_points = (counts['bien'] * 1.0) + (counts['regular'] * 0.5) + (counts['mal'] * 0.0)
        max_possible_points = evaluated * 1.0
        
        return round((total_points / max_possible_points) * 100, 1)

class OralExamStudentQuestion(models.Model):
    EVALUATION_CHOICES = [
        ('bien', 'Bien'),
        ('regular', 'Regular'),
        ('mal', 'Mal'),
        ('pendiente', 'Pendiente'),
    ]
    
    student = models.ForeignKey(OralExamStudent, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(
        verbose_name='Orden de la pregunta'
    )
    evaluation = models.CharField(
        max_length=10,
        choices=EVALUATION_CHOICES,
        default='pendiente',
        verbose_name='Evaluación'
    )
    evaluated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de evaluación'
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Notas adicionales'
    )
    
    class Meta:
        verbose_name = 'Pregunta de Estudiante'
        verbose_name_plural = 'Preguntas de Estudiantes'
        ordering = ['student', 'order']
        unique_together = [('student', 'order')]

class Rubric(models.Model):
    title = models.CharField(
        max_length=255,
        verbose_name="Título"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rubrics',
        verbose_name="Creado por"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Rúbrica"
        verbose_name_plural = "Rúbricas"
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ExamRubric(models.Model):
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='exam_rubrics',
        verbose_name="Examen"
    )
    rubric = models.ForeignKey(
        Rubric,
        on_delete=models.CASCADE,
        related_name='exam_rubrics',
        verbose_name="Rúbrica"
    )
    show_in_exam = models.BooleanField(
        default=True,
        verbose_name="Mostrar en examen",
        help_text="Si está activo, la rúbrica se incluye al imprimir el examen"
    )
    position = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Orden"
    )

    class Meta:
        verbose_name = "Rúbrica de examen"
        verbose_name_plural = "Rúbricas de examen"
        ordering = ['position', 'id']
        unique_together = ('exam', 'rubric')

    def __str__(self):
        return f"{self.exam} — {self.rubric.title}"


class BaseFormatoImpresionFields(models.Model):
    FONT_CHOICES = [
        ('Arial', 'Arial'),
        ('Times New Roman', 'Times New Roman'),
        ('Calibri', 'Calibri'),
        ('Helvetica', 'Helvetica'),
    ]

    PAPER_SIZE_CHOICES = [
        ('A4', 'A4 (21,0 x 29,7 cm)'),
        ('Carta', 'Carta / Letter (21,6 x 27,9 cm)'),
        ('Oficio', 'Oficio / Legal (21,6 x 33,0 cm)'),
    ]

    fuente = models.CharField(max_length=50, choices=FONT_CHOICES, default='Arial')
    tamano_fuente = models.PositiveSmallIntegerField(default=11)
    interlineado = models.FloatField(default=1.15)
    tamano_hoja = models.CharField(max_length=10, choices=PAPER_SIZE_CHOICES, default='A4')

    margen_superior_cm = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)
    margen_inferior_cm = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)
    margen_izquierdo_cm = models.DecimalField(max_digits=5, decimal_places=2, default=2.50)
    margen_derecho_cm = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)

    color_titulo = models.CharField(max_length=7, blank=True, default='')
    color_texto = models.CharField(max_length=7, blank=True, default='')

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        for field_name in ['color_titulo', 'color_texto']:
            value = getattr(self, field_name, '') or ''
            if value and (len(value) != 7 or not value.startswith('#')):
                raise ValidationError({field_name: 'Debe usar formato hex #RRGGBB'})


class FormatoImpresion(BaseFormatoImpresionFields):
    nombre = models.CharField(max_length=120)
    es_default = models.BooleanField(default=False, verbose_name='Predeterminado')
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='formatos_impresion'
    )
    institution = models.ForeignKey(
        InstitutionV2,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='formatos_impresion'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Formato de impresión'
        verbose_name_plural = 'Formatos de impresión'
        ordering = ['nombre']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'es_default'],
                condition=models.Q(es_default=True, user__isnull=False, institution__isnull=True),
                name='unique_default_print_format_per_user'
            ),
            models.UniqueConstraint(
                fields=['institution', 'es_default'],
                condition=models.Q(es_default=True, institution__isnull=False, user__isnull=True),
                name='unique_default_print_format_per_institution'
            ),
            models.UniqueConstraint(
                fields=['es_default'],
                condition=models.Q(es_default=True, user__isnull=True, institution__isnull=True),
                name='unique_default_print_format_global'
            ),
        ]

    def clean(self):
        super().clean()
        if self.user_id and self.institution_id:
            raise ValidationError('El formato no puede pertenecer a usuario e institución al mismo tiempo.')

    def __str__(self):
        return self.nombre


class FormatoImpresionAsignado(BaseFormatoImpresionFields):
    exam = models.OneToOneField(
        Exam,
        on_delete=models.CASCADE,
        related_name='formato_impresion_asignado'
    )
    formato_base = models.ForeignKey(
        FormatoImpresion,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='formatos_asignados'
    )
    nombre_snapshot = models.CharField(max_length=120, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Formato de impresión asignado'
        verbose_name_plural = 'Formatos de impresión asignados'

    def __str__(self):
        return self.nombre_snapshot or f'Formato examen {self.exam_id}'

    @classmethod
    def crear_desde_formato(cls, exam, formato):
        return cls.objects.create(
            exam=exam,
            formato_base=formato,
            nombre_snapshot=formato.nombre,
            tamano_hoja=formato.tamano_hoja,
            fuente=formato.fuente,
            tamano_fuente=formato.tamano_fuente,
            interlineado=formato.interlineado,
            margen_superior_cm=formato.margen_superior_cm,
            margen_inferior_cm=formato.margen_inferior_cm,
            margen_izquierdo_cm=formato.margen_izquierdo_cm,
            margen_derecho_cm=formato.margen_derecho_cm,
            color_titulo=formato.color_titulo,
            color_texto=formato.color_texto,
        )


class RubricLevel(models.Model):
    """Columna de la grilla (ej: 4, 3, 2, 1 o Excelente, Bien, etc.)"""
    rubric = models.ForeignKey(
        Rubric,
        on_delete=models.CASCADE,
        related_name='levels',
        verbose_name="Rúbrica"
    )
    label = models.CharField(max_length=100, verbose_name="Etiqueta")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Nivel de rúbrica"
        ordering = ['order']

    def __str__(self):
        return f"{self.rubric.title} — {self.label}"


class RubricCriterion(models.Model):
    """Fila de la grilla (ej: Preparación, Recursos, etc.)"""
    rubric = models.ForeignKey(
        Rubric,
        on_delete=models.CASCADE,
        related_name='criteria',
        verbose_name="Rúbrica"
    )
    name = models.CharField(max_length=255, verbose_name="Criterio")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Criterio de rúbrica"
        ordering = ['order']

    def __str__(self):
        return f"{self.rubric.title} — {self.name}"


class RubricCell(models.Model):
    """Descriptor textual para una intersección criterio × nivel."""
    criterion = models.ForeignKey(
        RubricCriterion,
        on_delete=models.CASCADE,
        related_name='cells',
        verbose_name="Criterio"
    )
    level = models.ForeignKey(
        RubricLevel,
        on_delete=models.CASCADE,
        related_name='cells',
        verbose_name="Nivel"
    )
    description = models.TextField(blank=True, verbose_name="Descripción")

    class Meta:
        verbose_name = "Celda de rúbrica"
        unique_together = ('criterion', 'level')

    def __str__(self):
        return f"{self.criterion} × {self.level.label}"


# ---------------------------------------------------------------------------
# Helpers de cifrado para API keys
# ---------------------------------------------------------------------------
import base64
import hashlib

def _get_fernet():
    """Devuelve una instancia Fernet derivada del SECRET_KEY de Django."""
    from django.conf import settings
    from cryptography.fernet import Fernet
    raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw))

def encrypt_api_key(plaintext: str) -> str:
    if not plaintext:
        return ''
    return _get_fernet().encrypt(plaintext.encode()).decode()

def decrypt_api_key(ciphertext: str) -> str:
    if not ciphertext:
        return ''
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except Exception:
        return ''


# ---------------------------------------------------------------------------
# Configuración de IA Institucional
# ---------------------------------------------------------------------------
class InstitutionAIConfig(models.Model):
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI (GPT-4o, GPT-4, etc.)'),
        ('anthropic', 'Anthropic (Claude 3, etc.)'),
        ('openai_compatible', 'Compatible con OpenAI (Groq, Mistral, OpenRouter…)'),
    ]

    institution = models.OneToOneField(
        InstitutionV2,
        on_delete=models.CASCADE,
        related_name='ai_config',
        verbose_name="Institución",
    )
    provider = models.CharField(
        max_length=30,
        choices=PROVIDER_CHOICES,
        verbose_name="Proveedor",
    )
    api_key_encrypted = models.TextField(
        blank=True,
        verbose_name="API Key (cifrada)",
    )
    model = models.CharField(
        max_length=100,
        # Sin default hardcodeado a propósito (ver ai_router.py: ya no rellena
        # ningún modelo de fallback) — el admin tiene que escribir el nombre
        # exacto y vigente que indica el proveedor. blank=False (default de
        # CharField) hace que Django Admin lo exija al guardar.
        verbose_name="Modelo",
    )
    base_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="URL base",
        help_text="Solo para endpoints compatibles con OpenAI (ej. Groq, OpenRouter).",
    )
    is_active = models.BooleanField(default=True, verbose_name="Activa")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración IA Institucional"
        verbose_name_plural = "Configuraciones IA Institucionales"

    def __str__(self):
        return f"{self.institution.name} → {self.get_provider_display()}"

    @property
    def api_key(self):
        return decrypt_api_key(self.api_key_encrypted)

    @api_key.setter
    def api_key(self, value):
        self.api_key_encrypted = encrypt_api_key(value)


# ---------------------------------------------------------------------------
# Configuración de IA por Usuario
# ---------------------------------------------------------------------------
class UserAIConfig(models.Model):
    SOURCE_CHOICES = [
        ('shared_demo', 'IA de prueba gratuita de EducaApp (limitada)'),
        ('ollama_local', 'IA Local (Ollama)'),
        ('byok', 'Mi propia API Key (BYOK)'),
        ('institutional', 'Configuración de la Institución'),
    ]
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI (GPT-4o, GPT-4, etc.)'),
        ('gemini', 'Google Gemini (Gemini 1.5 Flash / Pro)'),
        ('anthropic', 'Anthropic (Claude 3, etc.)'),
        ('groq', 'Groq (Llama, Mixtral)'),
        ('mistral', 'Mistral AI'),
        ('openrouter', 'OpenRouter'),
        ('openai_compatible', 'Compatible con OpenAI (URL personalizada)'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='ai_config',
        verbose_name="Usuario",
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='ollama_local',
        verbose_name="Fuente de IA",
    )
    # Campos BYOK
    provider = models.CharField(
        max_length=30,
        choices=PROVIDER_CHOICES,
        blank=True,
        verbose_name="Proveedor",
    )
    api_key_encrypted = models.TextField(blank=True, verbose_name="API Key (cifrada)")
    model = models.CharField(
        max_length=100,
        blank=True,  # opcional a nivel de base: solo aplica cuando source='byok'
        # Sin default hardcodeado a propósito (ver ai_router.py) — cuando
        # source='byok' se exige explícitamente en clean() más abajo.
        verbose_name="Modelo",
    )
    base_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="URL base",
        help_text="Solo para endpoints compatibles con OpenAI.",
    )
    ollama_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="URL de Ollama",
        help_text="URL del servidor Ollama. Por defecto: http://192.168.12.236:11434",
    )
    # Institutional
    institution = models.ForeignKey(
        InstitutionV2,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Institución",
        related_name='ai_user_configs',
    )

    class Meta:
        verbose_name = "Configuración IA de Usuario"
        verbose_name_plural = "Configuraciones IA de Usuarios"

    def __str__(self):
        return f"{self.user.username} → {self.get_source_display()}"

    def clean(self):
        super().clean()
        # 'model' es blank=True a nivel de base porque no aplica a
        # shared_demo/ollama_local/institutional — pero si el usuario eligió
        # traer su propia key (byok), hace falta sí o sí (sin esto, ai_router.py
        # manda un modelo vacío a la API). Corre vía full_clean() — Django
        # Admin lo llama solo; la vista propia (ai_config_view) valida lo
        # mismo a mano antes de guardar, ver ahí.
        if self.source == 'byok':
            if not self.provider:
                raise ValidationError({'provider': 'Falta elegir un proveedor para "Mi propia API Key".'})
            if not self.model:
                raise ValidationError({'model': 'Falta indicar el modelo — no hay uno por defecto, hay que escribirlo o buscarlo.'})

    @property
    def api_key(self):
        return decrypt_api_key(self.api_key_encrypted)

    @api_key.setter
    def api_key(self, value):
        self.api_key_encrypted = encrypt_api_key(value) if value else ''


# ---------------------------------------------------------------------------
# Configuración de IA global de demo (fallback, solo editable desde Django Admin)
# ---------------------------------------------------------------------------
class GlobalAIConfig(models.Model):
    """
    Config de IA compartida a nivel de todo el sistema, usada como último
    fallback automático cuando un usuario no tiene proveedor propio
    configurado y el Ollama local no está disponible.
    Solo visible/editable desde Django Admin (superuser) — no aparece en
    ninguna pantalla de la aplicación.
    """
    provider = models.CharField(max_length=30, default='gemini', verbose_name="Proveedor")
    # blank=False (default de CharField) a propósito: es el único fallback
    # automático que le queda al sistema (ver ai_router.py, que ya no rellena
    # ningún modelo por su cuenta) — Django Admin lo exige al guardar.
    model = models.CharField(max_length=100, verbose_name="Modelo")
    api_key_encrypted = models.TextField(blank=True, verbose_name="API Key (cifrada)")
    is_active = models.BooleanField(default=True, verbose_name="Activa")
    updated_at = models.DateTimeField(auto_now=True)

    # Último cupo conocido, tomado de los headers de rate-limit que devuelve el
    # proveedor en cada llamada real de generación (hoy solo Groq expone RPD/TPM
    # ahí). Se actualiza en cada uso — no es una consulta activa, es "lo último
    # que sabemos" desde la última pregunta generada con este fallback.
    quota_checked_at = models.DateTimeField(null=True, blank=True, verbose_name="Cupo verificado")
    quota_remaining_requests = models.IntegerField(null=True, blank=True, verbose_name="Solicitudes restantes")
    quota_limit_requests = models.IntegerField(null=True, blank=True, verbose_name="Límite de solicitudes")
    quota_requests_reset_at = models.DateTimeField(null=True, blank=True, verbose_name="Reinicio de solicitudes")
    quota_remaining_tokens = models.IntegerField(null=True, blank=True, verbose_name="Tokens restantes (ventana)")
    quota_limit_tokens = models.IntegerField(null=True, blank=True, verbose_name="Límite de tokens (ventana)")

    class Meta:
        verbose_name = "Configuración IA Global (demo)"
        verbose_name_plural = "Configuración IA Global (demo)"

    def __str__(self):
        return f"Demo global → {self.provider} ({'activa' if self.is_active else 'inactiva'})"

    @property
    def api_key(self):
        return decrypt_api_key(self.api_key_encrypted)

    @api_key.setter
    def api_key(self, value):
        self.api_key_encrypted = encrypt_api_key(value) if value else ''


# ---------------------------------------------------------------------------
# Monitoreo del fallback compartido de Groq (test de carga programado)
# ---------------------------------------------------------------------------
class GroqMonitorSchedule(models.Model):
    """
    Fila única (singleton) que controla el monitoreo periódico del fallback de
    Groq. No depende de ningún cron externo: se dispara desde adentro de la
    propia app cada vez que llega una request a /health/ (que UptimeRobot ya
    pinguea regularmente para evitar que Render duerma el free tier) — si pasó
    más de `interval_minutes` desde la última corrida, dispara una nueva en un
    thread de background sin bloquear la respuesta del health check.
    """
    enabled = models.BooleanField(default=False, verbose_name="Activo")
    interval_minutes = models.PositiveIntegerField(default=60, verbose_name="Intervalo (minutos)")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Iniciado")
    ends_at = models.DateTimeField(null=True, blank=True, verbose_name="Se apaga solo")
    last_run_at = models.DateTimeField(null=True, blank=True, verbose_name="Última corrida")

    class Meta:
        verbose_name = "Monitoreo de Groq — configuración"
        verbose_name_plural = "Monitoreo de Groq — configuración"

    def __str__(self):
        return f"Monitoreo Groq ({'activo' if self.enabled else 'inactivo'})"


class GroqMonitorRun(models.Model):
    """Resultado de una corrida individual del test de carga contra Groq."""
    # default=timezone.now (no auto_now_add) a propósito: las corridas
    # automáticas se guardan primero en un buffer local (ver
    # groq_monitor.sync_buffer_to_db) y se insertan acá recién en la
    # sincronización periódica (4 veces/día) — auto_now_add pisaría ese
    # valor con la hora de la sincronización en vez de la hora real de la
    # corrida, rompiendo el análisis de cadencia por tiempo.
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Fecha")
    model_name = models.CharField(max_length=150, blank=True, verbose_name="Modelo")
    success = models.BooleanField(default=False, verbose_name="Corrida sin errores")
    target_questions = models.PositiveIntegerField(default=30, verbose_name="Preguntas pedidas")
    total_generated = models.PositiveIntegerField(default=0, verbose_name="Preguntas generadas")
    met_target = models.BooleanField(default=False, verbose_name="Cumplió el objetivo")
    empty_questions = models.PositiveIntegerField(default=0, verbose_name="Preguntas vacías")
    duplicate_questions = models.PositiveIntegerField(default=0, verbose_name="Preguntas duplicadas")
    failed_chunks = models.PositiveIntegerField(default=0, verbose_name="Fragmentos fallidos")
    fixture = models.CharField(max_length=20, default='easy', verbose_name="Documento usado")
    elapsed_seconds = models.FloatField(null=True, blank=True, verbose_name="Duración (seg)")
    reason = models.CharField(max_length=100, blank=True, verbose_name="Motivo de falla")
    detail = models.TextField(blank=True, verbose_name="Detalle")
    quota_remaining_requests = models.IntegerField(null=True, blank=True)
    quota_limit_requests = models.IntegerField(null=True, blank=True)
    quota_remaining_tokens = models.IntegerField(null=True, blank=True)
    quota_limit_tokens = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Monitoreo de Groq — corrida"
        verbose_name_plural = "Monitoreo de Groq — corridas"

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} — {'OK' if self.met_target else 'ALERTA'} ({self.total_generated}/{self.target_questions})"


class QuestionGenerationConfig(models.Model):
    """
    Fila única (singleton) con el prompt usado para generar preguntas con IA
    (ver material/views_document_processor.py::_generate_questions_for_chunk),
    editable desde Administración → "Prompt de generación IA" — no desde
    Django Admin, para que cualquier admin de la app lo pueda ajustar sin
    necesitar esas credenciales.

    El template usa placeholders estilo str.format() (ver
    material/ai_prompts.py::PROMPT_PLACEHOLDERS) — si el texto guardado
    tiene un placeholder inválido o se rompe el formato, el código cae al
    default de fábrica en vez de fallar la generación.
    """
    prompt_template = models.TextField(verbose_name="Prompt (con placeholders)")
    temperature = models.FloatField(default=0.2, verbose_name="Temperature")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Prompt de generación IA"
        verbose_name_plural = "Prompt de generación IA"

    def __str__(self):
        return f"Prompt de generación IA (actualizado {self.updated_at:%d/%m/%Y %H:%M})"


class GroqVisionTestRun(models.Model):
    """
    Resultado de una prueba manual de un modelo de Groq con soporte de
    imágenes (visión). No usa GlobalAIConfig — se prueba un modelo puntual
    contra la key ya guardada ahí, sin cambiar cuál es el modelo de texto
    activo para el fallback de demo real.
    """
    # Ver comentario en GroqMonitorRun.created_at — mismo motivo.
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Fecha")
    model_name = models.CharField(max_length=150, verbose_name="Modelo")
    success = models.BooleanField(default=False, verbose_name="Corrida sin errores")
    response_text = models.TextField(blank=True, verbose_name="Respuesta del modelo")
    # Si el modelo efectivamente "leyó" el gráfico de prueba (contiene los
    # valores esperados) — None cuando success=False (no aplica).
    content_check_passed = models.BooleanField(null=True, blank=True, verbose_name="Leyó bien la imagen")
    error = models.TextField(blank=True, verbose_name="Error")
    elapsed_seconds = models.FloatField(null=True, blank=True, verbose_name="Duración (seg)")
    quota_remaining_requests = models.IntegerField(null=True, blank=True)
    quota_limit_requests = models.IntegerField(null=True, blank=True)
    quota_remaining_tokens = models.IntegerField(null=True, blank=True)
    quota_limit_tokens = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Monitoreo de Groq — prueba de visión"
        verbose_name_plural = "Monitoreo de Groq — pruebas de visión"

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} — {self.model_name} ({'OK' if self.success else 'ERROR'})"


class VisionMonitorSchedule(models.Model):
    """
    Fila única (singleton) que controla la corrida cíclica del modelo de
    visión ya elegido (ver GroqVisionTestRun) — mismo patrón que
    GroqMonitorSchedule, pero para medir cupo/cadencia de renovación de un
    modelo con imágenes en vez de carga de texto.
    """
    enabled = models.BooleanField(default=False, verbose_name="Activo")
    provider = models.CharField(max_length=30, default='gemini', verbose_name="Proveedor")
    model = models.CharField(max_length=150, default='gemini-2.5-flash', verbose_name="Modelo")
    interval_minutes = models.PositiveIntegerField(default=60, verbose_name="Intervalo (minutos)")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Iniciado")
    ends_at = models.DateTimeField(null=True, blank=True, verbose_name="Se apaga solo")
    last_run_at = models.DateTimeField(null=True, blank=True, verbose_name="Última corrida")

    class Meta:
        verbose_name = "Monitoreo de visión — configuración"
        verbose_name_plural = "Monitoreo de visión — configuración"

    def __str__(self):
        return f"Monitoreo visión ({'activo' if self.enabled else 'inactivo'}) — {self.provider}/{self.model}"


# --- GRUPOS DE CONFIANZA (compartir preguntas entre docentes) ------------------
# Ver [[project_onboarding_seed_content_plan]] / Fase D: reemplaza el diseño
# original "compartir por institución" (parking lot) porque Question no tiene
# ningún vínculo real a Institution. La relación de confianza es explícita:
# grupo -> miembros (con invitación/aceptación) -> materias compartidas por
# cada miembro dentro de ese grupo.

class SharingGroup(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nombre del grupo")
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='created_sharing_groups',
        verbose_name="Creado por",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Grupo de confianza"
        verbose_name_plural = "Grupos de confianza"
        ordering = ['name']

    def __str__(self):
        return self.name


class GroupMembership(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('accepted', 'Aceptada'),
        ('rejected', 'Rechazada'),
    ]

    group = models.ForeignKey(
        SharingGroup, on_delete=models.CASCADE, related_name='memberships',
        verbose_name="Grupo",
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='group_memberships',
        verbose_name="Usuario",
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name="Estado",
    )
    invited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='sent_group_invites',
        verbose_name="Invitado por",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('group', 'user')
        verbose_name = "Membresía de grupo"
        verbose_name_plural = "Membresías de grupo"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} en {self.group.name} ({self.get_status_display()})"


class ContentShare(models.Model):
    """
    Reemplaza a SubjectShare y RubricShare con un único modelo de "compartir"
    (ver informe de rediseño del catálogo — elegiste una tabla genérica en
    vez de una por tipo). No hay migración de datos porque no había nada
    que preservar (reset de base acordado, ver Fase 4).

    Es un híbrido a propósito, no 100% genérico objeto-por-objeto:
      - kind='materia': usa `subject` — comparte automáticamente TODOS los
        Temas/Unidades/Preguntas de `shared_by` etiquetados a esa materia
        (una regla, no fila por fila — así funciona hoy y es el modelo
        mental que ya se usa).
      - kind='rubrica' / 'plantilla' / 'formato': usa `content_type` +
        `object_id` (GenericForeignKey) — apunta a un objeto puntual
        (Rubric / ExamTemplate / FormatoImpresion).
    """
    KIND_CHOICES = [
        ('materia', 'Materia (temas y preguntas)'),
        ('rubrica', 'Rúbrica'),
        ('plantilla', 'Plantilla de examen'),
        ('formato', 'Formato de impresión'),
    ]

    group = models.ForeignKey(
        SharingGroup, on_delete=models.CASCADE, related_name='content_shares',
        verbose_name="Grupo",
    )
    shared_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='content_shares',
        verbose_name="Compartido por",
    )
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, verbose_name="Tipo")

    # kind='materia'
    subject = models.ForeignKey(
        'Subject', on_delete=models.CASCADE, null=True, blank=True,
        related_name='group_shares', verbose_name="Materia",
    )

    # kind en rubrica/plantilla/formato
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True,
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    shared_object = GenericForeignKey('content_type', 'object_id')

    is_active = models.BooleanField(default=True, verbose_name="Activa")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Contenido compartido"
        verbose_name_plural = "Contenidos compartidos"
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'shared_by', 'subject'],
                condition=models.Q(kind='materia'),
                name='unique_materia_share',
            ),
            models.UniqueConstraint(
                fields=['group', 'shared_by', 'content_type', 'object_id'],
                condition=~models.Q(kind='materia'),
                name='unique_object_share',
            ),
        ]

    def __str__(self):
        target = self.subject.name if self.kind == 'materia' else str(self.shared_object)
        return f"{self.shared_by.username} comparte {target} ({self.kind}) con {self.group.name}"


class Favorite(models.Model):
    """
    Marca genérica de "favorito" por usuario, aplicable a cualquier modelo
    (Exam, ExamVersionBatch, ExamTemplate, Subject, etc.) vía ContentType,
    para no necesitar un campo/tabla propia por cada entidad.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'content_type', 'object_id')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} ★ {self.content_type.model}#{self.object_id}"
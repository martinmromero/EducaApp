from pathlib import Path
import os

# Cargar variables de entorno desde .env si existe
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(Path(__file__).resolve().parent.parent, '.env'))
except ImportError:
    pass  # python-dotenv no instalado; usar variables del sistema

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-d-@xe!&5f3#io6!3ach#f3!k$3uj6%7)42gc$0)7@cbpbj%++b'
)
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
# Mantenés tu línea intacta para no romper la lectura de Render
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h.strip()]

# Le sumás tus dominios explícitos de forma segura (se anexan a la lista anterior)
ALLOWED_HOSTS.extend(['educaapp.vercel.app', 'localhost', '127.0.0.1'])

# Configurás la lista de confianza para el login (CSRF)
CSRF_TRUSTED_ORIGINS = ['https://educaapp.onrender.com', 'https://educaapp.vercel.app']

# URL pública de la app (Vercel actúa de redirect proxy hacia Render). Se usa
# para armar links que se comparten fuera de la app (ej. invitaciones), para
# que siempre apunten al dominio público en vez del host real de Render.
PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL', 'https://educaapp.vercel.app')

# Usuario técnico dueño de todo el contenido semilla/demo del sistema
# (instituciones, materias y preguntas de ejemplo no borrables). Se crea via
# la migración de datos material/migrations/0042_seed_content_user.py.
SEED_CONTENT_USERNAME = 'educaapp_demo'

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'material.apps.MaterialConfig',
    'django_extensions',
    'rest_framework', 
    'crispy_forms',
    'crispy_bootstrap5',

]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"  # Si usas Bootstrap
CRISPY_TEMPLATE_PACK = "bootstrap5"  # Si usas Bootstrap

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # ONBOARDING WIZARD V2 — ROLLBACK: eliminar esta línea
    'material.middleware.OnboardingGateMiddleware',
]

ROOT_URLCONF = 'educaapp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'material/templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # ONBOARDING WIZARD — ROLLBACK: eliminar esta línea
                'material.context_processors.onboarding_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'educaapp.wsgi.application'

# Database — usa PostgreSQL (DATABASE_URL) en producción, SQLite en desarrollo
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es-ar'  # Cambiado a español argentina
TIME_ZONE = 'America/Argentina/Buenos_Aires'  # Zona horaria Argentina
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static'),
                    os.path.join(BASE_DIR, 'material/static'),]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ---------------------------------------------------------------------------
# Límites de contenidos/IA (pensados para el plan gratuito de Render: 1 solo
# worker gunicorn, ~512MB de RAM y timeout de 120s por request. Ver análisis
# en el chat del 2026-07-27 para el detalle de por qué estos números).
# ---------------------------------------------------------------------------
CONTENIDO_MAX_UPLOAD_MB = 8
CONTENIDO_MAX_TOTAL_TOKENS = 50_000   # aviso: documento entero muy extenso, mejor generar por capítulos
CONTENIDO_MAX_RUN_TOKENS = 45_000     # tope duro por corrida de generación (~15 chunks de 3000 tokens)
CONTENIDO_MAX_PAGES = 2000            # techo de sanity (PDF corrupto/patológico), no un límite de "tamaño de libro"
CONTENIDO_PAGES_PER_CHAPTER_BLOCK = 40  # sin TOC: partir el libro en bloques de esta cantidad de páginas

# Default primary key field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication settings
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend' 
]

# Login/Logout settings
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Email settings (para desarrollo)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Custom user model (opcional, si en el futuro necesitas personalizar)
# AUTH_USER_MODEL = 'material.CustomUser'

# Session settings
SESSION_COOKIE_AGE = 1209600  # 2 semanas en segundos
# False (default de Django): un request que solo LEE la sesión (ej. cualquier
# vista con @login_required, que ya toca la sesión para resolver request.user)
# no la vuelve a guardar. Con True, todo request la regrababa igual, incluso
# sin cambios — si ese request cargó la sesión ANTES de que otro request
# concurrente le escribiera una clave nueva (ej. subir un documento), su save
# posterior pisaba esa escritura con la copia vieja. Reproducido en vivo:
# subir un PDF justo después de cargar el dashboard (mientras sus fetches
# iniciales, ej. checkLocalAIStatus(), todavía están en vuelo) podía borrar
# session['doc_processor'] silenciosamente, y "Generar preguntas" caía al
# preview truncado a 6000 caracteres en vez del contenido completo. Ver
# [[project_pdf_inspector_evaluation]]. Los varios `request.session.modified
# = True` explícitos en el código (ver doc_processor, security setup, etc.)
# siguen garantizando el guardado real cuando SÍ hay una escritura.
SESSION_SAVE_EVERY_REQUEST = False

# Security settings (para cuando DEBUG=False)
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # Render termina SSL antes del dyno
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]  # Para archivos durante desarrollo
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
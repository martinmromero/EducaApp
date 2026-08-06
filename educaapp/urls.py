from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from material.views import (
    CustomLoginView, index, health_check, service_worker,
    password_reset_request, password_reset_question, password_reset_new,
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    path('sw.js', service_worker, name='service_worker'),

    # Configuración corregida de accounts
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    # Recuperación de contraseña sin email, por pregunta de seguridad (ver
    # Profile.security_question) — no reemplaza el flujo de
    # django.contrib.auth.urls incluido abajo, solo es lo que enlaza el
    # link "¿Olvidó su contraseña?" del login.
    path('accounts/recuperar/', password_reset_request, name='password_reset_request'),
    path('accounts/recuperar/pregunta/', password_reset_question, name='password_reset_question'),
    path('accounts/recuperar/nueva-clave/', password_reset_new, name='password_reset_new'),
    path('accounts/', include('django.contrib.auth.urls')),  # Esto incluirá las demás URLs de auth

    path('', include('material.urls')),
    path('', index, name='index'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from material.views import CustomLoginView, index  # Asegúrate de que CustomLoginView esté importado

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Configuración corregida de accounts
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('accounts/', include('django.contrib.auth.urls')),  # Esto incluirá las demás URLs de auth
    
    path('', include('material.urls')),
    path('', index, name='index'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
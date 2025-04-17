from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from material.views import CustomLoginView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/login/', CustomLoginView.as_view(), name='login'),  # Usar la vista personalizada de login
    path('', include('material.urls')),

]

# Solo agregamos las rutas de archivos multimedia si estamos en modo DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
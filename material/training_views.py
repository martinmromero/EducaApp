"""
Vistas del Área de Pruebas — entrar/salir/restablecer la cuenta espejo de
práctica de cada docente. La lógica de dominio (crear, clonar, borrar,
resetear) vive en material/training_accounts.py; acá solo el manejo de
sesión/login() y los chequeos de permisos.
"""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .training_accounts import get_or_create_training_account, reset_training_account
from .views import is_admin

SESSION_ACTING_AS_TRAINING_FOR = 'acting_as_training_for'
_LOGIN_BACKEND = 'django.contrib.auth.backends.ModelBackend'


@login_required
@require_POST
def entrar_area_pruebas(request):
    real_user = request.user
    training_user = get_or_create_training_account(real_user)
    login(request, training_user, backend=_LOGIN_BACKEND)
    # login() flushea/cicla la sesión al cambiar de usuario (protección
    # contra session fixation) — la marca se setea DESPUÉS, si no se
    # perdería en ese flush.
    request.session[SESSION_ACTING_AS_TRAINING_FOR] = real_user.id
    # extra_tags='area_pruebas_modal' a propósito: no pasa por el banner de
    # mensajes normal (ver base.html) — ahí ya se muestra el banner fijo
    # de "Estás en el Área de Pruebas" y se pisaban los dos. Este mensaje
    # se muestra como modal en vez de eso.
    messages.success(
        request,
        'Ingresó al Área de Pruebas. Todo lo que se haga aquí queda separado de la cuenta real.',
        extra_tags='area_pruebas_modal',
    )
    return redirect('material:index')


@login_required
@require_POST
def salir_area_pruebas(request):
    real_user_id = request.session.get(SESSION_ACTING_AS_TRAINING_FOR)
    if not real_user_id:
        return redirect('material:index')

    real_user = get_object_or_404(User, pk=real_user_id)
    # Nunca se confía solo en el entero guardado en sesión para decidir a
    # qué cuenta volver — se revalida siempre contra TrainingAccountLink,
    # la única fuente de verdad de qué cuenta espejo es de quién.
    link = getattr(real_user, 'training_link', None)
    if link is None or link.training_user_id != request.user.id:
        raise PermissionDenied

    login(request, real_user, backend=_LOGIN_BACKEND)
    messages.success(request, 'Volvió a la cuenta real.', extra_tags='general')
    return redirect('material:index')


@login_required
@require_POST
def restablecer_area_pruebas(request):
    # Solo se puede restablecer estando DENTRO del Área de Pruebas — nunca
    # se dispara solo ni automáticamente.
    if not request.session.get(SESSION_ACTING_AS_TRAINING_FOR):
        raise PermissionDenied
    reset_training_account(request.user)
    messages.success(
        request,
        'Área de Pruebas restablecida: todo lo que se había creado allí se borró y se repuso el contenido de ejemplo.',
        extra_tags='area_pruebas_modal',
    )
    return redirect('material:index')


@user_passes_test(is_admin, login_url='/')
@require_POST
def admin_restablecer_area_pruebas(request, user_id):
    real_user = get_object_or_404(User, pk=user_id)
    link = getattr(real_user, 'training_link', None)
    if link is None:
        # Nunca se crea un Área de Pruebas desde el lado admin — si el
        # usuario nunca la pidió, no hay nada que resetear.
        messages.error(request, f'{real_user.username} todavía no tiene Área de Pruebas creada.', extra_tags='usuarios')
        return redirect('material:user_list')

    reset_training_account(link.training_user)
    messages.success(request, f'Área de Pruebas de {real_user.username} restablecida.', extra_tags='usuarios')
    return redirect('material:user_list')

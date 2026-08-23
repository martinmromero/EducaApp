"""
Vistas del "Modo Testing" — panel lateral derecho, colapsable, que le muestra
a un tester marcado (`profile.is_tester`) el checklist de UAT paso a paso
mientras navega la app real, y le deja registrar el resultado sin salir de
la pantalla en la que está. Ver Plan de Pruebas EducaApp (memoria
project_uat_testing_plan) para el contenido del checklist.

Separado de views.py, mismo criterio que training_views.py: es un
subsistema chico y autocontenido, no vale la pena mezclarlo con el resto.
"""
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse
from django.views.decorators.http import require_POST

from .models import TEST_STAGE_CHOICES, TestChecklistItem, TestResult
from .views import is_admin

SESSION_TESTING_MODE_ACTIVE = 'testing_mode_active'
SESSION_TESTING_CURRENT_INDEX = 'testing_panel_current_index'


def _resolve_url(name):
    """target_url_name se guarda sin namespace — la mayoría vive bajo
    material:, un puñado (login, password_reset_request) en el urlconf raíz."""
    if not name:
        return None
    for candidate in (f'material:{name}', name):
        try:
            return reverse(candidate)
        except NoReverseMatch:
            continue
    return None


def _visible_items(user):
    qs = TestChecklistItem.objects.all()
    if not is_admin(user):
        qs = qs.exclude(admin_only=True)
    stage = user.profile.test_stage
    if stage:
        # stage=None en el ítem = transversal, aparece para cualquier etapa
        # asignada (Alta y primer acceso, Apariencia, Administración).
        qs = qs.filter(Q(stage__isnull=True) | Q(stage=stage))
    return qs


def _item_payload(item, result):
    return {
        'id': item.id,
        'area_number': item.area_number,
        'area_name': item.area_name,
        'text': item.text,
        'target_url': _resolve_url(item.target_url_name),
        'admin_only': item.admin_only,
        'status': result.status if result else 'pendiente',
        'comment': result.comment if result else '',
    }


def _state_payload(request, index=None):
    items = list(_visible_items(request.user))
    total = len(items)
    if total == 0:
        return {'total': 0, 'index': 0, 'item': None}

    if index is None:
        index = request.session.get(SESSION_TESTING_CURRENT_INDEX, 0)
    index = max(0, min(index, total - 1))
    request.session[SESSION_TESTING_CURRENT_INDEX] = index

    item = items[index]
    result = TestResult.objects.filter(user=request.user, item=item).first()

    done = TestResult.objects.filter(
        user=request.user, item__in=items,
    ).exclude(status='pendiente').count()

    return {
        'total': total,
        'index': index,
        'done': done,
        'item': _item_payload(item, result),
    }


@login_required
@require_POST
def toggle_testing_mode(request):
    if not request.user.profile.is_tester:
        return redirect('material:index')
    active = not request.session.get(SESSION_TESTING_MODE_ACTIVE, False)
    request.session[SESSION_TESTING_MODE_ACTIVE] = active
    next_url = request.POST.get('next') or 'material:index'
    try:
        return redirect(next_url)
    except Exception:
        return redirect('material:index')


@login_required
def testing_panel_state(request):
    if not request.user.profile.is_tester or not request.session.get(SESSION_TESTING_MODE_ACTIVE):
        return JsonResponse({'active': False})
    return JsonResponse({'active': True, **_state_payload(request)})


@login_required
@require_POST
def testing_panel_navigate(request):
    if not request.user.profile.is_tester or not request.session.get(SESSION_TESTING_MODE_ACTIVE):
        return JsonResponse({'active': False}, status=403)

    current = request.session.get(SESSION_TESTING_CURRENT_INDEX, 0)
    direction = request.POST.get('direction')
    if direction == 'prev':
        current -= 1
    elif direction == 'next':
        current += 1
    else:
        try:
            current = int(request.POST.get('index', current))
        except (TypeError, ValueError):
            pass

    return JsonResponse({'active': True, **_state_payload(request, index=current)})


@login_required
@require_POST
def testing_panel_save(request):
    if not request.user.profile.is_tester or not request.session.get(SESSION_TESTING_MODE_ACTIVE):
        return JsonResponse({'active': False}, status=403)

    item_id = request.POST.get('item_id')
    status = request.POST.get('status', 'pendiente')
    comment = request.POST.get('comment', '').strip()

    valid_statuses = dict(TestResult.STATUS_CHOICES)
    if status not in valid_statuses:
        return JsonResponse({'success': False, 'error': 'Resultado inválido'}, status=400)

    item = _visible_items(request.user).filter(pk=item_id).first()
    if item is None:
        return JsonResponse({'success': False, 'error': 'Ítem no encontrado'}, status=404)

    TestResult.objects.update_or_create(
        user=request.user, item=item,
        defaults={'status': status, 'comment': comment},
    )
    return JsonResponse({'success': True, **_state_payload(request)})


@login_required
@user_passes_test(is_admin, login_url='/')
def testing_admin_results(request):
    results = (
        TestResult.objects
        .select_related('user', 'item')
        .exclude(status='pendiente')
        .order_by('item__area_number', 'item__order', 'user__username')
    )
    total_items = TestChecklistItem.objects.count()
    return render(request, 'material/testing_admin_results.html', {
        'results': results,
        'total_items': total_items,
    })

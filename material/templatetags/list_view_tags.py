from django import template

from ..list_columns import LIST_REGISTRY, resolve_config

register = template.Library()


@register.simple_tag(takes_context=True)
def list_view_config(context, list_key):
    """Vista elegida por el usuario para un listado (ver list_columns.py).
    Se resuelve acá y no en cada view para no tocar las views de listado; el
    Profile ya viene cacheado en request.user por el middleware de
    onboarding, así que no suma una consulta."""
    if list_key not in LIST_REGISTRY:
        raise template.TemplateSyntaxError('Listado sin registrar: %s' % list_key)
    request = context.get('request')
    profile = None
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        try:
            profile = user.profile
        except Exception:
            profile = None
    return resolve_config(profile, list_key)

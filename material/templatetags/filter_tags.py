from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Permite hacer dict[key] en templates cuando key es una variable."""
    if mapping is None:
        return None
    return mapping.get(key)

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Permite hacer dict[key] en templates cuando key es una variable."""
    if mapping is None:
        return None
    return mapping.get(key)


# Clave: el caracter peligroso. Valor: su escape de JSON escrito a mano
# (barra invertida literal + u + hex), por eso las barras dobles.
_JSON_EMBED_ESCAPES = {
    '<': '\\u003c',
    '>': '\\u003e',
    '&': '\\u0026',
    '\u2028': '\\u2028',
    '\u2029': '\\u2029',
}


@register.filter
def json_embed(value):
    """Para embeber JSON ya serializado (json.dumps) dentro de un <script>.

    json.dumps no escapa "</script>": un nombre, título o texto de pregunta
    que lo contenga cierra el script y ejecuta lo que siga (XSS almacenado).
    Esto reemplaza <, > y & (y los separadores de línea unicode) por su
    escape de JSON (barra, "u" y cuatro dígitos hexadecimales). Sigue siendo
    JSON y JavaScript válido, porque dentro de un string se decodifica al
    mismo carácter, y ya no puede cerrar la etiqueta. Reemplaza al |safe en
    esos casos.
    """
    text = '' if value is None else str(value)
    for char, escaped in _JSON_EMBED_ESCAPES.items():
        text = text.replace(char, escaped)
    return mark_safe(text)

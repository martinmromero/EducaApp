from django import template
from django.contrib.messages import get_messages

register = template.Library()

@register.simple_tag(takes_context=True)
def get_filtered_messages(context, categories=None):
    """
    Template tag para obtener mensajes filtrados por categorías.
    
    Uso:
    {% get_filtered_messages as all_messages %}
    {% get_filtered_messages "general" as general_messages %}
    """
    request = context['request']
    # get_messages(request) devuelve el storage de Django UNA sola vez por
    # request — iterarlo (list(...)) lo marca "leído" y Django lo descarta
    # al final de la respuesta, sin importar si el mensaje fue realmente
    # mostrado. base.html llama {% show_messages "general" %} en TODA
    # página; si otra vista renderizaba (sin redirigir) una plantilla con
    # {% show_messages "otra_categoria" %} propia, la llamada de base.html
    # consumía el storage completo primero y el mensaje de "otra_categoria"
    # se perdía en silencio (nunca se mostraba en ningún lado) — hallazgo de
    # la auditoría 2026-09-11 (institución con sede duplicada no mostraba
    # ningún error). Fix: cachear la lista materializada en el `request`, así
    # todas las llamadas a este tag dentro del mismo render comparten la
    # MISMA lista ya extraída, en vez de re-consumir (vacío) el storage.
    if not hasattr(request, '_message_tags_cache'):
        request._message_tags_cache = list(get_messages(request))
    messages_list = request._message_tags_cache

    if categories:
        # Convertir la cadena de categorías en una lista
        if isinstance(categories, str):
            category_list = [cat.strip() for cat in categories.split(',')]
        else:
            category_list = [categories]
        
        # Filtrar mensajes por categorías
        filtered_messages = []
        for message in messages_list:
            # Si no tiene extra_tags, se considera "general"
            message_tags = message.extra_tags if message.extra_tags else 'general'
            message_categories = [tag.strip() for tag in message_tags.split(',')]
            
            # Si alguna categoría del mensaje coincide con las solicitadas
            if any(cat in category_list for cat in message_categories):
                filtered_messages.append(message)
        
        return filtered_messages
    else:
        return messages_list


@register.inclusion_tag('material/components/messages.html', takes_context=True)
def show_messages(context, categories=None):
    """
    Template tag de inclusión para mostrar mensajes filtrados.
    """
    filtered_messages = get_filtered_messages(context, categories)
    return {'messages': filtered_messages}

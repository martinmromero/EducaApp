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
    messages = get_messages(request)
    
    # Convertir el iterador a lista para poder usar múltiples veces
    messages_list = list(messages)
    
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


@register.filter
def has_messages_for_category(messages, category):
    """
    Filtro para verificar si hay mensajes para una categoría específica.
    """
    for message in messages:
        message_tags = message.extra_tags if message.extra_tags else 'general'
        message_categories = [tag.strip() for tag in message_tags.split(',')]
        if category in message_categories:
            return True
    return False
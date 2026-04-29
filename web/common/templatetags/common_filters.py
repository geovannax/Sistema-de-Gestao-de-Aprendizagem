from django import template

register = template.Library()

@register.filter
def get_attr(obj, attr):
    """
    Obtém o atributo de um objeto dinamicamente.
    Se for um campo de data, formata como d/m/Y.
    """
    value = getattr(obj, attr, '')    
    
    return value

@register.filter
def get_attr_with_truncate(obj, attr, max_length=70):
    """
    Obtém o atributo de um objeto dinamicamente.
    Se for um campo de data, formata como d/m/Y.
    """
    value = getattr(obj, attr, '')    
    if isinstance(value, str) and len(value) > max_length:
        return value[:max_length-3] + '...'
    return value


@register.filter
def get_model_only_fields(obj, only_fields):
    """
    Obtém os campos de um modelo Django, filtrando apenas
    os campos especificados em only_fields.
    """
    return [
        (field.verbose_name, field)
        for field in obj._meta.fields
        if field.name in only_fields
    ]

@register.filter
def get_item(obj, key):
    """Pega um atributo dinâmico do objeto"""
    try:
        if hasattr(obj, key):
            return getattr(obj, key)
        return obj.get(key) if isinstance(obj, dict) else '-'
    except:
        return '-'


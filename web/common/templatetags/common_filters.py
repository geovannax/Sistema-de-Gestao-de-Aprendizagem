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
def get_model_only_fields(obj, only_fields):
    """
    Obtém os campos de um modelo Django, filtrando apenas
    os campos especificados em only_fields.
    """
    return [
        (field.verbose_name, getattr(obj, field.name))
        for field in obj._meta.fields
        if field.name in only_fields
    ]

@register.filter
def archived_groups_is_archived_by(group, user):
    """
    Verifica se um grupo foi arquivado por um usuário específico.
    Uso: {{ group|archived_groups_is_archived_by:request.user }}
    """
    return group.archived_groups.filter(user=user, is_archived=True).exists()

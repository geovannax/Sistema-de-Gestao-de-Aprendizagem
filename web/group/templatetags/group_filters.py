from django import template

register = template.Library()

@register.filter
def archived_groups_is_archived_by(group, user):
    """
    Verifica se um grupo foi arquivado por um usuário específico.
    Uso: {{ group|archived_groups_is_archived_by:request.user }}
    """
    return group.archived_groups.filter(user=user, is_archived=True).exists()

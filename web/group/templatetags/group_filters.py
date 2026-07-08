from __future__ import annotations

from django import template
from django.contrib.auth.models import User

from group.models import Group

register = template.Library()


@register.filter
def archived_groups_is_archived_by(group: Group, user: User) -> bool:
    """Verifica se um grupo foi arquivado por um usuário específico.

    Args:
        group: Instância da turma a verificar.
        user: Usuário cujo arquivamento será consultado.

    Returns:
        ``True`` se o usuário arquivou esta turma e o flag ainda está ativo.

    Example:
        ``{{ group|archived_groups_is_archived_by:request.user }}``
    """
    return group.archived_groups.filter(user=user, is_archived=True).exists()

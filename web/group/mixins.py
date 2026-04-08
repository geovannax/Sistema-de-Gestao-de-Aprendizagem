from django.db.models import Q, QuerySet
from group.models import Group


class GroupAccessMixin:
    """Mixin para retornar turmas criadas + compartilhadas ativas"""
    
    def get_queryset(self) -> QuerySet:
        """
        Retorna os grupos que o usuário tem acesso,
        seja como criador ou por compartilhamento
        """
        return Group.objects.filter(
            Q(created_by=self.request.user) | Q(sharings__shared_with=self.request.user)
        ).distinct().order_by('-id')

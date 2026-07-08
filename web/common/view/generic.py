"""View genérica de listagem aprimorada para o projeto.

Centraliza autenticação, filtragem, ordenação, tipo de visualização,
paginação e enriquecimento de ações em uma única classe base reutilizável.
"""
from __future__ import annotations

from typing import Any

from common.mixins import ActionsMixin, FilteringMixin, NavigationMixin, OrderingMixin, ViewTypeMixin
from django.db.models import QuerySet
from django.views.generic import ListView


class EnhancedListView(
    NavigationMixin,
    FilteringMixin,
    OrderingMixin,
    ViewTypeMixin,
    ActionsMixin,
    ListView
):
    """ListView com filtragem, ordenação, tipo de visualização e ações de UI.

    Combina os mixins de ``common.mixins`` em uma única classe base para
    todas as listagens do projeto. As subclasses obrigatoriamente definem:

    - ``model``: modelo Django da listagem.
    - ``allowed_fields``: campos pesquisáveis e ordenáveis.
    - ``page_title``: título exibido no cabeçalho da página.

    Atributos opcionais:
        create_url: Nome da URL de criação (ex: ``'group:create'``).
        detail_url: Nome da URL de detalhe (ex: ``'group:detail'``).
        page_description: Subtítulo descritivo da página.
        paginate_by: Itens por página. Padrão: ``10``.

    O template padrão é ``global/partials/generic/list/view.html``, que
    utiliza o contexto gerado por ``get_context_data`` para renderizar
    tabela ou cards conforme a preferência do usuário.
    """
    create_url = None
    detail_url = None
    page_description = None
    page_title = None
    paginate_by = 10
    template_name = 'global/partials/generic/list/view.html'

    def get_queryset(self) -> QuerySet:
        """Retorna o queryset com filtragem aplicada.

        Delega a filtragem a :meth:`~common.mixins.FilteringMixin.apply_filtering`
        após obter o queryset base do ``ListView`` (que já aplica ``ordering``).

        Returns:
            QuerySet filtrado conforme os parâmetros de busca ativos.
        """
        queryset = super().get_queryset()
        queryset = self.apply_filtering(queryset)
        return queryset

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Monta o contexto completo da listagem.

        Adiciona ao contexto padrão do ``ListView``:
        - ``page_title`` e ``page_description``
        - ``create_url`` e ``detail_url``
        - ``view_type`` (preferência de visualização do usuário)
        - Flags de filtro e ordenação ativos (``has_filtering_session``,
          ``has_ordering_session``)

        Returns:
            Dicionário de contexto pronto para o template de listagem.
        """
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': self.page_title,
            'page_description': self.page_description,
            'create_url': self.create_url,
            'detail_url': self.detail_url,
            'view_type': self.get_view_type(),
            **self.has_filtering(return_context=True),
            **self.has_ordering(return_context=True),
        })
        return context

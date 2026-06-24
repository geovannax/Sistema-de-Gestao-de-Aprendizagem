"""Utilitários compartilhados entre os apps do projeto."""
from __future__ import annotations


def get_btn_action(action: list[str], app_name: str) -> list[dict[str, str] | None]:
    """Retorna a configuração de botões de ação para um ou mais tipos de operação.

    Cada tipo de ação mapeia para um dicionário com URL nomeada, método HTTP,
    ícone Bootstrap Icons e classe CSS. Usado por
    :class:`~common.mixins.EnrichObjectMixin` para injetar ``ui_actions``
    em cada objeto de uma listagem.

    Args:
        action: Lista de identificadores de ação (ex: ``['update', 'delete']``).
            Ações reconhecidas: ``'archive'``, ``'delete'``, ``'unshare'``,
            ``'update'``, ``'assign_update'``.
        app_name: Namespace do app usado para construir a URL nomeada
            (ex: ``'group'`` → ``'group:update'``).

    Returns:
        Lista de dicionários com as chaves ``url``, ``method``, ``icon`` e
        ``class``. Ações não reconhecidas resultam em ``None`` na posição
        correspondente da lista.

    Raises:
        ValueError: Se ``action`` não for uma lista.

    Example:
        >>> get_btn_action(['update', 'delete'], 'group')
        [
            {'url': 'group:update', 'method': 'get', 'icon': 'bi-pencil', 'class': 'btn-outline-primary'},
            {'url': 'group:delete', 'method': 'get', 'icon': 'bi-trash', 'class': 'btn-outline-danger'},
        ]
    """
    if not isinstance(action, list):
        raise ValueError("O parâmetro 'action' deve ser uma lista.")

    actions = {
        'archive': {
            'url': f'{app_name}:archive',
            'method': 'post',
            'icon': 'bi-inbox',
            'class': 'btn-outline-success',
        },
        'delete': {
            'url': f'{app_name}:delete',
            'method': 'get',
            'icon': 'bi-trash',
            'class': 'btn-outline-danger',
        },
        'unshare': {
            'url': f'{app_name}:unshare',
            'method': 'post',
            'icon': 'bi-trash',
            'class': 'btn-outline-danger',
        },
        'update': {
            'url': f'{app_name}:update',
            'method': 'get',
            'icon': 'bi-pencil',
            'class': 'btn-outline-primary',
        },
        'assign_update': {
            'url': f'{app_name}:assign_update',
            'method': 'get',
            'icon': 'bi-pencil',
            'class': 'btn-outline-primary',
        },
    }

    return [actions.get(act) for act in action]

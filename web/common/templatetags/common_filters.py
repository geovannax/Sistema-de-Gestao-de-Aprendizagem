"""Filtros de template reutilizáveis do app common."""
from __future__ import annotations
from django import template

register = template.Library()


@register.filter
def get_attr(obj: object, attr: str) -> object:
    """Retorna o valor de um atributo de um objeto pelo nome.

    Args:
        obj: Objeto de qualquer tipo.
        attr: Nome do atributo a ser lido.

    Returns:
        Valor do atributo ou string vazia se não existir.
    """
    return getattr(obj, attr, '')


@register.filter
def get_attr_with_truncate(obj: object, attr: str, max_length: int = 70) -> object:
    """Retorna o atributo de um objeto truncado se exceder o comprimento máximo.

    Args:
        obj: Objeto de qualquer tipo.
        attr: Nome do atributo a ser lido.
        max_length: Comprimento máximo antes de truncar. Padrão: ``70``.

    Returns:
        Valor do atributo; se for string e exceder ``max_length``, retorna
        os primeiros ``max_length - 3`` caracteres seguidos de ``'...'``.
    """
    value = getattr(obj, attr, '')
    if isinstance(value, str) and len(value) > max_length:
        return value[:max_length - 3] + '...'
    return value


@register.filter
def get_model_only_fields(obj: object, only_fields: list[str]) -> list[tuple[str, object]]:
    """Retorna os campos de um modelo Django filtrados por nome.

    Útil para renderizar dinamicamente apenas os campos selecionados
    de um objeto de modelo nos templates de listagem.

    Args:
        obj: Instância de modelo Django (com ``_meta.fields``).
        only_fields: Lista ou conjunto de nomes de campos a incluir.

    Returns:
        Lista de tuplas ``(verbose_name, field)`` para cada campo cujo
        nome esteja em ``only_fields``.
    """
    return [
        (field.verbose_name, field)
        for field in obj._meta.fields  # type: ignore[attr-defined]
        if field.name in only_fields
    ]


@register.filter
def get_item(obj: object, key: str) -> object:
    """Acessa um valor em um dicionário ou atributo em um objeto pelo nome.

    Tenta primeiro ``getattr``; se o atributo não existir, tenta ``dict.get``.
    Retorna ``'-'`` como fallback seguro para uso em templates.

    Args:
        obj: Dicionário ou objeto Python.
        key: Chave do dicionário ou nome do atributo.

    Returns:
        Valor encontrado ou ``'-'`` se não existir.
    """
    try:
        if hasattr(obj, key):
            return getattr(obj, key)
        return obj.get(key) if isinstance(obj, dict) else '-'
    except:  # pragma: no cover
        return '-'

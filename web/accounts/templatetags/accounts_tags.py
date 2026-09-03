"""Template tags do app accounts."""
from __future__ import annotations

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def pop_login_view_mode(context) -> str:
    """Consome (lê e remove) o papel a forçar no viewMode do localStorage.

    ``accounts.signals.on_login`` grava ``request.session['login_view_mode']``
    com o ``role`` do usuário logo após o login. Precisa ser um template tag
    — e não um context processor — porque templates internos do allauth
    (ex.: a mensagem "login realizado com sucesso") também são renderizados
    dentro do mesmo request via ``render_to_string``; um context processor
    rodaria (e consumiria a chave) nesses renders internos antes do
    ``base_template.html`` chegar a usá-la.

    Args:
        context: Contexto do template, usado para acessar ``request``.

    Returns:
        ``'professor'``, ``'aluno'`` ou string vazia.
    """
    request = context['request']
    return request.session.pop('login_view_mode', '') or ''

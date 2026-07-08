"""Middleware do app accounts."""
from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse


class CookieMiddleware:
    """Aplica cookies pendentes e remove cookies marcados para exclusão.

    Permite que views e signals escrevam em ``request._set_cookies``
    (dicionário ``{chave: valor}``) ou em ``request._delete_cookies``
    (lista de chaves) para que este middleware aplique as mudanças na
    resposta HTTP, sem acoplamento direto ao objeto ``response``.

    Registrado em ``MIDDLEWARE`` no ``settings.py``.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Processa a requisição e aplica/remove cookies na resposta.

        Args:
            request: Requisição HTTP Django.

        Returns:
            HttpResponse com os cookies adicionados e/ou removidos.
        """
        response = self.get_response(request)

        cookies_to_set = getattr(request, '_set_cookies', {})
        for key, value in cookies_to_set.items():
            response.set_cookie(
                key,
                value,
                max_age=365 * 24 * 3600,
                httponly=True,
                samesite='Lax'
            )

        cookies_to_delete = getattr(request, '_delete_cookies', [])
        for key in cookies_to_delete:
            response.delete_cookie(key)

        return response

"""Signals do app accounts.

Conecta os eventos de login e logout do Django Auth a comportamentos
específicos do projeto: exibição de mensagem de boas-vindas, restauração
de cookies de preferência no login e limpeza desses cookies no logout.
"""
from __future__ import annotations

from typing import Any

from accounts.models import UserPreferences
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.http import HttpRequest


@receiver(user_logged_in)
def on_login(sender: type, request: HttpRequest, user: User, **kwargs: Any) -> None:
    """Exibe mensagem de boas-vindas e restaura cookies de preferência.

    Garante que a sessão seja criada imediatamente (workaround necessário
    para que o ``CookieMiddleware`` possa acessar os cookies). Em seguida,
    carrega as preferências salvas e sinaliza ao middleware via
    ``request._set_cookies`` para restaurar os cookies do usuário.

    Args:
        sender: Classe que disparou o signal.
        request: Requisição HTTP do login.
        user: Usuário que acabou de autenticar.
    """
    # WORKAROUND: forçar a criação da sessão para garantir que o middleware possa acessar os cookies
    request.session['versao'] = '2'
    messages.success(request, f'Bem-vindo, {user.get_full_name()}!')
    if user_prefs := UserPreferences.objects.filter(user=user).first():
        request._set_cookies = {}
        for cookie_key, cookie_value in user_prefs.preferences.get('cookies', {}).items():
            request._set_cookies.update({cookie_key: cookie_value})

        if user_prefs.role:
            # Consumido uma única vez por accounts.templatetags.accounts_tags
            # ::pop_login_view_mode, na primeira página renderizada após o
            # login, para forçar o viewMode do localStorage a refletir o
            # papel salvo no banco.
            request.session['login_view_mode'] = user_prefs.role


@receiver(user_logged_out)
def on_logout(sender: type, request: HttpRequest, user: User, **kwargs: Any) -> None:
    """Remove cookies de preferência do navegador ao fazer logout.

    Sinaliza ao ``CookieMiddleware`` via ``request._delete_cookies`` para
    remover todos os cookies de preferência salvos pelo usuário.

    Args:
        sender: Classe que disparou o signal.
        request: Requisição HTTP do logout.
        user: Usuário que está saindo.
    """
    if user_prefs := UserPreferences.objects.filter(user=user).first():
        request._delete_cookies = [
            cookie_key
            for cookie_key, _ in user_prefs.preferences.get('cookies', {}).items()
        ]

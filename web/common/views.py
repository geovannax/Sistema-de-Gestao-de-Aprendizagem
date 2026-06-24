"""Views globais do projeto: landing page, home e handlers de erro."""
from __future__ import annotations
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView


class LandingPage(TemplateView):
    """Página inicial pública do sistema.

    Acessível sem autenticação. Exibe a apresentação do produto e
    links para login/cadastro.
    """
    template_name = 'global/partials/landing.html'


class HomeView(LoginRequiredMixin, TemplateView):
    """Dashboard inicial para usuários autenticados.

    Redireciona para login se o usuário não estiver autenticado.
    """
    template_name = 'global/partials/home.html'


def permission_denied(request: HttpRequest, exception: Exception | None = None) -> HttpResponse:
    """Handler para erros HTTP 403 (acesso negado).

    Registrado em ``core/urls.py`` como ``handler403``. Renderiza o
    template ``global/partials/403.html`` com status 403.

    Args:
        request: Requisição HTTP.
        exception: Exceção que gerou o 403 (opcional).

    Returns:
        HttpResponse com status 403 e o template de erro.
    """
    return render(request, 'global/partials/403.html', status=403)


def page_not_found(request: HttpRequest, exception: Exception | None = None) -> HttpResponse:
    """Handler para erros HTTP 404 (página não encontrada).

    Registrado em ``core/urls.py`` como ``handler404``. Renderiza o
    template ``global/partials/404.html`` com status 404.

    Args:
        request: Requisição HTTP.
        exception: Exceção que gerou o 404 (opcional).

    Returns:
        HttpResponse com status 404 e o template de erro.
    """
    return render(request, 'global/partials/404.html', status=404)

"""Adapter allauth para login social.

Login via Google vincula direto (por e-mail) a um ``User`` já existente. Se
não existir, o allauth cai no formulário de cadastro (``SocialSignupForm``),
onde o usuário escolhe o próprio papel (Professor/Aluno) e a conta é criada
ali — sem convite, aprovação ou restrição de domínio.
"""
from __future__ import annotations

from typing import Any

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialLogin
from django.contrib.auth.models import User
from django.http import HttpRequest

from accounts.models import UserPreferences


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Vincula contas Google a ``User`` existente por e-mail; senão, cadastra."""

    def pre_social_login(self, request: HttpRequest, sociallogin: SocialLogin) -> None:
        """Vincula ``sociallogin`` a um ``User`` existente com o mesmo e-mail.

        Chamado pelo allauth logo após a autenticação bem-sucedida no
        provedor, antes do login ser processado. Se não houver ``User`` com
        o e-mail retornado pelo Google, não faz nada aqui — o allauth segue
        o fluxo normal e redireciona para o formulário de cadastro.

        Args:
            request: Requisição HTTP em andamento.
            sociallogin: Login social em processamento.
        """
        if sociallogin.is_existing:
            return

        email = sociallogin.user.email
        user = User.objects.filter(email__iexact=email).first() if email else None
        if user is not None:
            sociallogin.connect(request, user)

    def is_open_for_signup(self, request: HttpRequest, sociallogin: SocialLogin) -> bool:
        """Sempre permite cadastro via login social.

        Args:
            request: Requisição HTTP em andamento.
            sociallogin: Login social em processamento.

        Returns:
            Sempre ``True``.
        """
        return True

    def save_user(
        self,
        request: HttpRequest,
        sociallogin: SocialLogin,
        form: Any = None,
    ) -> User:
        """Cria o ``User`` e grava o papel escolhido no formulário de cadastro.

        Ignora um e-mail diferente que o usuário eventualmente tenha digitado
        no formulário: o ``User.email`` salvo é sempre o e-mail verificado
        pelo Google. Caso contrário, ``pre_social_login`` não acharia mais
        essa conta pelo e-mail em um próximo login (o lookup usa o e-mail do
        provedor, não o que foi digitado), e o usuário cairia de novo no
        cadastro, criando uma conta duplicada.

        Args:
            request: Requisição HTTP em andamento.
            sociallogin: Login social em processamento.
            form: ``SocialSignupForm`` preenchido, com o campo ``role``.

        Returns:
            O ``User`` recém-criado.
        """
        google_email = sociallogin.email_addresses[0].email if sociallogin.email_addresses else None

        user = super().save_user(request, sociallogin, form=form)

        if google_email and user.email != google_email:
            user.email = google_email
            user.save(update_fields=['email'])

        role = form.cleaned_data.get('role', '') if form else ''
        UserPreferences.objects.update_or_create(user=user, defaults={'role': role})
        return user

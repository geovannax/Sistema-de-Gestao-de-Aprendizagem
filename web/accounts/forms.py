"""Formulários do app accounts."""
from allauth.socialaccount.forms import SignupForm as BaseSocialSignupForm
from django import forms

from accounts.models import ROLE_CHOICES


class SocialSignupForm(BaseSocialSignupForm):
    """Formulário de cadastro via login social — pede o papel do usuário."""

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        label='Eu sou',
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['class'] = 'form-control'
        if 'email' in self.fields:
            # Somente leitura: o e-mail salvo é sempre o verificado pelo
            # Google (SocialAccountAdapter.save_user ignora o valor
            # submetido), então não faz sentido deixar editável.
            self.fields['email'].widget.attrs.update({
                'class': 'form-control',
                'readonly': 'readonly',
            })

"""Modelos do app accounts.

Estende o ``User`` padrão do Django com preferências persistidas em JSON,
eliminando a necessidade de migrações ao adicionar novas preferências.
"""
from django.db import models
from django.contrib.auth.models import User

ROLE_CHOICES = [
    ('professor', 'Professor'),
    ('aluno', 'Aluno'),
]


class UserPreferences(models.Model):
    """Preferências de usuário armazenadas em um único campo JSON.

    Vinculada ao ``User`` via OneToOne; criada sob demanda com
    ``get_or_create`` nos mixins que precisam persistir preferências
    (ex: tipo de visualização de lista).

    A estrutura interna do JSON é livre; a chave ``'cookies'`` armazena
    um mapeamento ``{cookie_key: value}`` sincronizado via
    :class:`~accounts.signals` no login e removido no logout.

    Attributes:
        user: Usuário Django ao qual as preferências pertencem.
        role: Papel escolhido pelo usuário (``ROLE_CHOICES``). Em branco para
            contas provisionadas antes da existência deste campo.
        preferences: Dicionário JSON com preferências arbitrárias.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, blank=True, default='')

    preferences = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def set_view_type(self, cookie_key: str, view_type: str) -> None:
        """Persiste a preferência de tipo de visualização para uma view específica.

        Args:
            cookie_key: Chave do cookie da view (ex: ``'groupactivelistview-view-type'``).
            view_type: Tipo de visualização (ex: ``'cards'`` ou ``'table'``).
        """
        if 'view_type' not in self.preferences:
            self.preferences['view_type'] = {}
        self.preferences['view_type'][cookie_key] = view_type
        self.save()

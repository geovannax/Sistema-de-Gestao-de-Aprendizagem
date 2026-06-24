"""Formulários do app group.

Contém o formulário de criação/edição de turmas e o formulário de
compartilhamento com outros professores via Select2.
"""
from __future__ import annotations
from django import forms
from django_select2.forms import ModelSelect2MultipleWidget
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from group.models import Group, GroupSharing


class GroupForm(forms.ModelForm):
    """Formulário para criação e edição de turmas.

    Remove a opção em branco do campo ``shift`` (RadioSelect) para
    forçar uma seleção explícita de turno.
    """

    class Meta:
        model = Group
        fields = ['name', 'shift', 'description']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ADS 2026.3.12'
            }),
            'description': forms.Textarea(
                attrs={
                'rows': 5,
                'class': 'form-control',
                'placeholder': 'Turma introdutória de algoritmos com foco em lógica de programação e resolução de problemas...'
            }),
            'shift': forms.RadioSelect(attrs={
                'class': 'radio-group'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove a opção vazia do campo de turno
        self.fields['shift'].choices = [
            choice for choice in self.fields['shift'].choices
            if choice[0] != ''
        ]


class GroupSharingWidget(ModelSelect2MultipleWidget):
    """Widget Select2 para seleção de professores no compartilhamento de turmas.

    Pesquisa por ``username`` ou ``email`` e exibe o nome de usuário como
    rótulo. Injeta um mapeamento JSON de usuários no atributo ``data-users``
    para uso no template.
    """
    search_fields = [
        "username__icontains",
        "email__icontains",
    ]

    def label_from_instance(self, obj: User) -> str:
        """Retorna o ``username`` do usuário como rótulo da opção."""
        return obj.username

    def get_context(self, name: str, value: object, attrs: dict) -> dict:
        """Adiciona o mapeamento ``data-users`` (JSON) ao contexto do widget.

        O mapeamento associa cada ``user.id`` ao nome completo ou username,
        permitindo ao JavaScript exibir informações adicionais no Select2.
        """
        context = super().get_context(name, value, attrs)

        import json
        users_data = {}
        for user in User.objects.all():
            users_data[str(user.id)] = {
                'fullname': user.get_full_name() or user.username,
            }

        context['widget']['attrs']['data-users'] = json.dumps(users_data)
        return context


class GroupSharingForm(forms.Form):
    """Formulário para compartilhar uma turma com outros professores.

    Exclui do queryset o próprio usuário e usuários que já possuem
    compartilhamento ativo com a turma.

    Args:
        group_pk: PK da turma a ser compartilhada. Obrigatório.
        request_user: Usuário que está compartilhando. Obrigatório.

    Raises:
        ValidationError: Se ``group_pk`` ou ``request_user`` não forem informados.
    """
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=GroupSharingWidget(attrs={
            'data-placeholder': 'Digite o nome de usuário',
            'class': 'form-control',
        }),
        required=False
    )

    def __init__(self, group_pk: int | None = None, request_user: User | None = None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        if group_pk is None:
            raise ValidationError('group_pk é obrigatório')

        if request_user is None:
            raise ValidationError('request_user é obrigatório')

        if group_pk:
            # Usuários que já têm compartilhamento ativo com este grupo
            excluded_users = GroupSharing.objects.filter(
                group_id=group_pk,
                is_active=True
            ).values_list('shared_with_id', flat=True)

            # Excluir do queryset
            self.fields['users'].queryset = User.objects.exclude(
                id__in=excluded_users
            ).exclude(
                id=request_user.id
            )

"""Formulários de criação, edição e vinculação de listas de atividades."""
from __future__ import annotations
from activity.models import ActivityList, ActivityListGroup
from django import forms
from django.contrib.auth.models import User
from django.db.models import Q, QuerySet
from django_select2.forms import ModelSelect2MultipleWidget
from group.models import Group
import json


class ActivityListForm(forms.ModelForm):
    """Formulário para criação e edição de uma lista de atividades.

    Campos expostos: ``title``, ``description`` e ``max_attempts``.
    Os demais campos (``created_by``, ``is_published``, etc.) são
    preenchidos automaticamente pela view.
    """
    class Meta:
        model = ActivityList
        fields = ['title', 'description', 'max_attempts', 'manual_grading']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Lista 01 - Logica de Programacao',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descreva o objetivo desta lista...',
            }),
            'max_attempts': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Ex: 3 (deixe em branco para ilimitado)',
            }),
            'manual_grading': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }


class ActivityAssignWidget(ModelSelect2MultipleWidget):
    """Widget Select2 para seleção de turmas no formulário de vinculação.

    Filtra o queryset para exibir apenas turmas do usuário autenticado
    ou compartilhadas com ele, excluindo turmas deletadas.
    """
    search_fields = [
        'name__icontains',
        'description__icontains',
    ]

    def label_from_instance(self, obj):
        """Retorna o nome da turma como rótulo da opção."""
        return obj.name

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        return context

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):  # pragma: no cover
        queryset = super().filter_queryset(request, term, queryset, **dependent_fields)

        if not request.user.is_authenticated:
            return queryset.none()

        return queryset.filter(
            Q(created_by=request.user) |
            Q(sharings__shared_with=request.user, sharings__is_active=True),
            deleted_at__isnull=True,
        ).distinct()


class ActivityAssignForm(forms.Form):
    """Formulário para vincular uma atividade a uma ou mais turmas.

    Permite definir período de disponibilidade (``starts_at``/``ends_at``) e
    selecionar turmas individualmente ou marcar ``bind_all_groups`` para
    vincular a todas as turmas disponíveis do usuário.

    Raises:
        ValidationError: Se ``ends_at`` for anterior a ``starts_at``.
    """
    starts_at = forms.DateTimeField(
        label='Inicio',
        required=False,
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control',
        })
    )
    ends_at = forms.DateTimeField(
        label='Fim',
        required=False,
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control',
        })
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.filter(deleted_at__isnull=True),
        widget=ActivityAssignWidget(attrs={
            'data-placeholder': 'Digite o nome da turma para vincular',
            'class': 'form-control',
        }),
        required=False
    )
    bind_all_groups = forms.BooleanField(
        label='Vincular a todas as turmas disponiveis',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )

    def clean(self):
        """Valida que o fim não seja anterior ao início do período."""
        cleaned_data = super().clean()
        starts_at = cleaned_data.get('starts_at')
        ends_at = cleaned_data.get('ends_at')

        if starts_at and ends_at and ends_at < starts_at:
            raise forms.ValidationError(
                'A data de fim deve ser posterior ou igual a data de inicio.'
            )

        return cleaned_data

    def get_available_groups(self, request_user: User | None) -> QuerySet[Group]:
        """Retorna as turmas disponíveis para o usuário vincular.

        Inclui turmas criadas pelo usuário e turmas compartilhadas com ele,
        excluindo turmas deletadas.

        Args:
            request_user: Usuário autenticado da requisição.

        Returns:
            QuerySet de :class:`~group.models.Group` disponíveis, ou
            ``Group.objects.none()`` se o usuário não estiver autenticado.
        """
        if request_user is None or not request_user.is_authenticated:
            return Group.objects.none()

        return (
            Group.objects
            .filter(
                Q(created_by=request_user) |
                Q(sharings__shared_with=request_user, sharings__is_active=True),
                deleted_at__isnull=True,
            )
            .distinct()
        )

    def __init__(self, request_user: User | None = None, *args, **kwargs) -> None:
        """Inicializa o formulário filtrando turmas disponíveis para o usuário.

        Args:
            request_user: Usuário autenticado; usado para filtrar o queryset
                de turmas e preencher o atributo ``data-groups`` do widget.
        """
        super().__init__(*args, **kwargs)

        groups = self.get_available_groups(request_user)

        if not groups.exists():
            self.fields['groups'].queryset = groups
            self.fields['groups'].widget.attrs['data-groups'] = '{}'
            return

        self.fields['groups'].queryset = groups
        self.fields['groups'].widget.attrs['data-groups'] = json.dumps({
            str(group.id): {
                'group': group.name,
                'description': group.description,
            }
            for group in groups
        })


class ActivityListGroupPeriodForm(forms.ModelForm):
    """Formulário para editar o período de disponibilidade de uma atividade vinculada.

    Permite ajustar ``starts_at`` e ``ends_at`` de um :class:`~activity.models.ActivityListGroup`
    já existente. O campo ``due_date`` é atualizado automaticamente pela view.

    Raises:
        ValidationError: Se ``ends_at`` for anterior a ``starts_at``.
    """
    class Meta:
        model = ActivityListGroup
        fields = ['starts_at', 'ends_at']
        widgets = {
            'starts_at': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control',
                }
            ),
            'ends_at': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control',
                }
            ),
        }
        labels = {
            'starts_at': 'Inicio',
            'ends_at': 'Fim',
        }

    def __init__(self, *args, **kwargs):
        """Configura o formato de input e o valor inicial dos campos de data."""
        super().__init__(*args, **kwargs)

        for field_name in ['starts_at', 'ends_at']:
            self.fields[field_name].input_formats = ['%Y-%m-%dT%H:%M']
            value = getattr(self.instance, field_name, None)
            if value:
                self.fields[field_name].initial = value.strftime('%Y-%m-%dT%H:%M')

    def clean(self):
        """Valida que o fim não seja anterior ao início do período."""
        cleaned_data = super().clean()
        starts_at = cleaned_data.get('starts_at')
        ends_at = cleaned_data.get('ends_at')

        if starts_at and ends_at and ends_at < starts_at:
            raise forms.ValidationError(
                'A data de fim deve ser posterior ou igual a data de inicio.'
            )

        return cleaned_data

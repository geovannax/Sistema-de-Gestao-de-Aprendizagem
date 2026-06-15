from activity.models import ActivityList, ActivityListGroup
from django import forms
from django.db.models import Q
from django_select2.forms import ModelSelect2MultipleWidget
from group.models import Group
import json


class ActivityListForm(forms.ModelForm):
    class Meta:
        model = ActivityList
        fields = ['title', 'description']
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
        }


class ActivityAssignWidget(ModelSelect2MultipleWidget):
    search_fields = [
        'name__icontains',
        'description__icontains',
    ]

    def label_from_instance(self, obj):
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
        cleaned_data = super().clean()
        starts_at = cleaned_data.get('starts_at')
        ends_at = cleaned_data.get('ends_at')

        if starts_at and ends_at and ends_at < starts_at:
            raise forms.ValidationError(
                'A data de fim deve ser posterior ou igual a data de inicio.'
            )

        return cleaned_data

    def get_available_groups(self, request_user):
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

    def __init__(self, request_user=None, *args, **kwargs):
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
        super().__init__(*args, **kwargs)

        for field_name in ['starts_at', 'ends_at']:
            self.fields[field_name].input_formats = ['%Y-%m-%dT%H:%M']
            value = getattr(self.instance, field_name, None)
            if value:
                self.fields[field_name].initial = value.strftime('%Y-%m-%dT%H:%M')

    def clean(self):
        cleaned_data = super().clean()
        starts_at = cleaned_data.get('starts_at')
        ends_at = cleaned_data.get('ends_at')

        if starts_at and ends_at and ends_at < starts_at:
            raise forms.ValidationError(
                'A data de fim deve ser posterior ou igual a data de inicio.'
            )

        return cleaned_data

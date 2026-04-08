from django import forms
from django_select2.forms import ModelSelect2MultipleWidget
from django.contrib.auth.models import User
from group.models import Group, GroupSharing


class GroupForm(forms.ModelForm):
    
    class Meta:
        model = Group
        fields = ['name', 'description']
        
        labels = {
            'name': 'Nome da Turma',
            'description': 'Descrição',
        }

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
            }),
        }


class GroupSharingWidget(ModelSelect2MultipleWidget):
    search_fields = [
        "username__icontains",
        "email__icontains",
    ]


class GroupSharingForm(forms.Form):
    """Formulário para compartilhar grupos com usuários"""
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=GroupSharingWidget(attrs={
            'data-placeholder': 'Digite o nome ou email...',
            'class': 'form-control',
        }),
        label='Adicionar Usuários',
        required=False
    )

    def __init__(self, group_pk=None, request_user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

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


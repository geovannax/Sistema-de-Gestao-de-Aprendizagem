from django import forms
from django_select2.forms import ModelSelect2MultipleWidget
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from group.models import Group, GroupSharing


class GroupForm(forms.ModelForm):

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
    search_fields = [
        "username__icontains",
        "email__icontains",
    ]
    
    def label_from_instance(self, obj):
        return obj.username
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        
        # Adiciona mapeamento de usuários como JSON
        import json
        users_data = {}
        for user in User.objects.all():
            users_data[str(user.id)] = {
                'fullname': user.get_full_name() or user.username,
            }
        
        context['widget']['attrs']['data-users'] = json.dumps(users_data)
        return context


class GroupSharingForm(forms.Form):
    """Formulário para compartilhar grupos com usuários"""
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=GroupSharingWidget(attrs={
            'data-placeholder': 'Digite o nome de usuário',
            'class': 'form-control',
        }),
        required=False
    )

    def __init__(self, group_pk=None, request_user=None, *args, **kwargs):
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


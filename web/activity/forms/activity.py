from activity.models import ActivityList
from django import forms
from django_select2.forms import ModelSelect2MultipleWidget
from group.models import Group
import json

class ActivityListForm(forms.ModelForm):
    class Meta:
        model = ActivityList
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Lista 01 — Lógica de Programação'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descreva o objetivo desta lista...'}),
        }


class ActivityAssignWidget(ModelSelect2MultipleWidget):
    search_fields = [
        "name__icontains",
    ]
    
    def label_from_instance(self, obj):
        return obj.name
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        
        groups_data = {}
        for group in Group.objects.all():
            groups_data[str(group.id)] = {
                'group': group.name,
                'description': group.description,
            }
        
        context['widget']['attrs']['data-groups'] = json.dumps(groups_data)
        return context


class ActivityAssignForm(forms.Form):
    """Formulário para vincular atividade com turmas"""
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=ActivityAssignWidget(attrs={
            'data-placeholder': 'Digite o nome da turma para vincular',
            'class': 'form-control',
        }),
        required=False
    )

    # def __init__(self, group_pk=None, request_user=None, *args, **kwargs):
    #     super().__init__(*args, **kwargs)

    #     if group_pk is None:
    #         raise ValidationError('group_pk é obrigatório')
        
    #     if request_user is None:
    #         raise ValidationError('request_user é obrigatório')

    #     if group_pk:
    #         # Usuários que já têm compartilhamento ativo com este grupo
    #         excluded_users = GroupSharing.objects.filter(
    #             group_id=group_pk,
    #             is_active=True
    #         ).values_list('shared_with_id', flat=True)
            
    #         # Excluir do queryset
    #         self.fields['users'].queryset = User.objects.exclude(
    #             id__in=excluded_users
    #         ).exclude(
    #             id=request_user.id
    #         )


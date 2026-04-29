from activity.models import ActivityList, Exercise, ExerciseOption, CompleteCodeExercise, MultipleChoiceExercise
from django import forms


class ActivityListForm(forms.ModelForm):
    class Meta:
        model = ActivityList
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Lista 01 — Lógica de Programação'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descreva o objetivo desta lista...'}),
        }




# class CodeExerciseForm(forms.ModelForm):
#     class Meta:
#         model = CodeExercise
#         fields = ['language', 'starter_code', 'expected_output']
#         widgets = {
#             'language': forms.Select(attrs={'class': 'form-select'}),
#             'starter_code': forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 4, 'placeholder': 'Código inicial para o aluno (opcional)'}),
#             'expected_output': forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 3, 'placeholder': 'Saída esperada para correção...'}),
#         }


# class CompleteCodeExerciseForm(forms.ModelForm):
#     class Meta:
#         model = CompleteCodeExercise
#         fields = ['language', 'starter_code', 'complete_code']
#         widgets = {
#             'language': forms.Select(attrs={'class': 'form-select'}),
#             'starter_code': forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 4, 'placeholder': 'Código com lacunas para o aluno completar...'}),
#             'complete_code': forms.Textarea(attrs={'class': 'form-control font-monospace', 'rows': 4, 'placeholder': 'Código completo (gabarito)...'}),
#         }
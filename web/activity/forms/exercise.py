from activity.models import Exercise, ExerciseOption
from django import forms


class ExerciseForm(forms.ModelForm):
    class Meta:
        model = Exercise
        fields = ['activity_list', 'statement', 'type']
        widgets = {
            'activity_list': forms.HiddenInput(),          
            'type': forms.HiddenInput(),            
            'statement': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enunciado...'
            }),  
        }


class ExerciseOptionForm(forms.ModelForm):
    class Meta:
        model = ExerciseOption
        fields = ['text', 'is_correct']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Texto da opção'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

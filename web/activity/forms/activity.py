from django import forms


class ActivityForm(forms.Form):
    nome = forms.CharField(
        max_length=100,
        label='Nome da Atividade',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite o nome da atividade'
        })
    )
    descricao = forms.CharField(
        label='Descrição da Atividade',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Digite a descrição'
        })
    )



class ActivityDissertativaForm(forms.Form):
    enunciado = forms.CharField(
        label='Enunciado',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Digite o enunciado da atividade'
        })
    )
    pontuacao = forms.DecimalField(
        label='Pontuação',
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: 10.00',
            'step': '0.01'
        })
    )
    criterios_avaliacao = forms.CharField(
        label='Critérios de Avaliação',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Liste os critérios de avaliação'
        })
    )



from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control py-3',
            'placeholder': 'seu@email.com',
        }),
        label='Email',
        required=True
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control py-3',
            'placeholder': 'Digite sua senha',
            'id': 'id_password',
        }),
        label='Senha',
        required=True
    )
    
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        
        if email and password:
            try:
                # Buscar usuário por email
                user = User.objects.get(email=email)
                # Autenticar com username do usuário
                self.user = authenticate(username=user.username, password=password)
                if not self.user:
                    raise forms.ValidationError('Email ou senha inválidos')
            except User.DoesNotExist:
                raise forms.ValidationError('Email ou senha inválidos')
        
        return cleaned_data
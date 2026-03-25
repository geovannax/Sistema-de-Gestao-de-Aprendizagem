from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import FormView
from .forms.authentication import LoginForm


# Create your views here.


class AuthenticationView(FormView):
    form_class = LoginForm
    success_url = '/home/'
    template_name = 'authentication/login.html'

    def form_valid(self, form):
        user = form.user
        login(self.request, user)
        messages.info(self.request, f'Bem vindo {user.first_name}!')
        return redirect(self.success_url)
    
    def dispatch(self, request, *args, **kwargs):
        # Se já está logado, redireciona para home
        if request.user.is_authenticated:
            return redirect('authentication:home')
        return super().dispatch(request, *args, **kwargs)


class HomeView(View):
    """View para a página inicial do sistema"""
    
    template_name = 'global/partials/home.html'

    def get(self, request, *args, **kwargs):       
        return render(request, self.template_name)



class LogoutView(View):
    """View para fazer logout do usuário"""
    
    def get(self, request, *args, **kwargs):
        logout(request)
        messages.info(self.request, 'Deslogado com sucesso!')
        return redirect('authentication:home')
from accounts.models import UserPreferences
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.contrib import messages

@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    
    # WORKAROUND: forçar a criação da sessão para garantir que o middleware possa acessar os cookies
    request.session['versao'] = '2'
    messages.success(request, f'Bem-vindo, {user.get_full_name()}!')
    if user_prefs := UserPreferences.objects.filter(user=user).first():
        request._set_cookies = {}
        for cookie_key, cookie_value in user_prefs.preferences.get('cookies', {}).items():
           request._set_cookies.update({cookie_key: cookie_value}) 

@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):

    if user_prefs := UserPreferences.objects.filter(user=user).first():
        request._delete_cookies = [
            cookie_key
           for cookie_key, _ in user_prefs.preferences.get('cookies', {}).items() 
        ]

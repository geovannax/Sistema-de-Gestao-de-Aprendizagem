from django.urls import path

from authentication.views import AuthenticationView, HomeView, LogoutView

app_name = 'authentication'

urlpatterns = [
    path('', AuthenticationView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('home/', HomeView.as_view(), name='home'),
]
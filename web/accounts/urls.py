from django.urls import path

from .views import OverviewView, PendingView, ProfileView, TurmasView

app_name = 'accounts'

urlpatterns = [
    path('profile/', OverviewView.as_view(), name='profile'),
    path('profile/overview/', OverviewView.as_view(), name='overview'),
    path('profile/notes/', ProfileView.as_view(), name='notes'),
    path('profile/pending/', PendingView.as_view(), name='pending'),
    path('profile/turmas/', TurmasView.as_view(), name='turmas'),
]

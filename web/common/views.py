from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

# Create your views here.

class LandingPage(TemplateView):
    template_name = 'global/partials/landing.html'

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'global/partials/home.html'

def permission_denied(request, exception=None):
    return render(request, 'global/partials/403.html', status=403)

def page_not_found(request, exception=None):
    return render(request, 'global/partials/404.html', status=404)
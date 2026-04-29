"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from common.views import page_not_found, permission_denied, LandingPage, HomeView


handler403 = permission_denied
handler404 = page_not_found

urlpatterns = [
    path('', LandingPage.as_view(), name='landing'),
    path('home/', HomeView.as_view(), name='home'),

    path('accounts/login/', LoginView.as_view(), name='login'),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),

    path('activity/', include('activity.urls')),
    path('admin/', admin.site.urls),
    path('group/', include('group.urls')),

    # Third party
    path("select2/", include("django_select2.urls")),
]

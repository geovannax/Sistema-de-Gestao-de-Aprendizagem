from django.urls import path

from classes.views import ClassesCreateView, ClassesListView

app_name = 'classes'

urlpatterns = [
    path('create', ClassesCreateView.as_view(), name='create'),
    path('list', ClassesListView.as_view(), name='list'),
]

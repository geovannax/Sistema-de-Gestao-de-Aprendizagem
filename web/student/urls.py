from django.urls import path
from student.views import StudentDashboardView, StudentGroupDetailView


app_name = 'student'

urlpatterns = [
    path('', StudentDashboardView.as_view(), name='dashboard'),
    path('group/<int:pk>/', StudentGroupDetailView.as_view(), name='group_detail'),
]

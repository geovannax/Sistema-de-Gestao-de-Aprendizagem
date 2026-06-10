from django.urls import path
from student.views import StudentDashboardView


app_name = 'student'

urlpatterns = [
    path('', StudentDashboardView.as_view(), name='dashboard'),
]

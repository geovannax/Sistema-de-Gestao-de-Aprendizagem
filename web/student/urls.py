from django.urls import path
from student.views import (
    StudentAbandonView,
    StudentActivityView,
    StudentActivityReviewView,
    StudentDashboardView,
    StudentFeedbackView,
    StudentGroupDetailView,
    StudentResultView,
    StudentSubmitView,
    TeacherGradeView,
    TeacherSubmissionsView,
)


app_name = 'student'

urlpatterns = [
    path('', StudentDashboardView.as_view(), name='dashboard'),
    path('group/<int:pk>/', StudentGroupDetailView.as_view(), name='group_detail'),
    path('activity/<int:link_pk>/', StudentActivityView.as_view(), name='activity'),
    path('activity/<int:link_pk>/review/', StudentActivityReviewView.as_view(), name='activity_review'),
    path('activity/<int:link_pk>/submit/', StudentSubmitView.as_view(), name='activity_submit'),
    path('activity/<int:link_pk>/abandon/', StudentAbandonView.as_view(), name='activity_abandon'),
    path('activity/<int:link_pk>/feedback/', StudentFeedbackView.as_view(), name='activity_feedback'),
    path('activity/<int:link_pk>/result/', StudentResultView.as_view(), name='activity_result'),
    path('activity/<int:link_pk>/submissions/', TeacherSubmissionsView.as_view(), name='activity_submissions'),
    path('activity/<int:link_pk>/submissions/<int:submission_pk>/grade/', TeacherGradeView.as_view(), name='activity_grade'),
]

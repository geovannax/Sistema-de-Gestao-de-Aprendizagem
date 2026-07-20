from django.urls import path
from django.views.generic import RedirectView
from student.views import (
    StudentAbandonView,
    StudentActivityView,
    StudentActivityReviewView,
    StudentExercisePingView,
    StudentFeedbackView,
    StudentGroupDetailView,
    StudentResultView,
    StudentRunCodePollView,
    StudentRunCodeView,
    StudentSubmitView,
    TeacherGradeView,
    TeacherSubmissionsView,
)


app_name = 'student'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='accounts:turmas', permanent=False), name='dashboard'),
    path('group/<int:pk>/', StudentGroupDetailView.as_view(), name='group_detail'),
    path('activity/<int:link_pk>/', StudentActivityView.as_view(), name='activity'),
    path('activity/<int:link_pk>/review/', StudentActivityReviewView.as_view(), name='activity_review'),
    path('activity/<int:link_pk>/submit/', StudentSubmitView.as_view(), name='activity_submit'),
    path('activity/<int:link_pk>/abandon/', StudentAbandonView.as_view(), name='activity_abandon'),
    path('activity/<int:link_pk>/feedback/', StudentFeedbackView.as_view(), name='activity_feedback'),
    path('activity/<int:link_pk>/result/', StudentResultView.as_view(), name='activity_result'),
    path('activity/<int:link_pk>/submissions/', TeacherSubmissionsView.as_view(), name='activity_submissions'),
    path('activity/<int:link_pk>/submissions/<int:submission_pk>/grade/', TeacherGradeView.as_view(), name='activity_grade'),
    path('activity/<int:link_pk>/ping/', StudentExercisePingView.as_view(), name='activity_exercise_ping'),
    path('activity/<int:link_pk>/run/', StudentRunCodeView.as_view(), name='activity_run_code'),
    path('activity/<int:link_pk>/run/poll/<str:task_id>/', StudentRunCodePollView.as_view(), name='activity_run_code_poll'),
]

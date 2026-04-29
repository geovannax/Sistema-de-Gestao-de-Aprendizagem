from django.urls import path
from activity.views import (
    ActivityCreateView,
    ActivityListView,
    MultipleChoiceExerciseCreateView,  # ← Adicionar
    MultipleChoiceExerciseAddOptionView,
    MultipleChoiceExerciseUpdateView,

    # Não implementado
    ActivityDetailView,
    ActivityUpdateView,
    ActivityArchiveView,
    ActivityDeleteView,

)
app_name = 'activity'

urlpatterns = [
    path('create/', ActivityCreateView.as_view(), name='create'),  
    path('list/', ActivityListView.as_view(), name='list'),


    path(
        'exercise/multiple-choice/create/<int:pk>/',
        MultipleChoiceExerciseCreateView.as_view(),
        name='multiple_choice_exercise_create'
    ),

    path(
        'exercise/multiple-choice/add-option/',
        MultipleChoiceExerciseAddOptionView.as_view(),
        name='multiple_choice_exercise_add_option'
    ),


    path(
        'exercise/multiple-choice/update/<int:pk>/',
        MultipleChoiceExerciseUpdateView.as_view(),
        name='multiple_choice_exercise_update'
    ),

    # Não implementado
    path('detail/<int:pk>/', ActivityDetailView.as_view(), name='detail'), 
    path('update/<int:pk>/', ActivityUpdateView.as_view(), name='update'),
    path('archive/<int:pk>/', ActivityArchiveView.as_view(), name='archive'),
    path('delete/<int:pk>/', ActivityDeleteView.as_view(), name='delete'),




]
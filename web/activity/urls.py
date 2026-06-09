from django.urls import path
from activity.views import (

    ActivityCreateView,
    ActivityArchivedListView,
    ActivityListView,

    # Não implementado
    ActivityDetailView,
    ActivityUpdateView,
    ActivityArchiveView,
    ActivityDeleteView,
    ActivityAssignView,
    ActivityUnshareView,

    DiscursiveExerciseCreateView,
    DiscursiveExerciseUpdateView,


    ExerciseCancelView,
    ExerciseDeleteView,

    CodeExerciseCreateView,
    CodeExerciseUpdateView,

    CompleteCodeExerciseCreateView,
    CompleteCodeExerciseUpdateView,

    MultipleChoiceExerciseCreateView,
    MultipleChoiceExerciseAddOptionView,
    MultipleChoiceExerciseUpdateView,


)
app_name = 'activity'

urlpatterns = [
    path('list/', ActivityListView.as_view(), name='list'),
    path('archived/', ActivityArchivedListView.as_view(), name='archived'),
    path('exercise/cancel/<int:pk>/', ExerciseCancelView.as_view(), name='exercise_cancel'),
    path('exercise/delete/<int:pk>/', ExerciseDeleteView.as_view(), name='exercise_delete'),

    path('exercise/code/create/<int:pk>/', CodeExerciseCreateView.as_view(), name='code_exercise_create'),
    path('exercise/code/update/<int:pk>/', CodeExerciseUpdateView.as_view(), name='code_exercise_update'),

    path( 'exercise/complete-code/create/<int:pk>/', CompleteCodeExerciseCreateView.as_view(), name='complete_code_exercise_create'),
    path( 'exercise/complete-code/update/<int:pk>/', CompleteCodeExerciseUpdateView.as_view(), name='complete_code_exercise_update'),

    path( 'exercise/discursive/create/<int:pk>/', DiscursiveExerciseCreateView.as_view(), name='discursive_exercise_create'),
    path( 'exercise/discursive/update/<int:pk>/', DiscursiveExerciseUpdateView.as_view(), name='discursive_exercise_update'),

    path( 'exercise/multiple-choice/create/<int:pk>/', MultipleChoiceExerciseCreateView.as_view(), name='multiple_choice_exercise_create'),
    path( 'exercise/multiple-choice/add-option/', MultipleChoiceExerciseAddOptionView.as_view(), name='multiple_choice_exercise_add_option'),
    path( 'exercise/multiple-choice/update/<int:pk>/', MultipleChoiceExerciseUpdateView.as_view(), name='multiple_choice_exercise_update'),

 
    # Não implementado
    path('create/', ActivityCreateView.as_view(), name='create'),  
    path('detail/<int:pk>/', ActivityDetailView.as_view(), name='detail'), 
    path('update/<int:pk>/', ActivityUpdateView.as_view(), name='update'),
    path('archive/<int:pk>/', ActivityArchiveView.as_view(), name='archive'),
    path('delete/<int:pk>/', ActivityDeleteView.as_view(), name='delete'),
    path('unshare/<int:pk>/', ActivityUnshareView.as_view(), name='unshare'),
    path('assign/<int:pk>/', ActivityAssignView.as_view(), name='assign'),




]

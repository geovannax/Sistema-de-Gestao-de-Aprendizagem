from django.urls import path

from activity.views import ActivityCreateView, ActivityListView, ActivityDissertativaCreateView

app_name = 'activity'

urlpatterns = [
    path('activity_list', ActivityListView.as_view(), name='activity_list'),
    path('create/', ActivityCreateView.as_view(), name='create'),
    path('dissertativa/', ActivityDissertativaCreateView.as_view(), name='dissertativa_create'),
]

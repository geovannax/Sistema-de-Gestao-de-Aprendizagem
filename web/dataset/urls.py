from django.urls import path
from dataset.views import (
    DatasetActivitiesPartial,
    DatasetDownloadView,
    DatasetGroupView,
    DatasetListView,
    DatasetPreviewPartial,
)

app_name = 'dataset'

urlpatterns = [
    path('', DatasetListView.as_view(), name='list'),
    path('download/<str:ds_type>/', DatasetDownloadView.as_view(), name='download'),
    path('htmx/activities/', DatasetActivitiesPartial.as_view(), name='htmx_activities'),
    path('htmx/preview/', DatasetPreviewPartial.as_view(), name='htmx_preview'),
    path('<int:pk>/', DatasetGroupView.as_view(), name='group'),
]

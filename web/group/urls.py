from django.urls import path

from group.views import (

    GroupArchivedListView,
    GroupActiveListView,
    GroupCreateView,
    GroupDetailView,
    GroupManageArchivingView,
    GroupSharedListView,
    GroupShareView,
    GroupSoftDeleteView,
    GroupUnshareView,
    GroupUpdateView,
)

app_name = 'group'

urlpatterns = [
    path('archived/', GroupArchivedListView.as_view(), name='archived'),
    path('active/', GroupActiveListView.as_view(), name='active'),
    path('create/', GroupCreateView.as_view(), name='create'),
    path('shared/', GroupSharedListView.as_view(), name='shared'),

    path('<int:pk>/', GroupDetailView.as_view(), name='detail'),
    path('<int:pk>/archive/', GroupManageArchivingView.as_view(), name='archive'),
    path('<int:pk>/delete/', GroupSoftDeleteView.as_view(), name='delete'),
    path('<int:pk>/share/', GroupShareView.as_view(), name='share'),
    path('<int:pk>/unshare/', GroupUnshareView.as_view(), name='unshare'),
    path('<int:pk>/update/', GroupUpdateView.as_view(), name='update'),

]

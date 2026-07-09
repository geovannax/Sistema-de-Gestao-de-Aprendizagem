from django.urls import path

from group.views import (

    GroupArchivedListView,
    GroupActiveListView,
    GroupCreateView,
    GroupDetailView,
    GroupInviteConfirmView,
    GroupInviteCreateView,
    GroupInviteExpireView,
    GroupManageArchivingView,
    GroupReviewView,
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
    path('invite/<str:token>/', GroupInviteConfirmView.as_view(), name='invite_confirm'),
    path('shared/', GroupSharedListView.as_view(), name='shared'),

    path('<int:pk>/', GroupReviewView.as_view(), name='detail'),
    path('<int:pk>/archive/', GroupManageArchivingView.as_view(), name='archive'),
    path('<int:pk>/delete/', GroupSoftDeleteView.as_view(), name='delete'),
    path('<int:pk>/invite/create/', GroupInviteCreateView.as_view(), name='invite_create'),
    path('<int:pk>/invite/<int:invite_pk>/expire/', GroupInviteExpireView.as_view(), name='invite_expire'),
    path('<int:pk>/share/', GroupShareView.as_view(), name='share'),
    path('<int:pk>/stats/', GroupDetailView.as_view(), name='stats'),
    path('<int:pk>/unshare/', GroupUnshareView.as_view(), name='unshare'),
    path('<int:pk>/review/', GroupReviewView.as_view(), name='review'),
    path('<int:pk>/update/', GroupUpdateView.as_view(), name='update'),

]

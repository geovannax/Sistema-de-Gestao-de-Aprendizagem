import pytest
from datetime import timedelta
from django.contrib.auth.models import User
from django.test import Client
from django.utils import timezone

from activity.models import ActivityList, ActivityListGroup
from group.models import Group, GroupStudent


@pytest.mark.django_db
class TestStudentDashboard:
    def test_unauthenticated_redirects(self):
        response = Client().get('/student/')
        assert response.status_code == 302

    def test_empty_dashboard(self, authenticated_client):
        response = authenticated_client.get('/student/')
        assert response.status_code == 200

    def test_dashboard_with_enrollment(self, authenticated_client, user, group):
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        response = authenticated_client.get('/student/')
        assert response.status_code == 200

    def test_dashboard_table_view(self, authenticated_client, user, group):
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        response = authenticated_client.get('/student/?view_type=table')
        assert response.status_code == 200

    def test_dashboard_invalid_view_type(self, authenticated_client, user, group):
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        response = authenticated_client.get('/student/?view_type=invalid')
        assert response.status_code == 200

    def test_dashboard_with_open_activity(self, authenticated_client, user, group):
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        activity = ActivityList.objects.create(title='Open Act', created_by=user)
        ActivityListGroup.objects.create(group=group, activity_list=activity)
        response = authenticated_client.get('/student/')
        assert response.status_code == 200

    def test_dashboard_with_future_activity(self, authenticated_client, user, group):
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        activity = ActivityList.objects.create(title='Future Act', created_by=user)
        ActivityListGroup.objects.create(
            group=group,
            activity_list=activity,
            starts_at=timezone.now() + timedelta(days=1),
        )
        response = authenticated_client.get('/student/')
        assert response.status_code == 200

    def test_dashboard_with_closed_activity(self, authenticated_client, user, group):
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        activity = ActivityList.objects.create(title='Closed Act', created_by=user)
        ActivityListGroup.objects.create(
            group=group,
            activity_list=activity,
            ends_at=timezone.now() - timedelta(days=1),
        )
        response = authenticated_client.get('/student/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestStudentGroupDetail:
    def test_enrolled_student_sees_detail(self, authenticated_client, user, group):
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        response = authenticated_client.get(f'/student/group/{group.pk}/')
        assert response.status_code == 200

    def test_not_enrolled_gets_404(self, authenticated_client, group):
        response = authenticated_client.get(f'/student/group/{group.pk}/')
        assert response.status_code == 404

    def test_group_detail_with_open_activity(self, authenticated_client, user, group):
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        activity = ActivityList.objects.create(
            title='Open Published', created_by=user, is_published=True
        )
        ActivityListGroup.objects.create(group=group, activity_list=activity)
        response = authenticated_client.get(f'/student/group/{group.pk}/')
        assert response.status_code == 200

    def test_group_detail_with_future_activity(self, authenticated_client, user, group):
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        activity = ActivityList.objects.create(
            title='Future Published', created_by=user, is_published=True
        )
        ActivityListGroup.objects.create(
            group=group,
            activity_list=activity,
            starts_at=timezone.now() + timedelta(days=1),
        )
        response = authenticated_client.get(f'/student/group/{group.pk}/')
        assert response.status_code == 200

    def test_group_detail_with_closed_activity(self, authenticated_client, user, group):
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        activity = ActivityList.objects.create(
            title='Closed Published', created_by=user, is_published=True
        )
        ActivityListGroup.objects.create(
            group=group,
            activity_list=activity,
            ends_at=timezone.now() - timedelta(days=1),
        )
        response = authenticated_client.get(f'/student/group/{group.pk}/')
        assert response.status_code == 200

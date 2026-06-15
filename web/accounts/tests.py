import pytest
from django.contrib.auth.models import User
from django.test import Client

from accounts.models import UserPreferences


@pytest.mark.django_db
class TestUserPreferences:
    def test_set_view_type_creates_key_when_absent(self):
        user = User.objects.create_user(username='u_prefs1', password='pass123')
        prefs = UserPreferences.objects.create(user=user)
        prefs.set_view_type('group_list', 'cards')
        prefs.refresh_from_db()
        assert prefs.preferences['view_type']['group_list'] == 'cards'

    def test_set_view_type_updates_existing_key(self):
        user = User.objects.create_user(username='u_prefs2', password='pass123')
        prefs = UserPreferences.objects.create(
            user=user,
            preferences={'view_type': {'group_list': 'table'}},
        )
        prefs.set_view_type('group_list', 'cards')
        prefs.refresh_from_db()
        assert prefs.preferences['view_type']['group_list'] == 'cards'


@pytest.mark.django_db
class TestLoginSignal:
    def test_login_without_preferences(self):
        User.objects.create_user(username='u_login1', password='pass123')
        response = Client().post('/accounts/login/', {
            'username': 'u_login1',
            'password': 'pass123',
        })
        assert response.status_code in (200, 302)

    def test_login_with_cookie_preferences(self):
        user = User.objects.create_user(username='u_login2', password='pass123')
        UserPreferences.objects.create(
            user=user,
            preferences={'cookies': {'theme': 'dark', 'sidebar': 'open'}},
        )
        Client().post('/accounts/login/', {
            'username': 'u_login2',
            'password': 'pass123',
        })


@pytest.mark.django_db
class TestLogoutSignal:
    def test_logout_without_preferences(self):
        User.objects.create_user(username='u_logout1', password='pass123')
        client = Client()
        client.post('/accounts/login/', {'username': 'u_logout1', 'password': 'pass123'})
        response = client.post('/accounts/logout/')
        assert response.status_code in (200, 302)

    def test_logout_with_cookie_preferences(self):
        user = User.objects.create_user(username='u_logout2', password='pass123')
        UserPreferences.objects.create(
            user=user,
            preferences={'cookies': {'theme': 'dark'}},
        )
        client = Client()
        client.post('/accounts/login/', {'username': 'u_logout2', 'password': 'pass123'})
        client.post('/accounts/logout/')

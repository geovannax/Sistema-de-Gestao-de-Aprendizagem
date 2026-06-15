import pytest
from django.contrib.auth.models import User
from django.test import Client
from group.models import Group


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        password='testpass123',
        first_name='Test',
        last_name='User',
    )


@pytest.fixture
def group(user):
    return Group.objects.create(
        name='Turma Test',
        description='Descricao da turma de teste para uso nos testes.',
        shift='Manhã',
        created_by=user,
    )


@pytest.fixture
def authenticated_client(user):
    client = Client()
    client.post('/accounts/login/', {
        'username': user.username,
        'password': 'testpass123',
    })
    return client

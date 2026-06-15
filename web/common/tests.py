import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, override_settings

from common.utils import get_btn_action


# ─── get_btn_action ─────────────────────────────────────────────────────────

class TestGetBtnAction:
    def test_returns_actions_for_valid_list(self):
        result = get_btn_action(['update', 'delete'], 'group')
        assert len(result) == 2
        assert result[0]['url'] == 'group:update'
        assert result[1]['url'] == 'group:delete'

    def test_raises_for_non_list(self):
        with pytest.raises(ValueError):
            get_btn_action('update', 'group')

    def test_returns_none_for_unknown_action(self):
        result = get_btn_action(['unknown_action'], 'group')
        assert result == [None]

    def test_all_action_keys(self):
        result = get_btn_action(['archive', 'delete', 'unshare', 'update', 'assign_update'], 'activity')
        assert len(result) == 5
        assert all(r is not None for r in result)


# ─── LandingPage ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLandingPage:
    def test_get_unauthenticated(self):
        response = Client().get('/')
        assert response.status_code == 200

    def test_get_authenticated(self, authenticated_client):
        response = authenticated_client.get('/')
        assert response.status_code == 200


# ─── HomeView ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestHomeView:
    def test_get_authenticated(self, authenticated_client):
        response = authenticated_client.get('/home/')
        assert response.status_code == 200

    def test_get_unauthenticated_redirects(self):
        response = Client().get('/home/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']


# ─── Error handlers ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestErrorHandlers:
    def test_permission_denied_403(self, authenticated_client, user):
        other = User.objects.create_user(username='owner_403', password='pass')
        from group.models import Group
        other_group = Group.objects.create(
            name='Outros', description='x' * 20, shift='Manhã', created_by=other
        )
        response = authenticated_client.get(f'/group/{other_group.pk}/update/')
        assert response.status_code == 403

    @override_settings(DEBUG=False)
    def test_page_not_found_404(self):
        response = Client().get('/pagina-que-nao-existe-jamais-99999/')
        assert response.status_code == 404


# ─── FilteringMixin / OrderingMixin unit tests ──────────────────────────────

class TestFilteringMixin:
    def test_apply_filtering_raises_when_not_configured(self):
        from common.mixins import FilteringMixin
        view = FilteringMixin()
        view.allowed_fields = None
        view.model = None
        with pytest.raises(ImproperlyConfigured):
            view.apply_filtering(queryset=None)


class TestOrderingMixin:
    def test_get_ordering_raises_when_not_configured(self):
        from common.mixins import OrderingMixin
        view = OrderingMixin()
        view.allowed_fields = None
        view.model = None
        with pytest.raises(ImproperlyConfigured):
            view.get_ordering()


# ─── HTMXLoginRequiredMixin ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestHTMXLoginRequiredMixin:
    def test_unauthenticated_htmx_returns_401(self):
        response = Client().post(
            '/activity/exercise/multiple-choice/add-option/',
            {'total_forms': '0'},
            HTTP_HX_REQUEST='true',
        )
        assert response.status_code == 401
        assert 'HX-Redirect' in response

    def test_unauthenticated_non_htmx_redirects(self):
        response = Client().get('/activity/exercise/cancel/1/')
        assert response.status_code == 302


# ─── OrderingMixin.apply_ordering with tuple result ─────────────────────────

class TestOrderingMixinApplyOrdering:
    def test_apply_ordering_with_tuple_calls_order_by_with_unpack(self):
        from common.mixins import OrderingMixin
        from unittest.mock import MagicMock
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get('/?sort=name&order=asc')
        request.session = {}
        request._navigation = {}

        model = MagicMock()
        model._meta.app_label = 'test'

        class MockView(OrderingMixin):
            ordering = '-id'
            allowed_fields = ['name']

        view = MockView()
        view.model = model
        view.request = request

        ordering = view.get_ordering()
        assert isinstance(ordering, tuple)

        queryset = MagicMock()
        view.apply_ordering(queryset)
        queryset.order_by.assert_called_once()


# ─── Template tag tests ─────────────────────────────────────────────────────

class TestCommonTemplateTags:
    def test_get_attr_with_truncate_long_string(self):
        from common.templatetags.common_filters import get_attr_with_truncate

        class Obj:
            name = 'a' * 100

        result = get_attr_with_truncate(Obj(), 'name')
        assert result.endswith('...')
        assert len(result) <= 70

    def test_get_item_with_dict_key(self):
        from common.templatetags.common_filters import get_item
        result = get_item({'key': 'value'}, 'key')
        assert result == 'value'

    def test_get_item_with_object_attribute(self):
        from common.templatetags.common_filters import get_item

        class Obj:
            name = 'test'

        result = get_item(Obj(), 'name')
        assert result == 'test'

    def test_get_item_non_dict_no_attribute(self):
        from common.templatetags.common_filters import get_item
        result = get_item(object(), 'nonexistent_xyz')
        assert result == '-'

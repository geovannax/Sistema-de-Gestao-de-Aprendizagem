import pytest
from datetime import timedelta

from django.contrib.admin import site as admin_site
from django.contrib.auth.models import User
from django.test import Client, RequestFactory, override_settings
from django.utils import timezone

from group.admin import (
    GroupArchivedAdmin,
    GroupInviteAdmin,
    GroupSharingAdmin,
    GroupStudentAdmin,
)
from group.models import (
    Group,
    GroupArchived,
    GroupInvite,
    GroupSharing,
    GroupStudent,
    generate_group_invite_token,
)
from activity.models import ActivityList, ActivityListGroup, DiscursiveExercise, Exercise
from student.models import ExerciseAnswer, Submission


@pytest.mark.django_db
def test_generate_group_invite_token():
    token = generate_group_invite_token()
    assert isinstance(token, str) and len(token) > 0


@pytest.mark.django_db
class TestGroup:
    def test_str(self, group):
        assert str(group) == group.name

    def test_active_sharings_count_zero(self, group):
        assert group.active_sharings_count == 0

    def test_active_sharings_count_with_active_sharing(self, group, user):
        other = User.objects.create_user(username='shared_other', password='pass')
        GroupSharing.objects.create(group=group, shared_with=other, shared_by=user, is_active=True)
        assert group.active_sharings_count == 1


@pytest.mark.django_db
class TestGroupStudent:
    def test_str(self, group):
        student = User.objects.create_user(username='gs_student', password='pass')
        gs = GroupStudent.objects.create(group=group, student=student)
        assert str(gs) == f'{student} - {group}'


@pytest.mark.django_db
class TestGroupInvite:
    def test_save_sets_default_expires_at(self, group, user):
        before = timezone.now()
        invite = GroupInvite.objects.create(group=group, created_by=user)
        assert invite.expires_at >= before

    def test_save_keeps_provided_expires_at(self, group, user):
        future = timezone.now() + timedelta(days=30)
        invite = GroupInvite(group=group, created_by=user, expires_at=future)
        invite.save()
        assert invite.expires_at == future

    def test_is_expired_returns_false_for_future(self, group, user):
        invite = GroupInvite.objects.create(group=group, created_by=user)
        assert invite.is_expired() is False

    def test_is_expired_returns_true_for_past(self, group, user):
        past = timezone.now() - timedelta(days=1)
        invite = GroupInvite(group=group, created_by=user, expires_at=past)
        invite.save()
        assert invite.is_expired() is True

    def test_has_uses_available_when_unlimited(self, group, user):
        invite = GroupInvite.objects.create(group=group, created_by=user, max_uses=None)
        assert invite.has_uses_available() is True

    def test_has_uses_available_when_within_limit(self, group, user):
        invite = GroupInvite.objects.create(group=group, created_by=user, max_uses=5)
        assert invite.has_uses_available() is True

    def test_has_uses_available_when_at_limit(self, group, user):
        invite = GroupInvite.objects.create(group=group, created_by=user, max_uses=2)
        invite.used_count = 2
        invite.save()
        assert invite.has_uses_available() is False

    def test_can_be_used_returns_true(self, group, user):
        invite = GroupInvite.objects.create(group=group, created_by=user)
        assert invite.can_be_used() is True

    def test_can_be_used_false_when_inactive(self, group, user):
        invite = GroupInvite.objects.create(group=group, created_by=user, is_active=False)
        assert invite.can_be_used() is False

    def test_can_be_used_false_when_expired(self, group, user):
        past = timezone.now() - timedelta(days=1)
        invite = GroupInvite(group=group, created_by=user, expires_at=past)
        invite.save()
        assert invite.can_be_used() is False

    def test_can_be_used_false_when_group_deleted(self, group, user):
        group.deleted_at = timezone.now()
        group.save()
        invite = GroupInvite.objects.create(group=group, created_by=user)
        assert invite.can_be_used() is False

    def test_can_be_used_false_when_no_uses_left(self, group, user):
        invite = GroupInvite.objects.create(group=group, created_by=user, max_uses=1)
        invite.used_count = 1
        invite.save()
        assert invite.can_be_used() is False

    def test_str(self, group, user):
        invite = GroupInvite.objects.create(group=group, created_by=user)
        assert str(invite) == f'Convite para {group}'


@pytest.mark.django_db
class TestGroupAdmin:
    def _make_request(self):
        superuser = User.objects.create_superuser(
            username=f'admin_{id(self)}', password='adminpass'
        )
        request = RequestFactory().get('/')
        request.user = superuser
        return request

    def test_groupsharing_get_group(self, group, user):
        other = User.objects.create_user(username='sharing_target', password='pass')
        sharing = GroupSharing.objects.create(group=group, shared_with=other, shared_by=user)
        admin = GroupSharingAdmin(GroupSharing, admin_site)
        assert admin.get_group(sharing) == group.name

    def test_groupsharing_get_queryset(self):
        admin = GroupSharingAdmin(GroupSharing, admin_site)
        assert admin.get_queryset(self._make_request()) is not None

    def test_grouparchived_get_group(self, group, user):
        archived = GroupArchived.objects.create(group=group, user=user)
        admin = GroupArchivedAdmin(GroupArchived, admin_site)
        assert admin.get_group(archived) == group.name

    def test_grouparchived_get_queryset(self):
        admin = GroupArchivedAdmin(GroupArchived, admin_site)
        assert admin.get_queryset(self._make_request()) is not None

    def test_groupstudent_get_group(self, group):
        student = User.objects.create_user(username='admin_stu', password='pass')
        gs = GroupStudent.objects.create(group=group, student=student)
        admin = GroupStudentAdmin(GroupStudent, admin_site)
        assert admin.get_group(gs) == group.name

    def test_groupstudent_get_queryset(self):
        admin = GroupStudentAdmin(GroupStudent, admin_site)
        assert admin.get_queryset(self._make_request()) is not None

    def test_groupinvite_get_group(self, group, user):
        invite = GroupInvite.objects.create(group=group, created_by=user)
        admin = GroupInviteAdmin(GroupInvite, admin_site)
        assert admin.get_group(invite) == group.name

    def test_groupinvite_get_queryset(self):
        admin = GroupInviteAdmin(GroupInvite, admin_site)
        assert admin.get_queryset(self._make_request()) is not None


# ─── Group Views Integration Tests ──────────────────────────────────────────

@pytest.mark.django_db
class TestGroupViews:
    # ── List views ───────────────────────────────────────────────────────────

    def test_active_list_authenticated(self, authenticated_client):
        response = authenticated_client.get('/group/active/')
        assert response.status_code == 200

    def test_active_list_unauthenticated(self):
        response = Client().get('/group/active/')
        assert response.status_code == 302

    def test_archived_list(self, authenticated_client):
        response = authenticated_client.get('/group/archived/')
        assert response.status_code == 200

    def test_shared_list(self, authenticated_client):
        response = authenticated_client.get('/group/shared/')
        assert response.status_code == 200

    # ── Filter / ordering ────────────────────────────────────────────────────

    def test_active_list_with_filter(self, authenticated_client, group):
        response = authenticated_client.get('/group/active/?search_field=name&q=Turma')
        assert response.status_code == 200

    def test_active_list_invalid_search_field(self, authenticated_client, group):
        response = authenticated_client.get('/group/active/?search_field=invalid&q=test')
        assert response.status_code == 200

    def test_active_list_filter_persists_in_session(self, authenticated_client, group):
        authenticated_client.get('/group/active/?search_field=name&q=Turma')
        response = authenticated_client.get('/group/active/')
        assert response.status_code == 200

    def test_active_list_with_ordering(self, authenticated_client, group):
        response = authenticated_client.get('/group/active/?sort=name&order=asc')
        assert response.status_code == 200

    def test_active_list_order_desc(self, authenticated_client, group):
        response = authenticated_client.get('/group/active/?sort=name&order=desc')
        assert response.status_code == 200

    def test_active_list_invalid_sort_field(self, authenticated_client, group):
        response = authenticated_client.get('/group/active/?sort=invalid&order=asc')
        assert response.status_code == 200

    def test_active_list_order_persists_in_session(self, authenticated_client, group):
        authenticated_client.get('/group/active/?sort=name&order=asc')
        response = authenticated_client.get('/group/active/')
        assert response.status_code == 200

    def test_active_list_clear_filter(self, authenticated_client, group):
        authenticated_client.get('/group/active/?search_field=name&q=Turma')
        response = authenticated_client.get('/group/active/?clear_filter=1')
        assert response.status_code == 200

    def test_active_list_clear_order(self, authenticated_client, group):
        authenticated_client.get('/group/active/?sort=name&order=asc')
        response = authenticated_client.get('/group/active/?clear_order=1')
        assert response.status_code == 200

    def test_filter_cleared_when_view_changes(self, authenticated_client, group):
        authenticated_client.get('/group/archived/?search_field=name&q=Turma')
        authenticated_client.get('/group/active/')
        response = authenticated_client.get('/group/archived/')
        assert response.status_code == 200

    def test_order_cleared_when_view_changes(self, authenticated_client, group):
        authenticated_client.get('/group/archived/?sort=name&order=asc')
        authenticated_client.get('/group/active/')
        response = authenticated_client.get('/group/archived/')
        assert response.status_code == 200

    def test_active_list_table_view_type(self, authenticated_client, group):
        response = authenticated_client.get('/group/active/?view_type=table')
        assert response.status_code == 200

    def test_view_type_cookie_used(self, authenticated_client, group):
        authenticated_client.cookies['groupactivelistview-view-type'] = 'table'
        response = authenticated_client.get('/group/active/')
        assert response.status_code == 200

    def test_view_type_preference_not_updated_when_same(self, authenticated_client, group):
        authenticated_client.get('/group/active/?view_type=table')
        response = authenticated_client.get('/group/active/?view_type=table')
        assert response.status_code == 200

    # ── CRUD views ───────────────────────────────────────────────────────────

    def test_create_view_get(self, authenticated_client):
        response = authenticated_client.get('/group/create/')
        assert response.status_code == 200

    def test_create_view_post_valid(self, authenticated_client):
        response = authenticated_client.post('/group/create/', {
            'name': 'Nova Turma Criada',
            'description': 'Descricao valida com mais de dez caracteres',
            'shift': 'Manhã',
        })
        assert response.status_code in (200, 302)

    def test_create_view_post_duplicate_name(self, authenticated_client, group):
        response = authenticated_client.post('/group/create/', {
            'name': group.name,
            'description': 'Descricao valida com mais de dez caracteres',
            'shift': 'Manhã',
        })
        assert response.status_code == 200

    def test_detail_view(self, authenticated_client, group):
        response = authenticated_client.get(f'/group/{group.pk}/')
        assert response.status_code == 200

    def test_detail_view_shared_user(self, user, group):
        other = User.objects.create_user(username='detail_shared', password='pass')
        GroupSharing.objects.create(group=group, shared_with=other, shared_by=user, is_active=True)
        client = Client()
        client.post('/accounts/login/', {'username': 'detail_shared', 'password': 'pass'})
        response = client.get(f'/group/{group.pk}/')
        assert response.status_code == 200

    def test_update_view_get(self, authenticated_client, group):
        response = authenticated_client.get(f'/group/{group.pk}/update/')
        assert response.status_code == 200

    def test_update_view_post_valid(self, authenticated_client, group):
        response = authenticated_client.post(f'/group/{group.pk}/update/', {
            'name': 'Turma Atualizada OK',
            'description': 'Descricao atualizada valida com caracteres suficientes',
            'shift': 'Tarde',
        })
        assert response.status_code in (200, 302)

    def test_update_view_403_for_non_owner(self, authenticated_client, user):
        other = User.objects.create_user(username='update_other', password='pass')
        other_group = Group.objects.create(
            name='Ajena', description='y' * 20, shift='Manhã', created_by=other
        )
        response = authenticated_client.get(f'/group/{other_group.pk}/update/')
        assert response.status_code == 403

    def test_delete_view_get(self, authenticated_client, group):
        response = authenticated_client.get(f'/group/{group.pk}/delete/')
        assert response.status_code == 200

    def test_delete_view_post(self, authenticated_client, group):
        response = authenticated_client.post(f'/group/{group.pk}/delete/')
        assert response.status_code == 302

    # ── Archive ──────────────────────────────────────────────────────────────

    def test_archive_post_archives(self, authenticated_client, group):
        response = authenticated_client.post(f'/group/{group.pk}/archive/')
        assert response.status_code == 302

    def test_archive_post_unarchives(self, authenticated_client, group):
        authenticated_client.post(f'/group/{group.pk}/archive/')
        response = authenticated_client.post(f'/group/{group.pk}/archive/')
        assert response.status_code == 302

    # ── Share view ───────────────────────────────────────────────────────────

    def test_share_view_get_teachers(self, authenticated_client, group):
        response = authenticated_client.get(f'/group/{group.pk}/share/')
        assert response.status_code == 200

    def test_share_view_get_students(self, authenticated_client, group):
        response = authenticated_client.get(f'/group/{group.pk}/share/?share_view=students')
        assert response.status_code == 200

    def test_share_view_invalid_share_view_param(self, authenticated_client, group):
        response = authenticated_client.get(f'/group/{group.pk}/share/?share_view=invalid')
        assert response.status_code == 200

    def test_share_view_with_existing_sharing(self, authenticated_client, group, user):
        other = User.objects.create_user(username='shared_teach', password='pass')
        GroupSharing.objects.create(group=group, shared_with=other, shared_by=user, is_active=True)
        response = authenticated_client.get(f'/group/{group.pk}/share/')
        assert response.status_code == 200

    def test_share_view_with_filter(self, authenticated_client, group):
        response = authenticated_client.get(
            f'/group/{group.pk}/share/?search_field=shared_with&q=user'
        )
        assert response.status_code == 200

    def test_share_view_post_no_users(self, authenticated_client, group):
        response = authenticated_client.post(f'/group/{group.pk}/share/', {})
        assert response.status_code == 200

    def test_share_view_post_with_users(self, authenticated_client, group, user):
        other = User.objects.create_user(username='share_target_v', password='pass')
        response = authenticated_client.post(
            f'/group/{group.pk}/share/', {'users': [other.pk]}
        )
        assert response.status_code in (200, 302)

    def test_share_view_with_invite_in_session(self, authenticated_client, group, user):
        invite = GroupInvite.objects.create(group=group, created_by=user)
        session = authenticated_client.session
        session['latest_group_invite_id'] = invite.pk
        session.save()
        response = authenticated_client.get(f'/group/{group.pk}/share/')
        assert response.status_code == 200

    # ── Invite ───────────────────────────────────────────────────────────────

    def test_invite_create_post(self, authenticated_client, group):
        response = authenticated_client.post(f'/group/{group.pk}/invite/create/')
        assert response.status_code == 302

    def test_invite_create_post_htmx(self, authenticated_client, group):
        response = authenticated_client.post(
            f'/group/{group.pk}/invite/create/', HTTP_HX_REQUEST='true'
        )
        assert response.status_code == 200

    def test_invite_expire_post(self, authenticated_client, group, user):
        invite = GroupInvite.objects.create(group=group, created_by=user)
        response = authenticated_client.post(
            f'/group/{group.pk}/invite/{invite.pk}/expire/'
        )
        assert response.status_code == 302

    def test_invite_expire_post_htmx(self, authenticated_client, group, user):
        invite = GroupInvite.objects.create(group=group, created_by=user)
        response = authenticated_client.post(
            f'/group/{group.pk}/invite/{invite.pk}/expire/',
            HTTP_HX_REQUEST='true',
        )
        assert response.status_code == 200

    def test_invite_confirm_get_valid_invite(self, group, user):
        student = User.objects.create_user(username='inv_student', password='pass')
        invite = GroupInvite.objects.create(group=group, created_by=user)
        client = Client()
        client.post('/accounts/login/', {'username': 'inv_student', 'password': 'pass'})
        response = client.get(f'/group/invite/{invite.token}/')
        assert response.status_code == 200

    def test_invite_confirm_get_is_owner(self, authenticated_client, group, user):
        invite = GroupInvite.objects.create(group=group, created_by=user)
        response = authenticated_client.get(f'/group/invite/{invite.token}/')
        assert response.status_code == 200

    def test_invite_confirm_get_already_joined(self, group, user):
        student = User.objects.create_user(username='already_joined_s', password='pass')
        GroupStudent.objects.create(group=group, student=student, is_active=True)
        invite = GroupInvite.objects.create(group=group, created_by=user)
        client = Client()
        client.post('/accounts/login/', {'username': 'already_joined_s', 'password': 'pass'})
        response = client.get(f'/group/invite/{invite.token}/')
        assert response.status_code == 200

    def test_invite_confirm_get_invalid_token(self, authenticated_client):
        response = authenticated_client.get('/group/invite/invalid-token-xyz-123/')
        assert response.status_code == 200

    def test_invite_confirm_post_join(self, group, user):
        student = User.objects.create_user(username='joining_student', password='pass')
        invite = GroupInvite.objects.create(group=group, created_by=user)
        client = Client()
        client.post('/accounts/login/', {'username': 'joining_student', 'password': 'pass'})
        response = client.post(f'/group/invite/{invite.token}/')
        assert response.status_code == 302

    def test_invite_confirm_post_blocked_owner(self, authenticated_client, group, user):
        invite = GroupInvite.objects.create(group=group, created_by=user)
        response = authenticated_client.post(f'/group/invite/{invite.token}/')
        assert response.status_code == 400

    def test_invite_confirm_post_invalid_token(self, authenticated_client):
        response = authenticated_client.post('/group/invite/nonexistent-token-abc/')
        assert response.status_code == 400

    def test_invite_confirm_post_reactivates_enrollment(self, group, user):
        student = User.objects.create_user(username='reactivate_s', password='pass')
        GroupStudent.objects.create(group=group, student=student, is_active=False)
        invite = GroupInvite.objects.create(group=group, created_by=user)
        client = Client()
        client.post('/accounts/login/', {'username': 'reactivate_s', 'password': 'pass'})
        response = client.post(f'/group/invite/{invite.token}/')
        assert response.status_code == 302

    # ── Shared list with actual shared group ────────────────────────────────

    def test_shared_list_with_shared_group(self, authenticated_client, user):
        other = User.objects.create_user(username='other_shared_v2', password='pass')
        other_group = Group.objects.create(
            name='SharedByOther', description='x' * 15, shift='Manhã', created_by=other
        )
        GroupSharing.objects.create(group=other_group, shared_with=user, shared_by=other, is_active=True)
        response = authenticated_client.get('/group/shared/')
        assert response.status_code == 200

    # ── Unauthorized access ─────────────────────────────────────────────────

    def test_detail_view_unauthorized_user(self, authenticated_client, user):
        other = User.objects.create_user(username='other_det2', password='pass')
        other_group = Group.objects.create(
            name='PrivateGrp', description='x' * 15, shift='Manhã', created_by=other
        )
        response = authenticated_client.get(f'/group/{other_group.pk}/')
        assert response.status_code == 403

    def test_share_view_unauthorized_user(self, authenticated_client, user):
        other = User.objects.create_user(username='other_share2', password='pass')
        other_group = Group.objects.create(
            name='PrivateShare', description='x' * 15, shift='Manhã', created_by=other
        )
        response = authenticated_client.get(f'/group/{other_group.pk}/share/')
        assert response.status_code == 403

    def test_archive_view_unauthorized_user(self, authenticated_client, user):
        other = User.objects.create_user(username='other_arc2', password='pass')
        other_group = Group.objects.create(
            name='PrivateArc', description='x' * 15, shift='Manhã', created_by=other
        )
        response = authenticated_client.post(f'/group/{other_group.pk}/archive/')
        assert response.status_code == 403

    def test_delete_view_post_unauthorized(self, authenticated_client, user):
        other = User.objects.create_user(username='other_del2', password='pass')
        other_group = Group.objects.create(
            name='PrivateDel', description='x' * 15, shift='Manhã', created_by=other
        )
        response = authenticated_client.post(f'/group/{other_group.pk}/delete/')
        assert response.status_code == 403

    # ── Share POST with invalid users ───────────────────────────────────────

    def test_share_view_post_invalid_users(self, authenticated_client, group):
        response = authenticated_client.post(
            f'/group/{group.pk}/share/', {'users': [99999]}
        )
        assert response.status_code == 200

    # ── Share view with ordering ─────────────────────────────────────────────

    def test_share_view_with_ordering(self, authenticated_client, group, user):
        other = User.objects.create_user(username='sort_teach_v', password='pass')
        GroupSharing.objects.create(group=group, shared_with=other, shared_by=user, is_active=True)
        response = authenticated_client.get(
            f'/group/{group.pk}/share/?sort=shared_with&order=asc'
        )
        assert response.status_code == 200

    # ── Expired invite ───────────────────────────────────────────────────────

    def test_invite_confirm_get_expired_invite(self, authenticated_client, group, user):
        from django.utils import timezone as tz
        past = tz.now() - timedelta(days=1)
        invite = GroupInvite(group=group, created_by=user, expires_at=past)
        invite.save()
        response = authenticated_client.get(f'/group/invite/{invite.token}/')
        assert response.status_code == 200

    # ── Unshare ──────────────────────────────────────────────────────────────

    def test_unshare_post(self, authenticated_client, group, user):
        other = User.objects.create_user(username='unshare_target_v', password='pass')
        sharing = GroupSharing.objects.create(
            group=group, shared_with=other, shared_by=user, is_active=True
        )
        response = authenticated_client.post(f'/group/{sharing.pk}/unshare/')
        assert response.status_code == 302


# ─── GroupSharingForm unit tests ────────────────────────────────────────────

@pytest.mark.django_db
class TestGroupSharingForm:
    def test_raises_when_group_pk_is_none(self):
        from group.forms.group import GroupSharingForm
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            GroupSharingForm(group_pk=None, request_user=None)

    def test_raises_when_request_user_is_none(self, user, group):
        from group.forms.group import GroupSharingForm
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            GroupSharingForm(group_pk=group.pk, request_user=None)

    def test_label_from_instance(self, user):
        from group.forms.group import GroupSharingWidget
        widget = GroupSharingWidget()
        assert widget.label_from_instance(user) == user.username


# ─── Group template tag tests ────────────────────────────────────────────────

@pytest.mark.django_db
class TestGroupTemplateTags:
    def test_archived_groups_is_archived_by_true(self, group, user):
        from group.templatetags.group_filters import archived_groups_is_archived_by
        GroupArchived.objects.create(group=group, user=user, is_archived=True)
        assert archived_groups_is_archived_by(group, user) is True

    def test_archived_groups_is_archived_by_false(self, group, user):
        from group.templatetags.group_filters import archived_groups_is_archived_by
        assert archived_groups_is_archived_by(group, user) is False


# ─── GroupReviewView ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestGroupReviewView:
    def test_owner_can_access(self, authenticated_client, group):
        response = authenticated_client.get(f'/group/{group.pk}/review/')
        assert response.status_code == 200

    def test_shared_teacher_can_access(self, user, group):
        shared = User.objects.create_user(username='shared_review', password='pass')
        GroupSharing.objects.create(group=group, shared_with=shared, shared_by=user, is_active=True)
        client = Client()
        client.post('/accounts/login/', {'username': 'shared_review', 'password': 'pass'})
        response = client.get(f'/group/{group.pk}/review/')
        assert response.status_code == 200

    def test_unrelated_user_gets_403(self, group):
        other = User.objects.create_user(username='other_review', password='pass')
        client = Client()
        client.post('/accounts/login/', {'username': 'other_review', 'password': 'pass'})
        response = client.get(f'/group/{group.pk}/review/')
        assert response.status_code == 403

    def test_unauthenticated_redirects(self, group):
        response = Client().get(f'/group/{group.pk}/review/')
        assert response.status_code == 302


# ─── GroupDetailView (stats tab) ─────────────────────────────────────────────

@pytest.mark.django_db
class TestGroupDetailView:
    def test_owner_can_access_stats(self, authenticated_client, group):
        response = authenticated_client.get(f'/group/{group.pk}/stats/')
        assert response.status_code == 200

    def test_shared_user_can_access_stats(self, group, user):
        shared = User.objects.create_user(username='shared_stats', password='pass')
        GroupSharing.objects.create(
            group=group, shared_with=shared, shared_by=user, is_active=True
        )
        client = Client()
        client.post('/accounts/login/', {'username': 'shared_stats', 'password': 'pass'})
        response = client.get(f'/group/{group.pk}/stats/')
        assert response.status_code == 200

    def test_non_owner_without_sharing_gets_403(self, group):
        other = User.objects.create_user(username='stranger_stats', password='pass')
        client = Client()
        client.post('/accounts/login/', {'username': 'stranger_stats', 'password': 'pass'})
        response = client.get(f'/group/{group.pk}/stats/')
        assert response.status_code == 403

    def test_unauthenticated_redirects(self, group):
        response = Client().get(f'/group/{group.pk}/stats/')
        assert response.status_code == 302

    def test_stats_with_submissions_and_at_risk_students(self, authenticated_client, user, group):
        activity1 = ActivityList.objects.create(title='Ativ 1', created_by=user)
        activity2 = ActivityList.objects.create(title='Ativ 2', created_by=user)
        link1 = ActivityListGroup.objects.create(group=group, activity_list=activity1)
        link2 = ActivityListGroup.objects.create(group=group, activity_list=activity2)

        ex1 = Exercise.objects.create(activity_list=activity1, type='discursive', statement='Q1', points=5)
        DiscursiveExercise.objects.create(exercise=ex1, min_words=0)
        ex2 = Exercise.objects.create(activity_list=activity2, type='discursive', statement='Q2', points=10)
        DiscursiveExercise.objects.create(exercise=ex2, min_words=0)

        s1 = User.objects.create_user(username='s1', password='pass')
        s2 = User.objects.create_user(username='s2', password='pass')
        s3 = User.objects.create_user(username='s3', password='pass')
        s4 = User.objects.create_user(username='s4', password='pass')
        for s in (s1, s2, s3, s4):
            GroupStudent.objects.create(group=group, student=s, is_active=True)

        sub1a = Submission.objects.create(student=s1, activity_link=link1, submitted_at=timezone.now())
        ExerciseAnswer.objects.create(submission=sub1a, exercise=ex1, is_correct=True, time_spent_seconds=120)
        sub1b = Submission.objects.create(student=s1, activity_link=link2, submitted_at=timezone.now())
        ExerciseAnswer.objects.create(submission=sub1b, exercise=ex2, is_correct=True, time_spent_seconds=90)

        sub2a = Submission.objects.create(student=s2, activity_link=link1, submitted_at=timezone.now())
        ExerciseAnswer.objects.create(submission=sub2a, exercise=ex1, is_correct=False, time_spent_seconds=30)

        # s4 starts an attempt but never submits anything -> counts as "abandoned"
        Submission.objects.create(student=s4, activity_link=link2)

        # s3 never attempts anything -> fully at risk

        response = authenticated_client.get(f'/group/{group.pk}/stats/')
        assert response.status_code == 200
        ctx = response.context
        assert ctx['students_enrolled'] == 4
        assert ctx['students_submitted'] == 2
        assert ctx['students_abandoned'] >= 1
        assert ctx['activities_count'] == 2
        assert ctx['avg_points'] is not None
        assert ctx['median_points'] is not None

        at_risk_names = {r['name'] for r in ctx['at_risk_students']}
        assert 's3' in at_risk_names or (s3.get_full_name() or s3.username) in at_risk_names
        kpis = ctx['activity_kpis']
        assert 'all' in kpis
        assert str(link1.pk) in kpis
        assert kpis[str(link1.pk)]['students_submitted'] == 2
        stats_link1 = next(a for a in ctx['activity_stats'] if a.pk == link1.pk)
        assert stats_link1.grades_submitted_count == 2


# ─── GroupGradesView ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestGroupGradesView:
    def test_owner_can_access(self, authenticated_client, group):
        response = authenticated_client.get(f'/group/{group.pk}/grades/')
        assert response.status_code == 200

    def test_shared_teacher_can_access(self, user, group):
        shared = User.objects.create_user(username='shared_grades', password='pass')
        GroupSharing.objects.create(group=group, shared_with=shared, shared_by=user, is_active=True)
        client = Client()
        client.post('/accounts/login/', {'username': 'shared_grades', 'password': 'pass'})
        response = client.get(f'/group/{group.pk}/grades/')
        assert response.status_code == 200

    def test_unrelated_user_gets_403(self, group):
        other = User.objects.create_user(username='other_grades', password='pass')
        client = Client()
        client.post('/accounts/login/', {'username': 'other_grades', 'password': 'pass'})
        response = client.get(f'/group/{group.pk}/grades/')
        assert response.status_code == 403

    def test_unauthenticated_redirects(self, group):
        response = Client().get(f'/group/{group.pk}/grades/')
        assert response.status_code == 302

    def test_no_activities_grand_total_is_dash(self, authenticated_client, group, user):
        s1 = User.objects.create_user(username='g_s1', password='pass')
        GroupStudent.objects.create(group=group, student=s1, is_active=True)
        response = authenticated_client.get(f'/group/{group.pk}/grades/')
        assert response.context['total_activities'] == 0
        row = response.context['students_grades'][0]
        assert row['total_fmt'] == '—'
        assert row['pct'] == 0
        assert row['submitted'] is False

    def test_grades_rows_reflect_submitted_and_pending(self, authenticated_client, user, group):
        activity = ActivityList.objects.create(title='Ativ', created_by=user)
        link = ActivityListGroup.objects.create(group=group, activity_list=activity)
        ex = Exercise.objects.create(activity_list=activity, type='discursive', statement='Q', points=10)
        DiscursiveExercise.objects.create(exercise=ex, min_words=0)

        s1 = User.objects.create_user(username='gr_s1', password='pass')
        s2 = User.objects.create_user(username='gr_s2', password='pass')
        GroupStudent.objects.create(group=group, student=s1, is_active=True)
        GroupStudent.objects.create(group=group, student=s2, is_active=True)

        sub = Submission.objects.create(student=s1, activity_link=link, submitted_at=timezone.now())
        ExerciseAnswer.objects.create(submission=sub, exercise=ex, is_correct=True)

        response = authenticated_client.get(f'/group/{group.pk}/grades/')
        rows = {r['name']: r for r in response.context['students_grades']}
        assert rows[s1.get_full_name() or s1.username]['submitted'] is True
        assert rows[s1.get_full_name() or s1.username]['pct'] == 100
        assert rows[s2.get_full_name() or s2.username]['submitted'] is False
        breakdown_s2 = rows[s2.get_full_name() or s2.username]['breakdown'][0]
        assert breakdown_s2['submitted'] is False
        assert breakdown_s2['grade_class'] == 'd'


# ─── Module-level formatting/grading helpers ─────────────────────────────────

class TestGroupViewsHelpers:
    def test_fmt_pts_none(self):
        from group.views import _fmt_pts
        assert _fmt_pts(None) == '—'

    def test_fmt_pts_strips_trailing_zeros(self):
        from group.views import _fmt_pts
        assert _fmt_pts(5.0) == '5'
        assert _fmt_pts(5.5) == '5.5'

    def test_fmt_dur_none_or_zero(self):
        from group.views import _fmt_dur
        assert _fmt_dur(None) == '—'
        assert _fmt_dur(0) == '—'

    def test_fmt_dur_seconds_only(self):
        from group.views import _fmt_dur
        assert _fmt_dur(45) == '45s'

    def test_fmt_dur_minutes_and_seconds(self):
        from group.views import _fmt_dur
        assert _fmt_dur(90) == '1min 30s'

    def test_fmt_dur_minutes_only(self):
        from group.views import _fmt_dur
        assert _fmt_dur(120) == '2min'

    def test_fmt_dur_hours_and_minutes(self):
        from group.views import _fmt_dur
        assert _fmt_dur(3900) == '1h 5min'

    def test_fmt_dur_hours_only(self):
        from group.views import _fmt_dur
        assert _fmt_dur(7200) == '2h'

    def test_grades_grade_class_boundaries(self):
        from group.views import GroupGradesView
        assert GroupGradesView._grade_class(95) == 'a'
        assert GroupGradesView._grade_class(75) == 'b'
        assert GroupGradesView._grade_class(55) == 'c'
        assert GroupGradesView._grade_class(10) == 'd'

    def test_rank_class(self):
        from group.views import GroupGradesView
        assert GroupGradesView._rank_class(1) == 'rank-1'
        assert GroupGradesView._rank_class(2) == 'rank-2'
        assert GroupGradesView._rank_class(3) == 'rank-3'
        assert GroupGradesView._rank_class(4) == 'rank-n'

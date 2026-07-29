from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.utils import timezone

from accounts.models import UserPreferences
from activity.models import ActivityList, ActivityListGroup, DiscursiveExercise, Exercise
from group.models import GroupStudent
from student.models import ExerciseAnswer, Submission


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def activity(user):
    return ActivityList.objects.create(title='Atividade Teste', created_by=user)


@pytest.fixture
def activity_link(group, activity):
    return ActivityListGroup.objects.create(group=group, activity_list=activity)


@pytest.fixture
def enrolled(user, group):
    return GroupStudent.objects.create(group=group, student=user, is_active=True)


@pytest.fixture
def discursive_exercise(activity):
    ex = Exercise.objects.create(
        activity_list=activity, type='discursive', statement='Q', points=10,
    )
    DiscursiveExercise.objects.create(exercise=ex, min_words=0)
    return ex


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


# ─── OverviewView ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestOverviewView:
    def test_unauthenticated_redirects(self):
        response = Client().get('/accounts/profile/overview/')
        assert response.status_code == 302

    def test_empty_overview(self, authenticated_client):
        response = authenticated_client.get('/accounts/profile/overview/')
        assert response.status_code == 200
        assert response.context['total_turmas'] == 0
        assert response.context['total_atividades'] == 0
        assert response.context['upcoming'] == []
        assert response.context['timeline'] == []

    def test_overdue_activity_is_flagged_and_sorted_last(
        self, authenticated_client, user, group, enrolled, activity, activity_link
    ):
        activity_link.ends_at = timezone.now() - timedelta(days=1)
        activity_link.save()
        response = authenticated_client.get('/accounts/profile/overview/')
        assert response.context['upcoming'][0]['urgency'] == 'overdue'
        assert response.context['upcoming'][0]['stripe'] == '#ef4444'

    def test_urgent_activity_within_two_days(
        self, authenticated_client, enrolled, activity_link
    ):
        activity_link.ends_at = timezone.now() + timedelta(hours=10)
        activity_link.save()
        response = authenticated_client.get('/accounts/profile/overview/')
        assert response.context['upcoming'][0]['urgency'] == 'urgent'

    def test_upcoming_activity_within_a_week(
        self, authenticated_client, enrolled, activity_link
    ):
        activity_link.ends_at = timezone.now() + timedelta(days=5)
        activity_link.save()
        response = authenticated_client.get('/accounts/profile/overview/')
        assert response.context['upcoming'][0]['urgency'] == 'upcoming'

    def test_normal_activity_beyond_a_week(
        self, authenticated_client, enrolled, activity_link
    ):
        activity_link.ends_at = timezone.now() + timedelta(days=30)
        activity_link.save()
        response = authenticated_client.get('/accounts/profile/overview/')
        assert response.context['upcoming'][0]['urgency'] == 'normal'

    def test_no_deadline_activity_has_none_urgency(
        self, authenticated_client, enrolled, activity_link
    ):
        response = authenticated_client.get('/accounts/profile/overview/')
        assert response.context['upcoming'][0]['urgency'] == 'none'
        assert response.context['upcoming'][0]['stripe'] == '#94a3b8'

    def test_submitted_activity_excluded_from_upcoming(
        self, authenticated_client, user, enrolled, activity_link
    ):
        Submission.objects.create(student=user, activity_link=activity_link, submitted_at=timezone.now())
        response = authenticated_client.get('/accounts/profile/overview/')
        assert response.context['upcoming'] == []
        assert response.context['total_concluidas'] == 1

    def test_timeline_shows_recent_submission_with_pct(
        self, authenticated_client, user, enrolled, activity_link, discursive_exercise
    ):
        sub = Submission.objects.create(student=user, activity_link=activity_link, submitted_at=timezone.now())
        ExerciseAnswer.objects.create(submission=sub, exercise=discursive_exercise, is_correct=True)
        response = authenticated_client.get('/accounts/profile/overview/')
        entry = response.context['timeline'][0]
        assert entry['pct'] == 100
        assert entry['earned_fmt'] == '10.0'

    def test_timeline_pct_none_when_no_answers(
        self, authenticated_client, user, enrolled, activity_link
    ):
        Submission.objects.create(student=user, activity_link=activity_link, submitted_at=timezone.now())
        response = authenticated_client.get('/accounts/profile/overview/')
        entry = response.context['timeline'][0]
        assert entry['pct'] is None
        assert entry['earned_fmt'] is None


# ─── PendingView ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPendingView:
    def test_unauthenticated_redirects(self):
        response = Client().get('/accounts/profile/pending/')
        assert response.status_code == 302

    def test_empty_pending(self, authenticated_client):
        response = authenticated_client.get('/accounts/profile/pending/')
        assert response.status_code == 200
        assert response.context['pending_count'] == 0

    def test_pending_lists_unsubmitted_activity_with_teacher_and_urgency(
        self, authenticated_client, user, group, enrolled, activity, activity_link
    ):
        activity_link.ends_at = timezone.now() - timedelta(days=1)
        activity_link.save()
        response = authenticated_client.get('/accounts/profile/pending/')
        entry = response.context['pending'][0]
        assert entry['urgency'] == 'overdue'
        assert entry['teacher'] == (user.get_full_name() or user.username)
        assert response.context['pending_count'] == 1

    def test_pending_excludes_submitted(
        self, authenticated_client, user, enrolled, activity_link
    ):
        Submission.objects.create(student=user, activity_link=activity_link, submitted_at=timezone.now())
        response = authenticated_client.get('/accounts/profile/pending/')
        assert response.context['pending_count'] == 0

    def test_pending_urgency_buckets(self, authenticated_client, user, group, enrolled):
        deltas = {
            'urgent': timedelta(hours=10),
            'upcoming': timedelta(days=5),
            'normal': timedelta(days=30),
        }
        for label, delta in deltas.items():
            act = ActivityList.objects.create(title=f'Act {label}', created_by=user)
            link = ActivityListGroup.objects.create(
                group=group, activity_list=act, ends_at=timezone.now() + delta,
            )
        act_none = ActivityList.objects.create(title='Act none', created_by=user)
        link_none = ActivityListGroup.objects.create(group=group, activity_list=act_none)
        response = authenticated_client.get('/accounts/profile/pending/')
        urgencies = {p['link'].pk: p['urgency'] for p in response.context['pending']}
        assert urgencies[link.pk] == 'normal'
        assert urgencies[link_none.pk] == 'none'


# ─── ProfileView (notas) ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProfileView:
    def test_unauthenticated_redirects(self):
        response = Client().get('/accounts/profile/notes/')
        assert response.status_code == 302

    def test_empty_profile(self, authenticated_client):
        response = authenticated_client.get('/accounts/profile/notes/')
        assert response.status_code == 200
        assert response.context['groups_grades'] == []
        assert response.context['total_submitted'] == 0
        assert response.context['total_pending'] == 0

    def test_grade_class_boundaries(self):
        from accounts.views import ProfileView
        assert ProfileView._grade_class(95) == 'a'
        assert ProfileView._grade_class(75) == 'b'
        assert ProfileView._grade_class(55) == 'c'
        assert ProfileView._grade_class(20) == 'd'

    def test_submitted_activity_computes_score_and_grade(
        self, authenticated_client, user, group, enrolled, activity, activity_link, discursive_exercise
    ):
        sub = Submission.objects.create(student=user, activity_link=activity_link, submitted_at=timezone.now())
        ExerciseAnswer.objects.create(submission=sub, exercise=discursive_exercise, is_correct=True)
        response = authenticated_client.get('/accounts/profile/notes/')
        group_grade = response.context['groups_grades'][0]
        assert group_grade['submitted'] is True
        assert group_grade['pct'] == 100
        assert group_grade['grade_class'] == 'a'
        breakdown = group_grade['breakdown'][0]
        assert breakdown['submitted'] is True
        assert breakdown['pct'] == 100

    def test_unsubmitted_overdue_activity_marked_in_breakdown(
        self, authenticated_client, enrolled, activity_link, discursive_exercise
    ):
        activity_link.ends_at = timezone.now() - timedelta(days=1)
        activity_link.save()
        response = authenticated_client.get('/accounts/profile/notes/')
        group_grade = response.context['groups_grades'][0]
        assert group_grade['submitted'] is False
        breakdown = group_grade['breakdown'][0]
        assert breakdown['submitted'] is False
        assert breakdown['is_overdue'] is True
        assert breakdown['grade_class'] == 'd'

    def test_unsubmitted_not_overdue_activity(
        self, authenticated_client, enrolled, activity_link, discursive_exercise
    ):
        response = authenticated_client.get('/accounts/profile/notes/')
        breakdown = response.context['groups_grades'][0]['breakdown'][0]
        assert breakdown['is_overdue'] is False

    def test_group_with_no_activity_links_has_dash_total(
        self, authenticated_client, enrolled
    ):
        response = authenticated_client.get('/accounts/profile/notes/')
        group_grade = response.context['groups_grades'][0]
        assert group_grade['total_fmt'] == '—'
        assert group_grade['total_activities'] == 0


# ─── TurmasView ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTurmasView:
    def test_unauthenticated_redirects(self):
        response = Client().get('/accounts/profile/turmas/')
        assert response.status_code == 302

    def test_empty_turmas(self, authenticated_client):
        response = authenticated_client.get('/accounts/profile/turmas/')
        assert response.status_code == 200
        assert response.context['turmas'] == []

    def test_turma_progress_percentage(
        self, authenticated_client, user, group, enrolled, activity, activity_link
    ):
        Submission.objects.create(student=user, activity_link=activity_link, submitted_at=timezone.now())
        response = authenticated_client.get('/accounts/profile/turmas/')
        turma = response.context['turmas'][0]
        assert turma['total'] == 1
        assert turma['submitted'] == 1
        assert turma['pending'] == 0
        assert turma['pct'] == 100
        assert turma['teacher'] == (user.get_full_name() or user.username)

    def test_turma_with_no_activities_has_zero_pct(
        self, authenticated_client, enrolled
    ):
        response = authenticated_client.get('/accounts/profile/turmas/')
        turma = response.context['turmas'][0]
        assert turma['total'] == 0
        assert turma['pct'] == 0

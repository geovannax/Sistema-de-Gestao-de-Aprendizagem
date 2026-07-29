import zipfile
from io import BytesIO

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.utils import timezone

from activity.models import (
    ActivityList,
    ActivityListGroup,
    CodeExercise,
    CompleteCodeExercise,
    DiscursiveExercise,
    Exercise,
    ExerciseOption,
    MultipleChoiceExercise,
)
from group.models import Group, GroupSharing, GroupStudent
from student.models import CodeExecution, ExerciseAnswer, Submission

from dataset.views import _aggregate_stats


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def activity(user):
    return ActivityList.objects.create(title='Atividade Teste', created_by=user)


@pytest.fixture
def activity_link(group, activity):
    return ActivityListGroup.objects.create(group=group, activity_list=activity)


@pytest.fixture
def student_user():
    return User.objects.create_user(username='aluno1', password='pass123')


@pytest.fixture
def enrolled(student_user, group):
    return GroupStudent.objects.create(group=group, student=student_user, is_active=True)


@pytest.fixture
def discursive_exercise(activity):
    ex = Exercise.objects.create(
        activity_list=activity, type='discursive', statement='Explique OOP.', points=10,
    )
    DiscursiveExercise.objects.create(exercise=ex, min_words=0)
    return ex


@pytest.fixture
def mc_exercise(activity):
    ex = Exercise.objects.create(
        activity_list=activity, type='multiple_choice', statement='Capital?', points=5,
    )
    mc = MultipleChoiceExercise.objects.create(exercise=ex)
    ExerciseOption.objects.create(exercise=mc, text='São Paulo', is_correct=False)
    ExerciseOption.objects.create(exercise=mc, text='Brasília', is_correct=True)
    return ex


@pytest.fixture
def code_exercise(activity):
    ex = Exercise.objects.create(
        activity_list=activity, type='code', statement='Escreva um código.', points=5,
    )
    CodeExercise.objects.create(exercise=ex, language='python')
    return ex


@pytest.fixture
def complete_code_exercise(activity):
    ex = Exercise.objects.create(
        activity_list=activity, type='complete_code', statement='Complete.', points=5,
    )
    CompleteCodeExercise.objects.create(
        exercise=ex, language='python', starter_code='print(___)', complete_code='print(1)',
    )
    return ex


@pytest.fixture
def submission(student_user, activity_link):
    return Submission.objects.create(
        student=student_user, activity_link=activity_link, submitted_at=timezone.now(),
    )


# ─── _aggregate_stats helper ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestAggregateStatsWithLinkPks:
    def test_scoped_to_specific_activity_links(
        self, group, activity_link, enrolled, submission, discursive_exercise
    ):
        ExerciseAnswer.objects.create(submission=submission, exercise=discursive_exercise, is_correct=True)
        stats = _aggregate_stats([group], link_pks=[activity_link.pk])
        assert stats['students'] == 1
        assert stats['activities'] == 1
        assert stats['submissions'] == 1
        assert stats['answers'] == 1

    def test_no_groups_returns_zeroed_stats(self):
        stats = _aggregate_stats([])
        assert stats == {
            'students': 0, 'activities': 0, 'submissions': 0, 'answers': 0, 'executions': 0,
        }


# ─── DatasetListView ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDatasetListView:
    def test_unauthenticated_redirects(self):
        response = Client().get('/dataset/')
        assert response.status_code == 302

    def test_lists_owned_group(self, authenticated_client, group):
        response = authenticated_client.get('/dataset/')
        assert response.status_code == 200
        assert list(response.context['owned_groups']) == [group]
        assert list(response.context['shared_groups']) == []

    def test_lists_shared_group(self, authenticated_client, user, group):
        other = User.objects.create_user(username='other_teacher', password='pass123')
        GroupSharing.objects.create(group=group, shared_with=other, shared_by=user, is_active=True)
        client = Client()
        client.post('/accounts/login/', {'username': 'other_teacher', 'password': 'pass123'})
        response = client.get('/dataset/')
        assert list(response.context['shared_groups']) == [group]


# ─── DatasetActivitiesPartial ────────────────────────────────────────────────

@pytest.mark.django_db
class TestDatasetActivitiesPartial:
    def test_no_filter_lists_all_accessible_activities(self, authenticated_client, activity, activity_link):
        response = authenticated_client.get('/dataset/htmx/activities/')
        assert response.status_code == 200
        assert f'value="{activity.pk}"' in response.content.decode()
        assert activity.title in response.content.decode()

    def test_filter_by_group(self, authenticated_client, group, activity, activity_link):
        response = authenticated_client.get('/dataset/htmx/activities/', {'group': [str(group.pk)]})
        assert f'value="{activity.pk}"' in response.content.decode()

    def test_filter_by_non_accessible_group_returns_empty(self, authenticated_client, activity, activity_link):
        response = authenticated_client.get('/dataset/htmx/activities/', {'group': ['99999']})
        assert response.content.decode() == ''

    def test_non_digit_group_param_ignored(self, authenticated_client):
        response = authenticated_client.get('/dataset/htmx/activities/', {'group': ['abc']})
        assert response.status_code == 200


# ─── DatasetPreviewPartial ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestDatasetPreviewPartial:
    def test_empty_scope_has_zero_rows(self, authenticated_client):
        response = authenticated_client.get('/dataset/htmx/preview/')
        rows = {d['key']: d['rows'] for d in response.context['datasets']}
        assert rows['groups'] == 0
        assert rows['all'] == 0

    def test_scope_without_activity_filter_counts_all(
        self, authenticated_client, group, activity, activity_link, enrolled, submission
    ):
        response = authenticated_client.get('/dataset/htmx/preview/', {'group': [str(group.pk)]})
        rows = {d['key']: d['rows'] for d in response.context['datasets']}
        assert rows['groups'] == 1
        assert rows['students'] == 1
        assert rows['submissions'] == 1
        assert rows['all'] is None

    def test_scope_with_activity_filter(
        self, authenticated_client, group, activity, activity_link, enrolled, submission
    ):
        response = authenticated_client.get(
            '/dataset/htmx/preview/',
            {'group': [str(group.pk)], 'activity': [str(activity.pk)]},
        )
        rows = {d['key']: d['rows'] for d in response.context['datasets']}
        assert rows['activities'] == 1
        assert '_qs=' not in response.context['download_qs']

    def test_returns_error_response_when_scope_resolution_fails(self, authenticated_client):
        from unittest.mock import patch
        from django.http import HttpResponse
        error_response = HttpResponse('erro', status=400)
        with patch('dataset.views._resolve_scope', return_value=([], None, error_response)):
            response = authenticated_client.get('/dataset/htmx/preview/')
        assert response.status_code == 400


# ─── DatasetGroupView ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDatasetGroupView:
    def test_unauthenticated_redirects(self, group):
        response = Client().get(f'/dataset/{group.pk}/')
        assert response.status_code == 302

    def test_owner_has_access(self, authenticated_client, group, activity, activity_link, enrolled, submission):
        response = authenticated_client.get(f'/dataset/{group.pk}/')
        assert response.status_code == 200
        assert response.context['stats']['students'] == 1
        assert response.context['stats']['submissions'] == 1

    def test_shared_teacher_has_access(self, user, group):
        other = User.objects.create_user(username='shared_teacher', password='pass123')
        GroupSharing.objects.create(group=group, shared_with=other, shared_by=user, is_active=True)
        client = Client()
        client.post('/accounts/login/', {'username': 'shared_teacher', 'password': 'pass123'})
        response = client.get(f'/dataset/{group.pk}/')
        assert response.status_code == 200

    def test_unrelated_teacher_gets_403(self, group):
        User.objects.create_user(username='outsider', password='pass123')
        client = Client()
        client.post('/accounts/login/', {'username': 'outsider', 'password': 'pass123'})
        response = client.get(f'/dataset/{group.pk}/')
        assert response.status_code == 403


# ─── DatasetDownloadView ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestDatasetDownloadView:
    def test_unauthenticated_redirects(self):
        response = Client().get('/dataset/download/groups/')
        assert response.status_code == 302

    def test_invalid_ds_type_returns_404(self, authenticated_client):
        response = authenticated_client.get('/dataset/download/bogus/')
        assert response.status_code == 404

    def test_dl_cookie_is_set_when_token_present(self, authenticated_client):
        response = authenticated_client.get('/dataset/download/groups/', {'dl': 'tok123'})
        assert response.cookies['dl_tok123'].value == '1'

    def test_returns_error_response_when_scope_resolution_fails(self, authenticated_client):
        from unittest.mock import patch
        from django.http import HttpResponse
        error_response = HttpResponse('erro', status=400)
        with patch('dataset.views._resolve_scope', return_value=([], None, error_response)):
            response = authenticated_client.get('/dataset/download/groups/')
        assert response.status_code == 400

    def test_csv_groups(self, authenticated_client, group):
        response = authenticated_client.get('/dataset/download/groups/')
        assert response.status_code == 200
        assert response['Content-Type'].startswith('text/csv')
        body = response.content.decode('utf-8-sig')
        assert group.name in body

    def test_csv_students(self, authenticated_client, group, enrolled):
        response = authenticated_client.get('/dataset/download/students/')
        body = response.content.decode('utf-8-sig')
        assert 'student_anon_id' in body
        assert str(group.pk) in body

    def test_csv_activities_with_activity_filter(self, authenticated_client, group, activity, activity_link):
        response = authenticated_client.get(
            '/dataset/download/activities/', {'activity': [str(activity.pk)]}
        )
        body = response.content.decode('utf-8-sig')
        assert activity.title in body

    def test_csv_exercises_includes_complete_code_columns(
        self, authenticated_client, activity, activity_link, complete_code_exercise
    ):
        response = authenticated_client.get(
            '/dataset/download/exercises/', {'activity': [str(activity.pk)]}
        )
        body = response.content.decode('utf-8-sig')
        assert 'print(___)' in body
        assert 'print(1)' in body

    def test_csv_exercises_non_complete_code_has_blank_gabarito(
        self, authenticated_client, activity_link, discursive_exercise
    ):
        response = authenticated_client.get('/dataset/download/exercises/')
        body = response.content.decode('utf-8-sig')
        assert discursive_exercise.statement in body

    def test_csv_options(self, authenticated_client, activity, activity_link, mc_exercise):
        response = authenticated_client.get(
            '/dataset/download/options/', {'activity': [str(activity.pk)]}
        )
        body = response.content.decode('utf-8-sig')
        assert 'Brasília' in body
        assert 'São Paulo' in body

    def test_csv_submissions(
        self, authenticated_client, activity, activity_link, submission, discursive_exercise
    ):
        ExerciseAnswer.objects.create(submission=submission, exercise=discursive_exercise, is_correct=True)
        response = authenticated_client.get(
            '/dataset/download/submissions/', {'activity': [str(activity.pk)]}
        )
        body = response.content.decode('utf-8-sig')
        assert str(submission.pk) in body

    def test_csv_answers(
        self, authenticated_client, activity, activity_link, submission, discursive_exercise
    ):
        ExerciseAnswer.objects.create(submission=submission, exercise=discursive_exercise, is_correct=None)
        response = authenticated_client.get(
            '/dataset/download/answers/', {'activity': [str(activity.pk)]}
        )
        body = response.content.decode('utf-8-sig')
        assert 'discursive' in body

    def test_csv_engagement_includes_incomplete_attempt(
        self, authenticated_client, activity, activity_link, student_user
    ):
        Submission.objects.create(student=student_user, activity_link=activity_link)
        response = authenticated_client.get(
            '/dataset/download/engagement/', {'activity': [str(activity.pk)]}
        )
        body = response.content.decode('utf-8-sig')
        assert 'False' in body

    def test_csv_engagement_includes_completed_attempt(
        self, authenticated_client, activity_link, submission, discursive_exercise
    ):
        ExerciseAnswer.objects.create(submission=submission, exercise=discursive_exercise, is_correct=True)
        response = authenticated_client.get('/dataset/download/engagement/')
        body = response.content.decode('utf-8-sig')
        assert 'True' in body

    def test_csv_executions(
        self, authenticated_client, activity, activity_link, submission, code_exercise
    ):
        CodeExecution.objects.create(
            submission=submission, exercise=code_exercise, source_code='print(1)',
            results=[{'is_correct': True}],
        )
        response = authenticated_client.get(
            '/dataset/download/executions/', {'activity': [str(activity.pk)]}
        )
        body = response.content.decode('utf-8-sig')
        assert 'True' in body

    def test_csv_code_journey_tracks_delta_between_executions(
        self, authenticated_client, activity, activity_link, submission, code_exercise
    ):
        CodeExecution.objects.create(
            submission=submission, exercise=code_exercise, source_code='v1',
            results=[{'is_correct': False}, {'is_correct': False}],
        )
        CodeExecution.objects.create(
            submission=submission, exercise=code_exercise, source_code='v2',
            results=[{'is_correct': True}, {'is_correct': False}],
        )
        response = authenticated_client.get(
            '/dataset/download/code_journey/', {'activity': [str(activity.pk)]}
        )
        body = response.content.decode('utf-8-sig')
        assert 'v1' in body
        assert 'v2' in body

    def test_download_all_returns_zip_with_all_csvs(
        self, authenticated_client, group, activity_link, submission, discursive_exercise
    ):
        ExerciseAnswer.objects.create(submission=submission, exercise=discursive_exercise, is_correct=True)
        response = authenticated_client.get('/dataset/download/all/')
        assert response['Content-Type'] == 'application/zip'
        zf = zipfile.ZipFile(BytesIO(response.content))
        names = zf.namelist()
        assert 'turmas.csv' in names
        assert 'submissoes.csv' in names
        assert 'jornada_de_codigo.csv' in names

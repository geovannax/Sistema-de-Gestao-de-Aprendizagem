import pytest
from datetime import timedelta
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
def mc_exercise(activity):
    ex = Exercise.objects.create(
        activity_list=activity,
        type='multiple_choice',
        statement='Qual a capital do Brasil?',
        points=5,
    )
    mc = MultipleChoiceExercise.objects.create(exercise=ex)
    opt_wrong = ExerciseOption.objects.create(exercise=mc, text='São Paulo', is_correct=False)
    opt_correct = ExerciseOption.objects.create(exercise=mc, text='Brasília', is_correct=True)
    return ex, mc, opt_wrong, opt_correct


@pytest.fixture
def discursive_exercise(activity):
    ex = Exercise.objects.create(
        activity_list=activity,
        type='discursive',
        statement='Explique OOP.',
        points=10,
    )
    DiscursiveExercise.objects.create(exercise=ex, min_words=10)
    return ex


@pytest.fixture
def code_exercise(activity):
    ex = Exercise.objects.create(
        activity_list=activity,
        type='code',
        statement='Escreva um código.',
        points=5,
    )
    CodeExercise.objects.create(exercise=ex, language='python')
    return ex


@pytest.fixture
def complete_code_exercise(activity):
    ex = Exercise.objects.create(
        activity_list=activity,
        type='complete_code',
        statement='Complete o código.',
        points=5,
    )
    CompleteCodeExercise.objects.create(exercise=ex, language='python', starter_code='print(___)')
    return ex


@pytest.fixture
def submission(user, activity_link):
    return Submission.objects.create(student=user, activity_link=activity_link)


@pytest.fixture
def submitted_submission(user, activity_link):
    return Submission.objects.create(
        student=user,
        activity_link=activity_link,
        submitted_at=timezone.now(),
    )


# ─── Models ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSubmissionStr:
    def test_str(self, user, activity_link):
        sub = Submission.objects.create(student=user, activity_link=activity_link)
        assert user.username in str(sub)
        assert activity_link.activity_list.title in str(sub)


# ─── Dashboard ───────────────────────────────────────────────────────────────

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


# ─── Group Detail ─────────────────────────────────────────────────────────────

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

    def test_pending_and_completed_split(self, authenticated_client, user, group, activity_link):
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        # submitted → goes to completed_links
        Submission.objects.create(
            student=user,
            activity_link=activity_link,
            submitted_at=timezone.now(),
        )
        response = authenticated_client.get(f'/student/group/{group.pk}/')
        assert response.status_code == 200
        assert len(response.context['completed_links']) == 1
        assert len(response.context['pending_links']) == 0

    def test_in_progress_is_pending(self, authenticated_client, user, group, activity_link):
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        # submission without submitted_at → goes to pending_links
        Submission.objects.create(student=user, activity_link=activity_link)
        response = authenticated_client.get(f'/student/group/{group.pk}/')
        assert response.status_code == 200
        assert len(response.context['pending_links']) == 1
        assert len(response.context['completed_links']) == 0


# ─── Student Activity View ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestStudentActivityView:
    def test_unauthenticated_redirects(self, activity_link):
        response = Client().get(f'/student/activity/{activity_link.pk}/')
        assert response.status_code == 302

    def test_not_enrolled_returns_404(self, authenticated_client, activity_link):
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/')
        assert response.status_code == 404

    def test_nonexistent_link_returns_404(self, authenticated_client, enrolled):
        response = authenticated_client.get('/student/activity/99999/')
        assert response.status_code == 404

    def test_creates_submission_on_first_access(self, authenticated_client, user, activity_link, enrolled):
        assert not Submission.objects.filter(student=user, activity_link=activity_link).exists()
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/')
        assert response.status_code == 200
        assert Submission.objects.filter(student=user, activity_link=activity_link).exists()

    def test_redirects_to_result_when_max_attempts_reached(
        self, authenticated_client, activity_link, enrolled, submitted_submission
    ):
        activity_link.activity_list.max_attempts = 1
        activity_link.activity_list.save()
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/')
        assert response.status_code == 302
        assert 'result' in response['Location']

    def test_starts_new_attempt_if_submitted_and_unlimited(
        self, authenticated_client, activity_link, enrolled, submitted_submission
    ):
        # After an intentional submit, all activities (even unlimited) block retries
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/')
        assert response.status_code == 302
        assert 'result' in response['Location']

    def test_code_answer_uses_latest_execution_correctness(
        self, authenticated_client, activity_link, enrolled, code_exercise, submission
    ):
        from student.models import CodeExecution
        source = 'print("hello")'
        CodeExecution.objects.create(
            submission=submission,
            exercise=code_exercise,
            source_code=source,
            results=[{'is_correct': True, 'status': 'correct'}],
        )
        authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {
                'current_exercise_pk': code_exercise.pk,
                'navigate_to_pk': code_exercise.pk,
                'answer_text': source,
            },
        )
        answer = ExerciseAnswer.objects.get(submission=submission, exercise=code_exercise)
        assert answer.is_correct is True

    def test_get_with_exercise_param(self, authenticated_client, activity_link, enrolled, mc_exercise):
        ex, mc, opt_wrong, opt_correct = mc_exercise
        response = authenticated_client.get(
            f'/student/activity/{activity_link.pk}/?exercise={ex.pk}'
        )
        assert response.status_code == 200

    def test_get_with_invalid_exercise_param_falls_back_to_first(
        self, authenticated_client, activity_link, enrolled, discursive_exercise
    ):
        response = authenticated_client.get(
            f'/student/activity/{activity_link.pk}/?exercise=99999'
        )
        assert response.status_code == 200
        assert response.context['current_exercise'].pk == discursive_exercise.pk

    def test_get_with_htmx_returns_partial(self, authenticated_client, activity_link, enrolled):
        response = authenticated_client.get(
            f'/student/activity/{activity_link.pk}/',
            HTTP_HX_REQUEST='true',
        )
        assert response.status_code == 200

    def test_prev_and_next_exercise_navigation(
        self, authenticated_client, activity_link, enrolled
    ):
        ex1 = Exercise.objects.create(
            activity_list=activity_link.activity_list,
            type='discursive',
            statement='Questão 1',
        )
        ex2 = Exercise.objects.create(
            activity_list=activity_link.activity_list,
            type='discursive',
            statement='Questão 2',
        )
        DiscursiveExercise.objects.create(exercise=ex1)
        DiscursiveExercise.objects.create(exercise=ex2)
        # navigate to second exercise → prev exists, next is None
        response = authenticated_client.get(
            f'/student/activity/{activity_link.pk}/?exercise={ex2.pk}'
        )
        assert response.status_code == 200
        assert response.context['prev_exercise'].pk == ex1.pk
        assert response.context['next_exercise'] is None

    def test_next_exercise_present_when_not_last(
        self, authenticated_client, activity_link, enrolled
    ):
        ex1 = Exercise.objects.create(
            activity_list=activity_link.activity_list,
            type='discursive',
            statement='Questão 1',
        )
        ex2 = Exercise.objects.create(
            activity_list=activity_link.activity_list,
            type='discursive',
            statement='Questão 2',
        )
        DiscursiveExercise.objects.create(exercise=ex1)
        DiscursiveExercise.objects.create(exercise=ex2)
        # navigate to first → prev is None, next exists
        response = authenticated_client.get(
            f'/student/activity/{activity_link.pk}/?exercise={ex1.pk}'
        )
        assert response.status_code == 200
        assert response.context['prev_exercise'] is None
        assert response.context['next_exercise'].pk == ex2.pk

    # ── POST ─────────────────────────────────────────────────────────────────

    def test_post_saves_discursive_answer(
        self, authenticated_client, activity_link, enrolled, discursive_exercise, submission
    ):
        response = authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {
                'current_exercise_pk': discursive_exercise.pk,
                'navigate_to_pk': discursive_exercise.pk,
                'answer_text': 'Minha resposta sobre OOP',
            },
        )
        assert response.status_code == 200
        assert ExerciseAnswer.objects.filter(
            submission=submission, exercise=discursive_exercise
        ).exists()

    def test_post_saves_code_answer(
        self, authenticated_client, activity_link, enrolled, code_exercise, submission
    ):
        authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {
                'current_exercise_pk': code_exercise.pk,
                'navigate_to_pk': code_exercise.pk,
                'answer_text': 'print("hello")',
            },
        )
        assert ExerciseAnswer.objects.filter(
            submission=submission, exercise=code_exercise
        ).exists()

    def test_post_saves_complete_code_answer(
        self, authenticated_client, activity_link, enrolled, complete_code_exercise, submission
    ):
        authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {
                'current_exercise_pk': complete_code_exercise.pk,
                'navigate_to_pk': complete_code_exercise.pk,
                'answer_text': "print('hello')",
            },
        )
        assert ExerciseAnswer.objects.filter(
            submission=submission, exercise=complete_code_exercise
        ).exists()

    def test_complete_code_correct_answer_auto_graded(
        self, authenticated_client, activity_link, enrolled, submission, activity
    ):
        ex = Exercise.objects.create(activity_list=activity, type='complete_code', statement='Q', points=1)
        CompleteCodeExercise.objects.create(
            exercise=ex, language='python', starter_code='x = ___', complete_code='x = 42'
        )
        authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {'current_exercise_pk': ex.pk, 'navigate_to_pk': ex.pk, 'answer_text': 'x = 42'},
        )
        answer = ExerciseAnswer.objects.get(submission=submission, exercise=ex)
        assert answer.is_correct is True

    def test_complete_code_whitespace_ignored_in_grading(
        self, authenticated_client, activity_link, enrolled, submission, activity
    ):
        ex = Exercise.objects.create(activity_list=activity, type='complete_code', statement='Q', points=1)
        CompleteCodeExercise.objects.create(
            exercise=ex, language='python', starter_code='x = ___', complete_code='x=42'
        )
        authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {'current_exercise_pk': ex.pk, 'navigate_to_pk': ex.pk, 'answer_text': 'x  =  42'},
        )
        answer = ExerciseAnswer.objects.get(submission=submission, exercise=ex)
        assert answer.is_correct is True

    def test_complete_code_wrong_answer_auto_graded(
        self, authenticated_client, activity_link, enrolled, submission, activity
    ):
        ex = Exercise.objects.create(activity_list=activity, type='complete_code', statement='Q', points=1)
        CompleteCodeExercise.objects.create(
            exercise=ex, language='python', starter_code='x = ___', complete_code='x = 42'
        )
        authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {'current_exercise_pk': ex.pk, 'navigate_to_pk': ex.pk, 'answer_text': 'x = 99'},
        )
        answer = ExerciseAnswer.objects.get(submission=submission, exercise=ex)
        assert answer.is_correct is False

    def test_post_saves_correct_multiple_choice(
        self, authenticated_client, activity_link, enrolled, mc_exercise, submission
    ):
        ex, mc, opt_wrong, opt_correct = mc_exercise
        authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {
                'current_exercise_pk': ex.pk,
                'navigate_to_pk': ex.pk,
                'selected_option': opt_correct.pk,
            },
        )
        answer = ExerciseAnswer.objects.get(submission=submission, exercise=ex)
        assert answer.selected_option == opt_correct
        assert answer.is_correct is True

    def test_post_saves_wrong_multiple_choice(
        self, authenticated_client, activity_link, enrolled, mc_exercise, submission
    ):
        ex, mc, opt_wrong, opt_correct = mc_exercise
        authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {
                'current_exercise_pk': ex.pk,
                'navigate_to_pk': ex.pk,
                'selected_option': opt_wrong.pk,
            },
        )
        answer = ExerciseAnswer.objects.get(submission=submission, exercise=ex)
        assert answer.is_correct is False

    def test_post_mc_invalid_option_pk_not_saved(
        self, authenticated_client, activity_link, enrolled, mc_exercise, submission
    ):
        ex, mc, opt_wrong, opt_correct = mc_exercise
        authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {
                'current_exercise_pk': ex.pk,
                'navigate_to_pk': ex.pk,
                'selected_option': '99999',
            },
        )
        assert not ExerciseAnswer.objects.filter(submission=submission, exercise=ex).exists()

    def test_post_mc_no_option_not_saved(
        self, authenticated_client, activity_link, enrolled, mc_exercise, submission
    ):
        ex, mc, opt_wrong, opt_correct = mc_exercise
        authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {'current_exercise_pk': ex.pk, 'navigate_to_pk': ex.pk},
        )
        assert not ExerciseAnswer.objects.filter(submission=submission, exercise=ex).exists()

    def test_post_empty_text_not_saved(
        self, authenticated_client, activity_link, enrolled, discursive_exercise, submission
    ):
        authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {
                'current_exercise_pk': discursive_exercise.pk,
                'navigate_to_pk': discursive_exercise.pk,
                'answer_text': '   ',
            },
        )
        assert not ExerciseAnswer.objects.filter(
            submission=submission, exercise=discursive_exercise
        ).exists()

    def test_post_non_digit_exercise_pk_ignored(
        self, authenticated_client, activity_link, enrolled, submission
    ):
        response = authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {'current_exercise_pk': 'abc', 'answer_text': 'something'},
        )
        assert response.status_code == 200

    def test_post_nonexistent_exercise_pk_ignored(
        self, authenticated_client, activity_link, enrolled, submission
    ):
        response = authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {'current_exercise_pk': '99999', 'answer_text': 'something'},
        )
        assert response.status_code == 200

    def test_post_htmx_returns_partial(
        self, authenticated_client, activity_link, enrolled, submission
    ):
        response = authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {'current_exercise_pk': '', 'answer_text': ''},
            HTTP_HX_REQUEST='true',
        )
        assert response.status_code == 200

    def test_post_redirects_to_result_when_max_attempts_reached(
        self, authenticated_client, activity_link, enrolled, submitted_submission
    ):
        activity_link.activity_list.max_attempts = 1
        activity_link.activity_list.save()
        response = authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {'current_exercise_pk': '', 'answer_text': ''},
        )
        assert response.status_code == 302
        assert 'result' in response['Location']

    def test_post_updates_existing_answer(
        self, authenticated_client, activity_link, enrolled, discursive_exercise, submission
    ):
        ExerciseAnswer.objects.create(
            submission=submission,
            exercise=discursive_exercise,
            answer_text='Resposta antiga',
        )
        authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {
                'current_exercise_pk': discursive_exercise.pk,
                'navigate_to_pk': discursive_exercise.pk,
                'answer_text': 'Resposta nova',
            },
        )
        answer = ExerciseAnswer.objects.get(submission=submission, exercise=discursive_exercise)
        assert answer.answer_text == 'Resposta nova'


# ─── Submit View ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestStudentSubmitView:
    def test_submit_marks_submitted_at(
        self, authenticated_client, activity_link, enrolled, submission
    ):
        assert submission.submitted_at is None
        response = authenticated_client.post(f'/student/activity/{activity_link.pk}/submit/')
        assert response.status_code == 302
        submission.refresh_from_db()
        assert submission.submitted_at is not None

    def test_submit_redirects_to_result(
        self, authenticated_client, activity_link, enrolled, submission
    ):
        response = authenticated_client.post(f'/student/activity/{activity_link.pk}/submit/')
        assert 'result' in response['Location']

    def test_submit_idempotent_when_already_submitted(
        self, authenticated_client, activity_link, enrolled, submitted_submission
    ):
        first_submitted_at = submitted_submission.submitted_at
        authenticated_client.post(f'/student/activity/{activity_link.pk}/submit/')
        submitted_submission.refresh_from_db()
        assert submitted_submission.submitted_at == first_submitted_at

    def test_submit_with_no_submission_returns_404(
        self, authenticated_client, activity_link, enrolled
    ):
        response = authenticated_client.post(f'/student/activity/{activity_link.pk}/submit/')
        assert response.status_code == 404


# ─── Result View ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestStudentResultView:
    def test_no_submission_redirects_to_activity(
        self, authenticated_client, activity_link, enrolled
    ):
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/result/')
        assert response.status_code == 302
        assert f'/student/activity/{activity_link.pk}/' in response['Location']

    def test_not_submitted_redirects_to_activity(
        self, authenticated_client, activity_link, enrolled, submission
    ):
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/result/')
        assert response.status_code == 302

    def test_submitted_shows_result_page(
        self, authenticated_client, activity_link, enrolled, submitted_submission
    ):
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/result/')
        assert response.status_code == 200

    def test_result_with_correct_mc_answer(
        self, authenticated_client, activity_link, enrolled, submitted_submission, mc_exercise
    ):
        ex, mc, opt_wrong, opt_correct = mc_exercise
        ExerciseAnswer.objects.create(
            submission=submitted_submission,
            exercise=ex,
            selected_option=opt_correct,
            is_correct=True,
        )
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/result/')
        assert response.status_code == 200
        ctx = response.context
        assert ctx['earned_points'] > 0
        assert ctx['answered_count'] == 1
        assert ctx['auto_graded'] == 1
        assert ctx['pending_review'] == 0

    def test_result_with_pending_manual_answer(
        self, authenticated_client, activity_link, enrolled, submitted_submission, discursive_exercise
    ):
        ExerciseAnswer.objects.create(
            submission=submitted_submission,
            exercise=discursive_exercise,
            answer_text='Minha resposta',
            is_correct=None,
        )
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/result/')
        assert response.status_code == 200
        ctx = response.context
        assert ctx['pending_review'] == 1
        assert ctx['auto_graded'] == 0


# ─── Teacher Submissions View ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestTeacherSubmissionsView:
    def test_owner_can_access(self, authenticated_client, activity_link):
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/submissions/')
        assert response.status_code == 200

    def test_non_owner_gets_404(self, activity_link):
        other = User.objects.create_user(username='other', password='pass')
        client = Client()
        client.post('/accounts/login/', {'username': 'other', 'password': 'pass'})
        response = client.get(f'/student/activity/{activity_link.pk}/submissions/')
        assert response.status_code == 404

    def test_nonexistent_link_returns_404(self, authenticated_client):
        response = authenticated_client.get('/student/activity/99999/submissions/')
        assert response.status_code == 404

    def test_shows_submitted_submissions(
        self, authenticated_client, user, activity_link, enrolled, submitted_submission
    ):
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/submissions/')
        assert response.status_code == 200
        assert len(response.context['submissions']) == 1

    def test_in_progress_count(
        self, authenticated_client, activity_link, enrolled, submission
    ):
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/submissions/')
        assert response.status_code == 200
        assert response.context['in_progress_count'] == 1

    def test_submission_answer_counts(
        self, authenticated_client, activity_link, enrolled,
        submitted_submission, discursive_exercise
    ):
        ExerciseAnswer.objects.create(
            submission=submitted_submission,
            exercise=discursive_exercise,
            answer_text='Resposta',
            is_correct=None,
        )
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/submissions/')
        sub = response.context['submissions'][0]
        assert sub.answered_count == 1
        assert sub.pending_count == 1
        assert sub.correct_count == 0

    def test_empty_submissions(self, authenticated_client, activity_link):
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/submissions/')
        assert response.status_code == 200
        assert len(response.context['submissions']) == 0


# ─── Teacher Grade View ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTeacherGradeView:
    def test_owner_can_access(
        self, authenticated_client, activity_link, enrolled, submitted_submission
    ):
        response = authenticated_client.get(
            f'/student/activity/{activity_link.pk}/submissions/{submitted_submission.pk}/grade/'
        )
        assert response.status_code == 200

    def test_unsubmitted_submission_returns_404(
        self, authenticated_client, activity_link, enrolled, submission
    ):
        response = authenticated_client.get(
            f'/student/activity/{activity_link.pk}/submissions/{submission.pk}/grade/'
        )
        assert response.status_code == 404

    def test_nonexistent_submission_returns_404(
        self, authenticated_client, activity_link
    ):
        response = authenticated_client.get(
            f'/student/activity/{activity_link.pk}/submissions/99999/grade/'
        )
        assert response.status_code == 404

    def test_non_owner_gets_404(self, activity_link, enrolled, submitted_submission):
        other = User.objects.create_user(username='other2', password='pass')
        client = Client()
        client.post('/accounts/login/', {'username': 'other2', 'password': 'pass'})
        response = client.get(
            f'/student/activity/{activity_link.pk}/submissions/{submitted_submission.pk}/grade/'
        )
        assert response.status_code == 404

    def test_grade_view_renders_exercises(
        self, authenticated_client, activity_link, enrolled,
        submitted_submission, discursive_exercise
    ):
        response = authenticated_client.get(
            f'/student/activity/{activity_link.pk}/submissions/{submitted_submission.pk}/grade/'
        )
        assert response.status_code == 200
        assert len(response.context['exercises']) == 1

    def test_post_grades_correct(
        self, authenticated_client, activity_link, enrolled,
        submitted_submission, discursive_exercise
    ):
        answer = ExerciseAnswer.objects.create(
            submission=submitted_submission,
            exercise=discursive_exercise,
            answer_text='Resposta',
            is_correct=None,
        )
        response = authenticated_client.post(
            f'/student/activity/{activity_link.pk}/submissions/{submitted_submission.pk}/grade/',
            {f'grade_{answer.pk}': 'correct'},
        )
        assert response.status_code == 302
        answer.refresh_from_db()
        assert answer.is_correct is True

    def test_post_grades_incorrect(
        self, authenticated_client, activity_link, enrolled,
        submitted_submission, discursive_exercise
    ):
        answer = ExerciseAnswer.objects.create(
            submission=submitted_submission,
            exercise=discursive_exercise,
            answer_text='Resposta errada',
            is_correct=None,
        )
        authenticated_client.post(
            f'/student/activity/{activity_link.pk}/submissions/{submitted_submission.pk}/grade/',
            {f'grade_{answer.pk}': 'incorrect'},
        )
        answer.refresh_from_db()
        assert answer.is_correct is False

    def test_post_ignores_invalid_grade_value(
        self, authenticated_client, activity_link, enrolled,
        submitted_submission, discursive_exercise
    ):
        answer = ExerciseAnswer.objects.create(
            submission=submitted_submission,
            exercise=discursive_exercise,
            answer_text='Resposta',
            is_correct=None,
        )
        authenticated_client.post(
            f'/student/activity/{activity_link.pk}/submissions/{submitted_submission.pk}/grade/',
            {f'grade_{answer.pk}': 'invalid'},
        )
        answer.refresh_from_db()
        assert answer.is_correct is None

    def test_post_ignores_non_digit_answer_pk(
        self, authenticated_client, activity_link, enrolled, submitted_submission
    ):
        response = authenticated_client.post(
            f'/student/activity/{activity_link.pk}/submissions/{submitted_submission.pk}/grade/',
            {'grade_abc': 'correct'},
        )
        assert response.status_code == 302

    def test_post_comment_answer_updates_teacher_comment(
        self, authenticated_client, activity_link, enrolled,
        submitted_submission, discursive_exercise
    ):
        answer = ExerciseAnswer.objects.create(
            submission=submitted_submission,
            exercise=discursive_exercise,
            answer_text='Resposta',
            is_correct=None,
        )
        authenticated_client.post(
            f'/student/activity/{activity_link.pk}/submissions/{submitted_submission.pk}/grade/',
            {
                f'comment_answer_{answer.pk}': 'Bom trabalho',
                'teacher_comment': 'Correção geral',
            },
        )
        answer.refresh_from_db()
        submitted_submission.refresh_from_db()
        assert submitted_submission.teacher_comment == 'Correção geral'

    def test_post_teacher_shared_access(self, activity_link, enrolled, submitted_submission):
        from group.models import GroupSharing
        shared_teacher = User.objects.create_user(username='shared_tea', password='pass')
        GroupSharing.objects.create(
            group=activity_link.group,
            shared_with=shared_teacher,
            shared_by=activity_link.group.created_by,
            is_active=True,
        )
        client = Client()
        client.post('/accounts/login/', {'username': 'shared_tea', 'password': 'pass'})
        response = client.get(
            f'/student/activity/{activity_link.pk}/submissions/{submitted_submission.pk}/grade/'
        )
        assert response.status_code == 200


# ─── StudentActivityReviewView ────────────────────────────────────────────────

@pytest.mark.django_db
class TestStudentActivityReviewView:
    def test_review_redirects_to_activity_if_no_submission(
        self, authenticated_client, activity_link, enrolled
    ):
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/review/')
        assert response.status_code == 302
        assert f'/student/activity/{activity_link.pk}/' in response['Location']

    def test_review_redirects_to_activity_when_no_in_progress_submission(
        self, authenticated_client, activity_link, enrolled, submitted_submission
    ):
        # No in-progress submission → review redirects to activity (retry or limit check)
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/review/')
        assert response.status_code == 302
        assert f'/student/activity/{activity_link.pk}/' in response['Location']

    def test_review_shows_page_with_in_progress_submission(
        self, authenticated_client, activity_link, enrolled, submission, discursive_exercise
    ):
        ExerciseAnswer.objects.create(
            submission=submission,
            exercise=discursive_exercise,
            answer_text='Minha resposta',
        )
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/review/')
        assert response.status_code == 200
        assert response.context['unanswered_count'] == 0

    def test_review_unanswered_count_correct(
        self, authenticated_client, activity_link, enrolled, submission, discursive_exercise
    ):
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/review/')
        assert response.status_code == 200
        assert response.context['unanswered_count'] == 1


# ─── StudentFeedbackView ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestStudentFeedbackView:
    def test_post_saves_feedback(
        self, authenticated_client, activity_link, enrolled, submitted_submission
    ):
        response = authenticated_client.post(
            f'/student/activity/{activity_link.pk}/feedback/',
            {'student_feedback': 'Atividade muito boa!'},
        )
        assert response.status_code == 302
        submitted_submission.refresh_from_db()
        assert submitted_submission.student_feedback == 'Atividade muito boa!'

    def test_post_no_submission_returns_404(
        self, authenticated_client, activity_link, enrolled
    ):
        response = authenticated_client.post(
            f'/student/activity/{activity_link.pk}/feedback/',
            {'student_feedback': 'Feedback'},
        )
        assert response.status_code == 404

    def test_post_in_progress_submission_returns_404(
        self, authenticated_client, activity_link, enrolled, submission
    ):
        response = authenticated_client.post(
            f'/student/activity/{activity_link.pk}/feedback/',
            {'student_feedback': 'Feedback'},
        )
        assert response.status_code == 404


# ─── _check_window deadline tests ────────────────────────────────────────────

@pytest.mark.django_db
class TestCheckWindowDeadline:
    def test_activity_not_yet_started_blocks_get(
        self, authenticated_client, user, group, activity
    ):
        from group.models import GroupStudent
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        link = ActivityListGroup.objects.create(
            group=group,
            activity_list=activity,
            starts_at=timezone.now() + timedelta(days=1),
        )
        response = authenticated_client.get(f'/student/activity/{link.pk}/')
        assert response.status_code == 302

    def test_activity_deadline_passed_blocks_get(
        self, authenticated_client, user, group, activity
    ):
        from group.models import GroupStudent
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        link = ActivityListGroup.objects.create(
            group=group,
            activity_list=activity,
            ends_at=timezone.now() - timedelta(days=1),
        )
        response = authenticated_client.get(f'/student/activity/{link.pk}/')
        assert response.status_code == 302

    def test_activity_deadline_passed_blocks_post(
        self, authenticated_client, user, group, activity
    ):
        from group.models import GroupStudent
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        link = ActivityListGroup.objects.create(
            group=group,
            activity_list=activity,
            ends_at=timezone.now() - timedelta(days=1),
        )
        response = authenticated_client.post(
            f'/student/activity/{link.pk}/',
            {'current_exercise_pk': '', 'answer_text': ''},
        )
        assert response.status_code == 302

    def test_deadline_passed_blocks_submit(
        self, authenticated_client, user, group, activity
    ):
        from group.models import GroupStudent
        from student.models import Submission
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        link = ActivityListGroup.objects.create(
            group=group,
            activity_list=activity,
            ends_at=timezone.now() - timedelta(days=1),
        )
        Submission.objects.create(student=user, activity_link=link)
        response = authenticated_client.post(f'/student/activity/{link.pk}/submit/')
        assert response.status_code == 302

    def test_deadline_passed_blocks_review(
        self, authenticated_client, user, group, activity
    ):
        from group.models import GroupStudent
        from student.models import Submission
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        link = ActivityListGroup.objects.create(
            group=group,
            activity_list=activity,
            ends_at=timezone.now() - timedelta(days=1),
        )
        Submission.objects.create(student=user, activity_link=link)
        response = authenticated_client.get(f'/student/activity/{link.pk}/review/')
        assert response.status_code == 302


# ─── StudentActivityView go_review ───────────────────────────────────────────

@pytest.mark.django_db
class TestStudentActivityGoReview:
    def test_post_go_review_redirects_to_review(
        self, authenticated_client, activity_link, enrolled, submission
    ):
        response = authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {'current_exercise_pk': '', 'go_review': '1'},
        )
        assert response.status_code == 302
        assert 'review' in response['Location']

    def test_post_go_review_htmx_returns_hx_redirect(
        self, authenticated_client, activity_link, enrolled, submission
    ):
        response = authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {'current_exercise_pk': '', 'go_review': '1'},
            HTTP_HX_REQUEST='true',
        )
        assert response.status_code == 200
        assert 'HX-Redirect' in response


# ─── StudentResultView deleted activity branch ────────────────────────────────

@pytest.mark.django_db
class TestStudentResultDeletedActivity:
    def test_result_accessible_after_delete_if_submitted(
        self, authenticated_client, user, group, activity
    ):
        from group.models import GroupStudent
        from student.models import Submission
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        link = ActivityListGroup.objects.create(group=group, activity_list=activity)
        sub = Submission.objects.create(
            student=user, activity_link=link, submitted_at=timezone.now()
        )
        activity.deleted_at = timezone.now()
        activity.save()
        response = authenticated_client.get(f'/student/activity/{link.pk}/result/')
        assert response.status_code == 200

    def test_result_404_after_delete_if_not_submitted(
        self, authenticated_client, user, group, activity
    ):
        from group.models import GroupStudent
        GroupStudent.objects.create(group=group, student=user, is_active=True)
        link = ActivityListGroup.objects.create(group=group, activity_list=activity)
        activity.deleted_at = timezone.now()
        activity.save()
        response = authenticated_client.get(f'/student/activity/{link.pk}/result/')
        assert response.status_code == 404


# ─── _save_answer delete branch ───────────────────────────────────────────────

@pytest.mark.django_db
class TestSaveAnswerDeleteBranch:
    def test_empty_answer_deletes_existing(
        self, authenticated_client, activity_link, enrolled, discursive_exercise, submission
    ):
        ExerciseAnswer.objects.create(
            submission=submission,
            exercise=discursive_exercise,
            answer_text='Resposta para deletar',
        )
        authenticated_client.post(
            f'/student/activity/{activity_link.pk}/',
            {
                'current_exercise_pk': discursive_exercise.pk,
                'navigate_to_pk': discursive_exercise.pk,
                'answer_text': '   ',
            },
        )
        assert not ExerciseAnswer.objects.filter(
            submission=submission, exercise=discursive_exercise
        ).exists()


# ─── StudentResultView 404 branches ──────────────────────────────────────────

@pytest.mark.django_db
class TestStudentResultView404Branches:
    def test_result_404_for_nonexistent_link(self, authenticated_client):
        response = authenticated_client.get('/student/activity/99999/result/')
        assert response.status_code == 404

    def test_result_404_when_not_enrolled(self, authenticated_client, user, group, activity):
        other_owner = User.objects.create_user(username='result_owner', password='pass')
        other_group = Group.objects.create(
            name='G Not Enrolled', description='x' * 15, shift='Manhã', created_by=other_owner
        )
        link = ActivityListGroup.objects.create(group=other_group, activity_list=activity)
        response = authenticated_client.get(f'/student/activity/{link.pk}/result/')
        assert response.status_code == 404


# ─── StudentAbandonView ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestStudentAbandonView:
    def _make_limited_link(self, group, activity, max_attempts=2):
        activity.max_attempts = max_attempts
        activity.save()
        return ActivityListGroup.objects.create(group=group, activity_list=activity)

    def test_abandon_closes_in_progress_submission(
        self, authenticated_client, user, group, activity, enrolled
    ):
        link = self._make_limited_link(group, activity)
        sub = Submission.objects.create(student=user, activity_link=link)
        response = authenticated_client.post(f'/student/activity/{link.pk}/abandon/')
        assert response.status_code == 204
        sub.refresh_from_db()
        assert sub.submitted_at is not None
        assert sub.is_abandoned is True

    def test_abandon_no_op_for_unlimited_activity(
        self, authenticated_client, user, group, activity, enrolled
    ):
        link = ActivityListGroup.objects.create(group=group, activity_list=activity)
        sub = Submission.objects.create(student=user, activity_link=link)
        response = authenticated_client.post(f'/student/activity/{link.pk}/abandon/')
        assert response.status_code == 204
        sub.refresh_from_db()
        assert sub.submitted_at is None
        assert sub.is_abandoned is False


# ─── StudentActivityView — limited activity paths ─────────────────────────────

@pytest.mark.django_db
class TestStudentActivityViewLimited:
    def _make_limited_link(self, group, activity, max_attempts=2):
        activity.max_attempts = max_attempts
        activity.save()
        return ActivityListGroup.objects.create(group=group, activity_list=activity)

    def test_get_creates_new_attempt_after_abandoned(
        self, authenticated_client, user, group, activity, enrolled
    ):
        """GET opens a fresh attempt when previous one was abandoned and attempts remain."""
        link = self._make_limited_link(group, activity, max_attempts=2)
        Submission.objects.create(
            student=user, activity_link=link,
            submitted_at=timezone.now(), is_abandoned=True, attempt_number=1,
        )
        response = authenticated_client.get(f'/student/activity/{link.pk}/')
        assert response.status_code == 200
        assert Submission.objects.filter(
            student=user, activity_link=link, submitted_at__isnull=True
        ).exists()

    def test_get_redirects_to_result_when_all_attempts_abandoned(
        self, authenticated_client, user, group, activity, enrolled
    ):
        """GET redirects with error when all attempts are abandoned (no intentional submit)."""
        link = self._make_limited_link(group, activity, max_attempts=1)
        Submission.objects.create(
            student=user, activity_link=link,
            submitted_at=timezone.now(), is_abandoned=True, attempt_number=1,
        )
        response = authenticated_client.get(f'/student/activity/{link.pk}/')
        assert response.status_code == 302
        assert 'result' in response['Location']

    def test_post_creates_new_attempt_after_abandoned(
        self, authenticated_client, user, group, activity, enrolled, discursive_exercise
    ):
        """POST creates new submission when previous was abandoned but attempts remain."""
        link = self._make_limited_link(group, activity, max_attempts=2)
        Submission.objects.create(
            student=user, activity_link=link,
            submitted_at=timezone.now(), is_abandoned=True, attempt_number=1,
        )
        response = authenticated_client.post(
            f'/student/activity/{link.pk}/',
            {'current_exercise_pk': '', 'answer_text': ''},
        )
        assert response.status_code in (200, 302)
        assert Submission.objects.filter(student=user, activity_link=link).count() == 2

    def test_post_redirects_to_result_when_all_abandoned_and_exhausted(
        self, authenticated_client, user, group, activity, enrolled
    ):
        """POST to limited activity with all attempts abandoned and exhausted returns None → redirect."""
        link = self._make_limited_link(group, activity, max_attempts=1)
        Submission.objects.create(
            student=user, activity_link=link,
            submitted_at=timezone.now(), is_abandoned=True, attempt_number=1,
        )
        response = authenticated_client.post(
            f'/student/activity/{link.pk}/',
            {'current_exercise_pk': '', 'answer_text': ''},
        )
        assert response.status_code == 302
        assert 'result' in response['Location']


@pytest.mark.django_db
class TestStudentActivityViewUnlimitedPostNoInProgress:
    def test_post_creates_new_submission_when_previous_submitted(
        self, authenticated_client, user, group, activity, enrolled
    ):
        """POST to unlimited activity without in-progress submission creates a new one."""
        link = ActivityListGroup.objects.create(group=group, activity_list=activity)
        Submission.objects.create(
            student=user, activity_link=link,
            submitted_at=timezone.now(), attempt_number=1,
        )
        response = authenticated_client.post(
            f'/student/activity/{link.pk}/',
            {'current_exercise_pk': '', 'answer_text': ''},
        )
        assert response.status_code in (200, 302)
        assert Submission.objects.filter(student=user, activity_link=link).count() == 2


# ─── StudentResultView — limited activity paths ───────────────────────────────

@pytest.mark.django_db
class TestStudentResultViewLimited:
    def _make_limited_link(self, group, activity, max_attempts=2):
        activity.max_attempts = max_attempts
        activity.save()
        return ActivityListGroup.objects.create(group=group, activity_list=activity)

    def test_result_shows_intentional_submission(
        self, authenticated_client, user, group, activity, enrolled
    ):
        """GET /result/ for limited activity shows the intentional submission."""
        link = self._make_limited_link(group, activity, max_attempts=2)
        Submission.objects.create(
            student=user, activity_link=link,
            submitted_at=timezone.now(), is_abandoned=True, attempt_number=1,
        )
        Submission.objects.create(
            student=user, activity_link=link,
            submitted_at=timezone.now(), is_abandoned=False, attempt_number=2,
        )
        response = authenticated_client.get(f'/student/activity/{link.pk}/result/')
        assert response.status_code == 200

    def test_result_fallback_to_abandoned_when_no_intentional(
        self, authenticated_client, user, group, activity, enrolled
    ):
        """GET /result/ falls back to latest abandoned submission when no intentional one exists."""
        link = self._make_limited_link(group, activity, max_attempts=1)
        Submission.objects.create(
            student=user, activity_link=link,
            submitted_at=timezone.now(), is_abandoned=True, attempt_number=1,
        )
        response = authenticated_client.get(f'/student/activity/{link.pk}/result/')
        assert response.status_code == 200

    def test_result_context_has_attempts_remaining_limited(
        self, authenticated_client, user, group, activity, enrolled
    ):
        """Context includes attempts_remaining for limited activities."""
        link = self._make_limited_link(group, activity, max_attempts=3)
        Submission.objects.create(
            student=user, activity_link=link,
            submitted_at=timezone.now(), is_abandoned=True, attempt_number=1,
        )
        Submission.objects.create(
            student=user, activity_link=link,
            submitted_at=timezone.now(), is_abandoned=False, attempt_number=2,
        )
        response = authenticated_client.get(f'/student/activity/{link.pk}/result/')
        assert response.status_code == 200
        assert response.context['attempts_remaining'] == 1
        assert response.context['can_retry'] is False  # has intentional → no retry

    def test_result_can_retry_false_after_intentional(
        self, authenticated_client, user, group, activity, enrolled
    ):
        """can_retry is False after an intentional submission, regardless of attempts left."""
        link = self._make_limited_link(group, activity, max_attempts=3)
        Submission.objects.create(
            student=user, activity_link=link,
            submitted_at=timezone.now(), is_abandoned=False, attempt_number=1,
        )
        response = authenticated_client.get(f'/student/activity/{link.pk}/result/')
        assert response.status_code == 200
        assert response.context['can_retry'] is False


# ─── StudentFeedbackView — limited activity path ──────────────────────────────

@pytest.mark.django_db
class TestStudentFeedbackViewLimited:
    def _make_limited_link(self, group, activity, max_attempts=2):
        activity.max_attempts = max_attempts
        activity.save()
        return ActivityListGroup.objects.create(group=group, activity_list=activity)

    def test_feedback_saved_for_intentional_submission(
        self, authenticated_client, user, group, activity, enrolled
    ):
        """POST feedback uses the non-abandoned submission for limited activities."""
        link = self._make_limited_link(group, activity)
        Submission.objects.create(
            student=user, activity_link=link,
            submitted_at=timezone.now(), is_abandoned=True, attempt_number=1,
        )
        intentional = Submission.objects.create(
            student=user, activity_link=link,
            submitted_at=timezone.now(), is_abandoned=False, attempt_number=2,
        )
        response = authenticated_client.post(
            f'/student/activity/{link.pk}/feedback/',
            {'student_feedback': 'Ótima atividade!'},
        )
        assert response.status_code == 302
        intentional.refresh_from_db()
        assert intentional.student_feedback == 'Ótima atividade!'

    def test_feedback_404_when_only_abandoned_submissions(
        self, authenticated_client, user, group, activity, enrolled
    ):
        """POST feedback returns 404 when only abandoned submissions exist (no intentional)."""
        link = self._make_limited_link(group, activity)
        Submission.objects.create(
            student=user, activity_link=link,
            submitted_at=timezone.now(), is_abandoned=True, attempt_number=1,
        )
        response = authenticated_client.post(
            f'/student/activity/{link.pk}/feedback/',
            {'student_feedback': 'Feedback'},
        )
        assert response.status_code == 404


# ─── CodeExecution model properties ──────────────────────────────────────────

@pytest.mark.django_db
class TestCodeExecutionProperties:
    def test_all_correct_true_when_all_pass(self, user, activity_link):
        from student.models import CodeExecution
        submission = Submission.objects.create(student=user, activity_link=activity_link)
        ex = Exercise.objects.create(
            activity_list=activity_link.activity_list, type='code', statement='Q', points=1
        )
        CodeExercise.objects.create(exercise=ex, language='python')
        exec_ = CodeExecution.objects.create(
            submission=submission,
            exercise=ex,
            source_code='print(1)',
            results=[
                {'is_correct': True, 'status': 'correct'},
                {'is_correct': True, 'status': 'correct'},
            ],
        )
        assert exec_.all_correct is True
        assert exec_.correct_count == 2
        assert exec_.total_count == 2

    def test_all_correct_false_when_some_fail(self, user, activity_link):
        from student.models import CodeExecution
        submission = Submission.objects.create(student=user, activity_link=activity_link)
        ex = Exercise.objects.create(
            activity_list=activity_link.activity_list, type='code', statement='Q', points=1
        )
        CodeExercise.objects.create(exercise=ex, language='python')
        exec_ = CodeExecution.objects.create(
            submission=submission,
            exercise=ex,
            source_code='print(1)',
            results=[
                {'is_correct': True, 'status': 'correct'},
                {'is_correct': False, 'status': 'wrong_answer'},
            ],
        )
        assert exec_.all_correct is False
        assert exec_.correct_count == 1
        assert exec_.total_count == 2

    def test_all_correct_false_when_results_empty(self, user, activity_link):
        from student.models import CodeExecution
        submission = Submission.objects.create(student=user, activity_link=activity_link)
        ex = Exercise.objects.create(
            activity_list=activity_link.activity_list, type='code', statement='Q', points=1
        )
        CodeExercise.objects.create(exercise=ex, language='python')
        exec_ = CodeExecution.objects.create(
            submission=submission, exercise=ex, source_code='print(1)', results=[]
        )
        assert exec_.all_correct is False
        assert exec_.correct_count == 0
        assert exec_.total_count == 0


# ─── _auto_grade via StudentSubmitView ───────────────────────────────────────

@pytest.mark.django_db
class TestAutoGradeOnSubmit:
    def test_auto_grade_complete_code_correct(
        self, authenticated_client, user, group, activity, enrolled
    ):
        link = ActivityListGroup.objects.create(group=group, activity_list=activity)
        ex = Exercise.objects.create(
            activity_list=activity, type='complete_code', statement='Q', points=1
        )
        CompleteCodeExercise.objects.create(
            exercise=ex, language='python', starter_code='x = ___', complete_code='x = 42'
        )
        sub = Submission.objects.create(student=user, activity_link=link)
        ExerciseAnswer.objects.create(submission=sub, exercise=ex, answer_text='x = 42')
        authenticated_client.post(f'/student/activity/{link.pk}/submit/')
        answer = ExerciseAnswer.objects.get(submission=sub, exercise=ex)
        assert answer.is_correct is True

    def test_auto_grade_complete_code_wrong(
        self, authenticated_client, user, group, activity, enrolled
    ):
        link = ActivityListGroup.objects.create(group=group, activity_list=activity)
        ex = Exercise.objects.create(
            activity_list=activity, type='complete_code', statement='Q', points=1
        )
        CompleteCodeExercise.objects.create(
            exercise=ex, language='python', starter_code='x = ___', complete_code='x = 42'
        )
        sub = Submission.objects.create(student=user, activity_link=link)
        ExerciseAnswer.objects.create(submission=sub, exercise=ex, answer_text='x = 99')
        authenticated_client.post(f'/student/activity/{link.pk}/submit/')
        answer = ExerciseAnswer.objects.get(submission=sub, exercise=ex)
        assert answer.is_correct is False

    def test_auto_grade_code_dispatches_task(
        self, authenticated_client, user, group, activity, enrolled
    ):
        from unittest.mock import patch, MagicMock
        link = ActivityListGroup.objects.create(group=group, activity_list=activity)
        ex = Exercise.objects.create(
            activity_list=activity, type='code', statement='Q', points=1
        )
        CodeExercise.objects.create(exercise=ex, language='python')
        sub = Submission.objects.create(student=user, activity_link=link)
        ExerciseAnswer.objects.create(submission=sub, exercise=ex, answer_text='print("hello")')
        with patch('student.tasks.execute_code_task') as mock_task:
            mock_task.delay.return_value = MagicMock()
            authenticated_client.post(f'/student/activity/{link.pk}/submit/')
        mock_task.delay.assert_called_once_with(sub.pk, ex.pk, 'print("hello")')

    def test_auto_grade_skips_annulled_exercise(
        self, authenticated_client, user, group, activity, enrolled
    ):
        link = ActivityListGroup.objects.create(group=group, activity_list=activity)
        ex = Exercise.objects.create(
            activity_list=activity, type='complete_code', statement='Q', points=1, is_annulled=True
        )
        CompleteCodeExercise.objects.create(
            exercise=ex, language='python', starter_code='x = ___', complete_code='x = 42'
        )
        sub = Submission.objects.create(student=user, activity_link=link)
        ExerciseAnswer.objects.create(submission=sub, exercise=ex, answer_text='x = 42')
        authenticated_client.post(f'/student/activity/{link.pk}/submit/')
        answer = ExerciseAnswer.objects.get(submission=sub, exercise=ex)
        assert answer.is_correct is None

    def test_auto_grade_complete_code_exception_caught_silently(
        self, authenticated_client, user, group, activity, enrolled
    ):
        link = ActivityListGroup.objects.create(group=group, activity_list=activity)
        # complete_code exercise WITHOUT a CompleteCodeExercise record → raises on access
        ex = Exercise.objects.create(
            activity_list=activity, type='complete_code', statement='Q', points=1
        )
        sub = Submission.objects.create(student=user, activity_link=link)
        ExerciseAnswer.objects.create(submission=sub, exercise=ex, answer_text='x = 42')
        response = authenticated_client.post(f'/student/activity/{link.pk}/submit/')
        assert response.status_code == 302


# ─── StudentRunCodeView ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestStudentRunCodeView:
    def test_invalid_exercise_param_returns_error(
        self, authenticated_client, activity_link, enrolled, submission
    ):
        response = authenticated_client.post(
            f'/student/activity/{activity_link.pk}/run/',
            {'exercise_pk': 'abc'},
        )
        assert response.status_code == 200
        assert 'Exercício inválido' in response.content.decode()

    def test_nonexistent_exercise_returns_404(
        self, authenticated_client, activity_link, enrolled, submission
    ):
        response = authenticated_client.post(
            f'/student/activity/{activity_link.pk}/run/',
            {'exercise_pk': '99999'},
        )
        assert response.status_code == 404

    def test_no_submission_returns_error(
        self, authenticated_client, activity_link, enrolled, code_exercise
    ):
        response = authenticated_client.post(
            f'/student/activity/{activity_link.pk}/run/',
            {'exercise_pk': str(code_exercise.pk), 'source_code': 'print(1)'},
        )
        assert response.status_code == 200
        assert 'tentativa' in response.content.decode()

    def test_max_executions_reached_returns_error(
        self, authenticated_client, activity_link, enrolled, submission
    ):
        from student.models import CodeExecution
        ex = Exercise.objects.create(
            activity_list=activity_link.activity_list, type='code', statement='Q', points=1
        )
        CodeExercise.objects.create(exercise=ex, language='python', max_executions=1)
        CodeExecution.objects.create(
            submission=submission, exercise=ex, source_code='x', results=[]
        )
        response = authenticated_client.post(
            f'/student/activity/{activity_link.pk}/run/',
            {'exercise_pk': str(ex.pk), 'source_code': 'print(1)'},
        )
        assert response.status_code == 200
        assert 'Limite' in response.content.decode()

    def test_empty_source_code_returns_error(
        self, authenticated_client, activity_link, enrolled, code_exercise, submission
    ):
        response = authenticated_client.post(
            f'/student/activity/{activity_link.pk}/run/',
            {'exercise_pk': str(code_exercise.pk), 'source_code': '   '},
        )
        assert response.status_code == 200
        assert 'vazio' in response.content.decode()

    def test_dispatches_task_and_returns_polling(
        self, authenticated_client, activity_link, enrolled, code_exercise, submission
    ):
        from unittest.mock import patch, MagicMock
        with patch('student.tasks.execute_code_task') as mock_task:
            mock_task.delay.return_value = MagicMock(id='fake-task-id')
            response = authenticated_client.post(
                f'/student/activity/{activity_link.pk}/run/',
                {'exercise_pk': str(code_exercise.pk), 'source_code': 'print("hello")'},
            )
        assert response.status_code == 200
        mock_task.delay.assert_called_once()

    def test_complete_code_exercise_dispatches_task(
        self, authenticated_client, activity_link, enrolled, complete_code_exercise, submission
    ):
        from unittest.mock import patch, MagicMock
        with patch('student.tasks.execute_code_task') as mock_task:
            mock_task.delay.return_value = MagicMock(id='fake-task-id')
            response = authenticated_client.post(
                f'/student/activity/{activity_link.pk}/run/',
                {
                    'exercise_pk': str(complete_code_exercise.pk),
                    'source_code': 'print("hello")',
                },
            )
        assert response.status_code == 200
        mock_task.delay.assert_called_once()


# ─── StudentRunCodePollView ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestStudentRunCodePollView:
    def test_task_not_ready_returns_polling_spinner(
        self, authenticated_client, activity_link, enrolled, code_exercise, submission
    ):
        from unittest.mock import patch, MagicMock
        mock_result = MagicMock()
        mock_result.ready.return_value = False
        with patch('celery.result.AsyncResult', return_value=mock_result):
            response = authenticated_client.get(
                f'/student/activity/{activity_link.pk}/run/poll/fake-id/'
                f'?exercise_pk={code_exercise.pk}',
            )
        assert response.status_code == 200

    def test_task_error_returns_error_html(
        self, authenticated_client, activity_link, enrolled, code_exercise, submission
    ):
        from unittest.mock import patch, MagicMock
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.get.return_value = {'error': 'Algo deu errado'}
        with patch('celery.result.AsyncResult', return_value=mock_result):
            response = authenticated_client.get(
                f'/student/activity/{activity_link.pk}/run/poll/fake-id/'
                f'?exercise_pk={code_exercise.pk}',
            )
        assert response.status_code == 200
        assert 'Algo deu errado' in response.content.decode()

    def test_task_run_only_returns_stdout(
        self, authenticated_client, activity_link, enrolled, complete_code_exercise, submission
    ):
        from unittest.mock import patch, MagicMock
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.get.return_value = {
            'run_only': True,
            'stdout': 'hello',
            'stderr': '',
            'status': 'correct',
        }
        with patch('celery.result.AsyncResult', return_value=mock_result):
            response = authenticated_client.get(
                f'/student/activity/{activity_link.pk}/run/poll/fake-id/'
                f'?exercise_pk={complete_code_exercise.pk}',
            )
        assert response.status_code == 200

    def test_task_with_results_returns_result_html(
        self, authenticated_client, activity_link, enrolled, code_exercise, submission
    ):
        from unittest.mock import patch, MagicMock
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.get.return_value = {
            'results': [{'stdin': '', 'expected_output': '1', 'stdout': '1', 'is_correct': True, 'status': 'correct', 'stderr': ''}],
            'all_correct': True,
            'correct_count': 1,
            'total_count': 1,
        }
        with patch('celery.result.AsyncResult', return_value=mock_result):
            response = authenticated_client.get(
                f'/student/activity/{activity_link.pk}/run/poll/fake-id/'
                f'?exercise_pk={code_exercise.pk}',
            )
        assert response.status_code == 200


# ─── execute_code_task ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestExecuteCodeTask:
    def _make_code_exercise(self, activity, with_test_case=True):
        from activity.models import CodeTestCase
        ex = Exercise.objects.create(
            activity_list=activity, type='code', statement='Q', points=1
        )
        ce = CodeExercise.objects.create(exercise=ex, language='python')
        if with_test_case:
            CodeTestCase.objects.create(
                exercise=ce, input='', expected_output='hello', order=1
            )
        return ex

    def test_code_exercise_no_test_cases_returns_error(self, user, activity_link):
        from student.tasks import execute_code_task
        ex = self._make_code_exercise(activity_link.activity_list, with_test_case=False)
        sub = Submission.objects.create(student=user, activity_link=activity_link)
        result = execute_code_task.run(sub.pk, ex.pk, 'print("hello")')
        assert 'error' in result
        assert 'casos de teste' in result['error']

    def test_code_exercise_success(self, user, activity_link):
        from unittest.mock import patch
        from student.tasks import execute_code_task
        ex = self._make_code_exercise(activity_link.activity_list)
        sub = Submission.objects.create(student=user, activity_link=activity_link)
        mock_results = [
            {'stdin': '', 'expected_output': 'hello', 'stdout': 'hello',
             'stderr': '', 'is_correct': True, 'status': 'correct'}
        ]
        with patch('common.executor.execute_code', return_value=mock_results):
            result = execute_code_task.run(sub.pk, ex.pk, 'print("hello")')
        assert result['all_correct'] is True
        assert result['total_count'] == 1

    def test_code_exercise_compilation_error(self, user, activity_link):
        from unittest.mock import patch
        from student.tasks import execute_code_task
        from common.executor import CompilationError
        ex = self._make_code_exercise(activity_link.activity_list)
        sub = Submission.objects.create(student=user, activity_link=activity_link)
        with patch('common.executor.execute_code', side_effect=CompilationError('syntax error')):
            result = execute_code_task.run(sub.pk, ex.pk, 'bad code')
        assert 'error' in result
        assert 'compilação' in result['error']

    def test_code_exercise_language_not_supported(self, user, activity_link):
        from unittest.mock import patch
        from student.tasks import execute_code_task
        from common.executor import LanguageNotSupportedError
        ex = self._make_code_exercise(activity_link.activity_list)
        sub = Submission.objects.create(student=user, activity_link=activity_link)
        with patch('common.executor.execute_code', side_effect=LanguageNotSupportedError('no')):
            result = execute_code_task.run(sub.pk, ex.pk, 'x')
        assert 'error' in result

    def test_code_exercise_executor_error(self, user, activity_link):
        from unittest.mock import patch
        from student.tasks import execute_code_task
        from common.executor import ExecutorError
        ex = self._make_code_exercise(activity_link.activity_list)
        sub = Submission.objects.create(student=user, activity_link=activity_link)
        with patch('common.executor.execute_code', side_effect=ExecutorError('fail')):
            result = execute_code_task.run(sub.pk, ex.pk, 'x')
        assert 'error' in result

    def test_complete_code_exercise_success(self, user, activity_link):
        from unittest.mock import patch
        from student.tasks import execute_code_task
        ex = Exercise.objects.create(
            activity_list=activity_link.activity_list, type='complete_code', statement='Q', points=1
        )
        CompleteCodeExercise.objects.create(
            exercise=ex, language='python', starter_code='___', complete_code='print(1)'
        )
        sub = Submission.objects.create(student=user, activity_link=activity_link)
        mock_results = [
            {'stdin': '', 'expected_output': '', 'stdout': '1',
             'stderr': '', 'is_correct': True, 'status': 'correct'}
        ]
        with patch('common.executor.execute_code', return_value=mock_results):
            result = execute_code_task.run(sub.pk, ex.pk, 'print(1)')
        assert result['run_only'] is True
        assert result['stdout'] == '1'

    def test_complete_code_compilation_error(self, user, activity_link):
        from unittest.mock import patch
        from student.tasks import execute_code_task
        from common.executor import CompilationError
        ex = Exercise.objects.create(
            activity_list=activity_link.activity_list, type='complete_code', statement='Q', points=1
        )
        CompleteCodeExercise.objects.create(
            exercise=ex, language='python', starter_code='___', complete_code='x'
        )
        sub = Submission.objects.create(student=user, activity_link=activity_link)
        with patch('common.executor.execute_code', side_effect=CompilationError('err')):
            result = execute_code_task.run(sub.pk, ex.pk, 'bad')
        assert 'error' in result

    def test_complete_code_language_not_supported(self, user, activity_link):
        from unittest.mock import patch
        from student.tasks import execute_code_task
        from common.executor import LanguageNotSupportedError
        ex = Exercise.objects.create(
            activity_list=activity_link.activity_list, type='complete_code', statement='Q', points=1
        )
        CompleteCodeExercise.objects.create(
            exercise=ex, language='python', starter_code='___', complete_code='x'
        )
        sub = Submission.objects.create(student=user, activity_link=activity_link)
        with patch('common.executor.execute_code', side_effect=LanguageNotSupportedError('no')):
            result = execute_code_task.run(sub.pk, ex.pk, 'x')
        assert 'error' in result

    def test_complete_code_executor_error(self, user, activity_link):
        from unittest.mock import patch
        from student.tasks import execute_code_task
        from common.executor import ExecutorError
        ex = Exercise.objects.create(
            activity_list=activity_link.activity_list, type='complete_code', statement='Q', points=1
        )
        CompleteCodeExercise.objects.create(
            exercise=ex, language='python', starter_code='___', complete_code='x'
        )
        sub = Submission.objects.create(student=user, activity_link=activity_link)
        with patch('common.executor.execute_code', side_effect=ExecutorError('err')):
            result = execute_code_task.run(sub.pk, ex.pk, 'x')
        assert 'error' in result

    def test_unsupported_exercise_type_returns_error(self, user, activity_link):
        from student.tasks import execute_code_task
        ex = Exercise.objects.create(
            activity_list=activity_link.activity_list, type='discursive', statement='Q', points=1
        )
        DiscursiveExercise.objects.create(exercise=ex)
        sub = Submission.objects.create(student=user, activity_link=activity_link)
        result = execute_code_task.run(sub.pk, ex.pk, 'x')
        assert 'error' in result
        assert 'suporta execução' in result['error']

    def test_outer_exception_returns_error(self, user, activity_link):
        from unittest.mock import patch
        from student.tasks import execute_code_task
        with patch('student.models.Submission.objects') as mock_qs:
            mock_qs.get.side_effect = Exception('unexpected')
            result = execute_code_task.run(user.pk, 99999, 'x')
        assert 'error' in result
        assert 'Erro interno' in result['error']

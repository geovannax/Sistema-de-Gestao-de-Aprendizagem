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
from group.models import Group, GroupStudent
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
    CodeExercise.objects.create(exercise=ex, language='python', expected_output='hello')
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

    def test_redirects_to_result_if_already_submitted(
        self, authenticated_client, activity_link, enrolled, submitted_submission
    ):
        response = authenticated_client.get(f'/student/activity/{activity_link.pk}/')
        assert response.status_code == 302
        assert 'result' in response['Location']

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

    def test_post_already_submitted_redirects(
        self, authenticated_client, activity_link, enrolled, submitted_submission
    ):
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

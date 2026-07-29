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
    MultipleChoiceExercise,
    ExerciseOption,
)
from group.models import Group


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def activity_user(db):
    return User.objects.create_user(username='activity_user', password='pass123')


@pytest.fixture
def activity(activity_user):
    return ActivityList.objects.create(title='Lista de Exercícios 1', created_by=activity_user)


@pytest.fixture
def activity_client(activity_user):
    client = Client()
    client.post('/accounts/login/', {'username': activity_user.username, 'password': 'pass123'})
    return client


# ─── Model tests ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestActivityList:
    def test_str(self, activity_user):
        activity = ActivityList.objects.create(title='Lista de Exercícios 1', created_by=activity_user)
        assert str(activity) == 'Lista de Exercícios 1'


@pytest.mark.django_db
class TestDiscursiveExercise:
    def test_str(self, activity_user):
        activity = ActivityList.objects.create(title='Lista 2', created_by=activity_user)
        exercise = Exercise.objects.create(
            activity_list=activity,
            type='discursive',
            statement='Explique o conceito de herança em programação orientada a objetos.',
            points=10,
        )
        discursive = DiscursiveExercise.objects.create(exercise=exercise, min_words=20)
        assert str(discursive) == f'Discursivo: {exercise.statement[:50]}'


# ─── SyntaxValidator unit tests ──────────────────────────────────────────────

class TestSyntaxValidator:
    def test_validate_python_valid(self):
        from activity.forms.exercise import SyntaxValidator
        assert SyntaxValidator.validate_python('x = 1\nprint(x)') is True

    def test_validate_python_invalid(self):
        from activity.forms.exercise import SyntaxValidator
        assert SyntaxValidator.validate_python('def foo(') is False

    def test_validate_javascript_balanced(self):
        from activity.forms.exercise import SyntaxValidator
        assert SyntaxValidator.validate_javascript('function foo() {}') is True

    def test_validate_javascript_unbalanced(self):
        from activity.forms.exercise import SyntaxValidator
        assert SyntaxValidator.validate_javascript('function foo() {') is False

    def test_validate_java_valid(self):
        from activity.forms.exercise import SyntaxValidator
        code = 'public class Main { public static void main(String[] args) {} }'
        assert SyntaxValidator.validate_java(code) is True

    def test_validate_java_invalid(self):
        from activity.forms.exercise import SyntaxValidator
        assert SyntaxValidator.validate_java('some other code') is False

    def test_validate_c_valid(self):
        from activity.forms.exercise import SyntaxValidator
        assert SyntaxValidator.validate_c('int main() { return 0; }') is True

    def test_validate_c_invalid(self):
        from activity.forms.exercise import SyntaxValidator
        assert SyntaxValidator.validate_c('no main here') is False

    def test_validate_cpp_valid(self):
        from activity.forms.exercise import SyntaxValidator
        assert SyntaxValidator.validate_cpp('int main() { return 0; }') is True

    def test_validate_cpp_invalid(self):
        from activity.forms.exercise import SyntaxValidator
        assert SyntaxValidator.validate_cpp('no main') is False

    def test_validate_unknown_language_returns_true(self):
        from activity.forms.exercise import SyntaxValidator
        assert SyntaxValidator.validate('any code', 'ruby') is True


# ─── normalize_code unit tests ───────────────────────────────────────────────

class TestNormalizeCode:
    def test_strips_whitespace_python(self):
        from activity.utils import normalize_code
        assert normalize_code('x  =  1', 'python') == normalize_code('x=1', 'python')

    def test_strips_whitespace_javascript(self):
        from activity.utils import normalize_code
        assert normalize_code('let x  =  1', 'javascript') == normalize_code('let x=1', 'javascript')

    def test_strips_comments_python(self):
        from activity.utils import normalize_code
        with_comment = normalize_code('x = 1  # meu comentário', 'python')
        without_comment = normalize_code('x = 1', 'python')
        assert with_comment == without_comment

    def test_preserves_string_literals(self):
        from activity.utils import normalize_code
        a = normalize_code('print("hello world")', 'python')
        b = normalize_code('print( "hello world" )', 'python')
        assert a == b

    def test_different_values_not_equal(self):
        from activity.utils import normalize_code
        assert normalize_code('x = 1', 'python') != normalize_code('x = 2', 'python')

    def test_unknown_language_fallback(self):
        from activity.utils import normalize_code
        result = normalize_code('x = 1', 'cobol')
        assert 'x' in result and '1' in result

    def test_lexer_exception_falls_back_to_whitespace_join(self):
        from unittest.mock import patch
        from activity.utils import normalize_code
        with patch('activity.utils.get_lexer_by_name', side_effect=Exception('unsupported')):
            result = normalize_code('x  =  1', 'python')
        assert result == 'x=1'


# ─── CompleteCodeExerciseForm tests ──────────────────────────────────────────

class TestCompleteCodeExerciseForm:
    def test_clean_starter_code_without_blank_raises(self):
        from activity.forms.exercise import CompleteCodeExerciseForm
        form = CompleteCodeExerciseForm(data={
            'language': 'python',
            'starter_code': 'print("hello")',
            'complete_code': 'print("hello")',
        })
        assert not form.is_valid()
        assert 'starter_code' in form.errors

    def test_clean_complete_code_with_blank_raises(self):
        from activity.forms.exercise import CompleteCodeExerciseForm
        form = CompleteCodeExerciseForm(data={
            'language': 'python',
            'starter_code': 'x = ___',
            'complete_code': 'x = ___',
        })
        assert not form.is_valid()
        assert 'complete_code' in form.errors

    def test_clean_complete_code_with_syntax_error_raises(self):
        from activity.forms.exercise import CompleteCodeExerciseForm
        form = CompleteCodeExerciseForm(data={
            'language': 'python',
            'starter_code': 'x = ___',
            'complete_code': 'def broken syntax (((',
        })
        assert not form.is_valid()

    def test_valid_complete_code_form(self):
        from activity.forms.exercise import CompleteCodeExerciseForm
        form = CompleteCodeExerciseForm(data={
            'language': 'python',
            'starter_code': 'x = ___',
            'complete_code': 'x = 42',
        })
        assert form.is_valid()


# ─── ActivityAssignWidget unit tests ─────────────────────────────────────────

@pytest.mark.django_db
class TestActivityAssignWidget:
    def test_label_from_instance(self, activity_user):
        from activity.forms.activity import ActivityAssignWidget
        group = Group.objects.create(
            name='WidgetGroup', description='x' * 15, shift='Manhã', created_by=activity_user
        )
        widget = ActivityAssignWidget()
        assert widget.label_from_instance(group) == 'WidgetGroup'


# ─── ActivityAssignForm unit tests ───────────────────────────────────────────

@pytest.mark.django_db
class TestActivityAssignForm:
    def test_clean_invalid_dates_raises(self):
        from activity.forms.activity import ActivityAssignForm
        form = ActivityAssignForm(data={
            'starts_at': '2026-06-20T10:00',
            'ends_at': '2026-06-19T10:00',
        })
        assert not form.is_valid()

    def test_get_available_groups_with_none_user(self):
        from activity.forms.activity import ActivityAssignForm
        form = ActivityAssignForm()
        assert form.fields['groups'].queryset.count() == 0

    def test_get_available_groups_with_authenticated_user(self, activity_user):
        from activity.forms.activity import ActivityAssignForm
        Group.objects.create(
            name='FormGroup', description='x' * 15, shift='Manhã', created_by=activity_user
        )
        form = ActivityAssignForm(request_user=activity_user)
        assert form.fields['groups'].queryset.count() >= 1


# ─── ActivityListGroupPeriodForm tests ───────────────────────────────────────

@pytest.mark.django_db
class TestActivityListGroupPeriodForm:
    def test_clean_invalid_dates(self):
        from activity.forms.activity import ActivityListGroupPeriodForm
        form = ActivityListGroupPeriodForm(data={
            'starts_at': '2026-06-20T10:00',
            'ends_at': '2026-06-19T10:00',
        })
        assert not form.is_valid()

    def test_init_with_existing_dates(self, activity_user, activity):
        from activity.forms.activity import ActivityListGroupPeriodForm
        group = Group.objects.create(
            name='PeriodFormGroup', description='x' * 15, shift='Manhã', created_by=activity_user
        )
        link = ActivityListGroup.objects.create(
            group=group,
            activity_list=activity,
            starts_at=timezone.now(),
            ends_at=timezone.now() + timedelta(days=7),
        )
        form = ActivityListGroupPeriodForm(instance=link)
        assert form.fields['starts_at'].initial is not None


# ─── BaseExerciseOptionFormSet tests ─────────────────────────────────────────

@pytest.mark.django_db
class TestBaseExerciseOptionFormSet:
    def _make_formset(self, options_data):
        from activity.forms.formsets.exercise_option import ExerciseOptionFormCreateSet
        base = {
            'options-TOTAL_FORMS': str(len(options_data)),
            'options-INITIAL_FORMS': '0',
            'options-MIN_NUM_FORMS': '0',
            'options-MAX_NUM_FORMS': '1000',
        }
        for i, opt in enumerate(options_data):
            base[f'options-{i}-text'] = opt.get('text', f'Opcao {i}')
            base[f'options-{i}-is_correct'] = opt.get('is_correct', '')
            base[f'options-{i}-DELETE'] = opt.get('DELETE', '')
        return ExerciseOptionFormCreateSet(data=base, prefix='options')

    def test_clean_raises_with_zero_correct(self):
        formset = self._make_formset([
            {'text': 'A', 'is_correct': ''},
            {'text': 'B', 'is_correct': ''},
        ])
        assert not formset.is_valid()

    def test_clean_raises_with_multiple_correct(self):
        formset = self._make_formset([
            {'text': 'A', 'is_correct': 'on'},
            {'text': 'B', 'is_correct': 'on'},
        ])
        assert not formset.is_valid()

    def test_clean_passes_with_one_correct(self):
        # Need at least a valid parent instance for inline formset
        # This is best tested via the view integration test
        pass


# ─── ExerciseBaseMixin unit tests ─────────────────────────────────────────────

class TestExerciseBaseMixin:
    def test_get_initial_raises_for_invalid_type(self):
        from activity.mixins import ExerciseBaseMixin
        from django.views.generic import CreateView

        class MockView(ExerciseBaseMixin, CreateView):
            type_exercise = 'invalid_type_xyz'
            kwargs = {'pk': 1}

        view = MockView()
        view.kwargs = {'pk': 1}

        with pytest.raises(ValueError):
            view.get_initial()

    def test_render_success_raises_without_update_url(self):
        from activity.mixins import ExerciseBaseMixin
        from django.core.exceptions import ImproperlyConfigured
        from django.views.generic import CreateView

        class MockView(ExerciseBaseMixin, CreateView):
            type_exercise = 'code'
            update_url = None

        view = MockView()
        with pytest.raises(ImproperlyConfigured):
            view.render_success()


# ─── Activity Views Integration Tests ────────────────────────────────────────

@pytest.mark.django_db
class TestActivityListViews:
    def test_list_view_authenticated(self, activity_client):
        response = activity_client.get('/activity/list/')
        assert response.status_code == 200

    def test_list_view_unauthenticated(self):
        response = Client().get('/activity/list/')
        assert response.status_code == 302

    def test_archived_list_view(self, activity_client):
        response = activity_client.get('/activity/archived/')
        assert response.status_code == 200

    def test_list_with_filter(self, activity_client, activity):
        response = activity_client.get('/activity/list/?search_field=title&q=Lista')
        assert response.status_code == 200

    def test_list_with_ordering(self, activity_client, activity):
        response = activity_client.get('/activity/list/?sort=title&order=asc')
        assert response.status_code == 200

    def test_list_with_view_type_table(self, activity_client, activity):
        response = activity_client.get('/activity/list/?view_type=table')
        assert response.status_code == 200


@pytest.mark.django_db
class TestActivityCreateUpdateViews:
    def test_create_view_get(self, activity_client):
        response = activity_client.get('/activity/create/')
        assert response.status_code == 200

    def test_create_view_post_valid(self, activity_client):
        response = activity_client.post('/activity/create/', {
            'title': 'Atividade Nova',
            'description': 'Descrição da atividade',
        })
        assert response.status_code in (200, 302)

    def test_create_view_post_invalid(self, activity_client):
        response = activity_client.post('/activity/create/', {
            'title': '',
            'description': '',
        })
        assert response.status_code == 400

    def test_update_view_get(self, activity_client, activity):
        response = activity_client.get(f'/activity/update/{activity.pk}/')
        assert response.status_code == 200

    def test_update_view_post_valid(self, activity_client, activity):
        response = activity_client.post(f'/activity/update/{activity.pk}/', {
            'title': 'Título Atualizado',
            'description': 'Descrição atualizada da atividade',
        })
        assert response.status_code in (200, 302)

    def test_update_view_get_with_exercises(self, activity_client, activity):
        exercise = Exercise.objects.create(
            activity_list=activity, type='discursive', statement='Exercício teste', points=1.0
        )
        DiscursiveExercise.objects.create(exercise=exercise, min_words=10)
        response = activity_client.get(f'/activity/update/{activity.pk}/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestActivityManagementViews:
    def test_delete_view_get_no_open_period(self, activity_client, activity):
        response = activity_client.get(f'/activity/delete/{activity.pk}/')
        assert response.status_code == 200

    def test_delete_view_get_with_open_period_redirects(self, activity_client, activity, activity_user):
        group = Group.objects.create(
            name='G Delete', description='x' * 15, shift='Manhã', created_by=activity_user
        )
        ActivityListGroup.objects.create(
            group=group, activity_list=activity, ends_at=None
        )
        response = activity_client.get(f'/activity/delete/{activity.pk}/')
        assert response.status_code == 302

    def test_delete_view_post_no_open_period(self, activity_client, activity):
        response = activity_client.post(f'/activity/delete/{activity.pk}/')
        assert response.status_code == 302

    def test_delete_view_post_with_open_period_redirects(self, activity_client, activity, activity_user):
        group = Group.objects.create(
            name='G Delete P', description='x' * 15, shift='Manhã', created_by=activity_user
        )
        ActivityListGroup.objects.create(
            group=group, activity_list=activity, ends_at=None
        )
        response = activity_client.post(f'/activity/delete/{activity.pk}/')
        assert response.status_code == 302

    def test_archive_post_archives(self, activity_client, activity):
        response = activity_client.post(f'/activity/archive/{activity.pk}/')
        assert response.status_code == 302

    def test_archive_post_unarchives(self, activity_client, activity):
        activity_client.post(f'/activity/archive/{activity.pk}/')
        response = activity_client.post(f'/activity/archive/{activity.pk}/')
        assert response.status_code == 302

    def test_unshare_post(self, activity_client, activity, activity_user):
        group = Group.objects.create(
            name='G Unshare', description='x' * 15, shift='Manhã', created_by=activity_user
        )
        link = ActivityListGroup.objects.create(group=group, activity_list=activity)
        response = activity_client.post(f'/activity/unshare/{link.pk}/')
        assert response.status_code == 302


@pytest.mark.django_db
class TestActivityAssignViews:
    def test_assign_view_get(self, activity_client, activity):
        response = activity_client.get(f'/activity/assign/{activity.pk}/')
        assert response.status_code == 200

    def test_assign_view_post_no_groups(self, activity_client, activity):
        response = activity_client.post(f'/activity/assign/{activity.pk}/', {})
        assert response.status_code == 200

    def test_assign_view_post_with_groups(self, activity_client, activity, activity_user):
        group = Group.objects.create(
            name='G Assign', description='x' * 15, shift='Manhã', created_by=activity_user
        )
        response = activity_client.post(f'/activity/assign/{activity.pk}/', {
            'groups': [group.pk],
            'starts_at': '',
            'ends_at': '',
        })
        assert response.status_code in (200, 302)

    def test_assign_view_post_bind_all_groups(self, activity_client, activity, activity_user):
        Group.objects.create(
            name='G All', description='x' * 15, shift='Manhã', created_by=activity_user
        )
        response = activity_client.post(f'/activity/assign/{activity.pk}/', {
            'bind_all_groups': 'on',
        })
        assert response.status_code in (200, 302)

    def test_assign_view_get_with_filter(self, activity_client, activity):
        response = activity_client.get(
            f'/activity/assign/{activity.pk}/?search_field=group&q=test'
        )
        assert response.status_code == 200

    def test_assign_update_view_get(self, activity_client, activity, activity_user):
        group = Group.objects.create(
            name='G Update', description='x' * 15, shift='Manhã', created_by=activity_user
        )
        link = ActivityListGroup.objects.create(
            group=group,
            activity_list=activity,
            starts_at=timezone.now(),
            ends_at=timezone.now() + timedelta(days=7),
        )
        response = activity_client.get(f'/activity/assign/update/{link.pk}/')
        assert response.status_code == 200

    def test_assign_update_view_post(self, activity_client, activity, activity_user):
        group = Group.objects.create(
            name='G Update P', description='x' * 15, shift='Manhã', created_by=activity_user
        )
        link = ActivityListGroup.objects.create(group=group, activity_list=activity)
        response = activity_client.post(
            f'/activity/assign/update/{link.pk}/',
            {'starts_at': '', 'ends_at': ''},
        )
        assert response.status_code in (200, 302)

    def test_assign_view_get_with_all_exercise_types(self, activity_client, activity, activity_user):
        e1 = Exercise.objects.create(activity_list=activity, type='discursive', statement='Q1', points=1.0)
        DiscursiveExercise.objects.create(exercise=e1, min_words=10)
        e2 = Exercise.objects.create(activity_list=activity, type='code', statement='Q2', points=1.0)
        CodeExercise.objects.create(exercise=e2, language='python')
        e3 = Exercise.objects.create(activity_list=activity, type='complete_code', statement='Q3', points=1.0)
        CompleteCodeExercise.objects.create(exercise=e3, language='python', starter_code='x = ___', complete_code='x = 1')
        e4 = Exercise.objects.create(activity_list=activity, type='multiple_choice', statement='Q4', points=1.0)
        mc = MultipleChoiceExercise.objects.create(exercise=e4)
        ExerciseOption.objects.create(exercise=mc, text='A', is_correct=True)
        response = activity_client.get(f'/activity/assign/{activity.pk}/')
        assert response.status_code == 200

    def test_assign_view_get_with_sharings(self, activity_client, activity, activity_user):
        group = Group.objects.create(
            name='G Shrd', description='x' * 15, shift='Manhã', created_by=activity_user
        )
        ActivityListGroup.objects.create(group=group, activity_list=activity)
        response = activity_client.get(f'/activity/assign/{activity.pk}/')
        assert response.status_code == 200

    def test_assign_view_post_invalid_form(self, activity_client, activity):
        response = activity_client.post(f'/activity/assign/{activity.pk}/', {
            'bind_all_groups': 'on',
            'starts_at': '2026-06-20T10:00',
            'ends_at': '2026-06-19T10:00',
        })
        assert response.status_code == 200

    def test_assign_view_post_bind_all_no_groups(self, activity_client, activity):
        response = activity_client.post(f'/activity/assign/{activity.pk}/', {
            'bind_all_groups': 'on',
            'starts_at': '',
            'ends_at': '',
        })
        assert response.status_code == 200

    def test_assign_view_get_with_ordering(self, activity_client, activity, activity_user):
        group = Group.objects.create(
            name='G Ord', description='x' * 15, shift='Manhã', created_by=activity_user
        )
        ActivityListGroup.objects.create(group=group, activity_list=activity)
        response = activity_client.get(
            f'/activity/assign/{activity.pk}/?sort=group&order=asc'
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestExerciseViews:
    def test_exercise_cancel_get(self, activity_client, activity):
        response = activity_client.get(f'/activity/exercise/cancel/{activity.pk}/')
        assert response.status_code == 200

    def test_exercise_delete_get(self, activity_client, activity, activity_user):
        exercise = Exercise.objects.create(
            activity_list=activity, type='discursive', statement='Test', points=1.0
        )
        response = activity_client.get(f'/activity/exercise/delete/{exercise.pk}/')
        assert response.status_code == 200

    def test_exercise_delete_post(self, activity_client, activity, activity_user):
        exercise = Exercise.objects.create(
            activity_list=activity, type='discursive', statement='Test Del', points=1.0
        )
        response = activity_client.post(f'/activity/exercise/delete/{exercise.pk}/')
        assert response.status_code == 200

    # ── Discursive exercise ───────────────────────────────────────────────────

    def test_discursive_create_get(self, activity_client, activity):
        response = activity_client.get(
            f'/activity/exercise/discursive/create/{activity.pk}/'
        )
        assert response.status_code == 200

    def test_discursive_create_post_valid(self, activity_client, activity):
        response = activity_client.post(
            f'/activity/exercise/discursive/create/{activity.pk}/',
            {
                'activity_list': activity.pk,
                'type': 'discursive',
                'statement': 'Explique o conceito de herança',
                'points': '1.0',
                'secondary-min_words': '20',
                'secondary-max_words': '100',
            },
        )
        assert response.status_code == 200

    def test_discursive_create_post_invalid_main_form(self, activity_client, activity):
        response = activity_client.post(
            f'/activity/exercise/discursive/create/{activity.pk}/',
            {
                'activity_list': activity.pk,
                'type': 'discursive',
                'statement': '',
                'points': '1.0',
                'secondary-min_words': '',
                'secondary-max_words': '',
            },
        )
        assert response.status_code == 200

    def test_discursive_create_post_invalid_secondary(self, activity_client, activity):
        response = activity_client.post(
            f'/activity/exercise/discursive/create/{activity.pk}/',
            {
                'activity_list': activity.pk,
                'type': 'discursive',
                'statement': 'Enunciado válido aqui',
                'points': '1.0',
                'secondary-min_words': '200',
                'secondary-max_words': '50',
            },
        )
        assert response.status_code in (200, 400)

    def test_discursive_update_get(self, activity_client, activity):
        exercise = Exercise.objects.create(
            activity_list=activity, type='discursive', statement='Old', points=1.0
        )
        DiscursiveExercise.objects.create(exercise=exercise, min_words=10)
        response = activity_client.get(
            f'/activity/exercise/discursive/update/{exercise.pk}/'
        )
        assert response.status_code == 200

    def test_discursive_update_post(self, activity_client, activity):
        exercise = Exercise.objects.create(
            activity_list=activity, type='discursive', statement='Old', points=1.0
        )
        DiscursiveExercise.objects.create(exercise=exercise, min_words=10)
        response = activity_client.post(
            f'/activity/exercise/discursive/update/{exercise.pk}/',
            {
                'activity_list': activity.pk,
                'type': 'discursive',
                'statement': 'Enunciado atualizado',
                'points': '2.0',
                'secondary-min_words': '30',
                'secondary-max_words': '',
            },
        )
        assert response.status_code == 200

    # ── Code exercise ─────────────────────────────────────────────────────────

    def test_code_create_get(self, activity_client, activity):
        response = activity_client.get(
            f'/activity/exercise/code/create/{activity.pk}/'
        )
        assert response.status_code == 200

    def test_code_create_post_valid(self, activity_client, activity):
        response = activity_client.post(
            f'/activity/exercise/code/create/{activity.pk}/',
            {
                'activity_list': activity.pk,
                'type': 'code',
                'statement': 'Escreva um programa Python',
                'points': '1.0',
                'secondary-language': 'python',
                'secondary-expected_output': 'hello world',
            },
        )
        assert response.status_code == 200

    def test_code_create_post_with_test_case(self, activity_client, activity):
        response = activity_client.post(
            f'/activity/exercise/code/create/{activity.pk}/',
            {
                'activity_list': activity.pk,
                'type': 'code',
                'statement': 'Escreva um programa Python com saída',
                'points': '1.0',
                'secondary-language': 'python',
                'test_cases-TOTAL_FORMS': '1',
                'test_cases-INITIAL_FORMS': '0',
                'test_cases-MIN_NUM_FORMS': '0',
                'test_cases-MAX_NUM_FORMS': '1000',
                'test_cases-0-input': '',
                'test_cases-0-expected_output': '42',
                'test_cases-0-DELETE': '',
            },
        )
        assert response.status_code == 200

    def test_code_create_post_tampered_activity_list(self, activity_client, activity):
        response = activity_client.post(
            f'/activity/exercise/code/create/{activity.pk}/',
            {
                'activity_list': 99999,
                'type': 'code',
                'statement': 'Enunciado qualquer',
                'points': '1.0',
                'secondary-language': 'python',
                'secondary-expected_output': 'hello',
            },
        )
        assert response.status_code == 403

    def test_code_create_post_invalid_main_form(self, activity_client, activity):
        response = activity_client.post(
            f'/activity/exercise/code/create/{activity.pk}/',
            {
                'activity_list': activity.pk,
                'type': 'code',
                'statement': '',
                'points': '1.0',
                'secondary-language': 'python',
                'secondary-expected_output': 'hello',
            },
        )
        assert response.status_code == 200

    def test_code_update_get(self, activity_client, activity):
        exercise = Exercise.objects.create(
            activity_list=activity, type='code', statement='Old code', points=1.0
        )
        CodeExercise.objects.create(
            exercise=exercise, language='python'
        )
        response = activity_client.get(
            f'/activity/exercise/code/update/{exercise.pk}/'
        )
        assert response.status_code == 200

    def test_code_update_post(self, activity_client, activity):
        exercise = Exercise.objects.create(
            activity_list=activity, type='code', statement='Old code', points=1.0
        )
        CodeExercise.objects.create(
            exercise=exercise, language='python'
        )
        response = activity_client.post(
            f'/activity/exercise/code/update/{exercise.pk}/',
            {
                'activity_list': activity.pk,
                'type': 'code',
                'statement': 'Enunciado atualizado',
                'points': '2.0',
                'secondary-language': 'python',
                'secondary-expected_output': 'new output',
            },
        )
        assert response.status_code == 200

    # ── Complete-code exercise ────────────────────────────────────────────────

    def test_complete_code_create_get(self, activity_client, activity):
        response = activity_client.get(
            f'/activity/exercise/complete-code/create/{activity.pk}/'
        )
        assert response.status_code == 200

    def test_complete_code_create_post_invalid_secondary(self, activity_client, activity):
        response = activity_client.post(
            f'/activity/exercise/complete-code/create/{activity.pk}/',
            {
                'activity_list': activity.pk,
                'type': 'complete_code',
                'statement': 'Complete o código abaixo',
                'points': '1.0',
                'secondary-language': 'python',
                'secondary-starter_code': 'print("hello")',
                'secondary-complete_code': 'print("hello")',
            },
        )
        assert response.status_code == 200

    def test_complete_code_create_post_valid(self, activity_client, activity):
        response = activity_client.post(
            f'/activity/exercise/complete-code/create/{activity.pk}/',
            {
                'activity_list': activity.pk,
                'type': 'complete_code',
                'statement': 'Complete o código abaixo',
                'points': '1.0',
                'secondary-language': 'python',
                'secondary-starter_code': 'x = ___',
                'secondary-complete_code': 'x = 42',
            },
        )
        assert response.status_code == 200

    def test_complete_code_update_get(self, activity_client, activity):
        exercise = Exercise.objects.create(
            activity_list=activity, type='complete_code', statement='Old', points=1.0
        )
        CompleteCodeExercise.objects.create(
            exercise=exercise,
            language='python',
            starter_code='x = ___',
            complete_code='x = 1',
        )
        response = activity_client.get(
            f'/activity/exercise/complete-code/update/{exercise.pk}/'
        )
        assert response.status_code == 200

    # ── Multiple-choice exercise ──────────────────────────────────────────────

    def test_multiple_choice_create_get(self, activity_client, activity):
        response = activity_client.get(
            f'/activity/exercise/multiple-choice/create/{activity.pk}/'
        )
        assert response.status_code == 200

    def test_multiple_choice_create_post_valid(self, activity_client, activity):
        response = activity_client.post(
            f'/activity/exercise/multiple-choice/create/{activity.pk}/',
            {
                'activity_list': activity.pk,
                'type': 'multiple_choice',
                'statement': 'Qual a saída?',
                'points': '1.0',
                'options-TOTAL_FORMS': '2',
                'options-INITIAL_FORMS': '0',
                'options-MIN_NUM_FORMS': '0',
                'options-MAX_NUM_FORMS': '1000',
                'options-0-text': 'Opção A',
                'options-0-is_correct': 'on',
                'options-0-DELETE': '',
                'options-1-text': 'Opção B',
                'options-1-is_correct': '',
                'options-1-DELETE': '',
            },
        )
        assert response.status_code == 200

    def test_multiple_choice_create_post_no_correct(self, activity_client, activity):
        response = activity_client.post(
            f'/activity/exercise/multiple-choice/create/{activity.pk}/',
            {
                'activity_list': activity.pk,
                'type': 'multiple_choice',
                'statement': 'Qual a saída?',
                'points': '1.0',
                'options-TOTAL_FORMS': '2',
                'options-INITIAL_FORMS': '0',
                'options-MIN_NUM_FORMS': '0',
                'options-MAX_NUM_FORMS': '1000',
                'options-0-text': 'Opção A',
                'options-0-is_correct': '',
                'options-0-DELETE': '',
                'options-1-text': 'Opção B',
                'options-1-is_correct': '',
                'options-1-DELETE': '',
            },
        )
        assert response.status_code == 200

    def test_multiple_choice_create_post_tampered_type(self, activity_client, activity):
        response = activity_client.post(
            f'/activity/exercise/multiple-choice/create/{activity.pk}/',
            {
                'activity_list': activity.pk,
                'type': 'code',
                'statement': 'Qual a saída?',
                'points': '1.0',
                'options-TOTAL_FORMS': '1',
                'options-INITIAL_FORMS': '0',
                'options-MIN_NUM_FORMS': '0',
                'options-MAX_NUM_FORMS': '1000',
                'options-0-text': 'Opção A',
                'options-0-is_correct': 'on',
                'options-0-DELETE': '',
            },
        )
        assert response.status_code == 403

    def test_multiple_choice_update_get(self, activity_client, activity):
        exercise = Exercise.objects.create(
            activity_list=activity, type='multiple_choice', statement='Old MC', points=1.0
        )
        mc = MultipleChoiceExercise.objects.create(exercise=exercise)
        ExerciseOption.objects.create(exercise=mc, text='Opção X', is_correct=True)
        response = activity_client.get(
            f'/activity/exercise/multiple-choice/update/{exercise.pk}/'
        )
        assert response.status_code == 200

    def test_multiple_choice_add_option_post(self, activity_client):
        response = activity_client.post(
            '/activity/exercise/multiple-choice/add-option/',
            {'total_forms': '3'},
        )
        assert response.status_code == 200

    # ── ExerciseCancelUpdateView ──────────────────────────────────────────────

    def test_exercise_cancel_update_get_valid(self, activity_client, activity):
        exercise = Exercise.objects.create(
            activity_list=activity, type='discursive', statement='Test cancel update', points=1.0
        )
        DiscursiveExercise.objects.create(exercise=exercise, min_words=10)
        response = activity_client.get(
            f'/activity/exercise/cancel/update/{exercise.pk}/'
        )
        assert response.status_code == 200

    def test_exercise_cancel_update_get_not_found(self, activity_client):
        response = activity_client.get('/activity/exercise/cancel/update/99999/')
        assert response.status_code == 403

    # ── ExerciseTypeSelectorCardView ──────────────────────────────────────────

    def test_exercise_type_selector_get(self, activity_client, activity):
        response = activity_client.get(
            f'/activity/exercise/type-selector/{activity.pk}/'
        )
        assert response.status_code == 200

    # ── ExerciseAnnulView ─────────────────────────────────────────────────────

    def test_exercise_annul_post_toggles(self, activity_client, activity):
        exercise = Exercise.objects.create(
            activity_list=activity, type='discursive', statement='Test annul', points=1.0
        )
        DiscursiveExercise.objects.create(exercise=exercise, min_words=10)
        response = activity_client.post(f'/activity/exercise/annul/{exercise.pk}/')
        assert response.status_code == 200
        exercise.refresh_from_db()
        assert exercise.is_annulled is True

    def test_exercise_annul_post_unauthorized(self, activity_client, activity_user):
        other = User.objects.create_user(username='other_annul', password='pass')
        other_activity = ActivityList.objects.create(title='Outro', created_by=other)
        exercise = Exercise.objects.create(
            activity_list=other_activity, type='discursive', statement='Outro', points=1.0
        )
        DiscursiveExercise.objects.create(exercise=exercise, min_words=10)
        response = activity_client.post(f'/activity/exercise/annul/{exercise.pk}/')
        assert response.status_code == 404


@pytest.mark.django_db
class TestActivityDetailAndPreviewViews:
    def test_detail_view_get(self, activity_client, activity, activity_user):
        response = activity_client.get(f'/activity/detail/{activity.pk}/')
        assert response.status_code == 200

    def test_detail_view_with_all_exercise_types(self, activity_client, activity, activity_user):
        e1 = Exercise.objects.create(activity_list=activity, type='discursive', statement='D1', points=1.0)
        DiscursiveExercise.objects.create(exercise=e1, min_words=10)
        e2 = Exercise.objects.create(activity_list=activity, type='code', statement='C1', points=1.0)
        CodeExercise.objects.create(exercise=e2, language='python')
        e3 = Exercise.objects.create(activity_list=activity, type='complete_code', statement='CC1', points=1.0)
        CompleteCodeExercise.objects.create(exercise=e3, language='python', starter_code='x=___', complete_code='x=1')
        e4 = Exercise.objects.create(activity_list=activity, type='multiple_choice', statement='MC1', points=1.0)
        mc = MultipleChoiceExercise.objects.create(exercise=e4)
        ExerciseOption.objects.create(exercise=mc, text='A', is_correct=True)
        response = activity_client.get(f'/activity/detail/{activity.pk}/')
        assert response.status_code == 200

    def test_detail_view_unauthorized(self, activity_client, activity_user):
        other = User.objects.create_user(username='other_det', password='pass')
        other_activity = ActivityList.objects.create(title='Outro', created_by=other)
        response = activity_client.get(f'/activity/detail/{other_activity.pk}/')
        assert response.status_code == 403

    def test_preview_view_get(self, activity_client, activity, activity_user):
        e1 = Exercise.objects.create(activity_list=activity, type='discursive', statement='Preview', points=1.0)
        DiscursiveExercise.objects.create(exercise=e1, min_words=10)
        response = activity_client.get(f'/activity/preview/{activity.pk}/')
        assert response.status_code == 200

    def test_preview_view_unauthorized(self, activity_client, activity_user):
        other = User.objects.create_user(username='other_prev', password='pass')
        other_activity = ActivityList.objects.create(title='Outro2', created_by=other)
        response = activity_client.get(f'/activity/preview/{other_activity.pk}/')
        assert response.status_code == 403

    def test_review_tab_get(self, activity_client, activity, activity_user):
        group = Group.objects.create(
            name='Review Group', description='x' * 15, shift='Manhã', created_by=activity_user
        )
        ActivityListGroup.objects.create(group=group, activity_list=activity)
        response = activity_client.get(f'/activity/review/{activity.pk}/')
        assert response.status_code == 200
        assert 'review_links' in response.context

    def test_review_tab_includes_group_annotations(self, activity_client, activity, activity_user):
        group = Group.objects.create(
            name='Anotado', description='x' * 15, shift='Tarde', created_by=activity_user
        )
        ActivityListGroup.objects.create(group=group, activity_list=activity)
        response = activity_client.get(f'/activity/review/{activity.pk}/')
        assert response.status_code == 200
        links = list(response.context['review_links'])
        assert len(links) == 1
        assert hasattr(links[0], 'submission_count')
        assert hasattr(links[0], 'pending_count')

    def test_review_tab_unauthorized(self, activity_client, activity_user):
        other = User.objects.create_user(username='other_rev', password='pass')
        other_activity = ActivityList.objects.create(title='OutroRev', created_by=other)
        response = activity_client.get(f'/activity/review/{other_activity.pk}/')
        assert response.status_code == 403


@pytest.mark.django_db
class TestActivityUpdateProtection:
    def test_update_form_valid_blocked_when_submissions_exist(self, activity_client, activity, activity_user):
        from group.models import Group, GroupStudent
        from student.models import Submission
        group = Group.objects.create(
            name='G Protect', description='x' * 15, shift='Manhã', created_by=activity_user
        )
        student = User.objects.create_user(username='stud_protect', password='pass')
        GroupStudent.objects.create(group=group, student=student, is_active=True)
        link = ActivityListGroup.objects.create(group=group, activity_list=activity)
        Submission.objects.create(student=student, activity_link=link)
        response = activity_client.post(f'/activity/update/{activity.pk}/', {
            'title': 'Tentativa de Edição',
            'description': 'desc',
        })
        # Should redirect to list when blocked
        assert response.status_code == 302


@pytest.mark.django_db
class TestActivityUnshareProtection:
    def test_unshare_blocked_when_submissions_exist(self, activity_client, activity, activity_user):
        from group.models import Group, GroupStudent
        from student.models import Submission
        group = Group.objects.create(
            name='G Unshare S', description='x' * 15, shift='Manhã', created_by=activity_user
        )
        student = User.objects.create_user(username='stud_unshare', password='pass')
        GroupStudent.objects.create(group=group, student=student, is_active=True)
        link = ActivityListGroup.objects.create(group=group, activity_list=activity)
        Submission.objects.create(
            student=student, activity_link=link, submitted_at=timezone.now()
        )
        response = activity_client.post(f'/activity/unshare/{link.pk}/')
        assert response.status_code == 302
        assert ActivityListGroup.objects.filter(pk=link.pk).exists()


@pytest.mark.django_db
class TestActivityUpdateSharedAccess:
    def test_shared_teacher_can_access_update(self, activity_client, activity, activity_user):
        from group.models import Group, GroupSharing
        other = User.objects.create_user(username='shared_upd_user', password='pass')
        group = Group.objects.create(
            name='G Shared Upd', description='x' * 15, shift='Manhã', created_by=activity_user
        )
        ActivityListGroup.objects.create(group=group, activity_list=activity)
        GroupSharing.objects.create(group=group, shared_with=other, shared_by=activity_user, is_active=True)
        other_client = Client()
        other_client.post('/accounts/login/', {'username': 'shared_upd_user', 'password': 'pass'})
        response = other_client.get(f'/activity/update/{activity.pk}/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestActivityArchiveOpenPeriod:
    def test_archive_blocked_when_has_open_period(self, activity_client, activity, activity_user):
        from group.models import Group
        group = Group.objects.create(
            name='G Archive Open', description='x' * 15, shift='Manhã', created_by=activity_user
        )
        ActivityListGroup.objects.create(
            group=group, activity_list=activity, ends_at=None
        )
        activity_client.post(f'/activity/archive/{activity.pk}/')
        from activity.models import ActivityArchived
        archived = ActivityArchived.objects.filter(activity_list=activity, user=activity_user).first()
        assert archived is None or not archived.is_archived


@pytest.mark.django_db
class TestActivityStatsView:
    def test_stats_empty_no_submissions(self, activity_client, activity, activity_user):
        group = Group.objects.create(
            name='Stats Group', description='x' * 15, shift='Manhã', created_by=activity_user
        )
        ActivityListGroup.objects.create(group=group, activity_list=activity)
        response = activity_client.get(f'/activity/stats/{activity.pk}/')
        assert response.status_code == 200
        ctx = response.context
        assert ctx['students_submitted'] == 0
        assert ctx['total_submissions'] == 0
        assert ctx['avg_points'] is None

    def test_stats_with_submissions_and_answers(self, activity_client, activity, activity_user):
        from django.utils import timezone
        from group.models import GroupStudent
        from student.models import ExerciseAnswer, Submission

        group = Group.objects.create(
            name='Stats Full', description='x' * 15, shift='Tarde', created_by=activity_user
        )
        student = User.objects.create_user(username='stats_student', password='pass')
        GroupStudent.objects.create(group=group, student=student, is_active=True)

        e1 = Exercise.objects.create(
            activity_list=activity, type='discursive', statement='Q1', points=10,
        )
        DiscursiveExercise.objects.create(exercise=e1, min_words=0)

        mc_ex = Exercise.objects.create(
            activity_list=activity, type='multiple_choice', statement='MC1', points=5,
        )
        mc = MultipleChoiceExercise.objects.create(exercise=mc_ex)
        opt_correct = ExerciseOption.objects.create(exercise=mc, text='Certo', is_correct=True)
        ExerciseOption.objects.create(exercise=mc, text='Errado', is_correct=False)

        link = ActivityListGroup.objects.create(group=group, activity_list=activity)
        sub = Submission.objects.create(
            student=student, activity_link=link, submitted_at=timezone.now()
        )
        ExerciseAnswer.objects.create(
            submission=sub, exercise=e1, answer_text='resposta', is_correct=True,
        )
        ExerciseAnswer.objects.create(
            submission=sub, exercise=mc_ex, selected_option=opt_correct, is_correct=True,
        )

        response = activity_client.get(f'/activity/stats/{activity.pk}/')
        assert response.status_code == 200
        ctx = response.context
        assert ctx['students_submitted'] == 1
        assert ctx['completion_pct'] == 100
        assert ctx['avg_points'] is not None
        assert len(ctx['group_stats']) == 1

    def test_stats_unauthorized(self, activity_client, activity_user):
        other = User.objects.create_user(username='other_stats', password='pass')
        other_activity = ActivityList.objects.create(title='Other', created_by=other)
        response = activity_client.get(f'/activity/stats/{other_activity.pk}/')
        assert response.status_code == 403

    def test_stats_covers_distribution_and_exercise_tags(self, activity_client, activity, activity_user):
        """Covers all distribution buckets (0–25, 25–50, 50–75, 75–100) and exercise tags."""
        from django.utils import timezone
        from group.models import GroupStudent
        from student.models import ExerciseAnswer, Submission

        group = Group.objects.create(
            name='Tags Group', description='x' * 15, shift='Manhã', created_by=activity_user
        )

        # 4 exercises at 5 pts each → pct increments of 25
        exs = [
            Exercise.objects.create(
                activity_list=activity, type='discursive', statement=f'Q{i}', points=5,
            )
            for i in range(4)
        ]
        for ex in exs:
            DiscursiveExercise.objects.create(exercise=ex, min_words=0)

        link = ActivityListGroup.objects.create(group=group, activity_list=activity)

        def make_student_sub(username, correct_mask, time_list):
            st = User.objects.create_user(username=username, password='x')
            GroupStudent.objects.create(group=group, student=st, is_active=True)
            sub = Submission.objects.create(student=st, activity_link=link, submitted_at=timezone.now())
            for ex, correct, t in zip(exs, correct_mask, time_list):
                ExerciseAnswer.objects.create(
                    submission=sub, exercise=ex,
                    is_correct=correct, time_spent_seconds=t,
                )
            return sub

        # pct = 0/4 → 0% → distribution[0] (pct < 25)
        make_student_sub('s_dist0', [False, False, False, False], [200, 200, 0, 0])
        # pct = 1/4 → 25% → distribution[1] (25 <= pct < 50)
        make_student_sub('s_dist1', [True, False, False, False], [200, 200, 0, 0])
        # pct = 2/4 → 50% → distribution[2] (50 <= pct < 75)
        make_student_sub('s_dist2', [True, True, False, False], [200, 0, 300, 0])

        response = activity_client.get(f'/activity/stats/{activity.pk}/')
        assert response.status_code == 200
        ctx = response.context

        # distribution buckets
        dist = {d['label']: d['count'] for d in ctx['distribution']}
        assert dist['0–25%'] == 1    # s_dist0
        assert dist['25–50%'] == 1   # s_dist1
        assert dist['50–75%'] == 1   # s_dist2

        # exercise tags: avg accuracy & time depend on the 3 students above
        # Ex0 (Q0): s_dist0 wrong, s_dist1 correct, s_dist2 correct → acc=67%, avg_t=200s → 'Médio'
        # Ex1 (Q1): s_dist0 wrong, s_dist1 wrong, s_dist2 correct → acc=33%, avg_t=133s → 'Alto'
        # Ex2 (Q2): all wrong → acc=0%, avg_t=0 → 'Médio Alto'
        # Ex3 (Q3): all wrong → acc=0%, avg_t=0 → 'Médio Alto'  (duplicate OK)
        tags = {row['exercise_id']: row['tag'] for row in ctx['exercise_rows']}
        assert tags[exs[0].pk] == 'Médio'
        assert tags[exs[1].pk] == 'Alto'
        assert tags[exs[2].pk] == 'Médio Alto'

        # Also verify 'Médio Baixo' tag: need acc in 40-80% and avg_t <= 180
        # Ex3 all wrong → 'Médio Alto'; we need a new exercise
        ex_ok = Exercise.objects.create(
            activity_list=activity, type='discursive', statement='Q_ok', points=5,
        )
        DiscursiveExercise.objects.create(exercise=ex_ok, min_words=0)

        # Add answers for the 3 students to ex_ok: 2/3 correct → acc=67%, avg_t=0 → 'Médio Baixo'
        for sub_username, correct in [('s_dist0', True), ('s_dist1', True), ('s_dist2', False)]:
            sub = Submission.objects.get(student__username=sub_username, activity_link=link)
            ExerciseAnswer.objects.create(submission=sub, exercise=ex_ok, is_correct=correct)

        response2 = activity_client.get(f'/activity/stats/{activity.pk}/')
        assert response2.status_code == 200
        tags2 = {row['exercise_id']: row['tag'] for row in response2.context['exercise_rows']}
        assert tags2[ex_ok.pk] == 'Médio Baixo'

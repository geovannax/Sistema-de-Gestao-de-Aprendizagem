from activity.constants import EXERCISE_TYPES
from activity.forms.exercise import ExerciseForm
from activity.models import ActivityList, Exercise
from common.mixins import HTMXLoginRequiredMixin, ObjectAccessRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import UpdateView


class ExerciseBaseMixin(HTMXLoginRequiredMixin, ObjectAccessRequiredMixin):
    """
    Mixin base para views de criação e atualização de exercícios.

    Centraliza a lógica compartilhada entre todos os tipos de exercício
    (múltipla escolha, código, completar código, etc.), como controle de
    acesso, detecção de criação/atualização, resolução do objeto e contexto.

    Deve ser combinado com CreateView ou UpdateView e com um mixin de formulário
    secundário (InlineFormsetMixin ou SecondaryFormMixin).

    Atributos:
        model: Modelo principal da view (Exercise).
        form_class: Formulário principal (ExerciseForm).
        update_url: Nome da URL de atualização usada no render_success.
        type_exercise: Tipo do exercício (ex: 'code', 'multiple_choice').
    """
    model = Exercise
    form_class = ExerciseForm
    update_url = None
    type_exercise = None

    @property
    def is_update(self) -> bool:
        """Retorna True se a view atual é uma instância de UpdateView."""
        return isinstance(self, UpdateView)

    def has_object_access(self, user: User, obj: Exercise | ActivityList) -> bool:
        if self.is_update:
            return obj.activity_list.created_by == user
        return False if not obj else obj.created_by == user

    def get_initial(self) -> dict:
        if self.is_update:
            return super().get_initial()

        if self.type_exercise not in dict(EXERCISE_TYPES):
            raise ValueError(f"Tipo de exercício inválido: {self.type_exercise}")

        if not self.type_exercise:  # pragma: no cover
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} precisa de 'type_exercise'"
            )

        pk = self.kwargs.get('pk')
        return {'activity_list': pk, 'type': self.type_exercise}

    def get_activity_list_id(self) -> int:
        if self.is_update:
            if not hasattr(self, 'object'):  # pragma: no cover
                self.object = self.get_object()
            return self.object.activity_list.id
        return self.kwargs.get('pk')

    def get_object(self) -> Exercise | ActivityList | None:
        if self.is_update:
            return Exercise.objects.filter(
                id=self.kwargs.get('pk'),
                activity_list__created_by=self.request.user,
                activity_list__deleted_at__isnull=True
            ).first()

        return ActivityList.objects.filter(
            id=self.kwargs.get('pk'),
            created_by=self.request.user,
            deleted_at__isnull=True
        ).first()

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context['activity_list'] = self.get_activity_list_id()
        context['is_update'] = self.is_update
        context['type_exercise'] = self.type_exercise
        return context

    def render_success(self) -> HttpResponse:
        if not self.update_url:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} precisa de 'update_url'"
            )

        exercise = (
            Exercise.objects
            .select_related(
                'code_exercise',
                'complete_code_exercise',
                'discursive_exercise',
                'multiple_choice_exercise',
            )
            .prefetch_related(
                'code_exercise__test_cases',
                'multiple_choice_exercise__options',
            )
            .get(pk=self.object.pk)
        )
        exercise.update_url = self.update_url
        from student.models import ExerciseAnswer
        exercise.has_submissions = ExerciseAnswer.objects.filter(
            exercise=exercise,
            submission__submitted_at__isnull=False,
        ).exists()

        activity_list_id = exercise.activity_list_id
        total_points = (
            Exercise.objects
            .filter(activity_list_id=activity_list_id, is_annulled=False)
            .aggregate(total=Sum('points'))['total'] or 0
        )

        return render(
            self.request,
            'activity/_exercise_card_save_response.html',
            {
                'exercise': exercise,
                'is_new': not self.is_update,
                'total_points': total_points,
                'activity_list_id': activity_list_id,
            }
        )

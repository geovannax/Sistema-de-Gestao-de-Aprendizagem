"""Mixins base para views de criação e edição de exercícios.

Fornece :class:`ExerciseBaseMixin`, que centraliza controle de acesso,
detecção de fluxo (criação vs. edição), resolução de objeto e renderização
do card de exercício após salvar. Deve ser combinado com
:class:`~common.mixins.SecondaryFormMixin` ou
:class:`~common.mixins.InlineFormsetMixin`.
"""
from __future__ import annotations

from typing import Any

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
    """Mixin base para views de criação e atualização de exercícios.

    Centraliza controle de acesso, detecção de fluxo (criação vs. edição),
    resolução do objeto e renderização do card após salvar. Deve ser combinado
    com ``CreateView`` ou ``UpdateView`` e com um mixin de formulário secundário
    (:class:`~common.mixins.InlineFormsetMixin` ou
    :class:`~common.mixins.SecondaryFormMixin`).

    Attributes:
        model: Modelo principal da view (``Exercise``).
        form_class: Formulário principal (:class:`~activity.forms.exercise.ExerciseForm`).
        update_url: Nome da URL de atualização usada em :meth:`render_success`.
        type_exercise: Tipo do exercício (ex: ``'code'``, ``'multiple_choice'``).
    """

    model = Exercise
    form_class = ExerciseForm
    update_url = None
    type_exercise = None

    @property
    def is_update(self) -> bool:
        """Indica se a view atual é uma edição (UpdateView) ou criação."""
        return isinstance(self, UpdateView)

    def has_object_access(self, user: User, obj: Exercise | ActivityList) -> bool:
        """Verifica se o usuário tem acesso ao objeto.

        Na edição, valida que o exercício pertence a uma lista criada pelo
        usuário. Na criação, verifica se a lista-pai foi criada pelo usuário.

        Args:
            user: Usuário autenticado da requisição.
            obj: ``Exercise`` (edição) ou ``ActivityList`` (criação).

        Returns:
            ``True`` se o acesso for permitido; ``False`` caso contrário.
        """
        if self.is_update:
            return obj.activity_list.created_by == user
        return False if not obj else obj.created_by == user

    def get_initial(self) -> dict[str, Any]:
        """Retorna os valores iniciais do formulário principal.

        Na edição, delega ao comportamento padrão do Django. Na criação,
        preenche ``activity_list`` e ``type`` com os valores da URL e do
        atributo :attr:`type_exercise`.

        Returns:
            Dicionário com ``activity_list`` e ``type`` na criação,
            ou os dados padrão do Django na edição.

        Raises:
            ValueError: Se :attr:`type_exercise` não for um tipo válido.
            ImproperlyConfigured: Se :attr:`type_exercise` não estiver definido.
        """
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
        """Retorna o ID da lista de atividades associada à view.

        Na edição, extrai o ID de ``self.object.activity_list``.
        Na criação, lê diretamente de ``kwargs['pk']``.

        Returns:
            ID (inteiro) da ``ActivityList`` pai.
        """
        if self.is_update:
            if not hasattr(self, 'object'):  # pragma: no cover
                self.object = self.get_object()
            return self.object.activity_list.id
        return self.kwargs.get('pk')

    def get_object(self) -> Exercise | ActivityList | None:
        """Resolve o objeto principal da view com verificação de propriedade.

        Na edição, retorna o ``Exercise`` cujo ``activity_list`` pertença ao
        usuário. Na criação, retorna a ``ActivityList`` pai.

        Returns:
            Instância do modelo ou ``None`` se não encontrado/autorizado.
        """
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

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Injeta metadados do exercício no contexto do template.

        Adiciona ``activity_list`` (ID da lista), ``is_update`` e
        ``type_exercise`` ao contexto padrão do Django.

        Returns:
            Dicionário de contexto enriquecido.
        """
        context = super().get_context_data(**kwargs)
        context['activity_list'] = self.get_activity_list_id()
        context['is_update'] = self.is_update
        context['type_exercise'] = self.type_exercise
        return context

    def render_success(self) -> HttpResponse:
        """Renderiza o card do exercício após salvar com sucesso.

        Recarrega o exercício com todos os relacionamentos necessários para
        o template, calcula a pontuação total da lista (excluindo anulados)
        e retorna o partial ``_exercise_card_save_response.html`` para
        substituição via HTMX.

        Returns:
            HttpResponse com o HTML do card atualizado e o total de pontos
            via ``hx-swap-oob``.

        Raises:
            ImproperlyConfigured: Se :attr:`update_url` não estiver definido.
        """
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

"""Views do app activity.

Implementa listagens, criação, edição, arquivamento, compartilhamento e
preview de listas de atividades, além de CRUD completo para exercícios
polimórficos dos quatro tipos: ``code``, ``complete_code``,
``multiple_choice`` e ``discursive``.
"""
from __future__ import annotations
from typing import Any
from activity.constants import EXERCISE_TYPES
from activity.forms.activity import ActivityAssignForm, ActivityListForm, ActivityListGroupPeriodForm
from activity.forms.exercise import CodeExerciseForm, CodeTestCaseForm, CompleteCodeExerciseForm, DiscursiveExerciseForm, ExerciseOptionForm
from activity.forms.formsets.code_test_case import CodeTestCaseFormCreateSet, CodeTestCaseFormUpdateSet
from activity.forms.formsets.exercise_option import ExerciseOptionFormCreateSet, ExerciseOptionFormUpdateSet
from activity.mixins import ExerciseBaseMixin
from activity.models import (
    ActivityArchived,
    ActivityList,
    ActivityListGroup,
    CodeExercise,
    CodeTestCase,
    CompleteCodeExercise,
    DiscursiveExercise,
    Exercise,
    MultipleChoiceExercise
)
from common.mixins import (
    HTMXLoginRequiredMixin,
    InlineFormsetMixin,
    SecondaryFormMixin,
    AuthPermissionMixin,
    ObjectAccessRequiredMixin,
    InlineFormsetMixin,

    FilteringMixin,
    OrderingMixin,
    PaginationMixin,
    EnrichObjectMixin,
)
from common.utils import get_btn_action
from student.models import ExerciseAnswer, Submission
from common.view.generic import EnhancedListView
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Prefetch, Count, Exists, OuterRef, Q, QuerySet, Sum
from django.forms import BaseModelForm
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView, View
from django.views.generic.edit import FormMixin


class ActivityListBaseView(EnhancedListView):
    """Classe base para listagens de atividades.

    Compartilha lógica de enriquecimento de ações, filtro de arquivadas
    e configuração das abas de navegação entre
    :class:`ActivityListView` e :class:`ActivityArchivedListView`.
    """
    allowed_fields = ['title', 'description', 'created_at']
    detail_url = 'activity:detail'
    model = ActivityList
    page_description = 'Organize, acompanhe e compartilhe suas atividades com facilidade.'

    def get_archived_activity_ids(self) -> QuerySet:
        """Retorna subquery para uso em ``Exists()`` — atividades arquivadas pelo usuário."""
        return ActivityArchived.objects.filter(
            activity_list=OuterRef('pk'),
            user=self.request.user,
            is_archived=True
        )

    def has_object_enrich_actions(self, user: User, obj: ActivityList) -> bool:
        """Retorna ``True`` se o usuário for o criador da atividade."""
        return obj.created_by == user

    def enrich_actions(self, user: User, obj: ActivityList) -> list:
        """Retorna os botões de ação disponíveis para o objeto na listagem.

        O criador recebe ``update``, ``archive`` e ``delete``. Usuários
        com acesso compartilhado recebem apenas ``archive``.
        """
        if self.has_object_enrich_actions(user, obj):
            return get_btn_action(
                ['update', 'archive', 'delete'],
                self.request.resolver_match.app_name
            )
        else:  # pragma: no cover
            return get_btn_action(
                ['archive'],
                self.request.resolver_match.app_name
            )

    def get_queryset(self) -> QuerySet[ActivityList]:
        """Retorna as atividades não deletadas e não arquivadas do usuário."""
        qs_archived = self.get_archived_activity_ids()

        return super().get_queryset().filter(
            created_by=self.request.user,
            deleted_at__isnull=True
        ).exclude(
            Exists(qs_archived)
        )

    def get_context_data(self, **kwargs) -> dict:
        """Adiciona abas de navegação e configuração de colunas ao contexto."""
        context = super().get_context_data(**kwargs)
        context.update({
            'nav_tabs': self.set_nav_tabs(),
            'table': {
                'fields': self.allowed_fields,
            },
        })
        return context

    def set_nav_tabs(self) -> list:
        """Retorna as abas de navegação entre listagens ativa e arquivada."""
        return [
            {
                'title': 'Ativas',
                'url': 'activity:list',
                'icon': 'bi-check-circle',
                'active': self.__class__.__name__ == 'ActivityListView'
            },
            {
                'title': 'Arquivadas',
                'url': 'activity:archived',
                'icon': 'bi-inbox',
                'active': self.__class__.__name__ == 'ActivityArchivedListView'
            }
        ]


class ActivityListView(AuthPermissionMixin, ActivityListBaseView):
    page_title = 'Atividades Ativas'    
    create_url = 'activity:create'


class ActivityArchivedListView(AuthPermissionMixin, ActivityListBaseView):
    """Listagem das atividades arquivadas pelo professor autenticado."""

    page_title = 'Atividades Arquivadas'
    create_url = None

    def get_queryset(self):
        """Retorna as atividades marcadas como arquivadas pelo usuário atual."""
        return ActivityList.objects.filter(
            created_by=self.request.user,
            archived_activities__user=self.request.user,
            archived_activities__is_archived=True,
            deleted_at__isnull=True,
        ).distinct().order_by('-id')


##### INICIO VIEW DE CRIAÇÃO/ATUALIZAÇÃO DE ATIVIDADE #####
class ActivityCreateOrUpdateView:
    """Mixin compartilhado entre criação e edição de listas de atividades.

    Centraliza a lógica de renderização do builder de exercícios, exibição
    de exercícios existentes e o fluxo de ``form_valid``/``form_invalid``.
    Deve ser combinado com :class:`~django.views.generic.CreateView` ou
    :class:`~django.views.generic.UpdateView`.
    """
    template_name = 'activity/create.html'
    form_class = ActivityListForm
    is_update_flow = False
    form_title = None
    form_subtitle = None
    page_title = None
    page_description = None

    def render_activity_builder(self) -> HttpResponse:
        """Após salvar a atividade, redireciona para a página de edição."""
        return redirect('activity:update', pk=self.object.pk)

    def get_exercises(self) -> list:
        """Retorna exercícios com related models e prefetch para exibição."""
        if not getattr(self, 'object', None):
            return []

        exercises = (
            self.object.exercises
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
            .order_by('order')
        )

        exercises = list(exercises)

        answered_ids = set(
            ExerciseAnswer.objects.filter(
                exercise__activity_list=self.object,
                submission__submitted_at__isnull=False,
            ).values_list('exercise_id', flat=True)
        )

        for exercise in exercises:
            exercise.update_url = EXERCISE_TYPES[exercise.type]['update_url']
            exercise.has_submissions = exercise.pk in answered_ids

        return exercises

    def get_context_data(self, **kwargs) -> dict:
        """Adiciona exercícios existentes, pontuação total e metadados do formulário ao contexto."""
        context = super().get_context_data(**kwargs)
        exercises = self.get_exercises()
        total_points = sum(e.points for e in exercises if not e.is_annulled) if exercises else 0
        context.update({
            'form_title': self.form_title,
            'form_subtitle': self.form_subtitle,
            'page_description': self.page_description,
            'page_title': self.page_title,
            'activity_list_id': self.object.id if getattr(self, 'object', None) else None,
            'exercises': exercises,
            'is_update_flow': self.is_update_flow,
            'has_exercises': bool(exercises),
            'total_points': total_points,
        })
        return context

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        """Salva a atividade atribuindo o criador no fluxo de criação.

        Na criação define ``created_by`` e ``is_published=False`` antes de
        salvar. Na edição apenas persiste o objeto. Redireciona para o
        builder de exercícios ao final.
        """
        self.object = form.save(commit=False)
        if not self.is_update_flow:
            self.object.created_by = self.request.user
            self.object.is_published = False
        self.object.save()
        return self.render_activity_builder()

    def form_invalid(self, form: BaseModelForm) -> HttpResponse:
        """Renderiza o formulário com erros retornando HTTP 400."""
        return render(
            self.request,
            self.template_name,
            self.get_context_data(form=form),
            status=400
        )


class ActivityCreateView(AuthPermissionMixin, ActivityCreateOrUpdateView, CreateView):
    """Criação de uma nova lista de atividades pelo professor autenticado."""

    form_title = 'Informações da Atividade'
    form_subtitle = 'Preencha os dados para criar uma nova atividade'
    page_title = 'Criar Nova Atividade'
    page_description = '...'


class ActivityUpdateView(
    AuthPermissionMixin,
    ActivityCreateOrUpdateView,
    ObjectAccessRequiredMixin,
    UpdateView
):
    """Edição de uma lista de atividades — restrita ao criador e professores com acesso compartilhado."""

    model = ActivityList
    form_class = ActivityListForm
    template_name = 'activity/create.html'
    is_update_flow = True
    form_title = 'Informações da Atividade'
    form_subtitle = 'Atualize os dados da atividade e gerencie seus exercícios.'
    page_title = 'Editar Atividade'
    page_description = 'Revise as informações da atividade e mantenha seus exercícios organizados.'

    def get_queryset(self) -> QuerySet[ActivityList]:
        """Retorna atividades não deletadas com prefetch de exercícios."""
        return (
            ActivityList.objects
            .filter(deleted_at__isnull=True)
            .prefetch_related('exercises')
        )

    def has_object_access(self, user: User, obj: ActivityList) -> bool:
        """Retorna ``True`` para o criador ou professores com turma compartilhada que contém a atividade."""
        if obj.created_by == user:
            return True
        return obj.list_groups.filter(
            group__sharings__shared_with=user,
            group__sharings__is_active=True,
            group__deleted_at__isnull=True,
        ).exists()

    def _has_submissions(self) -> bool:
        """Retorna ``True`` se existe ao menos uma submissão para esta atividade."""
        return Submission.objects.filter(
            activity_link__activity_list=self.get_object()
        ).exists()

    def get_context_data(self, **kwargs) -> dict:
        """Adiciona ``has_submissions`` ao contexto para controlar campos editáveis."""
        context = super().get_context_data(**kwargs)
        context['has_submissions'] = self._has_submissions()
        return context

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return super().get(request, *args, **kwargs)

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        """Salva a atividade com restrição de campos quando há submissões.

        Se já existem submissões, atualiza apenas ``title``, ``description`` e
        ``max_attempts`` para não invalidar respostas já entregues. Caso contrário,
        salva o formulário completo.
        """
        if self._has_submissions():
            obj = form.save(commit=False)
            obj.save(update_fields=['title', 'description', 'max_attempts', 'updated_at'])
            self.object = obj
            messages.success(self.request, 'Título, descrição e tentativas atualizados.')
            return self.render_activity_builder()
        self.object = form.save()
        return self.render_activity_builder()


##### INICIO VIEWS DE EXERCÍCIO #####

class ExerciseCancelView(HTMXLoginRequiredMixin, ObjectAccessRequiredMixin, View):
    """Cancela a criação de um novo exercício — retorna o slot de adicionar exercício."""

    def has_object_access(self, user: User, obj: ActivityList | None) -> bool:
        return False if not obj else obj.created_by == user

    def get_object(self) -> ActivityList | None:
        return ActivityList.objects.filter(
            id=self.kwargs.get('pk'),
            deleted_at__isnull=True
        ).first()

    def get(self, request: HttpRequest, pk: int, *args: Any, **kwargs: Any) -> HttpResponse:
        return render(
            request,
            'activity/_add_exercise_slot.html',
            {'activity_list_id': pk}
        )


class ExerciseCancelUpdateView(HTMXLoginRequiredMixin, ObjectAccessRequiredMixin, View):
    """Cancela a edição de um exercício existente — restaura o card de preview."""

    def has_object_access(self, user: User, obj: Exercise | None) -> bool:
        if not obj:
            return False
        return obj.activity_list.created_by == user

    def get_object(self) -> Exercise | None:
        return (
            Exercise.objects
            .select_related(
                'activity_list',
                'code_exercise',
                'complete_code_exercise',
                'discursive_exercise',
                'multiple_choice_exercise',
            )
            .prefetch_related(
                'code_exercise__test_cases',
                'multiple_choice_exercise__options',
            )
            .filter(
                id=self.kwargs.get('pk'),
                activity_list__deleted_at__isnull=True,
            )
            .first()
        )

    def get(self, request: HttpRequest, pk: int, *args: Any, **kwargs: Any) -> HttpResponse:
        exercise = self.get_object()
        exercise.update_url = EXERCISE_TYPES[exercise.type]['update_url']
        return render(request, 'activity/_exercise_card.html', {'exercise': exercise})


class ExerciseTypeSelectorCardView(HTMXLoginRequiredMixin, ObjectAccessRequiredMixin, View):
    """Retorna o card expandido de seleção de tipo de exercício."""

    def has_object_access(self, user: User, obj: ActivityList | None) -> bool:
        return False if not obj else obj.created_by == user

    def get_object(self) -> ActivityList | None:
        return ActivityList.objects.filter(
            id=self.kwargs.get('pk'),
            deleted_at__isnull=True
        ).first()

    def get(self, request: HttpRequest, pk: int, *args: Any, **kwargs: Any) -> HttpResponse:
        return render(
            request,
            'activity/_exercise_type_selector_card.html',
            {
                'exercise_types': EXERCISE_TYPES,
                'activity_list_id': pk,
            }
        )


##### INICIO VIEW DE DELETE DE EXERCÍCIO #####
class ExerciseDeleteView(AuthPermissionMixin, ObjectAccessRequiredMixin, DeleteView):
    """View para delete de exercício — usa confirmação inline no card."""
    model = Exercise
    template_name = 'activity/_exercise_delete_confirm.html'
    context_object_name = 'exercise'

    def has_object_access(self, user: User, obj: Exercise) -> bool:
        """Retorna ``True`` se o usuário for o criador da lista à qual o exercício pertence."""
        return obj.activity_list.created_by == user

    def get_activity_list_id(self) -> int:
        """Retorna o ``pk`` da lista de atividades do exercício sendo deletado."""
        return self.object.activity_list_id

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        """Deleta o exercício e retorna o fragmento com a pontuação total atualizada."""
        activity_list_id = self.get_activity_list_id()
        self.object.delete()
        total_points = (
            Exercise.objects
            .filter(activity_list_id=activity_list_id, is_annulled=False)
            .aggregate(total=Sum('points'))['total'] or 0
        )
        return render(
            self.request,
            'activity/_exercise_delete_response.html',
            {'total_points': total_points},
        )


class ExerciseAnnulView(AuthPermissionMixin, View):
    """Ativa ou desativa a anulação de um exercício."""

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        """Alterna ``is_annulled`` do exercício e retorna o card atualizado.

        Após o toggle, re-busca o exercício com todos os ``select_related`` e
        ``prefetch_related`` necessários para renderizar o card. Recalcula a
        pontuação total excluindo exercícios anulados.
        """
        exercise = get_object_or_404(Exercise, pk=pk)
        if exercise.activity_list.created_by != request.user:
            raise Http404
        exercise.is_annulled = not exercise.is_annulled
        exercise.save(update_fields=['is_annulled', 'updated_at'])

        exercise = (
            Exercise.objects
            .select_related('code_exercise', 'complete_code_exercise', 'discursive_exercise', 'multiple_choice_exercise')
            .prefetch_related('code_exercise__test_cases', 'multiple_choice_exercise__options')
            .get(pk=pk)
        )
        exercise.update_url = EXERCISE_TYPES[exercise.type]['update_url']
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
        return render(request, 'activity/_exercise_card_save_response.html', {
            'exercise': exercise,
            'is_new': False,
            'total_points': total_points,
            'activity_list_id': activity_list_id,
        })


class MultipleChoiceExerciseBaseView(ExerciseBaseMixin, InlineFormsetMixin):
    formset_model = MultipleChoiceExercise
    formset_related_name = 'multiple_choice_exercise'
    template_name = "activity/types/multiple_choice/_form.html"
    update_url = 'activity:multiple_choice_exercise_update'
    type_exercise = 'multiple_choice'


class MultipleChoiceExerciseCreateView(MultipleChoiceExerciseBaseView, CreateView):
    formset_class = ExerciseOptionFormCreateSet


class MultipleChoiceExerciseUpdateView(MultipleChoiceExerciseBaseView, UpdateView):
    formset_class = ExerciseOptionFormUpdateSet


class MultipleChoiceExerciseAddOptionView(HTMXLoginRequiredMixin, View):
    template_name = "activity/types/multiple_choice/_options.html"

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        total_forms = int(request.POST.get('total_forms', 0))
        
        # Criar formulário com o prefix correto
        form_prefix = f'options-{total_forms}'
        option_form = ExerciseOptionForm(prefix=form_prefix)
        
        return render(request, self.template_name, {'option_form': option_form})


class CodeExerciseBaseView(ExerciseBaseMixin, SecondaryFormMixin):
    secondary_form_class = CodeExerciseForm
    secondary_form_model = CodeExercise
    secondary_form_related_name = 'code_exercise'
    template_name = "activity/types/code/_form.html"
    update_url = 'activity:code_exercise_update'
    type_exercise = 'code'
    test_case_formset_class = None  # definido nas subclasses

    def get_test_case_formset(self):
        """Instancia o formset de casos de teste vinculado ao ``CodeExercise`` atual."""
        instance = self.get_secondary_instance()
        kwargs = {'prefix': 'test_cases', 'instance': instance}
        if self.request.POST:
            kwargs['data'] = self.request.POST
        return self.test_case_formset_class(**kwargs)

    def get_context_data(self, **kwargs):
        """Adiciona o formset de casos de teste ao contexto se ainda não estiver presente."""
        context = super().get_context_data(**kwargs)
        if 'test_case_formset' not in context:
            context['test_case_formset'] = self.get_test_case_formset()
        return context

    def form_valid(self, form):
        """Salva atomicamente o exercício base, o ``CodeExercise`` e os casos de teste."""
        instance = self.get_secondary_instance()
        secondary_form = self.get_secondary_form(instance=instance)
        test_case_formset = self.get_test_case_formset()

        if secondary_form.is_valid() and test_case_formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                secondary_obj = secondary_form.save(commit=False)
                secondary_obj.exercise = self.object
                secondary_obj.save()
                test_case_formset.instance = secondary_obj
                test_case_formset.save()
            return self.render_success()

        return self.form_invalid(form, secondary_form=secondary_form, test_case_formset=test_case_formset)

    def form_invalid(self, form, secondary_form=None, test_case_formset=None):
        """Reconstrói formulários secundários e formset antes de renderizar os erros."""
        if secondary_form is None:
            secondary_instance = self.get_secondary_instance()
            secondary_form = self.get_secondary_form(instance=secondary_instance)
        if test_case_formset is None:
            test_case_formset = self.get_test_case_formset()
        context = self.get_context_data(
            form=form,
            secondary_form=secondary_form,
            test_case_formset=test_case_formset,
        )
        return self.render_to_response(context)


class CodeExerciseCreateView(CodeExerciseBaseView, CreateView):
    test_case_formset_class = CodeTestCaseFormCreateSet


class CodeExerciseUpdateView(CodeExerciseBaseView, UpdateView):
    test_case_formset_class = CodeTestCaseFormUpdateSet


class CompleteCodeExerciseBaseView(ExerciseBaseMixin, SecondaryFormMixin):
    secondary_form_class = CompleteCodeExerciseForm
    secondary_form_model = CompleteCodeExercise
    secondary_form_related_name = 'complete_code_exercise'
    template_name = "activity/types/code/_form.html"
    update_url = 'activity:complete_code_exercise_update'
    type_exercise = 'complete_code'


class CompleteCodeExerciseCreateView(CompleteCodeExerciseBaseView, CreateView):
    pass    


class CompleteCodeExerciseUpdateView(CompleteCodeExerciseBaseView, UpdateView):
    pass


class DiscursiveExerciseBaseView(ExerciseBaseMixin, SecondaryFormMixin):
    secondary_form_class = DiscursiveExerciseForm
    secondary_form_model = DiscursiveExercise
    secondary_form_related_name = 'discursive_exercise'
    template_name = "activity/types/code/_form.html"
    update_url = 'activity:discursive_exercise_update'
    type_exercise = 'discursive'


class DiscursiveExerciseCreateView(DiscursiveExerciseBaseView, CreateView):
    pass


class DiscursiveExerciseUpdateView(DiscursiveExerciseBaseView, UpdateView):
    pass







############ Não Implementado ############
class ActivityDetailBaseView:
    """Classe base para as views de detalhe e vinculação de atividades.

    Compartilha a lógica de carregamento otimizado via ``select_related``
    e ``prefetch_related``, contagem de exercícios por tipo, cálculo de
    pontuação total e configuração das abas de navegação entre
    :class:`ActivityDetailView` e :class:`ActivityAssignView`.
    """
    model = ActivityList
    template_name = 'activity/detail.html'
    context_object_name = 'activity'
    allowed_fields = None
    
    def get_queryset(self) -> QuerySet[ActivityList]:
        """Retorna atividades não deletadas com select_related, prefetch e anotação de total de exercícios."""
        return super().get_queryset().filter(
            deleted_at__isnull=True
        ).select_related(
            'created_by'
        ).prefetch_related(
            Prefetch(
                'exercises',
                Exercise.objects.select_related(
                    'code_exercise',
                    'complete_code_exercise',
                    'discursive_exercise',
                    'multiple_choice_exercise'
                ).prefetch_related(
                    'multiple_choice_exercise__options'
                ).order_by('order')
            ),
            'list_groups__group'
        ).annotate(
            total_exercises=Count('exercises')
        )

    def get_context_data(self, **kwargs) -> dict:
        """Monta contexto com contagens por tipo de exercício, pontuação total e abas de navegação.

        Itera sobre os exercícios prefetchados para calcular ``count`` e ``points``
        por tipo, e determina ``can_edit`` com base na propriedade do criador ou no
        compartilhamento de turma.
        """
        context = super().get_context_data(**kwargs)
        activity = self.object

        # Contar exercícios por tipo
        exercises_by_type = self.init_exercise_info()
        total_points = Decimal('0')

        for exercise in activity.exercises.all():
            total_points += exercise.points
            if hasattr(exercise, 'discursive_exercise'):
                exercises_by_type['discursive']['count'] += 1
                exercises_by_type['discursive']['points'] += exercise.points
            elif hasattr(exercise, 'code_exercise'):
                exercises_by_type['code']['count'] += 1
                exercises_by_type['code']['points'] += exercise.points
            elif hasattr(exercise, 'complete_code_exercise'):
                exercises_by_type['complete_code']['count'] += 1
                exercises_by_type['complete_code']['points'] += exercise.points
            elif hasattr(exercise, 'multiple_choice_exercise'):
                exercises_by_type['multiple_choice']['count'] += 1
                exercises_by_type['multiple_choice']['points'] += exercise.points
                
        can_edit = (
            activity.created_by == self.request.user
            or activity.list_groups.filter(
                group__sharings__shared_with=self.request.user,
                group__sharings__is_active=True,
                group__deleted_at__isnull=True,
            ).exists()
        )
        context.update({
            'table': {
                'fields': self.allowed_fields,
            },
            'page_title': activity.title.title(),
            'page_description': f'Criado por {activity.created_by.get_full_name()}',
            'count_exercises_by_type': exercises_by_type,
            'count_all_exercises': activity.exercises.count(),
            'total_points': total_points,
            'nav_tabs': self.set_nav_tabs(),
            'count_groups': activity.list_groups.all().count(),
            'edit_url': reverse('activity:update', kwargs={'pk': activity.pk}) if can_edit else None,
            'preview_url': reverse('activity:preview', kwargs={'pk': activity.pk}),
        })
        
        return context
 
    def has_object_access(self, user: User, obj: ActivityList) -> bool:
        """Retorna ``True`` para o criador ou professores com turma compartilhada que contém a atividade."""
        if obj.created_by == user:
            return True
        return obj.list_groups.filter(
            group__sharings__shared_with=user,
            group__sharings__is_active=True,
            group__deleted_at__isnull=True,
        ).exists()

    def set_nav_tabs(self) -> list:
        """Retorna as abas de navegação entre Estatística, Revisão e Vincular a Turmas."""
        return [
            {
                'title': 'Estatística',
                'url': 'activity:stats',
                'pk': self.object.pk,
                'icon': 'bi-bar-chart',
                'active': self.__class__.__name__ == 'ActivityDetailView'
            }, {
                'title': 'Revisão',
                'url': 'activity:detail',
                'pk': self.object.pk,
                'icon': 'bi-pencil-square',
                'active': self.__class__.__name__ == 'ActivityReviewView'
            }, {
                'title': 'Vincular a Turmas',
                'url': 'activity:assign',
                'pk': self.object.pk,
                'icon': 'bi-share',
                'active': self.__class__.__name__ == 'ActivityAssignView'
            },
        ]

    def init_exercise_info(self) -> dict:
        """Retorna o dicionário inicial de contadores (``count`` e ``points``) por tipo de exercício."""
        return {
            'discursive': {
                'label': EXERCISE_TYPES['discursive']['label'],
                'count': 0,
                'points': Decimal('0'),
            },
            'code': {
                'label': EXERCISE_TYPES['code']['label'],
                'count': 0,
                'points': Decimal('0'),
            },
            'complete_code': {
                'label': EXERCISE_TYPES['complete_code']['label'],
                'count': 0,
                'points': Decimal('0'),
            },
            'multiple_choice': {
                'label': EXERCISE_TYPES['multiple_choice']['label'],
                'count': 0,
                'points': Decimal('0'),
            }
        }


class ActivityDetailView(ActivityDetailBaseView, AuthPermissionMixin, ObjectAccessRequiredMixin, DetailView):
    pass


class ActivityReviewView(ActivityDetailBaseView, AuthPermissionMixin, ObjectAccessRequiredMixin, DetailView):
    """Aba de revisão de submissões por turma dentro de uma atividade — restrita ao criador e compartilhados."""

    template_name = 'activity/review_tab.html'

    def get_context_data(self, **kwargs: Any) -> dict:
        """Adiciona ``review_links`` com contagens de submissões e pendências por turma."""
        context = super().get_context_data(**kwargs)
        links = (
            ActivityListGroup.objects
            .filter(
                activity_list=self.object,
                group__deleted_at__isnull=True,
            )
            .select_related('group')
            .annotate(
                submission_count=Count(
                    'submissions',
                    filter=Q(submissions__submitted_at__isnull=False),
                    distinct=True,
                ),
                pending_count=Count(
                    'submissions__answers',
                    filter=Q(
                        submissions__submitted_at__isnull=False,
                        submissions__answers__is_correct__isnull=True,
                    ),
                    distinct=True,
                ),
            )
            .order_by('group__name')
        )
        context['review_links'] = links
        return context


class ActivityPreviewView(AuthPermissionMixin, ObjectAccessRequiredMixin, DetailView):
    """Preview de uma atividade para o professor — visão similar à review do aluno."""
    model = ActivityList
    template_name = 'activity/preview.html'

    def get_queryset(self) -> QuerySet[ActivityList]:
        """Retorna atividades não deletadas com prefetch completo de exercícios e opções."""
        return (
            ActivityList.objects
            .filter(deleted_at__isnull=True)
            .prefetch_related(
                Prefetch(
                    'exercises',
                    Exercise.objects.filter(is_annulled=False).select_related(
                        'code_exercise',
                        'complete_code_exercise',
                        'discursive_exercise',
                        'multiple_choice_exercise',
                    ).prefetch_related(
                        'multiple_choice_exercise__options',
                        'code_exercise__test_cases',
                    ).order_by('order')
                )
            )
        )

    def has_object_access(self, user: User, obj: ActivityList) -> bool:
        """Retorna ``True`` para o criador ou professores com turma compartilhada que contém a atividade."""
        if obj.created_by == user:
            return True
        return obj.list_groups.filter(
            group__sharings__shared_with=user,
            group__sharings__is_active=True,
            group__deleted_at__isnull=True,
        ).exists()

    def get_context_data(self, **kwargs) -> dict:
        """Adiciona lista de exercícios com ``update_url`` anotado e metadados de preview."""
        context = super().get_context_data(**kwargs)
        exercises = list(self.object.exercises.all())
        for exercise in exercises:
            exercise.update_url = EXERCISE_TYPES[exercise.type]['update_url']
        context.update({
            'exercises': exercises,
            'total_exercises': len(exercises),
            'page_title': self.object.title,
            'has_exercises': len(exercises) > 0,
            'object': self.object,
            'is_preview': True,
        })
        return context


class ActivityAssignView(
    ActivityDetailBaseView,
    AuthPermissionMixin,
    ObjectAccessRequiredMixin,
    FilteringMixin,
    OrderingMixin,
    PaginationMixin,
    EnrichObjectMixin,
    FormMixin,
    DetailView
):
    template_name = 'activity/shared_list_view.html'
    model = ActivityList
    form_class = ActivityAssignForm
    allowed_fields = {
        "group": "group__name__icontains",
        "assigned_at": "assigned_at__icontains",
        "starts_at": "starts_at__icontains",
        "ends_at": "ends_at__icontains",
    }

    def get_sharings_queryset(self) -> QuerySet[ActivityListGroup]:
        """Retorna vínculos da atividade com turmas, com filtro e ordenação aplicados."""
        qs = (
            ActivityListGroup.objects
            .filter(activity_list=self.object)
            .select_related('group', 'activity_list')
        )

        # aplicar filtro
        qs = self.apply_filtering(
            queryset=qs,
        )

        # aplicar ordenação
        qs = self.apply_ordering(queryset=qs)

        return qs

    def has_object_enrich_actions(self, user: User, obj: ActivityListGroup) -> bool:
        """Retorna ``True`` se o usuário for o criador da atividade vinculada."""
        return obj.activity_list.created_by == user

    def enrich_actions(self, user: User, obj: ActivityListGroup) -> list:
        """Retorna ``assign_update`` e ``unshare`` para o criador da atividade."""
        if self.has_object_enrich_actions(user, obj):
            return get_btn_action(
                ['assign_update', 'unshare'],
                self.request.resolver_match.app_name
            )

    def get_context_data(self, **kwargs) -> dict:
        """Monta contexto da lista de vínculos com paginação, enriquecimento e dados do modal de vinculação."""
        context = super().get_context_data(**kwargs)

        sharings_qs = self.get_sharings_queryset()

        pagination = self.paginate_queryset(sharings_qs)

        enrichment = self.apply_enrichment(pagination)

        context.update({
            **enrichment,
            'modal_form': True,
            'modal_id': "shareModal",
            'modal_title': "Vincular Turmas",
            'modal_icon': "bi-share",
            'modal_form_id': "sharingForm",
            'modal_subtitle': "Adicione as turmas",
            'modal_button_submit': "Vincular",
        })

        return context

    def get_form_kwargs(self):
        """Injeta ``request_user`` nos kwargs do formulário para filtrar turmas disponíveis."""
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        return kwargs

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Valida a presença de turmas selecionadas antes de processar o formulário."""
        # Garantir que self.object esteja definido para o form_valid
        self.object = self.get_object()

        form = self.get_form()
        if 'groups' not in form.data and 'bind_all_groups' not in form.data:
            messages.error(request, 'Nenhum grupo selecionado para compartilhamento.')
            return self.get(request, *args, **kwargs)

        if form.is_valid():
            return self.form_valid(form)

        return self.get(request, *args, **kwargs)

    @transaction.atomic
    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        """Cria vínculos atividade↔turma em lote, atualizando períodos em caso de conflito."""
        bind_all_groups = form.cleaned_data.get('bind_all_groups')
        groups = (
            form.get_available_groups(self.request.user)
            if bind_all_groups
            else form.cleaned_data['groups']
        )
        starts_at = form.cleaned_data.get('starts_at')
        ends_at = form.cleaned_data.get('ends_at')
        activity_list = self.object

        if not groups.exists():
            messages.error(self.request, 'Nenhuma turma disponivel para vincular.')
            return self.get(self.request, *self.args, **self.kwargs)

        # Criamos uma lista de objetos ActivityListGroup na memória
        new_sharings = [
            ActivityListGroup(
                activity_list=activity_list,
                group=group,
                starts_at=starts_at,
                ends_at=ends_at,
                due_date=ends_at,
            )
            for group in groups
        ]
    
        # Insere todos de uma vez
        ActivityListGroup.objects.bulk_create(
            new_sharings,
            unique_fields=['activity_list', 'group'],
            update_conflicts=True,
            update_fields=['assigned_at', 'starts_at', 'ends_at', 'due_date']
        )

        return super().form_valid(form)

    def get_success_url(self):
        """Redireciona para a aba de vinculação da atividade após o POST."""
        return reverse('activity:assign', kwargs={'pk': self.object.pk})


class ActivityAssignUpdateView(AuthPermissionMixin, ObjectAccessRequiredMixin, UpdateView):
    """Edição do período (início e fim) de um vínculo atividade↔turma — restrita ao criador da atividade."""

    model = ActivityListGroup
    form_class = ActivityListGroupPeriodForm
    template_name = 'global/partials/generic/create_or_update/view.html'
    context_object_name = 'activity_group'
    page_title = 'Editar Periodo da Atividade'
    page_description = 'Ajuste o periodo em que esta atividade ficara disponivel para a turma.'
    form_title = 'Periodo da Atividade'
    form_subtitle = 'Defina quando os alunos poderao iniciar e finalizar esta atividade.'
    submit_title = 'Salvar'
    form_submit_confirm_text = None
    tip_card_content = [
        {
            'title': 'Inicio',
            'text': 'Use o inicio para liberar a atividade apenas no momento correto.',
            'icon': 'bi-calendar-event',
        },
        {
            'title': 'Fim',
            'text': 'Use o fim para encerrar o periodo de respostas dos alunos.',
            'icon': 'bi-clock-fill',
        },
    ]

    def get_queryset(self) -> QuerySet[ActivityListGroup]:
        """Retorna vínculos ativos da atividade cujo criador é o usuário autenticado."""
        return (
            ActivityListGroup.objects
            .select_related('activity_list', 'group')
            .filter(
                activity_list__created_by=self.request.user,
                activity_list__deleted_at__isnull=True,
                group__deleted_at__isnull=True,
            )
        )

    def has_object_access(self, user: User, obj: ActivityListGroup | None) -> bool:
        """Retorna ``True`` se o usuário for o criador da atividade vinculada."""
        return obj and obj.activity_list.created_by == user

    def get_context_data(self, **kwargs) -> dict:
        """Adiciona títulos, descrição, dicas e configurações do formulário de período ao contexto."""
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': self.page_title,
            'page_description': self.page_description,
            'form_title': self.form_title,
            'form_subtitle': self.form_subtitle,
            'submit_title': self.submit_title,
            'form_submit_confirm_text': self.form_submit_confirm_text,
            'tip_card_content': self.tip_card_content,
        })
        return context

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        """Salva o período e sincroniza ``due_date`` com ``ends_at`` antes de persistir."""
        self.object = form.save(commit=False)
        self.object.due_date = self.object.ends_at
        self.object.save(update_fields=['starts_at', 'ends_at', 'due_date'])

        messages.success(
            self.request,
            f'Periodo da atividade para a turma "{self.object.group.name}" atualizado com sucesso!'
        )

        return redirect(self.get_success_url())

    def get_success_url(self):
        """Redireciona para a aba de vinculação da atividade após salvar o período."""
        return reverse('activity:assign', kwargs={'pk': self.object.activity_list.pk})


class ActivityArchiveView(AuthPermissionMixin, ObjectAccessRequiredMixin, View):
    """Alterna o estado de arquivamento de uma atividade (arquivar / desarquivar) via POST."""

    def get_object(self) -> ActivityList | None:
        """Retorna a atividade não deletada do usuário ou ``None`` se não encontrada."""
        return ActivityList.objects.filter(
            pk=self.kwargs['pk'],
            created_by=self.request.user,
            deleted_at__isnull=True
        ).first()

    def has_object_access(self, user: User, obj: ActivityList | None) -> bool:
        """Retorna ``True`` se o objeto existir e o usuário for o criador."""
        return obj and obj.created_by == user

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Arquiva ou desarquiva a atividade, bloqueando se houver turma com período em aberto."""
        activity = self.get_object()

        existing = ActivityArchived.objects.filter(
            activity_list=activity,
            user=request.user,
        ).first()

        will_archive = not (existing and existing.is_archived)

        if will_archive:
            now = timezone.now()
            if activity.list_groups.filter(
                Q(ends_at__isnull=True) | Q(ends_at__gte=now)
            ).exists():
                messages.error(
                    request,
                    'Não é possível arquivar esta atividade: ela está vinculada a uma turma com período em aberto.'
                )
                return redirect('activity:list')

        if existing:
            existing.is_archived = not existing.is_archived
            existing.save(update_fields=['is_archived', 'updated_at'])
            archived = existing
        else:
            archived = ActivityArchived.objects.create(
                activity_list=activity,
                user=request.user,
                is_archived=True,
            )

        messages.success(
            request,
            f'Atividade {"arquivada" if archived.is_archived else "desarquivada"} com sucesso!'
        )

        return redirect('activity:list')


class ActivityDeleteView(AuthPermissionMixin, ObjectAccessRequiredMixin, DeleteView):
    """View de soft delete de atividade — bloqueia se houver turma com período em aberto."""

    model = ActivityList
    template_name = 'global/partials/generic/delete/view.html'
    context_object_name = 'delete'

    def get_queryset(self) -> QuerySet[ActivityList]:
        """Retorna atividades não deletadas do usuário autenticado."""
        return ActivityList.objects.filter(
            created_by=self.request.user,
            deleted_at__isnull=True,
        )

    def has_object_access(self, user: User, obj: ActivityList) -> bool:
        """Retorna ``True`` se o usuário for o criador da atividade."""
        return obj.created_by == user

    def has_open_group_period(self, obj: ActivityList) -> bool:
        """Verifica se a atividade possui algum vínculo com período em aberto.

        Args:
            obj: Instância de :class:`~activity.models.ActivityList`.

        Returns:
            ``True`` se existir ao menos um vínculo sem data de fim ou com
            data de fim no futuro.
        """
        now = timezone.now()
        return obj.list_groups.filter(
            Q(ends_at__isnull=True) |
            Q(ends_at__gte=now)
        ).exists()

    def redirect_if_has_open_group_period(self, request: HttpRequest, obj: ActivityList) -> HttpResponse | None:
        """Redireciona para o detalhe da atividade se houver período em aberto.

        Args:
            request: Requisição HTTP atual.
            obj: Instância de :class:`~activity.models.ActivityList`.

        Returns:
            ``HttpResponseRedirect`` para o detalhe da atividade com mensagem
            de erro, ou ``None`` se não houver período em aberto.
        """
        if not self.has_open_group_period(obj):
            return None

        messages.error(
            request,
            'Não é possível deletar esta atividade: ela está vinculada a uma turma com período em aberto. Encerre o período antes.'
        )
        return redirect('activity:detail', pk=obj.pk)

    def get_context_data(self, **kwargs) -> dict:
        """Adiciona lista de avisos de impacto exibidos na tela de confirmação de exclusão."""
        context = super().get_context_data(**kwargs)
        self.object.name = self.object.title
        context.update({
            'checks': [
                'O registro da atividade sera removido da listagem ativa.',
                'Os exercicios permanecem preservados no banco, vinculados ao registro deletado.',
            ]
        })
        return context

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Redireciona para o detalhe se houver período em aberto; caso contrário renderiza confirmação."""
        obj = self.get_object()

        redirect_response = self.redirect_if_has_open_group_period(request, obj)
        if redirect_response:
            return redirect_response

        return super().get(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Aplica o soft delete definindo ``deleted_at`` se não houver período em aberto."""
        obj = self.get_object()

        redirect_response = self.redirect_if_has_open_group_period(request, obj)
        if redirect_response:
            return redirect_response

        obj.deleted_at = timezone.now()
        obj.save(update_fields=['deleted_at'])

        messages.success(
            request,
            f'Atividade "{obj.title}" deletada com sucesso!'
        )

        return redirect('activity:list')


class ActivityUnshareView(AuthPermissionMixin, ObjectAccessRequiredMixin, View):
    """Remove o vínculo entre uma atividade e uma turma, se não houver submissões."""

    def get_object(self) -> ActivityListGroup | None:
        """Retorna o vínculo atividade↔turma com cache em ``self.object``."""
        if hasattr(self, 'object'):
            return self.object

        self.object = (
            ActivityListGroup.objects
            .select_related('activity_list', 'group')
            .filter(pk=self.kwargs['pk'])
            .first()
        )
        return self.object

    def has_object_access(self, user: User, obj: ActivityListGroup | None) -> bool:
        """Retorna ``True`` se o usuário for o criador da atividade vinculada."""
        return obj and obj.activity_list.created_by == user

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Deleta o vínculo, bloqueando com mensagem de erro se existirem submissões."""
        obj = self.get_object()
        activity_list_pk = obj.activity_list.pk
        group_name = obj.group.name

        if Submission.objects.filter(activity_link=obj).exists():
            messages.error(
                request,
                f'Não é possível desvincular "{group_name}": um ou mais alunos já responderam esta atividade.'
            )
            return redirect('activity:assign', pk=activity_list_pk)

        obj.delete()

        messages.success(
            request,
            f'Vínculo com a turma "{group_name}" removido com sucesso!'
        )

        return redirect('activity:assign', pk=activity_list_pk)

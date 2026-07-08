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
from student.models import Submission
from common.view.generic import EnhancedListView
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Prefetch, Count, Exists, OuterRef, Q, QuerySet
from django.forms import BaseModelForm
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
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
        return ActivityArchived.objects.filter(
            activity_list=OuterRef('pk'),
            user=self.request.user,
            is_archived=True
        )

    def has_object_enrich_actions(self, user: User, obj: ActivityList) -> bool:
        return obj.created_by == user

    def enrich_actions(self, user: User, obj: ActivityList) -> list:
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
        """Retorna as atividades ativas do usuario"""
        qs_archived = self.get_archived_activity_ids()

        return super().get_queryset().filter(
            created_by=self.request.user,
            deleted_at__isnull=True
        ).exclude(
            Exists(qs_archived)
        )

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context.update({
            'nav_tabs': self.set_nav_tabs(),
            'table': {
                'fields': self.allowed_fields,
            },
        })
        return context

    def set_nav_tabs(self) -> list:
        """Configura as abas de navegação"""
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
    page_title = 'Atividades Arquivadas'
    create_url = None

    def get_queryset(self):
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

    def get_exercises(self) -> list:
        """Retorna os exercícios da atividade com related models carregados.

        Returns:
            QuerySet de :class:`~activity.models.Exercise` ordenado por ``order``,
            ou lista vazia se ``self.object`` ainda não existir (fluxo de criação).
        """
        if not getattr(self, 'object', None):
            return []

        exercises = (
            self.object.exercises
            .select_related(
                'code_exercise',
                'complete_code_exercise',
                'discursive_exercise',
                'multiple_choice_exercise'
            )
            .order_by('order')
        )

        for exercise in exercises:
            exercise.update_url = EXERCISE_TYPES[exercise.type]['update_url']

        return exercises

    def render_activity_builder(self) -> HttpResponse:
        """Renderiza o partial HTMX do seletor de tipos de exercício.

        Returns:
            HttpResponse com o template ``activity/_exercise_type_selector.html``.
        """
        return render(
            self.request,
            'activity/_exercise_type_selector.html',
            {
                'exercise_types': EXERCISE_TYPES,
                'object': self.object,
                'activity_list_id': self.object.id,
                'is_update_flow': self.is_update_flow,
                'has_exercises': self.object.exercises.exists(),
            }
        )

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context.update({
            'form_title': self.form_title,
            'form_subtitle': self.form_subtitle,
            'page_description': self.page_description,
            'page_title': self.page_title,
            'exercise_types': EXERCISE_TYPES,
            'activity_list_id': self.object.id if getattr(self, 'object', None) else None,
            'exercises': self.get_exercises(),
            'is_update_flow': self.is_update_flow,
            'has_exercises': self.object.exercises.exists() if getattr(self, 'object', None) else False,
        })
        return context
    
    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        # Salva automaticamente com CreateView
        self.object = form.save(commit=False)
        self.object.created_by = self.request.user
        self.object.is_published = False
        self.object.save()

        return self.render_activity_builder()

    def form_invalid(self, form: BaseModelForm) -> HttpResponse:
        return render(
            self.request,
            self.template_name,
            self.get_context_data(form=form),
            status=400
        )


class ActivityCreateView(AuthPermissionMixin, ActivityCreateOrUpdateView, CreateView):
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
    model = ActivityList
    form_class = ActivityListForm
    template_name = 'activity/create.html'
    is_update_flow = True
    form_title = 'Informações da Atividade'
    form_subtitle = 'Atualize os dados da atividade e gerencie seus exercícios.'
    page_title = 'Editar Atividade'
    page_description = 'Revise as informações da atividade e mantenha seus exercícios organizados.'

    def get_queryset(self) -> QuerySet[ActivityList]:
        return (
            ActivityList.objects
            .filter(deleted_at__isnull=True)
            .prefetch_related('exercises')
        )

    def has_object_access(self, user: User, obj: ActivityList) -> bool:
        if obj.created_by == user:
            return True
        return obj.list_groups.filter(
            group__sharings__shared_with=user,
            group__sharings__is_active=True,
            group__deleted_at__isnull=True,
        ).exists()

    def _has_submissions(self) -> bool:
        return Submission.objects.filter(
            activity_link__activity_list=self.get_object()
        ).exists()

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if self._has_submissions():
            messages.error(
                request,
                'Não é possível editar esta atividade: um ou mais alunos já a responderam.'
            )
            return redirect('activity:list')
        return super().get(request, *args, **kwargs)

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        if self._has_submissions():
            messages.error(
                self.request,
                'Não é possível editar esta atividade: um ou mais alunos já a responderam.'
            )
            return redirect('activity:list')
        self.object = form.save()
        return self.render_activity_builder()


##### INICIO VIEW DE CRIAÇÃO/ATUALIZAÇÃO DE EXERCÍCIO#####
class ExerciseCancelView(
    HTMXLoginRequiredMixin,
    ObjectAccessRequiredMixin,
    View
):
    
    def has_object_access(self, user: User, obj: ActivityList | None) -> bool:
        """
        Verifica se o usuário tem acesso ao objeto de lista de atividades (ActivityList) relacionado ao exercício.
        """
        return False if not obj else obj.created_by == user

    def get_object(self) -> ActivityList | None:
        """
        Obtem a instância de ActivityList com base no ID fornecido na URL, garantindo que o usuário tenha acesso a ela.
        Retorna None se a instância não for encontrada ou se o usuário não tiver acesso.
        """
        return ActivityList.objects.filter(
            id=self.kwargs.get('pk'),
            deleted_at__isnull=True
        ).first()

    def get(self, request: HttpRequest, pk: int, *args: Any, **kwargs: Any) -> HttpResponse:
        return render(
            request,
            'activity/_exercise_type_selector.html',
            {
                'exercise_types': EXERCISE_TYPES,
                'activity_list_id': pk,
            }
        )


##### INICIO VIEW DE DELETE DE EXERCÍCIO #####
class ExerciseDeleteView(AuthPermissionMixin, ObjectAccessRequiredMixin, DeleteView):
    """View para delete de exercício"""
    model = Exercise
    template_name = 'global/partials/generic/delete/htmx_view.html'
    context_object_name = 'exercise'

    def has_object_access(self, user: User, obj: Exercise) -> bool:
        """
        Verifica se o usuário tem permissão de acesso ao objeto.

        Na criação, verifica se o usuário é dono da ActivityList.
        Na atualização, verifica se o usuário é dono da ActivityList do Exercise.

        params:
            user: Usuário autenticado da requisição.
            obj: ActivityList (criação) ou Exercise (atualização).

        Returns:
            True se o usuário tem acesso, False caso contrário.
        """
        return obj.activity_list.created_by == user

    def get_activity_list_id(self) -> int:
        """
        Retorna o ID da ActivityList associada ao exercício.

        Na criação, obtém o ID diretamente dos kwargs da URL.
        Na atualização, obtém o ID a partir do objeto Exercise.

        Returns:
            ID da ActivityList.
        """
        return self.object.activity_list.id

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context.update({'activity_list': self.get_activity_list_id()})
        return context

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        # Salva o ID do exercício antes de deletar para usar na resposta HTMX
        is_deleted = self.object.pk
        self.object.delete()
        return render(
            self.request,
            'activity/_exercise_type_selector.html',
            {
                'is_deleted': is_deleted,
                'exercise_types': EXERCISE_TYPES,
                'activity_list_id': self.get_activity_list_id(),
            }
        )


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
        instance = self.get_secondary_instance()
        kwargs = {'prefix': 'test_cases', 'instance': instance}
        if self.request.POST:
            kwargs['data'] = self.request.POST
        return self.test_case_formset_class(**kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'test_case_formset' not in context:
            context['test_case_formset'] = self.get_test_case_formset()
        return context

    def form_valid(self, form):
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
        """Otimiza queries com select_related e prefetch_related"""
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
        })
        
        return context
 
    def has_object_access(self, user: User, obj: ActivityList) -> bool:
        if obj.created_by == user:
            return True
        return obj.list_groups.filter(
            group__sharings__shared_with=user,
            group__sharings__is_active=True,
            group__deleted_at__isnull=True,
        ).exists()

    def set_nav_tabs(self) -> list:
        """Configura as abas de navegação"""
        return [{
                'title': 'Resumo',
                'url': 'activity:detail',                
                'pk': self.object.pk,
                'icon': 'bi-info-circle',
                'active': self.__class__.__name__ == 'ActivityDetailView'
            }, {
                'title': 'Vincular a Turmas',
                'url': 'activity:assign',                
                'pk': self.object.pk,
                'icon': 'bi-share',
                'active': self.__class__.__name__ == 'ActivityAssignView'
            }
        ]

    def init_exercise_info(self) -> dict:
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


class ActivityPreviewView(AuthPermissionMixin, ObjectAccessRequiredMixin, DetailView):
    """Preview de uma atividade para o professor — visão similar à review do aluno."""
    model = ActivityList
    template_name = 'activity/preview.html'

    def get_queryset(self) -> QuerySet[ActivityList]:
        return (
            ActivityList.objects
            .filter(deleted_at__isnull=True)
            .prefetch_related(
                Prefetch(
                    'exercises',
                    Exercise.objects.select_related(
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
        if obj.created_by == user:
            return True
        return obj.list_groups.filter(
            group__sharings__shared_with=user,
            group__sharings__is_active=True,
            group__deleted_at__isnull=True,
        ).exists()

    def get_context_data(self, **kwargs) -> dict:
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
        return obj.activity_list.created_by == user

    def enrich_actions(self, user: User, obj: ActivityListGroup) -> list:
        if self.has_object_enrich_actions(user, obj):
            return get_btn_action(
                ['assign_update', 'unshare'],
                self.request.resolver_match.app_name
            )

    def get_context_data(self, **kwargs) -> dict:
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
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        return kwargs

    
    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
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
        return reverse('activity:assign', kwargs={'pk': self.object.pk})


class ActivityAssignUpdateView(AuthPermissionMixin, ObjectAccessRequiredMixin, UpdateView):
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
        return obj and obj.activity_list.created_by == user

    def get_context_data(self, **kwargs) -> dict:
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
        self.object = form.save(commit=False)
        self.object.due_date = self.object.ends_at
        self.object.save(update_fields=['starts_at', 'ends_at', 'due_date'])

        messages.success(
            self.request,
            f'Periodo da atividade para a turma "{self.object.group.name}" atualizado com sucesso!'
        )

        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('activity:assign', kwargs={'pk': self.object.activity_list.pk})


class ActivityArchiveView(AuthPermissionMixin, ObjectAccessRequiredMixin, View):
    def get_object(self) -> ActivityList | None:
        return ActivityList.objects.filter(
            pk=self.kwargs['pk'],
            created_by=self.request.user,
            deleted_at__isnull=True
        ).first()

    def has_object_access(self, user: User, obj: ActivityList | None) -> bool:
        return obj and obj.created_by == user

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
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
    model = ActivityList
    template_name = 'global/partials/generic/delete/view.html'
    context_object_name = 'delete'

    def get_queryset(self) -> QuerySet[ActivityList]:
        return ActivityList.objects.filter(
            created_by=self.request.user,
            deleted_at__isnull=True,
        )

    def has_object_access(self, user: User, obj: ActivityList) -> bool:
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
        obj = self.get_object()

        redirect_response = self.redirect_if_has_open_group_period(request, obj)
        if redirect_response:
            return redirect_response

        return super().get(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
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
    def get_object(self) -> ActivityListGroup | None:
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
        return obj and obj.activity_list.created_by == user

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
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

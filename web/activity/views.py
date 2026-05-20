from activity.constants import EXERCISE_TYPES
from activity.forms.activity import ActivityListForm
from activity.forms.exercise import CodeExerciseForm, CompleteCodeExerciseForm, DiscursiveExerciseForm, ExerciseOptionForm
from activity.forms.formsets.exercise_option import ExerciseOptionFormCreateSet, ExerciseOptionFormUpdateSet
from activity.mixins import ExerciseBaseMixin
from activity.models import ActivityList, CodeExercise, CompleteCodeExercise, DiscursiveExercise, Exercise, MultipleChoiceExercise
from common.mixins import (
    HTMXLoginRequiredMixin,
    InlineFormsetMixin,
    SecondaryFormMixin,
    AuthPermissionMixin,
    ObjectAccessRequiredMixin,
    InlineFormsetMixin
)
from common.utils import get_btn_action
from common.view.generic import EnhancedListView
from django.contrib.auth.models import User
from django.db.models import Prefetch, Count
from django.shortcuts import render
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView, View




class ActivityBaseView(EnhancedListView):
    allowed_fields = ['title', 'description', 'created_at']
    detail_url = 'activity:detail'
    model = ActivityList
    page_description = 'Organize, acompanhe e compartilhe suas atividades com facilidade.'


    def has_object_enrich_actions(self, user, obj):
        return obj.created_by == user
    
    def enrich_actions(self, user, obj):
        if self.has_object_enrich_actions(user, obj):
            return get_btn_action(
                ['update', 'archive', 'delete'],
                self.request.resolver_match.app_name
            )
        else:
            return get_btn_action(
                ['archive'],
                self.request.resolver_match.app_name
            )

    def get_queryset(self):
        """Retorna os grupos ativos do usuário"""
        return super().get_queryset().filter(
            created_by=self.request.user,
            deleted_at__isnull=True
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'nav_tabs': self.set_nav_tabs(),
            'table': {
                'fields': self.allowed_fields,
            },
        })
        return context

    def set_nav_tabs(self):
        """Configura as abas de navegação"""
        return [
            {
                'title': 'Ativas',
                'url': 'activity:list',
                'icon': 'bi-check-circle',
                'list': self.__class__.__name__ == 'ActivityListListView'
            }
        ]


class ActivityListView(AuthPermissionMixin, ActivityBaseView):
    page_title = 'Atividades Ativas'    
    create_url = 'activity:create'


##### INICIO VIEW DE CRIAÇÃO/ATUALIZAÇÃO DE ATIVIDADE #####
class ActivityCreateOrUpdateView(CreateView):
    template_name = 'activity/create.html'
    form_class = ActivityListForm
    form_title = None
    form_subtitle = None
    page_title = None
    page_description = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'form_title': self.form_title,
            'form_subtitle': self.form_subtitle,
            'page_description': self.page_description,
            'page_title': self.page_title,
        })
        return context
    
    def form_valid(self, form):
        # Salva automaticamente com CreateView
        self.object = form.save(commit=False)
        self.object.created_by = self.request.user
        self.object.is_published = False
        self.object.save()

        # Retorna partial HTML para HTMX (sem redirect)
        return render(
            self.request,
            'activity/_exercise_type_selector.html',
            {
                'exercise_types': EXERCISE_TYPES,
                'object': self.object,
                'activity_list_id': self.object.id,
            }
        )

    def form_invalid(self, form):
        return render(self.request, self.template_name, {'form': form}, status=400)


class ActivityCreateView(AuthPermissionMixin, ActivityCreateOrUpdateView):
    form_title = 'Informações da Atividade'
    form_subtitle = 'Preencha os dados para criar uma nova atividade'
    page_title = 'Criar Nova Atividade'
    page_description = '...'


##### INICIO VIEW DE CRIAÇÃO/ATUALIZAÇÃO DE EXERCÍCIO#####
class ExerciseCancelView(
    HTMXLoginRequiredMixin,
    ObjectAccessRequiredMixin,
    View
):
    
    def has_object_access(self, user, obj):
        """
        Verifica se o usuário tem acesso ao objeto de lista de atividades (ActivityList) relacionado ao exercício.
        """
        return False if not obj else obj.created_by == user

    def get_object(self):
        """
        Obtem a instância de ActivityList com base no ID fornecido na URL, garantindo que o usuário tenha acesso a ela.
        Retorna None se a instância não for encontrada ou se o usuário não tiver acesso.
        """
        return ActivityList.objects.filter(
            id=self.kwargs.get('pk'),
            deleted_at__isnull=True
        ).first()

    def get(self, request, pk, *args, **kwargs):
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'activity_list': self.get_activity_list_id()})
        return context

    def form_valid(self, form):
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

    def post(self, request, *args, **kwargs):
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


class CodeExerciseCreateView(CodeExerciseBaseView, CreateView):
    pass


class CodeExerciseUpdateView(CodeExerciseBaseView, UpdateView):
    pass


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
class ActivityBaseView:
    """
    View para exibir detalhes de uma atividade e seus exercícios.
    
    Mostra:
    - Informações da atividade (título, descrição)
    - Estatísticas (total de exercícios, status de publicação)
    - Lista de exercícios organizados por tipo
    - Ações disponíveis (editar, deletar, publicar) para o criador
    """
    model = ActivityList
    template_name = 'activity/detail.html'
    context_object_name = 'activity'
    
    def get_queryset(self):
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        activity = self.object

        # Contar exercícios por tipo
        exercises_by_type = self.init_exercise_info()

        for exercise in activity.exercises.all():
            if hasattr(exercise, 'discursive_exercise'):
                exercises_by_type['discursive']['count'] += 1
            elif hasattr(exercise, 'code_exercise'):
                exercises_by_type['code']['count'] += 1
            elif hasattr(exercise, 'complete_code_exercise'):
                exercises_by_type['complete_code']['count'] += 1
            elif hasattr(exercise, 'multiple_choice_exercise'):
                exercises_by_type['multiple_choice']['count'] += 1
                
        context.update({
            'page_title': activity.title.title(),
            'page_description': f'Criado por {activity.created_by.get_full_name()}',
            'count_exercises_by_type': exercises_by_type,
            'count_all_exercises': activity.exercises.count(),
            'nav_tabs': self.set_nav_tabs(),
            'count_groups': activity.list_groups.all().count(),
        })
        
        return context
 
    def has_object_access(self, user: User, obj: ActivityList) -> bool:
        """Permite acesso apenas para o criador da atividade"""
        return obj.created_by == user

    def set_nav_tabs(self):
        """Configura as abas de navegação"""
        return [{
                'title': 'Resumo',
                'url': 'activity:detail',                
                'pk': self.object.pk,
                'icon': 'bi-info-circle',
                'active': self.__class__.__name__ == 'ActivityDetailView'
            }, {
                'title': 'Compartilhamento',
                'url': 'activity:share',                
                'pk': self.object.pk,
                'icon': 'bi-share',
                'active': self.__class__.__name__ == 'ActivityShareView'
            }
        ]

    def init_exercise_info(self):
        return {
            'discursive': {
                'label': EXERCISE_TYPES['discursive']['label'],
                'count': 0
            },
            'code': {
                'label': EXERCISE_TYPES['code']['label'],
                'count': 0
            },
            'complete_code': {
                'label': EXERCISE_TYPES['complete_code']['label'],
                'count': 0
            },
            'multiple_choice': {
                'label': EXERCISE_TYPES['multiple_choice']['label'],
                'count': 0
            }
        }

class ActivityDetailView(ActivityBaseView, AuthPermissionMixin, ObjectAccessRequiredMixin, DetailView):
    pass



class ActivityUpdateView(View):
    pass

    def get(self, request, *args, **kwargs):
        raise NotImplementedError("Implementar lógica de exibição de detalhes da atividade")


class ActivityArchiveView(View):
    pass

    def get(self, request, *args, **kwargs):
        raise NotImplementedError("Implementar lógica de exibição de detalhes da atividade")


class ActivityDeleteView(View):
    pass

    def get(self, request, *args, **kwargs):
        raise NotImplementedError("Implementar lógica de exibição de detalhes da atividade")


class ActivityShareView(View):
    pass

    def get(self, request, *args, **kwargs):
        raise NotImplementedError("Implementar lógica de exibição de detalhes da atividade")
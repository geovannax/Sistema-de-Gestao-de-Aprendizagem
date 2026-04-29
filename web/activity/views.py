from activity.constants import EXERCISE_TYPES
from common.mixins import ActionsMixin, AuthPermissionMixin, NavigationMixin, ObjectAccessRequiredMixin, InlineFormsetMixin
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import CreateView, ListView, View, UpdateView
from activity.forms.activity import ActivityListForm
from activity.forms.exercise import ExerciseForm
from activity.models import ActivityList, ExerciseOption, MultipleChoiceExercise
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from activity.forms.formsets.exercise_option import ExerciseOptionFormCreateSet, ExerciseOptionFormUpdateSet
from django.views.generic import CreateView
from django.db import transaction
from django.shortcuts import render
from activity.models import Exercise
from activity.forms.exercise import ExerciseOptionForm

from common.view.generic import EnhancedListView
from common.utils import get_btn_action

import logging
logger = logging.getLogger(__name__)
logger.warning('validar input requered no submit quando check e delete estiverem juntos')

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
class GroupCreateOrUpdateView(CreateView):
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
            'activity/_after_create.html',
            {
                'exercise_types': EXERCISE_TYPES,
                'object': self.object,
                'activity_list_id': self.object.id,
            }
        )

    def form_invalid(self, form):
        return render(self.request, self.template_name, {'form': form}, status=400)


class ActivityCreateView(AuthPermissionMixin, GroupCreateOrUpdateView):
    form_title = 'Informações da Atividade'
    form_subtitle = 'Preencha os dados para criar uma nova atividade'
    page_title = 'Criar Nova Atividade'
    page_description = '...'


class MultipleChoiceExerciseCreateView(
    AuthPermissionMixin,
    ObjectAccessRequiredMixin,
    InlineFormsetMixin,
    CreateView
):
    model = Exercise
    form_class = ExerciseForm
    formset_class = ExerciseOptionFormCreateSet
    template_name = "activity/types/multiple_choice/_form.html"

    def has_object_access(self, user, obj):
        return False if not obj else obj.created_by == user

    def get_object(self):
        return ActivityList.objects.filter(
            id=self.kwargs.get('pk'),
            created_by=self.request.user,
            deleted_at__isnull=True
        ).first()

    def get_initial(self):
        return {
            'activity_list': self.kwargs.get('pk'),
            'type': 'multiple_choice'
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['activity_list'] = self.kwargs.get("pk")
        return context

    def get_formset_parent_instance(self):
        # cria a instância de MultipleChoiceExercise
        return MultipleChoiceExercise(exercise=self.object)

    def save_parent_instance(self, instance):
        # salva a instância de MultipleChoiceExercise para garantir
        # que o formset tenha uma referência válida
        instance.save()

    def render_success(self):
        if self.request.headers.get('HX-Request'):
            return render(
                self.request,
                'activity/_after_create.html',
                {
                    'exercise': self.object,
                    'exercise_types': EXERCISE_TYPES,
                    'activity_list_id': self.kwargs.get("pk"),
                }
            )


class MultipleChoiceExerciseAddOptionView(AuthPermissionMixin, View):
    template_name = "activity/types/multiple_choice/_options.html"

    def post(self, request, *args, **kwargs):
        total_forms = int(request.POST.get('total_forms', 0))
        
        # Criar formulário com o prefix correto
        form_prefix = f'options-{total_forms}'
        option_form = ExerciseOptionForm(prefix=form_prefix)
        
        return render(request, self.template_name, {'option_form': option_form})
    

class MultipleChoiceExerciseUpdateView(
    AuthPermissionMixin,
    ObjectAccessRequiredMixin,
    InlineFormsetMixin,
    UpdateView
):
    model = Exercise
    form_class = ExerciseForm
    formset_class = ExerciseOptionFormUpdateSet
    template_name = "activity/types/multiple_choice/_form.html"
    pk_url_kwarg = 'pk'  # O pk vem da URL

    def has_object_access(self, user, obj):
        return obj.activity_list.created_by == user

    def get_object(self):
        # Recupera o Exercise por ID
        return Exercise.objects.filter(
            id=self.kwargs.get('pk'),
            activity_list__created_by=self.request.user,
            activity_list__deleted_at__isnull=True
        ).first()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['activity_list'] = self.object.activity_list.id
        return context

    def get_formset_parent_instance(self):
        # Recupera a instância MultipleChoiceExercise existente
        try:
            return self.object.multiple_choice_exercise
        except MultipleChoiceExercise.DoesNotExist:
            # Se não existir, cria uma nova
            return MultipleChoiceExercise(exercise=self.object)
    
    def save_parent_instance(self, instance):
        # Apenas salva se houver mudanças
        instance.save()

    def render_success(self):
        if self.request.headers.get('HX-Request'):
            return render(
                self.request,
                'activity/_after_create.html',
                {
                    'is_update': True,
                    'exercise': self.object,
                    'exercise_types': EXERCISE_TYPES,
                    'activity_list_id': self.object.activity_list.id,
                }
            )
        return redirect('activity:detail', pk=self.object.activity_list.id)


############ Não Implementado ############
class ActivityDetailView(View):
    pass

    def get(self, request, *args, **kwargs):
        raise NotImplementedError("Implementar lógica de exibição de detalhes da atividade")


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



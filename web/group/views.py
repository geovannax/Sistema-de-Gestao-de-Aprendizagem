from common.mixins import (
    AuthPermissionMixin,
    EnrichObjectMixin,
    FilteringMixin,
    NavigationMixin,
    OrderingMixin,
    ObjectAccessRequiredMixin,
    PaginationMixin,    
)
from common.utils import get_btn_action
from common.view.generic import EnhancedListView
from activity.models import ActivityListGroup
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.db.utils import IntegrityError
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView, View
from django.views.generic.edit import FormMixin
from group.forms.group import GroupForm, GroupSharingForm
from group.models import Group, GroupArchived, GroupSharing


##### INICIO VIEW NAVTABS DA ABA TURMAS #####
class GroupListBaseView(EnhancedListView):
    """Classe base para listagens de grupos"""
    allowed_fields = ['name', 'description', 'shift', 'created_at']
    detail_url = 'group:detail'
    model = Group
    page_description = 'Organize, acompanhe e compartilhe suas turmas com facilidade.'

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

    def get_archived_group_ids(self):
        """Retorna IDs de grupos arquivados do usuário - uma única query"""
        return GroupArchived.objects.filter(
            group=OuterRef('pk'),
            user=self.request.user,
            is_archived=True
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
                'url': 'group:active',
                'icon': 'bi-check-circle',
                'active': self.__class__.__name__ == 'GroupActiveListView'
            },{
                'title': 'Compartilhadas',
                'url': 'group:shared',
                'icon': 'bi-share',
                'active': self.__class__.__name__ == 'GroupSharedListView'
            },{
                'title': 'Arquivadas',
                'url': 'group:archived',
                'icon': 'bi-inbox',
                'active': self.__class__.__name__ == 'GroupArchivedListView'
            }
        ]


class GroupActiveListView(AuthPermissionMixin, GroupListBaseView):
    page_title = 'Turmas Ativas'
    create_url = 'group:create'

    def get_queryset(self):
        """Retorna os grupos ativos do usuário"""
        qs_archived = self.get_archived_group_ids()

        return super().get_queryset().filter(
            created_by=self.request.user,
            deleted_at__isnull=True
        ).exclude(
            Exists(qs_archived)
        )


class GroupArchivedListView(AuthPermissionMixin, GroupListBaseView):
    page_title = 'Turmas Arquivadas'

    def get_queryset(self):
        """Retorna os grupos arquivados do usuário"""
        return super().get_queryset().filter(
            archived_groups__user=self.request.user,
            archived_groups__is_archived=True,
            deleted_at__isnull=True
        )


class GroupSharedListView(AuthPermissionMixin, GroupListBaseView):
    page_title = 'Turmas Compartilhadas'

    def get_queryset(self):
        """Retorna os grupos compartilhados com o usuário.
        """
        qs_archived = self.get_archived_group_ids()

        return super().get_queryset().filter(
            sharings__shared_with=self.request.user,
            sharings__is_active=True,
            deleted_at__isnull=True
        ).exclude(
            Exists(qs_archived)
        )


##### INICIO VIEW DE CRIAÇÃO/ATUALIZAÇÃO DE TURMA #####
class GroupCreateOrUpdateView(SuccessMessageMixin):
    model = Group
    form_class = GroupForm
    template_name = 'global/partials/generic/create_or_update/view.html'
    success_url = '/group/active'
    success_message = None
    form_title = 'Informações da Turma'
    form_subtitle = None
    form_submit_confirm_text = 'Confirmo que estou ciente de que todas as informações desta turma serão visíveis para os alunos vinculados.'
    page_description = None
    page_title = None
    submit_title = None
    tip_card_content = [
        {
            'title': 'Nome Descritivo',
            'text': 'Use nomes padronizados como “CC 2026.3.12” para facilitar buscas futuras.',
            'icon': 'bi-lightbulb-fill',
        },
        {
            'title': 'Turno',
            'text': 'Escolha o turno que melhor representa o horário real da turma.',
            'icon': 'bi-clock-fill',
        },
        {
            'title': 'Descrição Clara',
            'text': 'Uma boa descrição ajuda alunos a entender objetivos da turma.',
            'icon': 'bi-file-earmark-text-fill',
        }
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'form_title': self.form_title,
            'form_subtitle': self.form_subtitle,
            'form_submit_confirm_text': self.form_submit_confirm_text,
            'page_description': self.page_description,
            'page_title': self.page_title,
            'submit_title': self.submit_title,
            'tip_card_content': self.tip_card_content
        })
        return context

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except IntegrityError as e:
            form.add_error(
                'name', 
                'Você já tem uma turma com este nome. Por favor, escolha outro nome.'
            )
            return self.form_invalid(form)


class GroupCreateView(
    AuthPermissionMixin,
    GroupCreateOrUpdateView,
    CreateView
):
    form_subtitle = 'Complete o formulário para ativar sua turma e começar a organizar suas atividades.'
    page_description = 'Crie uma nova turma para organizar as suas atividades e acompanhar o progresso dos alunos.'
    page_title = 'Criar Turma'
    submit_title = 'Cadastrar'
    success_message = 'Turma criada com sucesso!'
    
    def form_valid(self, form):
        # Atribuir o usuário logado como criador da turma
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class GroupUpdateView(
    AuthPermissionMixin,
    GroupCreateOrUpdateView,
    ObjectAccessRequiredMixin,
    UpdateView
):
    form_subtitle = 'Revise e atualize os dados da sua turma para garantir que tudo esteja sempre correto.'
    page_description = 'Gerencie e edite as informações da turma, mantendo alunos e atividades sempre organizados e atualizados.'
    page_title = 'Atualizar Turma'
    submit_title = 'Atualizar'
    success_message = 'Turma atualizada com sucesso!'

    def has_object_access(self, user, obj):
        return obj.created_by == user
    

##### INICIO VIEW DE DETALHAMENTO DE TURMA #####
class GroupBaseView:
    allowed_fields = None
    template_name = 'group/detail_list_view.html'

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'nav_tabs': self.set_nav_tabs(),
            'table': {
                'fields': self.allowed_fields,
            },
            'recent_activities': (
                ActivityListGroup.objects
                .filter(
                    group=self.object,
                    activity_list__deleted_at__isnull=True
                )
                .select_related('activity_list')
                .order_by('-pk')
            ),
        })

        return context

    def set_nav_tabs(self):
        """Configura as abas de navegação"""
        return [{
                'title': 'Resumo',
                'url': 'group:detail',                
                'pk': self.object.pk,
                'icon': 'bi-info-circle',
                'active': self.__class__.__name__ == 'GroupDetailView'
            }, {
                'title': 'Compartilhamento',
                'url': 'group:share',                
                'pk': self.object.pk,
                'icon': 'bi-share',
                'active': self.__class__.__name__ == 'GroupShareView'
            }
        ]


class GroupDetailView(
    AuthPermissionMixin,
    GroupBaseView,
    ObjectAccessRequiredMixin,
    NavigationMixin,
    DetailView
):
    model = Group

    def has_object_access(self, user, obj):
        # Verificar se o usuário é o criador da turma
        if obj.created_by == user:
            return True

        # Verificar se a turma foi compartilhada com o usuário
        if obj.sharings.filter(shared_with=user, is_active=True).exists():
            return True

        return False
 

class GroupShareView(
    AuthPermissionMixin,
    SuccessMessageMixin,
    GroupBaseView,
    ObjectAccessRequiredMixin,
    NavigationMixin,
    FilteringMixin,
    OrderingMixin,
    PaginationMixin,
    EnrichObjectMixin,
    FormMixin,
    DetailView
):
    template_name = 'group/shared_list_view.html'
    model = Group
    form_class = GroupSharingForm
    allowed_fields = {
        "shared_with": "shared_with__username__icontains",
        "created_at": "created_at__icontains",
    }
    success_message = "Compartilhado com sucesso!"

    def has_object_access(self, user, obj):
        # Verificar se o usuário é o criador da turma
        if hasattr(obj, 'created_by') and obj.created_by == user:
            return True

        return False

    def has_object_enrich_actions(self, user, obj):
        return obj.shared_by == user

    def enrich_actions(self, user, obj):
        if self.has_object_enrich_actions(user, obj):
            return get_btn_action(
                ['unshare'],
                self.request.resolver_match.app_name
            )

    def get_sharings_queryset(self):
        qs = (
            GroupSharing.objects
            .filter(group=self.object, is_active=True)
            .select_related('shared_with', 'shared_by')
        )

        # 🔹 aplicar filtro
        qs = self.apply_filtering(
            queryset=qs,
        )

        # 🔹 aplicar ordenação
        qs = self.apply_ordering(queryset=qs)

        return qs

    def get_filter_flags(self):
        return {
            'has_search_filter': bool(self.request.session.get(self.get_filtering_session_key())),
            'has_order_filter': bool(self.request.session.get(self.get_ordering_session_key())),
        }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['group_pk'] = self.kwargs.get('pk')
        kwargs['request_user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        sharings_qs = self.get_sharings_queryset()

        pagination = self.paginate_queryset(sharings_qs)

        enrichment = self.apply_enrichment(pagination)

        context.update({
            'form': self.get_form(),
            **enrichment,
            **self.get_filter_flags(),
            **self.has_filtering(return_context=True),
            **self.has_ordering(return_context=True)
        })

        return context

    def post(self, request, *args, **kwargs):
        # Garantir que self.object esteja definido para o form_valid
        self.object = self.get_object()

        form = self.get_form()
        if 'users' not in form.data:
            messages.error(request, 'Nenhum usuário selecionado para compartilhamento.')
            return self.get(request, *args, **kwargs)

        if form.is_valid():
            return self.form_valid(form)
        
        return self.get(request, *args, **kwargs)

    @transaction.atomic
    def form_valid(self, form):
        users = form.cleaned_data['users']
        group = self.object
        shared_by = self.request.user

        # Criamos uma lista de objetos GroupSharing na memória
        new_sharings = [
            GroupSharing(
                group=group,
                shared_with=user,
                shared_by=shared_by,
                is_active=True
            )
            for user in users
        ]
    
        # Insere todos de uma vez
        GroupSharing.objects.bulk_create(
            new_sharings,
            unique_fields=['group', 'shared_with'],
            update_conflicts=True,
            update_fields=['is_active', 'shared_by']
        )

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('group:share', kwargs={'pk': self.object.pk})


##### INICIO VIEW DE GERENCIAMENTO DE ARQUIVAMENTO DE TURMA #####
class GroupManageArchivingView(AuthPermissionMixin, ObjectAccessRequiredMixin, View):

    def get_object(self):
        return Group.objects.filter(
            pk=self.kwargs['pk'],
            deleted_at__isnull=True
        ).filter(
            Q(created_by=self.request.user) |
            Q(
                sharings__shared_with=self.request.user,
                sharings__is_active=True
            )
        ).first()

    def has_object_access(self, user, obj):
        # Verificar se o usuário é o criador da turma
        if (hasattr(obj, 'created_by') and obj.created_by == user) or self.get_object():
            return True

        return False

    def post(self, request, *args, **kwargs):
        group_pk = self.kwargs['pk']

        # Obter ou criar o registro
        archived, created = GroupArchived.objects.get_or_create(
            group_id=group_pk,
            user=request.user,
            defaults={'is_archived': True}
        )

        # Se já existe, faz o toggle
        if not created:
            archived.is_archived = not archived.is_archived
            archived.save()

        messages.success(
            request,
            f'Turma {"arquivada" if archived and archived.is_archived else "desarquivada"} com sucesso!'
        )

        return redirect('group:active')


##### INICIO VIEW DE SOFT DELETE DE TURMA #####
class GroupSoftDeleteView(AuthPermissionMixin, ObjectAccessRequiredMixin, DeleteView):
    """View para soft delete de grupo"""
    model = Group
    template_name = 'global/partials/generic/delete/view.html'
    context_object_name = 'delete'

    def has_object_access(self, user, obj):
        # Verificar se o usuário é o criador da turma
        if obj.created_by == user:
            return True

        return False

    def post(self, request, *args, **kwargs):
        obj = self.get_object()

        # 1. Realiza soft delete do grupo
        obj.deleted_at = timezone.now()
        obj.save(update_fields=['deleted_at'])

        # 2. Desativa todos os compartilhamentos vinculados a esse grupo
        obj.sharings.filter(is_active=True).update(is_active=False)

        messages.success(
            request,
            f'Turma "{obj.name}" deletada com sucesso!'
        )

        return redirect('group:active')


##### INICIO VIEW DE REMOÇÃO DE COMPARTILHAMENTO DE TURMA #####
class GroupUnshareView(AuthPermissionMixin, ObjectAccessRequiredMixin, View):
    """View para remover compartilhamento"""

    def get_object(self):
        return GroupSharing.objects.filter(
            pk=self.kwargs['pk'],
            shared_by=self.request.user
        ).first()

    def has_object_access(self, user, obj):
        return obj.group.created_by == user

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=['is_active'])

        messages.success(request,'Compartilhamento removido com sucesso!')
        return redirect('group:detail', pk=obj.group.pk)


from common.mixins import AuthPermissionMixin
from django.contrib import messages
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View
from django.views.generic.edit import FormMixin
from group.forms.group import GroupForm, GroupSharingForm
from group.mixins import GroupAccessMixin
from group.models import Group, GroupArchived, GroupSharing


class GroupListBaseView(ListView):
    """Classe base para listagens de grupos"""
    model = Group
    template_name = 'global/partials/generic/list_view.html'
    paginate_by = 10
    page_title = None
    create_url = None

    def get_queryset(self):
        """Cada subclass define seu próprio filtro"""
        raise NotImplementedError

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.create_url:
            context.update({'create_url': self.create_url})

        context.update({
            'page_title': self.page_title,
            'nav_tabs': self.set_nav_tabs(),
            'table': {
                'fields': ['name', 'description', 'created_at', 'updated_at'],                
                'actions': [
                    {
                        'url': 'group:detail',
                        'icon': 'bi-eye',
                    }
                ]
            }
        })
        return context

    def set_nav_tabs(self):
        """Configura as abas de navegação"""
        return [
            {
                'title': 'Ativas',
                'url': 'group:active',
                'active': self.__class__.__name__ == 'GroupActiveListView'
            },{
                'title': 'Compartilhadas',
                'url': 'group:shared',
                'active': self.__class__.__name__ == 'GroupSharedListView'
            },{
                'title': 'Arquivadas',
                'url': 'group:archived',
                'active': self.__class__.__name__ == 'GroupArchivedListView'
            },
        ]


class GroupActiveListView(AuthPermissionMixin, GroupListBaseView):
    page_title = 'Turmas Ativas'
    create_url = 'group:create'

    def get_queryset(self):
        """Retorna os grupos ativos do usuário"""
        return Group.objects.filter(
            created_by=self.request.user
        ).exclude(
            archived_groups__is_archived=True
        ).distinct().order_by('-id')


class GroupArchivedListView(AuthPermissionMixin, GroupAccessMixin, GroupListBaseView):
    page_title = 'Turmas Arquivadas'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            archived_groups__is_archived=True
        ).distinct()


class GroupCreateOrUpdateView:
    model = Group
    form_class = GroupForm
    template_name = 'global/partials/form.html'
    success_url = '/group/active'
    success_message = None
    form_title = None
    submit_title = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'form_title': self.form_title,
            'submit_title': self.submit_title,
            'card': {'col': 'col-6'}
        })
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, self.success_message)
            return response
        except IntegrityError as e:
            form.add_error(
                'name', 
                'Você já tem uma turma com este nome. Por favor, escolha outro nome.'
            )
            return self.form_invalid(form)


class GroupCreateView(AuthPermissionMixin, GroupCreateOrUpdateView, CreateView):
    form_title = 'Criar Turma'
    submit_title = 'Cadastrar Turma'
    success_message = 'Turma criada com sucesso!'

    def form_valid(self, form):
        # Atribuir o usuário logado como criador da turma
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class GroupDetailView(AuthPermissionMixin, GroupAccessMixin, DetailView):
    model = Group
    template_name = 'group/detail.html'
    context_object_name = 'group'


class GroupManageArchivingView(AuthPermissionMixin, GroupAccessMixin, View):

    def dispatch(self, *args, **kwargs):
        if not self.get_queryset().filter(pk=self.kwargs['pk']).exists():
            messages.error(
                self.request,
                'Você não tem permissão para ativar/arquivar esta turma.'
            )
            return redirect('group:active')

        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
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
            f'Turma movida para aba `{"Arquivadas" if archived and archived.is_archived else "Ativas"}`!'
        )

        return redirect('group:active')


class GroupShareView(AuthPermissionMixin, FormMixin, ListView):
    model = GroupSharing
    form_class = GroupSharingForm
    template_name = 'group/share.html'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if not self.get_group():
            messages.error(
                request,
                'Você não tem permissão para compartilhar esta turma.'
            )
            return redirect('group:active')

        return super().dispatch(request, *args, **kwargs)

    def get_group(self):
        return Group.objects.filter(
            pk=self.kwargs['pk'],
            created_by=self.request.user
        ).first()

    def get_queryset(self):
        """Retorna o grupo da URL"""
        return GroupSharing.objects.filter(
            group__pk=self.kwargs['pk'],
            group__created_by=self.request.user,
            is_active=True
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'group': self.get_group(),
            'form': self.get_form(),
            'table': {
                'fields': ['shared_with', 'created_at'],
                'actions': [
                    {
                        'url': 'group:unshare',
                        'icon': 'bi-trash',
                        'class': 'btn-outline-danger',
                        'text': 'Remover',
                    }
                ]
            }
        })
        return context

    def form_valid(self, form):
        for user in form.cleaned_data.get('users', []):
            update, create = GroupSharing.objects.update_or_create(
                group_id=self.kwargs['pk'],
                shared_with=user,
                defaults={'shared_by': self.request.user}
            )

            if not create:
                update.is_active = True
                update.save()

        messages.success(self.request, 'Turma compartilhada com sucesso!')
        return redirect('group:share', pk=self.kwargs['pk'])

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['group_pk'] = self.kwargs['pk']
        kwargs['request_user'] = self.request.user
        return kwargs


class GroupSharedListView(AuthPermissionMixin, GroupListBaseView):
    page_title = 'Turmas Compartilhadas'

    def get_queryset(self):
        """Retorna os grupos compartilhados com o usuário"""
        return Group.objects.filter(
            sharings__shared_with=self.request.user,
        ).exclude(
            archived_groups__is_archived=True
        ).distinct()


class GroupUnshareView(AuthPermissionMixin, View):
    """View para remover compartilhamento"""

    def get(self, request, *args, **kwargs):

        if not (
            sharing := GroupSharing.objects.filter(
                pk=self.kwargs['pk'],
                group__created_by=self.request.user
            ).first()
        ):
            messages.error(
                request,
                'Compartilhamento não encontrado ou você não tem permissão para alterar.'
            )
            return redirect('group:active')

        sharing.is_active = False
        sharing.save()

        messages.success(request,'Compartilhamento removido com sucesso!')
        return redirect('group:share', pk=sharing.group.pk)


class GroupUpdateView(AuthPermissionMixin, GroupCreateOrUpdateView, UpdateView):
    form_title = 'Editar Turma'
    submit_title = 'Atualizar Turma'
    success_message = 'Turma atualizada com sucesso!'

    def dispatch(self, request, *args, **kwargs):
        # Obtém o grupo informado na request
        group = self.get_object()

        # Verificar se o grupo existe e se o usuário tem permissão para alterar
        if group.created_by != request.user:
            messages.error(
                request,
                'Somente o criador do grupo pode editar.'
            )
            return redirect('group:active')

        return super().dispatch(request, *args, **kwargs)


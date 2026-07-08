from __future__ import annotations
from typing import Any
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
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q, QuerySet
from django.db.utils import IntegrityError
from django.forms import BaseModelForm
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView, View
from django.views.generic.edit import FormMixin
from group.forms.group import GroupForm, GroupSharingForm
from group.models import Group, GroupArchived, GroupInvite, GroupSharing, GroupStudent


##### INICIO VIEW NAVTABS DA ABA TURMAS #####
class GroupListBaseView(EnhancedListView):
    """Classe base para listagens de grupos"""
    allowed_fields = ['name', 'description', 'shift', 'created_at']
    detail_url = 'group:detail'
    model = Group
    page_description = 'Organize, acompanhe e compartilhe suas turmas com facilidade.'

    def has_object_enrich_actions(self, user: User, obj: Group) -> bool:
        return obj.created_by == user

    def enrich_actions(self, user: User, obj: Group) -> list:
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

    def get_archived_group_ids(self) -> QuerySet:
        """Retorna IDs de grupos arquivados do usuário - uma única query"""
        return GroupArchived.objects.filter(
            group=OuterRef('pk'),
            user=self.request.user,
            is_archived=True
        )

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        context.update({
            'nav_tabs': self.set_nav_tabs(),
            'table': {
                'fields': self.allowed_fields,
            },
            'create_url': self.create_url,
        })
        return context

    def set_nav_tabs(self) -> list:
        """Configura as abas de navegação"""
        return [
            {
                'title': 'Ativas',
                'url': 'group:active',
                'icon': 'bi-check-circle',
                'active': self.__class__.__name__ == 'GroupActiveListView'
            },
            {
                'title': 'Compartilhadas',
                'url': 'group:shared',
                'icon': 'bi-share',
                'active': self.__class__.__name__ == 'GroupSharedListView'
            },
            {
                'title': 'Arquivadas',
                'url': 'group:archived',
                'icon': 'bi-inbox',
                'active': self.__class__.__name__ == 'GroupArchivedListView'
            }
        ]


class GroupActiveListView(AuthPermissionMixin, GroupListBaseView):
    """Listagem de turmas ativas criadas pelo professor autenticado."""

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
    """Listagem de turmas arquivadas pelo professor autenticado."""

    page_title = 'Turmas Arquivadas'

    def get_queryset(self):
        """Retorna os grupos arquivados do usuário"""
        return super().get_queryset().filter(
            archived_groups__user=self.request.user,
            archived_groups__is_archived=True,
            deleted_at__isnull=True
        )


class GroupSharedListView(AuthPermissionMixin, GroupListBaseView):
    """Listagem de turmas compartilhadas com o professor autenticado por outros professores."""

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
    """Mixin compartilhado entre criação e edição de turmas.

    Centraliza contexto de formulário (título, dicas, confirmação) e
    captura ``IntegrityError`` para tratar nome duplicado com mensagem
    amigável em vez de 500.
    """
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

    def get_context_data(self, **kwargs) -> dict:
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

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
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
    """Criação de nova turma pelo professor autenticado."""

    form_subtitle = 'Complete o formulário para ativar sua turma e começar a organizar suas atividades.'
    page_description = 'Crie uma nova turma para organizar as suas atividades e acompanhar o progresso dos alunos.'
    page_title = 'Criar Turma'
    submit_title = 'Cadastrar'
    success_message = 'Turma criada com sucesso!'
    
    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        # Atribuir o usuário logado como criador da turma
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class GroupUpdateView(
    AuthPermissionMixin,
    GroupCreateOrUpdateView,
    ObjectAccessRequiredMixin,
    UpdateView
):
    """Edição de uma turma existente — restrita ao criador da turma."""

    form_subtitle = 'Revise e atualize os dados da sua turma para garantir que tudo esteja sempre correto.'
    page_description = 'Gerencie e edite as informações da turma, mantendo alunos e atividades sempre organizados e atualizados.'
    page_title = 'Atualizar Turma'
    submit_title = 'Atualizar'
    success_message = 'Turma atualizada com sucesso!'

    def has_object_access(self, user: User, obj: Group) -> bool:
        return obj.created_by == user


##### INICIO VIEW DE DETALHAMENTO DE TURMA #####
class GroupBaseView:
    """Classe base para as views de detalhe de turma.

    Compartilha queryset (excluindo deletadas), contexto de atividades
    recentes e configuração das abas de navegação entre
    :class:`GroupDetailView` e :class:`GroupShareView`.
    """
    allowed_fields = None
    template_name = 'group/detail_list_view.html'

    def get_queryset(self) -> QuerySet[Group]:
        return super().get_queryset().filter(deleted_at__isnull=True)

    def get_context_data(self, **kwargs) -> dict:
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
                .annotate(
                    submission_count=Count(
                        'submissions',
                        filter=Q(submissions__submitted_at__isnull=False),
                    )
                )
                .order_by('-pk')
            ),
        })

        return context

    def set_nav_tabs(self) -> list:
        """Configura as abas de navegação"""
        tabs = [
            {
                'title': 'Resumo',
                'url': 'group:detail',
                'pk': self.object.pk,
                'icon': 'bi-info-circle',
                'active': self.__class__.__name__ == 'GroupDetailView',
            },
            {
                'title': 'Compartilhamento',
                'url': 'group:share',
                'pk': self.object.pk,
                'icon': 'bi-share',
                'active': self.__class__.__name__ == 'GroupShareView',
            },
        ]
        is_owner = self.object.created_by == self.request.user
        is_shared = self.object.sharings.filter(shared_with=self.request.user, is_active=True).exists()
        if is_owner or is_shared:
            tabs.append({
                'title': 'Revisão',
                'url': 'group:review',
                'pk': self.object.pk,
                'icon': 'bi-pencil-square',
                'active': self.__class__.__name__ == 'GroupReviewView',
            })
        return tabs


class GroupDetailView(
    AuthPermissionMixin,
    GroupBaseView,
    ObjectAccessRequiredMixin,
    NavigationMixin,
    DetailView
):
    """Detalhes de uma turma: resumo, atividades recentes e abas de navegação."""

    model = Group

    def has_object_access(self, user: User, obj: Group) -> bool:
        # Verificar se o usuário é o criador da turma
        if obj.created_by == user:
            return True

        # Verificar se a turma foi compartilhada com o usuário
        if obj.sharings.filter(shared_with=user, is_active=True).exists():
            return True

        return False
 

class GroupReviewView(
    AuthPermissionMixin,
    GroupBaseView,
    ObjectAccessRequiredMixin,
    NavigationMixin,
    DetailView,
):
    """Aba de revisão de submissões dos alunos — visível para o dono e professores com turma compartilhada."""

    model = Group
    template_name = 'group/review.html'

    def has_object_access(self, user: User, obj: Group) -> bool:
        if obj.created_by == user:
            return True
        return obj.sharings.filter(shared_with=user, is_active=True).exists()

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        activity_links = (
            ActivityListGroup.objects
            .filter(
                group=self.object,
                activity_list__deleted_at__isnull=True,
            )
            .select_related('activity_list')
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
            .order_by('-assigned_at')
        )
        context['activity_links'] = activity_links
        return context


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
    """Aba de compartilhamento de turma: gerencia compartilhamentos com professores e matrículas de alunos."""

    template_name = 'group/shared_list_view.html'
    model = Group
    form_class = GroupSharingForm
    allowed_fields = {
        "shared_with": "shared_with__username__icontains",
        "created_at": "created_at__icontains",
    }
    success_message = "Compartilhado com sucesso!"

    def get_share_view(self) -> str:
        """Retorna a aba ativa de compartilhamento (``'teachers'`` ou ``'students'``).

        Lê o parâmetro ``share_view`` da query string; retorna ``'teachers'``
        como padrão se o valor não for reconhecido.
        """
        share_view = self.request.GET.get('share_view', 'teachers')
        return share_view if share_view in ['teachers', 'students'] else 'teachers'

    def get_share_allowed_fields(self) -> dict[str, str]:
        if self.get_share_view() == 'students':
            return {
                "student": "student__username__icontains",
                "joined_at": "joined_at__icontains",
            }

        return {
            "shared_with": "shared_with__username__icontains",
            "created_at": "created_at__icontains",
        }

    def get_share_tabs(self) -> list:
        """Retorna a configuração das abas de compartilhamento para o template.

        Returns:
            Lista de dicionários com ``title``, ``url``, ``icon`` e ``active``
            para as abas "Professores" e "Alunos".
        """
        share_view = self.get_share_view()

        return [
            {
                'title': 'Professores',
                'url': f'{self.request.path}?share_view=teachers',
                'icon': 'bi-person-check',
                'active': share_view == 'teachers',
            },
            {
                'title': 'Alunos',
                'url': f'{self.request.path}?share_view=students',
                'icon': 'bi-mortarboard',
                'active': share_view == 'students',
            }
        ]

    def has_object_access(self, user: User, obj: Group) -> bool:
        # Verificar se o usuário é o criador da turma
        if hasattr(obj, 'created_by') and obj.created_by == user:
            return True

        return False

    def has_object_enrich_actions(self, user: User, obj: GroupSharing) -> bool:
        return obj.shared_by == user

    def enrich_actions(self, user: User, obj: GroupSharing) -> list:
        if self.has_object_enrich_actions(user, obj):
            return get_btn_action(
                ['unshare'],
                self.request.resolver_match.app_name
            )

    def get_sharings_queryset(self) -> QuerySet:
        self.allowed_fields = self.get_share_allowed_fields()

        if self.get_share_view() == 'students':
            qs = (
                GroupStudent.objects
                .filter(group=self.object, is_active=True)
                .select_related('student', 'group')
            )
        else:
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

    def get_filter_flags(self) -> dict:
        """Retorna flags booleanas indicando se há filtros de busca ou ordenação ativos.

        Returns:
            Dicionário com ``has_search_filter`` e ``has_order_filter``.
        """
        return {
            'has_search_filter': bool(self.request.session.get(self.get_filtering_session_key())),
            'has_order_filter': bool(self.request.session.get(self.get_ordering_session_key())),
        }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['group_pk'] = self.kwargs.get('pk')
        kwargs['request_user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)

        sharings_qs = self.get_sharings_queryset()

        pagination = self.paginate_queryset(sharings_qs)

        enrichment = (
            self.apply_enrichment(pagination)
            if self.get_share_view() == 'teachers'
            else pagination
        )

        latest_invite = None
        latest_invite_url = None
        latest_invite_id = self.request.session.pop('latest_group_invite_id', None)

        if latest_invite_id:
            latest_invite = GroupInvite.objects.filter(
                pk=latest_invite_id,
                group=self.object,
                is_active=True,
            ).first()
        else:
            latest_invite = (
                GroupInvite.objects
                .filter(
                    group=self.object,
                    is_active=True,
                    expires_at__gt=timezone.now(),
                )
                .order_by('-created_at')
                .first()
            )

        if latest_invite:
            latest_invite_url = self.request.build_absolute_uri(
                reverse('group:invite_confirm', kwargs={'token': latest_invite.token})
            )

        context.update({
            'form': self.get_form(),
            **enrichment,
            **self.get_filter_flags(),
            **self.has_filtering(return_context=True),
            **self.has_ordering(return_context=True),
            'latest_invite': latest_invite,
            'latest_invite_url': latest_invite_url,
            'share_view': self.get_share_view(),
            'share_tabs': self.get_share_tabs(),
            'table': {
                'fields': self.get_share_allowed_fields(),
            },
        })

        return context

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
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
    def form_valid(self, form: BaseModelForm) -> HttpResponse:
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
    """Alterna o estado de arquivamento de uma turma (arquivar / desarquivar) via POST."""

    def get_object(self) -> Group | None:
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

    def has_object_access(self, user: User, obj: Group | None) -> bool:
        # Verificar se o usuário é o criador da turma
        if (hasattr(obj, 'created_by') and obj.created_by == user) or self.get_object():
            return True

        return False

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
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


class GroupInviteCreateView(AuthPermissionMixin, ObjectAccessRequiredMixin, View):
    """Gera um novo link de convite para matrícula de alunos via token."""

    def get_object(self) -> Group | None:
        return Group.objects.filter(
            pk=self.kwargs['pk'],
            created_by=self.request.user,
            deleted_at__isnull=True
        ).first()

    def has_object_access(self, user: User, obj: Group | None) -> bool:
        return obj and obj.created_by == user

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        group = self.get_object()
        invite = GroupInvite.objects.create(
            group=group,
            created_by=request.user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        invite_url = request.build_absolute_uri(
            reverse('group:invite_confirm', kwargs={'token': invite.token})
        )

        if request.headers.get('HX-Request'):
            return render(
                request,
                'group/partials/_invite_link.html',
                {
                    'latest_invite': invite,
                    'latest_invite_url': invite_url,
                    'object': group,
                }
            )

        request.session['latest_group_invite_id'] = invite.pk

        return redirect('group:share', pk=group.pk)


class GroupInviteExpireView(AuthPermissionMixin, ObjectAccessRequiredMixin, View):
    """Expira manualmente um convite ativo, tornando-o inválido para novos acessos."""

    def get_object(self) -> GroupInvite | None:
        if hasattr(self, 'object'):
            return self.object

        self.object = (
            GroupInvite.objects
            .select_related('group', 'created_by')
            .filter(
                pk=self.kwargs['invite_pk'],
                group_id=self.kwargs['pk'],
                group__deleted_at__isnull=True,
            )
            .first()
        )
        return self.object

    def has_object_access(self, user: User, obj: GroupInvite | None) -> bool:
        return obj and obj.group.created_by == user

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        invite = self.get_object()
        invite.is_active = False
        invite.expires_at = timezone.now()
        invite.save(update_fields=['is_active', 'expires_at', 'updated_at'])

        if request.headers.get('HX-Request'):
            return render(
                request,
                'group/partials/_invite_link.html',
                {
                    'object': invite.group,
                    'invite_expired': True,
                }
            )

        return redirect('group:share', pk=invite.group.pk)


class GroupInviteConfirmView(AuthPermissionMixin, View):
    """View de confirmação e uso de convite por token.

    GET exibe as informações da turma e o status do convite (pode entrar,
    já é membro, expirado, etc.). POST realiza a matrícula do aluno na turma
    e incrementa o contador de usos do convite.
    """
    template_name = 'group/invite_confirm.html'

    def get_invite(self) -> GroupInvite | None:
        if hasattr(self, 'invite'):
            return self.invite  # pragma: no cover

        self.invite = (
            GroupInvite.objects
            .select_related('group', 'group__created_by', 'created_by')
            .filter(token=self.kwargs['token'])
            .first()
        )
        return self.invite

    def get_context_data(self) -> dict:
        """Monta o contexto com o status do convite e dados da turma.

        Returns:
            Dicionário com ``invite``, ``can_join``, ``already_joined``,
            ``is_owner``, ``active_activities_count``, ``active_students_count``
            e ``blocked_reason`` (``None`` quando o aluno pode entrar).
        """
        invite = self.get_invite()
        context = {
            'invite': invite,
            'can_join': False,
            'already_joined': False,
            'is_owner': False,
            'active_activities_count': 0,
            'active_students_count': 0,
            'blocked_reason': None,
        }

        if not invite:
            context['blocked_reason'] = 'Convite não encontrado.'
            return context

        group = invite.group
        context.update({
            'already_joined': group.students.filter(
                student=self.request.user,
                is_active=True
            ).exists(),
            'is_owner': group.created_by == self.request.user,
            'active_activities_count': group.activity_list_groups.filter(
                activity_list__deleted_at__isnull=True
            ).count(),
            'active_students_count': group.students.filter(is_active=True).count(),
        })

        if not invite.can_be_used():
            context['blocked_reason'] = 'Este convite expirou ou não está mais disponível.'
        elif context['is_owner']:
            context['blocked_reason'] = 'Você é o professor responsável por esta turma.'
        elif context['already_joined']:
            context['blocked_reason'] = 'Você já participa desta turma.'
        else:
            context['can_join'] = True

        return context

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return render(request, self.template_name, self.get_context_data())

    @transaction.atomic
    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        context = self.get_context_data()
        invite = context['invite']

        if not invite or not context['can_join']:
            if context['blocked_reason']:
                messages.error(request, context['blocked_reason'])
            return render(request, self.template_name, context, status=400)

        enrollment, created = GroupStudent.objects.get_or_create(
            group=invite.group,
            student=request.user,
            defaults={'is_active': True}
        )

        if not created and not enrollment.is_active:
            enrollment.is_active = True
            enrollment.save(update_fields=['is_active', 'updated_at'])

        if created or not context['already_joined']:
            invite.used_count += 1
            invite.save(update_fields=['used_count', 'updated_at'])

        messages.success(
            request,
            f'Você entrou na turma "{invite.group.name}" com sucesso.'
        )

        return redirect('student:dashboard')


##### INICIO VIEW DE SOFT DELETE DE TURMA #####
class GroupSoftDeleteView(AuthPermissionMixin, ObjectAccessRequiredMixin, DeleteView):
    """View para soft delete de grupo"""
    model = Group
    template_name = 'global/partials/generic/delete/view.html'
    context_object_name = 'delete'

    def has_object_access(self, user: User, obj: Group) -> bool:
        # Verificar se o usuário é o criador da turma
        if obj.created_by == user:
            return True

        return False

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
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

    def get_object(self) -> GroupSharing | None:
        return GroupSharing.objects.filter(
            pk=self.kwargs['pk'],
            shared_by=self.request.user
        ).first()

    def has_object_access(self, user: User, obj: GroupSharing) -> bool:
        return obj.group.created_by == user

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=['is_active'])

        messages.success(request,'Compartilhamento removido com sucesso!')
        return redirect('group:detail', pk=obj.group.pk)


from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.paginator import Paginator
from accounts.models import UserPreferences
from django.db.models.functions import Lower
from django.db.models import F, QuerySet
from django.db import transaction


class AuthPermissionMixin(LoginRequiredMixin):
    
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class NavigationMixin:
    def dispatch(self, request, *args, **kwargs):
        match = request.resolver_match

        current = {
            'namespace': match.namespace,
            'view': match.view_name,
        }

        last = request.session.get('last_route')

        request._navigation = {
            'current': current,
            'last': last,
            'changed_view': bool(last and last['view'] != current['view']),
            'changed_namespace': bool(last and last['namespace'] != current['namespace']),  
        }

        request.session['last_route'] = current

        return super().dispatch(request, *args, **kwargs)


class FilteringMixin:
    allowed_fields: list|dict = None
    model = None

    def get_filtering_session_key(self):
        app_label = self.model._meta.app_label
        view_name = self.__class__.__name__
        return f'{app_label}_{view_name}_search'

    def has_filtering(self, return_data=False, return_context=False):
        
        # Retorna o contexto para o template, se houver uma sessão de filtragem ativa
        if return_context:
            return {
                'has_filtering_session': self.request.session.get(
                    self.get_filtering_session_key(),
                    False
                ),
            }

        # Retorna os dados da sessão de filtragem, se houver uma sessão ativa
        if return_data:
            return self.request.session.get(self.get_filtering_session_key(), False)

        # Retorna um booleano indicando se há uma sessão de filtragem ativa
        return self.get_filtering_session_key() in self.request.session


    def apply_filtering(self, queryset: QuerySet):
        if not self.allowed_fields or not self.model:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} precisa de 'allowed_fields' e 'model'"
            )

        # limpar filtro
        nav = getattr(self.request, '_navigation', {})
        if (self.request.GET.get('clear_filter') and self.has_filtering()) \
        or (nav.get('changed_view') and self.has_filtering()):
            key = self.get_filtering_session_key()
            del self.request.session[key]
            return queryset

        # pegar dados
        if 'search_field' in self.request.GET and 'q' in self.request.GET:
            search_field = self.request.GET.get('search_field')
            q = self.request.GET.get('q')

        elif session := self.has_filtering(return_data=True):
            search_field = session.get('search_field')
            q = session.get('q')
        else:
            return queryset

        # validar
        if search_field in self.allowed_fields:
            key = self.get_filtering_session_key()
            self.request.session[key] = {
                'search_field': search_field,
                'q': q
            }

            if isinstance(self.allowed_fields, dict):    
                return queryset.filter(**{
                    self.allowed_fields[search_field]: q
                })

            return queryset.filter(**{f'{search_field}__icontains': q})

        return queryset


class OrderingMixin:
    ordering = '-id'
    allowed_fields: list|dict = None
    model = None

    def get_ordering_session_key(self):
        app_label = self.model._meta.app_label
        view_name = self.__class__.__name__
        return f'{app_label}_{view_name}_ordering'

    def has_ordering(self, return_data=False, return_context=False):
        
        # Retorna o contexto para o template, se houver uma sessão de ordenação ativa
        if return_context:
            return {
                'has_ordering_session': self.request.session.get(
                    self.get_ordering_session_key(),
                    False
                ),
            }

        # Retorna os dados da sessão de ordenação, se houver uma sessão ativa
        if return_data:
            return self.request.session.get(self.get_ordering_session_key(), False)

        # Retorna um booleano indicando se há uma sessão de ordenação ativa
        return self.get_ordering_session_key() in self.request.session

    def get_ordering(self):
        if not self.allowed_fields or not self.model:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} precisa de 'allowed_fields' e 'model'"
            )

        # limpar ordenação
        nav = getattr(self.request, '_navigation', {})
        if (self.request.GET.get('clear_order') and self.has_ordering()) \
        or (nav.get('changed_view') and self.has_ordering()):
            key = self.get_ordering_session_key()
            del self.request.session[key]
            return self.ordering

        # pegar dados
        if 'sort' in self.request.GET and 'order' in self.request.GET:
            sort = self.request.GET.get('sort')
            order = self.request.GET.get('order')

        elif session := self.has_ordering(return_data=True):
            sort = session.get('sort')
            order = session.get('order')

        else:
            return self.ordering

        # validar
        if sort in self.allowed_fields and order in ['asc', 'desc']:
            key = self.get_ordering_session_key()
            self.request.session[key] = {'sort': sort, 'order': order}

            expr = Lower(F(sort))
            return (expr.desc(),) if order == 'desc' else (expr,)

        return self.ordering

    def apply_ordering(self, queryset: QuerySet):
        """
        Utilizado em views que não herdam de ListView, onde o método 
        get_ordering() não é chamado automaticamente.
        """
        ordering = self.get_ordering()

        if isinstance(ordering, (list, tuple)):
            return queryset.order_by(*ordering)
        
        return queryset.order_by(ordering)


class ViewTypeMixin:
    default_view_type = 'cards'
    view_types = ['table', 'cards']

    def get_view_type(self):
        view_name = self.__class__.__name__
        cookie_key = f'{view_name}-view-type'.lower()

        view_type = self.request.GET.get('view_type')

        if view_type and view_type in self.view_types and self.request.user.is_authenticated:

            # Obtém ou cria as preferências do usuário
            prefs, _ = UserPreferences.objects.get_or_create(user=self.request.user)
            preferences = prefs.preferences or {}
            preferences.setdefault('cookies', {})

            # Obtém o valor de preferência para o cookie específico
            current = preferences['cookies'].get(cookie_key)

            # Se o valor atual for diferente do novo, atualiza a preferência e salva
            if current != view_type:
                cookie = {cookie_key: view_type}
                preferences['cookies'].update(cookie)

                prefs.preferences = preferences
                prefs.save()

                self.request._set_cookies = cookie

            return view_type

        cookie_value = self.request.COOKIES.get(cookie_key)
        if cookie_value in self.view_types:
            return cookie_value

        return self.default_view_type


class EnrichObjectMixin:

    def has_object_enrich_actions(self, user, obj):
        # Implementar lógica na view para determinar se o usuário tem acesso ao objeto
        raise NotImplementedError

    def enrich_actions(self, user, obj):
        # Implementar lógica na view para retornar as ações disponíveis.
        # Dev validar se o usuário tem acesso ao objeto ou não,
        # utilizando o método has_object_enrich_actions.
        raise NotImplementedError

    def apply_enrichment(self, context):
        user = self.request.user

        # ListView
        if "object_list" in context:
            for obj in context["object_list"]:
                obj.ui_actions = self.enrich_actions(user, obj)

        # DetailView
        if obj := context.get("object"):
            obj.ui_actions = self.enrich_actions(user, obj)

        return context


class ActionsMixin(EnrichObjectMixin):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)       
        return self.apply_enrichment(context)


class ObjectAccessRequiredMixin:

    def has_object_access(self, user, obj):
        # Implementar lógica na view para determinar se o usuário tem acesso ao objeto
        raise NotImplementedError

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()

        if not self.has_object_access(request.user, obj):
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


class PaginationMixin:
    paginate_by = 10
    page_param = 'page'

    def paginate_queryset(self, queryset):
        paginator = Paginator(queryset, self.paginate_by)
        page_number = self.request.GET.get(self.page_param)

        page_obj = paginator.get_page(page_number)

        return {
            'paginator': paginator,
            'page_obj': page_obj,
            'object_list': page_obj.object_list,
            'is_paginated': page_obj.has_other_pages(),
        }


class InlineFormsetMixin:
    formset_class = None
    formset_context_name = 'formset'
    formset_prefix = 'options'

    def get_formset(self, instance=None):
        if self.request.POST:

            if hasattr(self, 'get_initial'):
                initial = self.get_initial()
                for key, value in initial.items():
                    if str(self.request.POST.get(key)) != str(value):
                        raise PermissionDenied

            return self.formset_class(
                self.request.POST,
                instance=instance, 
                prefix=self.formset_prefix
            )

        return self.formset_class(
            instance=instance,
            prefix=self.formset_prefix
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.formset_context_name not in context:
            # Obtém a instância pai para o formset carregar dados existentes
            parent_instance = self.get_formset_parent_instance()
            context[self.formset_context_name] = self.get_formset(instance=parent_instance)

        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)

        # hook pra quem herdar poder customizar
        parent_instance = self.get_formset_parent_instance()

        formset = self.get_formset(instance=parent_instance)

        if formset.is_valid():
            with transaction.atomic():
                self.object.save()
                self.save_parent_instance(parent_instance)
                formset.save()

            return self.render_success()

        return self.form_invalid(form)

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)

    # Hooks
    def get_formset_parent_instance(self):
        """
        Retorna a instância pai do formset.
        Default: usa self.object direto
        """
        return self.object

    def save_parent_instance(self, instance):
        """
        Caso precise salvar algo além do self.object
        """
        pass

    def render_success(self):
        """
        Override para HTMX ou redirect
        """
        pass

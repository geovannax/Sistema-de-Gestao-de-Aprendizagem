"""Mixins reutilizáveis para views Django do projeto.

Fornece blocos de construção para autenticação, navegação, filtragem,
ordenação, tipo de visualização, enriquecimento de objetos, controle de
acesso, paginação e formulários secundários/formsets.

Uso típico: combinados em ``EnhancedListView`` ou em views customizadas
que herdam de ``CreateView``/``UpdateView``/``DetailView``.
"""
from __future__ import annotations
from typing import Any, cast
from accounts.models import UserPreferences
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Model, QuerySet
from django.db.models.functions import Lower
from django.forms import BaseFormSet, BaseModelForm
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache


class AuthPermissionMixin(LoginRequiredMixin):
    """Exige autenticação e desabilita cache em todas as respostas.

    Aplica ``@never_cache`` via ``method_decorator`` no ``dispatch``,
    impedindo que proxies ou browsers armazenem páginas protegidas.
    Para requisições HTMX sem sessão ativa, retorna ``HX-Redirect``
    em vez de um 302, evitando que a página de login seja injetada
    dentro de um elemento HTMX.
    """

    @method_decorator(never_cache)
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if not request.user.is_authenticated and request.headers.get('HX-Request'):
            response = HttpResponse(status=401)
            response['HX-Redirect'] = self.get_login_url()
            return response
        return super().dispatch(request, *args, **kwargs)


class HTMXLoginRequiredMixin(LoginRequiredMixin):
    """Adapta o redirecionamento de login para requisições HTMX.

    Para requisições normais, comporta-se como ``LoginRequiredMixin``.
    Para requisições HTMX (header ``HX-Request``), retorna HTTP 401 com
    o header ``HX-Redirect`` para que o HTMX faça o redirecionamento
    no lado do cliente sem recarregar a página inteira.
    """

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if not request.user.is_authenticated:
            if request.headers.get('HX-Request'):
                response = HttpResponse(status=401)
                response['HX-Redirect'] = self.get_login_url()
                return response
            return super().dispatch(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)


class NavigationMixin:
    """Injeta metadados de navegação em ``request._navigation``.

    Registra a rota atual na sessão e disponibiliza em
    ``request._navigation`` informações sobre mudança de view ou de
    namespace entre requisições consecutivas. Usado por
    :class:`FilteringMixin` e :class:`OrderingMixin` para limpar filtros
    automaticamente quando o usuário muda de seção.

    Attributes injetados em ``request._navigation``:
        current: Dicionário ``{'namespace': ..., 'view': ...}`` da rota atual.
        last: Mesma estrutura da rota anterior (ou ``None``).
        changed_view: ``True`` se o nome da view mudou em relação à anterior.
        changed_namespace: ``True`` se o namespace mudou.
    """

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        match = request.resolver_match

        current = {
            'namespace': match.namespace,
            'view': match.view_name,
        }

        last = request.session.get('last_route')

        request._navigation = {  # type: ignore[attr-defined]
            'current': current,
            'last': last,
            'changed_view': bool(last and last['view'] != current['view']),
            'changed_namespace': bool(last and last['namespace'] != current['namespace']),
        }

        request.session['last_route'] = current

        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]


class FilteringMixin:
    """Adiciona busca textual persistida em sessão a qualquer ListView.

    O filtro é armazenado na sessão com uma chave derivada do ``app_label``
    e do nome da view, permitindo que filtros independentes coexistam entre
    views diferentes.

    Attributes:
        allowed_fields: Lista ou dicionário com os campos pesquisáveis.
            - ``list``: campo filtrado com ``__icontains`` automático.
            - ``dict``: mapeamento ``{campo_form: lookup_django}`` para
              filtros customizados (ex: ``{"grupo": "grupo__nome__icontains"}``).
        model: Modelo Django da view; obrigatório para construir a chave de sessão.
    """
    allowed_fields: list[str] | dict[str, str] | None = None
    model: type[Model] | None = None
    request: HttpRequest

    def get_filtering_session_key(self) -> str:
        """Retorna a chave de sessão exclusiva para o filtro desta view.

        Returns:
            String no formato ``{app_label}_{NomeDaView}_search``.
        """
        app_label = self.model._meta.app_label
        view_name = self.__class__.__name__
        return f'{app_label}_{view_name}_search'

    def has_filtering(self, return_data: bool = False, return_context: bool = False) -> bool | dict:
        """Verifica ou retorna o estado do filtro ativo na sessão.

        Args:
            return_data: Se ``True``, retorna os dados do filtro salvo em
                sessão (``dict`` com ``search_field`` e ``q``) ou ``False``.
            return_context: Se ``True``, retorna um dicionário pronto para
                injetar no contexto do template (``has_filtering_session``).

        Returns:
            - ``bool`` indicando se há filtro ativo (padrão).
            - ``dict`` com os dados do filtro quando ``return_data=True``.
            - ``dict`` de contexto quando ``return_context=True``.
        """
        if return_context:
            return {
                'has_filtering_session': self.request.session.get(
                    self.get_filtering_session_key(),
                    False
                ),
            }

        if return_data:
            return self.request.session.get(self.get_filtering_session_key(), False)

        return self.get_filtering_session_key() in self.request.session

    def apply_filtering(self, queryset: QuerySet) -> QuerySet:
        """Aplica o filtro de busca ao queryset e persiste na sessão.

        Limpa o filtro quando ``clear_filter=1`` está na query string ou
        quando o usuário muda de view (detectado via ``_navigation``).
        Persiste os parâmetros de busca na sessão para manter o filtro
        entre paginações e recarregamentos.

        Args:
            queryset: QuerySet base a ser filtrado.

        Returns:
            QuerySet filtrado ou o original se não houver filtro ativo.

        Raises:
            ImproperlyConfigured: Se ``allowed_fields`` ou ``model`` não
                estiverem definidos na view.
        """
        if not self.allowed_fields or not self.model:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} precisa de 'allowed_fields' e 'model'"
            )

        nav = getattr(self.request, '_navigation', {})
        if (self.request.GET.get('clear_filter') and self.has_filtering()) \
        or (nav.get('changed_view') and self.has_filtering()):
            key = self.get_filtering_session_key()
            del self.request.session[key]
            return queryset

        if 'search_field' in self.request.GET and 'q' in self.request.GET:
            search_field = self.request.GET.get('search_field')
            q = self.request.GET.get('q')

        elif session := self.has_filtering(return_data=True):
            search_field = session.get('search_field')  # type: ignore[union-attr]
            q = session.get('q')  # type: ignore[union-attr]
        else:
            return queryset

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
    """Adiciona ordenação persistida em sessão a qualquer ListView.

    A ordenação é armazenada na sessão com uma chave derivada do ``app_label``
    e do nome da view. Ao ordenar, aplica ``Lower(F(campo))`` para garantir
    ordenação case-insensitive em campos de texto.

    Attributes:
        ordering: Ordenação padrão aplicada quando nenhum parâmetro é fornecido.
            Padrão: ``'-id'``.
        allowed_fields: Lista ou dicionário com os campos ordenáveis.
        model: Modelo Django da view; obrigatório para construir a chave de sessão.
    """
    ordering = '-id'
    allowed_fields: list[str] | dict[str, str] | None = None
    model: type[Model] | None = None
    request: HttpRequest

    def get_ordering_session_key(self) -> str:
        """Retorna a chave de sessão exclusiva para a ordenação desta view.

        Returns:
            String no formato ``{app_label}_{NomeDaView}_ordering``.
        """
        app_label = self.model._meta.app_label
        view_name = self.__class__.__name__
        return f'{app_label}_{view_name}_ordering'

    def has_ordering(self, return_data: bool = False, return_context: bool = False) -> bool | dict:
        """Verifica ou retorna o estado da ordenação ativa na sessão.

        Args:
            return_data: Se ``True``, retorna os dados da ordenação salva em
                sessão (``dict`` com ``sort`` e ``order``) ou ``False``.
            return_context: Se ``True``, retorna um dicionário pronto para
                injetar no contexto do template (``has_ordering_session``).

        Returns:
            - ``bool`` indicando se há ordenação ativa (padrão).
            - ``dict`` com os dados da ordenação quando ``return_data=True``.
            - ``dict`` de contexto quando ``return_context=True``.
        """
        if return_context:
            return {
                'has_ordering_session': self.request.session.get(
                    self.get_ordering_session_key(),
                    False
                ),
            }

        if return_data:
            return self.request.session.get(self.get_ordering_session_key(), False)

        return self.get_ordering_session_key() in self.request.session

    def get_ordering(self) -> tuple | str:
        """Calcula a ordenação atual com base na query string ou na sessão.

        Limpa a ordenação quando ``clear_order=1`` está na query string ou
        quando o usuário muda de view. Persiste ``sort`` e ``order`` na sessão.
        Aplica ``Lower(F(campo))`` para ordenação case-insensitive.

        Returns:
            Tupla de expressões de ordenação (ex: ``(Lower(F('name')),)``)
            quando há parâmetros válidos, ou string de ordenação padrão
            (ex: ``'-id'``).

        Raises:
            ImproperlyConfigured: Se ``allowed_fields`` ou ``model`` não
                estiverem definidos na view.
        """
        if not self.allowed_fields or not self.model:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} precisa de 'allowed_fields' e 'model'"
            )

        nav = getattr(self.request, '_navigation', {})
        if (self.request.GET.get('clear_order') and self.has_ordering()) \
        or (nav.get('changed_view') and self.has_ordering()):
            key = self.get_ordering_session_key()
            del self.request.session[key]
            return self.ordering

        if 'sort' in self.request.GET and 'order' in self.request.GET:
            sort = self.request.GET.get('sort')
            order = self.request.GET.get('order')

        elif session := self.has_ordering(return_data=True):
            sort = session.get('sort')  # type: ignore[union-attr]
            order = session.get('order')  # type: ignore[union-attr]

        else:
            return self.ordering

        if sort in self.allowed_fields and order in ['asc', 'desc']:
            key = self.get_ordering_session_key()
            self.request.session[key] = {'sort': sort, 'order': order}

            expr = Lower(F(sort))
            return (expr.desc(),) if order == 'desc' else (expr,)

        return self.ordering

    def apply_ordering(self, queryset: QuerySet) -> QuerySet:
        """Aplica a ordenação calculada ao queryset.

        Utilizado em views que não herdam de ``ListView``, onde
        ``get_ordering()`` não é chamado automaticamente pelo Django.

        Args:
            queryset: QuerySet a ser ordenado.

        Returns:
            QuerySet com ``order_by`` aplicado.
        """
        ordering = self.get_ordering()

        if isinstance(ordering, (list, tuple)):
            return queryset.order_by(*ordering)

        return queryset.order_by(ordering)


class ViewTypeMixin:
    """Gerencia a preferência de visualização (lista/cards) por view e usuário.

    A preferência é lida de um cookie e persistida em
    :class:`~accounts.models.UserPreferences` quando alterada. O cookie é
    atualizado via ``CookieMiddleware`` ao final da requisição.

    Attributes:
        default_view_type: Tipo padrão quando nenhuma preferência existe.
            Padrão: ``'cards'``.
        view_types: Tipos de visualização aceitos. Padrão: ``['table', 'cards']``.
    """
    default_view_type = 'cards'
    view_types = ['table', 'cards']
    request: HttpRequest

    def get_view_type(self) -> str:
        """Determina e persiste o tipo de visualização ativo.

        Ordem de precedência:
        1. Parâmetro ``view_type`` na query string (para usuários autenticados).
        2. Cookie existente no navegador.
        3. ``default_view_type``.

        Quando o valor muda, atualiza ``UserPreferences`` e sinaliza ao
        ``CookieMiddleware`` para atualizar o cookie via
        ``request._set_cookies``.

        Returns:
            String com o tipo de visualização ativo (``'cards'`` ou ``'table'``).
        """
        view_name = self.__class__.__name__
        cookie_key = f'{view_name}-view-type'.lower()

        view_type = self.request.GET.get('view_type')

        if view_type and view_type in self.view_types and self.request.user.is_authenticated:

            prefs, _ = UserPreferences.objects.get_or_create(user=self.request.user)
            preferences = prefs.preferences or {}
            preferences.setdefault('cookies', {})

            current = preferences['cookies'].get(cookie_key)

            if current != view_type:
                cookie = {cookie_key: view_type}
                preferences['cookies'].update(cookie)

                prefs.preferences = preferences
                prefs.save()

                self.request._set_cookies = cookie  # type: ignore[attr-defined]

            return view_type

        cookie_value = self.request.COOKIES.get(cookie_key)
        if cookie_value in self.view_types:
            return cookie_value

        return self.default_view_type


class EnrichObjectMixin:
    """Interface para enriquecimento de objetos com ações de UI.

    Define os contratos ``has_object_enrich_actions`` e ``enrich_actions``
    que as views concretas devem implementar. O método ``apply_enrichment``
    itera sobre o ``object_list`` (ListView) e injeta ``ui_actions`` em
    cada objeto.

    As subclasses devem sobrescrever ambos os métodos abstratos.
    """
    request: HttpRequest

    def has_object_enrich_actions(self, user: User, obj: Model) -> bool:
        """Determina se o usuário tem permissão para ver ações no objeto.

        Args:
            user: Usuário autenticado da requisição.
            obj: Instância do modelo sendo enriquecida.

        Returns:
            ``True`` se o usuário deve ver as ações completas.

        Raises:
            NotImplementedError: Deve ser implementado na view concreta.
        """
        raise NotImplementedError  # pragma: no cover

    def enrich_actions(self, user: User, obj: Model) -> list:
        """Retorna a lista de ações de UI disponíveis para o objeto.

        Deve consultar ``has_object_enrich_actions`` internamente para
        decidir quais ações exibir (ex: proprietário vê editar/deletar,
        outros veem apenas arquivar).

        Args:
            user: Usuário autenticado da requisição.
            obj: Instância do modelo sendo enriquecida.

        Returns:
            Lista de dicionários de ação gerados por
            :func:`~common.utils.get_btn_action`.

        Raises:
            NotImplementedError: Deve ser implementado na view concreta.
        """
        raise NotImplementedError  # pragma: no cover

    def apply_enrichment(self, context: dict) -> dict:
        """Injeta ``ui_actions`` em cada objeto do contexto.

        Suporta o contexto de ``ListView`` (chave ``object_list``) e de
        ``DetailView`` (chave ``object``).

        Args:
            context: Dicionário de contexto do template.

        Returns:
            O mesmo dicionário com ``ui_actions`` adicionado em cada objeto.
        """
        user = cast(User, self.request.user)

        if "object_list" in context:
            for obj in context["object_list"]:
                obj.ui_actions = self.enrich_actions(user, obj)

        if obj := context.get("object"):
            obj.ui_actions = self.enrich_actions(user, obj)  # pragma: no cover

        return context


class ActionsMixin(EnrichObjectMixin):
    """Chama ``apply_enrichment`` automaticamente em ``get_context_data``.

    Combina com qualquer view que implemente ``EnrichObjectMixin``,
    eliminando a necessidade de chamar ``apply_enrichment`` manualmente.
    """

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)  # type: ignore[misc]
        return self.apply_enrichment(context)


class ObjectAccessRequiredMixin:
    """Garante que o usuário tem acesso ao objeto antes de processar a view.

    Chama ``get_object()`` no ``dispatch`` e delega a decisão de acesso
    para ``has_object_access()``, levantando ``PermissionDenied`` (HTTP 403)
    em caso de falha.

    As subclasses devem implementar ``has_object_access``.
    """

    def has_object_access(self, user: User, obj: Model) -> bool:
        """Verifica se o usuário tem acesso ao objeto.

        Args:
            user: Usuário autenticado da requisição.
            obj: Instância do modelo obtida por ``get_object()``.

        Returns:
            ``True`` se o acesso for permitido.

        Raises:
            NotImplementedError: Deve ser implementado na view concreta.
        """
        raise NotImplementedError  # pragma: no cover

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        """Verifica acesso ao objeto antes de despachar a requisição.

        Raises:
            PermissionDenied: Se ``has_object_access`` retornar ``False``.
        """
        obj = self.get_object()  # type: ignore[attr-defined]

        if not self.has_object_access(cast(User, request.user), obj):
            raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]


class PaginationMixin:
    """Adiciona paginação manual a views que não herdam de ``ListView``.

    Utilizado em views como ``DetailView`` + ``FormMixin`` que precisam
    paginar um queryset secundário (ex: lista de compartilhamentos).

    Attributes:
        paginate_by: Número de itens por página. Padrão: ``10``.
        page_param: Nome do parâmetro de página na query string. Padrão: ``'page'``.
    """
    paginate_by = 10
    page_param = 'page'
    request: HttpRequest

    def paginate_queryset(self, queryset: QuerySet) -> dict:
        """Pagina o queryset e retorna o contexto de paginação.

        Args:
            queryset: QuerySet a ser paginado.

        Returns:
            Dicionário com ``paginator``, ``page_obj``, ``object_list``
            e ``is_paginated``, compatível com os templates padrão do Django.
        """
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
    """Mixin para views com formulário secundário de relação um-para-muitos.

    Usado quando o modelo filho se relaciona via ForeignKey com um modelo
    intermediário, e as opções são gerenciadas por um inlineformset_factory.

    Exemplo de uso:
        MultipleChoiceExercise (OneToOne com Exercise) possui N ExerciseOption
        (ForeignKey com MultipleChoiceExercise) → gerenciado por formset.

    Deve ser combinado com CreateView ou UpdateView.

    Atributos:
        formset_class: Classe do formset gerada por inlineformset_factory.
        formset_context_name: Nome da variável no contexto do template.
        formset_model: Modelo pai do formset (ex: MultipleChoiceExercise).
        formset_prefix: Prefixo HTML dos campos do formset.
        formset_related_name: related_name do OneToOne em Exercise (ex: 'multiple_choice_exercise').
    """
    formset_class: type[BaseFormSet] | None = None
    formset_context_name: str = 'formset'
    formset_model: type[Model] | None = None
    formset_prefix: str = 'options'
    formset_related_name: str | None = None
    request: HttpRequest

    def get_formset(self, instance: Model | None = None) -> BaseFormSet:
        """Instancia o formset com ou sem dados do POST.

        Quando há POST, valida que os campos iniciais (ex: activity_list, type)
        não foram adulterados comparando com get_initial().

        Args:
            instance: Instância pai do formset (ex: MultipleChoiceExercise).

        Returns:
            Instância do formset configurado com prefix e dados.

        Raises:
            ImproperlyConfigured: Se formset_class ou formset_prefix não estiverem definidos.
            PermissionDenied: Se campos iniciais forem adulterados no POST.
        """
        if not self.formset_class or not self.formset_prefix:
            raise ImproperlyConfigured(  # pragma: no cover
                f"{self.__class__.__name__} precisa de 'formset_class' e 'formset_prefix'"
            )

        kwargs = {'prefix': self.formset_prefix, 'instance': instance}

        if self.request.POST:

            if hasattr(self, 'get_initial'):
                initial = self.get_initial()
                for key, value in initial.items():
                    if str(self.request.POST.get(key)) != str(value):
                        raise PermissionDenied

            kwargs['data'] = self.request.POST

        return self.formset_class(**kwargs)  # type: ignore[call-arg, arg-type]

    def get_context_data(self, **kwargs) -> dict:
        """Adiciona o formset ao contexto do template.

        Só instancia o formset se ainda não estiver no contexto,
        evitando sobrescrever um formset já passado (ex: em form_invalid).

        Returns:
            Dicionário de contexto com a chave definida em formset_context_name.
        """
        context = super().get_context_data(**kwargs)  # type: ignore[misc]

        if self.formset_context_name not in context:
            parent_instance = self.get_formset_parent_instance()
            context[self.formset_context_name] = self.get_formset(instance=parent_instance)

        return context

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        """Salva o formulário principal e o formset em uma transação atômica.

        Fluxo:
            1. Salva o Exercise (sem commit) para ter self.object.
            2. Obtém a instância pai do formset.
            3. Valida o formset com os dados do POST.
            4. Se válido: salva tudo atomicamente.
            5. Se inválido: retorna form_invalid com o formset com erros.

        params:
            form: Formulário principal (ExerciseForm) já validado.

        Returns:
            HttpResponse de sucesso (render_success) ou de erro (form_invalid).
        """
        self.object = form.save(commit=False)

        parent_instance = self.get_formset_parent_instance()

        formset = self.get_formset(instance=parent_instance)

        if formset.is_valid():
            with transaction.atomic():
                self.object.save()
                self.save_parent_instance(parent_instance)
                formset.save()  # type: ignore[attr-defined]

            return self.render_success()

        return self.form_invalid(form)

    def form_invalid(self, form: BaseModelForm) -> HttpResponse:
        """Retorna a resposta de erro com formulário e formset no contexto.

        Args:
            form: Formulário principal com erros.

        Returns:
            HttpResponse renderizado com o contexto de erro.
        """
        context = self.get_context_data(form=form)
        return self.render_to_response(context)  # type: ignore[attr-defined]

    def get_formset_parent_instance(self) -> Model:
        """Retorna a instância pai do formset (ex: MultipleChoiceExercise).

        Tenta buscar via related_name em self.object. Se não existir ainda
        (criação), retorna uma nova instância não salva do modelo pai.

        Returns:
            Instância existente ou nova do formset_model.

        Raises:
            ImproperlyConfigured: Se formset_related_name ou formset_model não estiverem definidos.
        """
        if not self.formset_related_name or not self.formset_model:
            raise ImproperlyConfigured(  # pragma: no cover
                f"{self.__class__.__name__} precisa de 'formset_related_name' e 'formset_model'"
            )

        try:
            return getattr(self.object, self.formset_related_name)
        except (AttributeError, self.formset_model.DoesNotExist):  # type: ignore[attr-defined]
            return self.formset_model(exercise=self.object)

    def save_parent_instance(self, instance: Model) -> None:
        """Salva a instância pai do formset.

        Necessário para garantir que o formset tenha uma chave estrangeira
        válida antes de salvar os itens filhos.

        Args:
            instance: Instância pai (ex: MultipleChoiceExercise) a ser salva.
        """
        instance.save()

    def render_success(self) -> HttpResponse:  # pragma: no cover
        """Retorna a resposta após salvar com sucesso.

        Deve ser sobrescrito nas views para retornar o HTML correto
        (ex: partial HTMX, redirect, etc.).

        Returns:
            HttpResponse de sucesso.
        """
        pass


class SecondaryFormMixin:
    """Mixin para views com formulário secundário de relação um-para-um.

    Usado quando o modelo relacionado se conecta via OneToOneField ao modelo
    principal (Exercise), sendo gerenciado por um ModelForm simples.

    Diferença do InlineFormsetMixin:
    - InlineFormsetMixin: um-para-muitos (ForeignKey + inlineformset_factory)
    - SecondaryFormMixin: um-para-um (OneToOneField + ModelForm)

    Exemplo de uso:
        CodeExercise (OneToOne com Exercise) → gerenciado por CodeExerciseForm.

    Deve ser combinado com CreateView ou UpdateView.

    Atributos:
        secondary_form_class: Classe do formulário secundário (ModelForm).
        secondary_form_context_name: Nome da variável no contexto do template.
        secondary_form_model: Modelo do formulário secundário (ex: CodeExercise).
        secondary_form_prefix: Prefixo HTML dos campos do formulário secundário.
        secondary_form_related_name: related_name do OneToOne em Exercise (ex: 'code_exercise').
    """
    secondary_form_class = None
    secondary_form_context_name = 'secondary_form'
    secondary_form_model = None
    secondary_form_prefix = 'secondary'
    secondary_form_related_name = None

    def get_secondary_instance(self) -> Model:
        """Retorna a instância OneToOne existente ou uma nova (sem salvar).

        Tenta buscar via related_name em self.object. Se não existir ainda
        (criação), retorna uma nova instância não salva do modelo secundário.

        Returns:
            Instância existente ou nova do secondary_form_model.

        Raises:
            ImproperlyConfigured: Se secondary_form_related_name ou secondary_form_model
                não estiverem definidos.
        """
        if not self.secondary_form_related_name or not self.secondary_form_model:
            raise ImproperlyConfigured(  # pragma: no cover
                f"{self.__class__.__name__} precisa de 'secondary_form_related_name' e 'secondary_form_model'"
            )

        try:
            return getattr(self.object, self.secondary_form_related_name)
        except (AttributeError, self.secondary_form_model.DoesNotExist):
            return self.secondary_form_model(exercise=self.object)

    def get_secondary_form(self, instance: Model | None = None) -> BaseModelForm:
        """Instancia o formulário secundário com ou sem dados do POST.

        Quando há POST, valida que os campos iniciais (ex: activity_list, type)
        não foram adulterados comparando com get_initial().

        Args:
            instance: Instância do modelo secundário (ex: CodeExercise).

        Returns:
            Instância do formulário configurado com prefix e dados.

        Raises:
            ImproperlyConfigured: Se secondary_form_class ou secondary_form_prefix
                não estiverem definidos.
            PermissionDenied: Se campos iniciais forem adulterados no POST.
        """
        if not self.secondary_form_class or not self.secondary_form_prefix:
            raise ImproperlyConfigured(  # pragma: no cover
                f"{self.__class__.__name__} precisa de 'secondary_form_class' e 'secondary_form_prefix'"
            )

        kwargs = {'prefix': self.secondary_form_prefix, 'instance': instance}

        if self.request.POST:

            if hasattr(self, 'get_initial'):
                initial = self.get_initial()
                for key, value in initial.items():
                    if str(self.request.POST.get(key)) != str(value):
                        raise PermissionDenied

            kwargs['data'] = self.request.POST

        return self.secondary_form_class(**kwargs)

    def get_context_data(self, **kwargs) -> dict:
        """Adiciona o formulário secundário ao contexto do template.

        Só instancia o formulário se ainda não estiver no contexto,
        evitando sobrescrever um formulário já passado (ex: em form_invalid).

        Returns:
            Dicionário de contexto com a chave definida em secondary_form_context_name.
        """
        context = super().get_context_data(**kwargs)  # type: ignore[misc]
        if self.secondary_form_context_name not in context:
            secondary_instance = self.get_secondary_instance()
            context[self.secondary_form_context_name] = self.get_secondary_form(
                instance=secondary_instance
            )
        return context

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        """Salva o formulário principal e o secundário em uma transação atômica.

        Fluxo:
            1. Obtém a instância secundária (existente ou nova).
            2. Instancia e valida o formulário secundário com os dados do POST.
            3. Se válido: salva tudo atomicamente e vincula exercise ao objeto salvo.
            4. Se inválido: retorna form_invalid com o formulário secundário com erros.

        Args:
            form: Formulário principal (ExerciseForm) já validado.

        Returns:
            HttpResponse de sucesso (render_success) ou de erro (form_invalid).
        """
        instance = self.get_secondary_instance()
        secondary_form = self.get_secondary_form(instance=instance)

        if secondary_form.is_valid():
            with transaction.atomic():
                self.object = form.save()
                secondary_obj = secondary_form.save(commit=False)
                secondary_obj.exercise = self.object
                secondary_obj.save()
            return self.render_success()

        return self.form_invalid(form, secondary_form=secondary_form)

    def form_invalid(self, form, secondary_form: BaseModelForm | None = None) -> HttpResponse:
        """Retorna a resposta de erro com ambos os formulários no contexto.

        Se o formulário secundário não for fornecido (ex: erro só no principal),
        instancia um novo com os dados do POST para preservar o que o usuário digitou.

        Args:
            form: Formulário principal com erros.
            secondary_form: Formulário secundário com erros (opcional).

        Returns:
            HttpResponse renderizado com o contexto de erro.
        """
        if secondary_form is None:
            secondary_instance = self.get_secondary_instance()
            secondary_form = self.get_secondary_form(instance=secondary_instance)
        context = self.get_context_data(
            form=form,
            **{self.secondary_form_context_name: secondary_form}
        )
        return self.render_to_response(context)  # type: ignore[attr-defined]

    def render_success(self) -> HttpResponse:  # pragma: no cover
        """Retorna a resposta após salvar com sucesso.

        Deve ser sobrescrito nas views para retornar o HTML correto
        (ex: partial HTMX, redirect, etc.).

        Returns:
            HttpResponse de sucesso.
        """
        pass

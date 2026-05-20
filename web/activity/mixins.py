from activity.constants import EXERCISE_TYPES
from activity.forms.exercise import ExerciseForm
from activity.models import ActivityList, Exercise
from common.mixins import HTMXLoginRequiredMixin, ObjectAccessRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import UpdateView


class ExerciseBaseMixin(HTMXLoginRequiredMixin, ObjectAccessRequiredMixin):
    """
    Mixin base para views de criação e atualização de exercícios.

    Centraliza a lógica compartilhada entre todos os tipos de exercício
    (múltipla escolha, código, completar código, etc.), como controle de
    acesso, detecção de criação/atualização, resolução do objeto e contexto.

    Deve ser combinado com CreateView ou UpdateView e com um mixin de formulário
    secundário (InlineFormsetMixin ou SecondaryFormMixin).

    Atributos:
        model: Modelo principal da view (Exercise).
        form_class: Formulário principal (ExerciseForm).
        update_url: Nome da URL de atualização usada no render_success.
        type_exercise: Tipo do exercício (ex: 'code', 'multiple_choice').
    """
    model = Exercise
    form_class = ExerciseForm
    update_url = None
    type_exercise = None

    @property
    def is_update(self) -> bool:
        """Retorna True se a view atual é uma instância de UpdateView."""
        return isinstance(self, UpdateView)

    def has_object_access(self, user: User, obj: Exercise | ActivityList) -> bool:
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
        if self.is_update:
            return obj.activity_list.created_by == user
        return False if not obj else obj.created_by == user
    
    def get_initial(self) -> dict:
        """
        Retorna os valores iniciais do formulário.

        Na criação, preenche automaticamente activity_list e type com base
        nos kwargs da URL e no atributo type_exercise.
        Na atualização, delega ao comportamento padrão do Django.

        Returns:
            Dicionário com os valores iniciais do formulário.

        Raises:
            ValueError: Se type_exercise não for um tipo válido.
            ImproperlyConfigured: Se type_exercise não estiver definido.
        """
        if self.is_update:
            return super().get_initial()
        
        if self.type_exercise not in dict(EXERCISE_TYPES):
            raise ValueError(f"Tipo de exercício inválido: {self.type_exercise}")
        
        if not self.type_exercise:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} precisa de 'type_exercise'"
            )

        pk = self.kwargs.get('pk')
        return {'activity_list': pk, 'type': self.type_exercise}

    def get_activity_list_id(self) -> int:
        """
        Retorna o ID da ActivityList associada ao exercício.

        Na criação, obtém o ID diretamente dos kwargs da URL.
        Na atualização, obtém o ID a partir do objeto Exercise.

        Returns:
            ID da ActivityList.
        """
        if self.is_update:
            if not hasattr(self, 'object'):
                self.object = self.get_object()
            return self.object.activity_list.id
        return self.kwargs.get('pk')

    def get_object(self) -> Exercise | ActivityList | None:
        """
        Retorna o objeto principal da view conforme o contexto.

        Na criação, retorna a ActivityList com base no pk da URL,
        garantindo que pertence ao usuário e não está deletada.
        Na atualização, retorna o Exercise com base no pk da URL,
        garantindo que pertence ao usuário e a ActivityList não está deletada.

        Returns:
            Instância de ActivityList (criação) ou Exercise (atualização),
            ou None se não encontrado.
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

    def get_context_data(self, **kwargs) -> dict:
        """
        Adiciona o ID da ActivityList ao contexto do template.

        Returns:
            Dicionário de contexto com a chave 'activity_list'.
        """
        context = super().get_context_data(**kwargs)
        context['activity_list'] = self.get_activity_list_id()
        return context

    def render_success(self) -> HttpResponse:
        """
        Renderiza a resposta de sucesso após salvar o formulário.

        Retorna o seletor de tipos de exercício via HTMX, com o exercício
        salvo e as informações necessárias para o template.

        Returns:
            HttpResponse com o partial HTML do seletor de exercícios.

        Raises:
            ImproperlyConfigured: Se update_url não estiver definido.
        """  
        if not self.update_url:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} precisa de 'update_url'"
            )

        return render(
            self.request,
            'activity/_exercise_type_selector.html',
            {
                'is_update': self.is_update,
                'exercise': self.object,
                'exercise_types': EXERCISE_TYPES,
                'activity_list_id': self.object.activity_list.id,
                'update_url': self.update_url,
            }
        )

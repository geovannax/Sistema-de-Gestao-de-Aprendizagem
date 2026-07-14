"""Modelos do app activity.

Define a estrutura de dados para listas de atividades e exercícios
polimórficos. Cada tipo de exercício possui um modelo OneToOne próprio
vinculado ao modelo base :class:`Exercise`.
"""
from __future__ import annotations

from activity.constants import EXERCISE_TYPE_CHOICES, LANGUAGE_CHOICES
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator, MinValueValidator
from django.db import models
from group.models import Group


class ActivityList(models.Model):
    """Lista de exercícios criada por um professor.

    Representa uma atividade publicável composta por um ou mais exercícios.
    Suporta soft delete via ``deleted_at``; todo queryset deve filtrar
    ``deleted_at__isnull=True``.

    Attributes:
        title: Título da atividade.
        description: Descrição e objetivos da atividade.
        created_by: Professor que criou a atividade.
        is_published: Indica se a atividade está visível para os alunos.
        max_attempts: Número máximo de tentativas permitidas por aluno.
            ``None`` significa sem limite.
        deleted_at: Preenchido no soft delete; ``None`` enquanto ativa.
    """
    title = models.CharField(
        max_length=200,
        verbose_name='Título',
        help_text='Dê um título claro e descritivo para a atividade, que reflita seu conteúdo e objetivo principal.'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Descrição',
        help_text='Descreva o objetivo da atividade, os tópicos abordados e quaisquer instruções importantes para os alunos.'
    )
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Criado por')
    is_published = models.BooleanField(default=False, db_index=True, verbose_name='Publicada')
    max_attempts = models.PositiveIntegerField(  # type: ignore[misc]
        null=True,
        blank=True,
        verbose_name='Máximo de Tentativas',
        help_text='Número máximo de tentativas que cada aluno pode realizar. Deixe em branco para tentativas ilimitadas.',
        validators=[MinValueValidator(1)],
    )
    manual_grading = models.BooleanField(
        default=False,
        verbose_name='Correção manual',
        help_text='Se marcado, a correção de todos os exercícios fica a cargo do professor. A autocorreção automática no envio é desativada.',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='Deletado em')  # type: ignore[misc]

    def __str__(self) -> str:
        return self.title

    class Meta:
        verbose_name = 'Lista de Exercícios'
        verbose_name_plural = 'Listas de Exercícios'


class ActivityArchived(models.Model):
    """Registro de arquivamento de uma atividade por um usuário.

    Permite que cada professor arquive atividades de forma independente,
    sem afetar outros usuários. O flag ``is_archived`` pode ser alternado
    via toggle.
    """
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='archived_activities')
    activity_list = models.ForeignKey(ActivityList, on_delete=models.CASCADE, related_name='archived_activities')
    is_archived = models.BooleanField(db_index=True, default=True, verbose_name='Arquivado')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Arquivado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['activity_list', 'user'],
                name='unique_activity_archived_user'
            )
        ]


class ActivityListGroup(models.Model):
    """Vínculo entre uma lista de atividades e uma turma.

    Registra o compartilhamento de uma atividade com uma turma com período
    de disponibilidade opcional. Quando ``starts_at`` ou ``ends_at`` estão
    definidos, o acesso do aluno é bloqueado fora desse intervalo pela view
    :class:`~student.views.StudentActivityView`.

    Attributes:
        activity_list: Lista de atividades vinculada.
        group: Turma que recebeu a atividade.
        assigned_at: Momento em que o vínculo foi criado.
        starts_at: Data/hora a partir da qual o aluno pode acessar a atividade.
            ``None`` significa sem restrição de início.
        ends_at: Prazo máximo para o aluno responder e submeter.
            ``None`` significa sem prazo. Igual a ``due_date``.
        due_date: Alias de ``ends_at`` mantido como atalho de consulta ORM.
    """
    activity_list = models.ForeignKey(ActivityList, on_delete=models.CASCADE, related_name='list_groups')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='activity_list_groups')
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name='Vinculado em')
    starts_at = models.DateTimeField(null=True, blank=True, verbose_name='Início')  # type: ignore[misc]
    ends_at = models.DateTimeField(null=True, blank=True, verbose_name='Fim')  # type: ignore[misc]
    due_date = models.DateTimeField(null=True, blank=True, verbose_name='Prazo')  # type: ignore[misc]

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['activity_list', 'group'], name='unique_activitylist_group')
        ]


class Exercise(models.Model):
    """Exercício base de uma lista de atividades.

    Armazena os dados comuns a todos os tipos de exercício. O conteúdo
    específico de cada tipo fica em um modelo relacionado via OneToOne:

    - ``code`` → :class:`CodeExercise`
    - ``complete_code`` → :class:`CompleteCodeExercise`
    - ``multiple_choice`` → :class:`MultipleChoiceExercise`
    - ``discursive`` → :class:`DiscursiveExercise`

    Attributes:
        activity_list: Lista à qual este exercício pertence.
        type: Tipo do exercício (chave de ``EXERCISE_TYPE_CHOICES``).
        statement: Enunciado do exercício.
        points: Pontuação na composição da atividade.
        order: Posição do exercício dentro da lista.
    """
    activity_list = models.ForeignKey(ActivityList, on_delete=models.CASCADE, related_name='exercises', verbose_name='Lista')
    type = models.CharField(
        max_length=20,
        choices=EXERCISE_TYPE_CHOICES,
        verbose_name='Tipo do Exercício',
        help_text='Selecione o tipo de exercício para definir a estrutura e os campos necessários para a criação.'
    )
    statement = models.TextField(
        verbose_name='Enunciado',
        help_text='Descreva o enunciado do exercício de forma clara e detalhada.',
        validators=[MinLengthValidator(10)]
    )
    points = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Nota',
        help_text='Informe quanto este exercício vale na composição da atividade.'
    )
    order = models.PositiveIntegerField(default=0, verbose_name='Ordem')
    is_annulled = models.BooleanField(default=False, verbose_name='Anulada')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'Exercício'
        verbose_name_plural = 'Exercícios'


class CodeExercise(models.Model):
    """Dados específicos de um exercício do tipo código."""
    exercise = models.OneToOneField(Exercise, on_delete=models.CASCADE, related_name='code_exercise')
    language = models.CharField(
        max_length=20,
        choices=LANGUAGE_CHOICES,
        verbose_name='Linguagem',
        help_text='Selecione a linguagem de programação para o exercício.'
    )
    max_executions = models.PositiveIntegerField(  # type: ignore[misc]
        null=True,
        blank=True,
        verbose_name='Limite de execuções',
        help_text='Máximo de vezes que o aluno pode clicar em Executar. Deixe em branco para ilimitado.',
    )


class CodeTestCase(models.Model):
    """Caso de teste para exercício do tipo código.

    Cada caso define uma entrada e a saída esperada correspondente.
    Exibido ao aluno como especificação e usado pelo professor na correção.
    """
    exercise = models.ForeignKey(
        CodeExercise,
        on_delete=models.CASCADE,
        related_name='test_cases',
        verbose_name='Exercício',
    )
    input = models.TextField(
        blank=True,
        default='',
        verbose_name='Entrada',
        help_text='Valores de entrada para o programa (pode ser vazio se não houver entrada).',
    )
    expected_output = models.TextField(
        verbose_name='Saída esperada',
        help_text='Saída que o programa deve produzir para esta entrada.',
    )
    order = models.PositiveIntegerField(default=0, verbose_name='Ordem')

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Caso de Teste'
        verbose_name_plural = 'Casos de Teste'


class CompleteCodeExercise(models.Model):
    """Dados específicos de um exercício do tipo completar código.

    O aluno preenche as lacunas marcadas com ``___`` no ``starter_code``.
    O ``complete_code`` serve como gabarito; não deve conter ``___``.
    """
    exercise = models.OneToOneField(Exercise, on_delete=models.CASCADE, related_name='complete_code_exercise')
    language = models.CharField(
        max_length=20,
        choices=LANGUAGE_CHOICES,
        verbose_name='Linguagem',
        help_text='Selecione a linguagem de programação para o exercício.'
    )
    starter_code = models.TextField(
        verbose_name='Código Incompleto',
        help_text='Forneça o código inicial com lacunas. Cada lacuna deve ser marcada com exatamente três underlines: "___". Ex: x = ___'
    )
    complete_code = models.TextField(
        verbose_name='Código Completo (Gabarito)',
        help_text='Forneça o código completo que serve como gabarito para correção.'
    )


class MultipleChoiceExercise(models.Model):
    """Dados específicos de um exercício de múltipla escolha.

    As alternativas ficam em :class:`ExerciseOption` (FK via ``options``).
    A validação no formset garante que exatamente uma opção seja correta.
    """
    exercise = models.OneToOneField(Exercise, on_delete=models.CASCADE, related_name='multiple_choice_exercise')


class ExerciseOption(models.Model):
    """Alternativa de um exercício de múltipla escolha.

    Attributes:
        exercise: Exercício de múltipla escolha ao qual esta opção pertence.
        text: Texto da alternativa exibido ao aluno.
        is_correct: Indica se esta é a alternativa correta. Deve ser ``True``
            em exatamente uma opção por exercício.
    """
    exercise = models.ForeignKey(MultipleChoiceExercise, on_delete=models.CASCADE, related_name='options')
    text = models.TextField(verbose_name='Texto da Opção')
    is_correct = models.BooleanField(default=False, verbose_name='É Correta')

    class Meta:
        ordering = ['id']


class DiscursiveExercise(models.Model):
    """Dados específicos de um exercício discursivo.

    O aluno responde com texto livre. A resposta é validada por contagem
    de palavras entre ``min_words`` e ``max_words`` (quando definido).

    Attributes:
        min_words: Número mínimo de palavras exigido na resposta.
        max_words: Número máximo de palavras permitido (opcional).
    """
    exercise = models.OneToOneField(Exercise, on_delete=models.CASCADE, related_name='discursive_exercise')

    min_words = models.PositiveIntegerField(
        default=10,
        verbose_name='Mínimo de Palavras',
        help_text='Número mínimo de palavras que a resposta deve conter.'
    )

    max_words = models.PositiveIntegerField(  # type: ignore[misc]
        null=True,
        blank=True,
        verbose_name='Máximo de Palavras',
        help_text='Número máximo de palavras que a resposta pode conter (opcional).'
    )

    class Meta:
        verbose_name = 'Exercício Discursivo'
        verbose_name_plural = 'Exercícios Discursivos'

    def __str__(self) -> str:
        return f"Discursivo: {self.exercise.statement[:50]}"

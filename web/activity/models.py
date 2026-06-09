from activity.constants import EXERCISE_TYPE_CHOICES, LANGUAGE_CHOICES
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator, MinValueValidator
from group.models import Group


class ActivityList(models.Model):
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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='Deletado em')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Lista de Exercícios'
        verbose_name_plural = 'Listas de Exercícios'


class ActivityArchived(models.Model):
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
    activity_list = models.ForeignKey(ActivityList, on_delete=models.CASCADE, related_name='list_groups')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='activity_list_groups')
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name='Vinculado em')
    starts_at = models.DateTimeField(null=True, blank=True, verbose_name='Início')
    ends_at = models.DateTimeField(null=True, blank=True, verbose_name='Fim')
    due_date = models.DateTimeField(null=True, blank=True, verbose_name='Prazo')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['activity_list', 'group'], name='unique_activitylist_group')
        ]


class Exercise(models.Model):
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'Exercício'
        verbose_name_plural = 'Exercícios'


class CodeExercise(models.Model):
    exercise = models.OneToOneField(Exercise, on_delete=models.CASCADE, related_name='code_exercise')
    language = models.CharField(
        max_length=20,
        choices=LANGUAGE_CHOICES,
        verbose_name='Linguagem',
        help_text='Selecione a linguagem de programação para o exercício.'
    )
    expected_output = models.TextField(
        validators=[MinLengthValidator(5)],
        verbose_name='Output Esperado',
        help_text='Forneça a saída esperada para o exercício.'
    )


class CompleteCodeExercise(models.Model):
    exercise = models.OneToOneField(Exercise, on_delete=models.CASCADE, related_name='complete_code_exercise')
    language = models.CharField(
        max_length=20,
        choices=LANGUAGE_CHOICES,
        verbose_name='Linguagem',
        help_text='Selecione a linguagem de programação para o exercício.'
    )
    starter_code = models.TextField(
        verbose_name='Código Incompleto',
        help_text='Forneça o código inicial com lacunas para o aluno completar. Use "___" para indicar as lacunas.'
    )
    complete_code = models.TextField(
        verbose_name='Código Completo (Gabarito)',
        help_text='Forneça o código completo que serve como gabarito para correção.'
    )


class MultipleChoiceExercise(models.Model):
    exercise = models.OneToOneField(Exercise, on_delete=models.CASCADE, related_name='multiple_choice_exercise')


class ExerciseOption(models.Model):
    exercise = models.ForeignKey(MultipleChoiceExercise, on_delete=models.CASCADE, related_name='options')
    text = models.TextField(verbose_name='Texto da Opção')
    is_correct = models.BooleanField(default=False, verbose_name='É Correta')

    class Meta:
        ordering = ['id']


class DiscursiveExercise(models.Model):
    exercise = models.OneToOneField(Exercise, on_delete=models.CASCADE, related_name='discursive_exercise')
    
    min_words = models.PositiveIntegerField(
        default=10,
        verbose_name='Mínimo de Palavras',
        help_text='Número mínimo de palavras que a resposta deve conter.'
    )
    
    max_words = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Máximo de Palavras',
        help_text='Número máximo de palavras que a resposta pode conter (opcional).'
    )

    class Meta:
        verbose_name = 'Exercício Discursivo'
        verbose_name_plural = 'Exercícios Discursivos'

    def __str__(self):
        return f"Discursivo: {self.exercise.statement[:50]}"


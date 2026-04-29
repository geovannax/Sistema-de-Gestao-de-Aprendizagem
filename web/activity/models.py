from activity.constants import EXERCISE_TYPE_CHOICES, LANGUAGE_CHOICES
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
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


class ActivityListGroup(models.Model):
    activity_list = models.ForeignKey(ActivityList, on_delete=models.CASCADE, related_name='list_groups')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='activity_list_groups')
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name='Vinculado em')
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
    order = models.PositiveIntegerField(default=0, verbose_name='Ordem')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'Exercício'
        verbose_name_plural = 'Exercícios'


class CodeExercise(models.Model):
    exercise = models.OneToOneField(Exercise, on_delete=models.CASCADE, related_name='code_exercise')
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, verbose_name='Linguagem')
    starter_code = models.TextField(blank=True, verbose_name='Código Inicial')
    expected_output = models.TextField(verbose_name='Output Esperado')


class CompleteCodeExercise(models.Model):
    exercise = models.OneToOneField(Exercise, on_delete=models.CASCADE, related_name='complete_code_exercise')
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, verbose_name='Linguagem')
    starter_code = models.TextField(verbose_name='Código Incompleto')
    complete_code = models.TextField(verbose_name='Código Completo (Gabarito)')


class MultipleChoiceExercise(models.Model):
    exercise = models.OneToOneField(Exercise, on_delete=models.CASCADE, related_name='multiple_choice_exercise')


class ExerciseOption(models.Model):
    exercise = models.ForeignKey(MultipleChoiceExercise, on_delete=models.CASCADE, related_name='options')
    text = models.TextField(verbose_name='Texto da Opção')
    is_correct = models.BooleanField(default=False, verbose_name='É Correta')

    class Meta:
        ordering = ['id']


"""Modelos do app student."""
from __future__ import annotations

from activity.models import ActivityListGroup, Exercise, ExerciseOption
from django.contrib.auth.models import User
from django.db import models


class Submission(models.Model):
    """Tentativa de um aluno em uma atividade vinculada a uma turma.

    Criada automaticamente ao acessar a atividade. ``attempt_number``
    incrementa a cada nova tentativa (quando ``max_attempts`` permite).
    ``submitted_at`` é ``None`` enquanto editável; preenchido na entrega
    final, após a qual a tentativa passa a ser somente leitura.

    Attributes:
        student: Aluno que realizou a tentativa.
        activity_link: Vínculo atividade↔turma ao qual a tentativa pertence.
        attempt_number: Número sequencial da tentativa do aluno (começa em 1).
        started_at: Momento em que a tentativa foi criada.
        submitted_at: Momento da entrega final; ``None`` enquanto em andamento.
        student_feedback: Comentário opcional do aluno após a entrega.
        teacher_comment: Comentário geral do professor sobre a tentativa.
    """

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    activity_link = models.ForeignKey(ActivityListGroup, on_delete=models.CASCADE, related_name='submissions')
    attempt_number = models.PositiveIntegerField(default=1, verbose_name='Tentativa')
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='Iniciado em')
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name='Submetido em')
    is_abandoned = models.BooleanField(default=False, verbose_name='Abandonada')
    student_feedback = models.TextField(blank=True, default='', verbose_name='Feedback do aluno')
    teacher_comment = models.TextField(blank=True, default='', verbose_name='Comentário do professor')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'activity_link', 'attempt_number'],
                name='unique_student_activity_attempt',
            )
        ]
        ordering = ['-attempt_number']
        verbose_name = 'Submissão'
        verbose_name_plural = 'Submissões'

    def __str__(self) -> str:
        return f"{self.student.username} — {self.activity_link.activity_list.title}"


class ExerciseAnswer(models.Model):
    """Resposta de um aluno a um exercício dentro de uma submissão.

    Para ``MULTIPLE_CHOICE``, ``selected_option`` armazena a alternativa
    escolhida e ``is_correct`` é preenchido automaticamente na submissão.
    Para os demais tipos, ``answer_text`` contém a resposta e
    ``is_correct`` permanece ``None`` até revisão manual.

    ``answered_at`` usa ``auto_now=True`` — atualizado a cada edição.
    """

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='answers')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='student_answers')
    answer_text = models.TextField(blank=True, default='', verbose_name='Resposta')
    selected_option = models.ForeignKey(
        ExerciseOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Opção selecionada',
    )
    is_correct = models.BooleanField(null=True, verbose_name='Correta')
    answered_at = models.DateTimeField(auto_now=True, verbose_name='Respondido em')
    student_observation = models.TextField(blank=True, default='', verbose_name='Observação do aluno')
    teacher_comment = models.TextField(blank=True, default='', verbose_name='Comentário do professor')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['submission', 'exercise'],
                name='unique_submission_exercise_answer',
            )
        ]
        verbose_name = 'Resposta'
        verbose_name_plural = 'Respostas'

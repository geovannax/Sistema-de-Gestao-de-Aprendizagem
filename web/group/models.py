"""Modelos do app group.

Define turmas (``Group``), seus mecanismos de compartilhamento entre
professores (``GroupSharing``), matrícula de alunos (``GroupStudent``) e
convites por token (``GroupInvite``). Todos os grupos suportam soft delete
via ``deleted_at``.
"""
from __future__ import annotations

import secrets
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone


def generate_group_invite_token() -> str:
    """Gera um token URL-safe criptograficamente seguro para convites.

    Returns:
        String de 43 caracteres URL-safe gerada com ``secrets.token_urlsafe``.
    """
    return secrets.token_urlsafe(32)


class Group(models.Model):
    """Turma criada por um professor.

    Suporta soft delete via ``deleted_at``; todo queryset deve filtrar
    ``deleted_at__isnull=True``. O par ``(name, created_by)`` é único
    entre turmas ativas (constraint condicional no banco).

    Attributes:
        name: Nome identificador da turma (ex: "ADS 2026.3.12").
        description: Objetivos e informações relevantes para os alunos.
        shift: Turno principal (Manhã, Tarde, Noite ou Integral).
        created_by: Professor responsável pela turma.
        deleted_at: Preenchido no soft delete; ``None`` enquanto ativa.
    """
    name = models.CharField(
        max_length=100,
        verbose_name='Nome da Turma',
        help_text='Digite um nome para identificar esta turma'
    )
    description = models.TextField(
        verbose_name='Descrição',
        help_text='Descreva objetivos, metodologia e informações importantes.',
        validators=[MinLengthValidator(10)]
    )
    shift = models.CharField(
        max_length=10,
        verbose_name='Turno',
        choices=[
            ('Manhã', 'Manhã'),
            ('Tarde', 'Tarde'),
            ('Noite', 'Noite'),
            ('Integral', 'Integral'),
        ],
        help_text='Horário principal da turma'
    )
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Criado por')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='Deletado em')

    def __str__(self) -> str:
        return self.name

    @property
    def active_sharings_count(self) -> int:
        """Retorna o número de compartilhamentos ativos desta turma."""
        return self.sharings.filter(is_active=True).count()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'created_by'],
                condition=models.Q(deleted_at__isnull=True),
                name='unique_group_name_created_by'
            )
        ]


class GroupArchived(models.Model):
    """Registro de arquivamento de uma turma por um usuário.

    Permite que cada professor arquive turmas de forma independente,
    sem afetar outros usuários. O flag ``is_archived`` pode ser alternado
    via toggle, inclusive para turmas compartilhadas.
    """
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='archived_users')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='archived_groups')
    is_archived = models.BooleanField(db_index=True, default=True, verbose_name='Arquivado')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Arquivado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'user'],
                name='unique_group_archived_user'
            )
        ]


class GroupSharing(models.Model):
    """Compartilhamento de uma turma entre professores.

    Quando ``is_active=False`` o compartilhamento está desativado mas o
    registro é mantido no banco para histórico.
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='sharings')
    shared_with = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='shared_group', verbose_name='Compartilhado com')
    shared_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='shared_by_me', verbose_name='Compartilhado por')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Compartilhado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    is_active = models.BooleanField(db_index=True, default=True, verbose_name='Está Ativo')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'shared_with'],
                name='unique_group_sharing_with'
            )
        ]


class GroupStudent(models.Model):
    """Matrícula de um aluno em uma turma.

    ``is_active=False`` representa uma matrícula desativada; o aluno
    pode ser reativado sem criar um novo registro.
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='students')
    student = models.ForeignKey(User, on_delete=models.PROTECT, related_name='student_groups')
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='Entrou em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    is_active = models.BooleanField(db_index=True, default=True, verbose_name='Esta ativo')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'student'],
                name='unique_group_student'
            )
        ]

    def __str__(self) -> str:
        return f'{self.student} - {self.group}'


class GroupInvite(models.Model):
    """Convite por token para matrícula de alunos em uma turma.

    O token é gerado automaticamente via :func:`generate_group_invite_token`.
    Quando não informado, ``expires_at`` é definido como 7 dias a partir
    da criação. Convites expirados ou com ``is_active=False`` não podem
    ser utilizados.
    """
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='invites')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_group_invites')
    token = models.CharField(max_length=128, unique=True, default=generate_group_invite_token)
    expires_at = models.DateTimeField(verbose_name='Expira em')
    max_uses = models.PositiveIntegerField(null=True, blank=True, verbose_name='Limite de usos')
    used_count = models.PositiveIntegerField(default=0, verbose_name='Usos')
    is_active = models.BooleanField(db_index=True, default=True, verbose_name='Esta ativo')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs) -> None:
        """Define ``expires_at`` para 7 dias no futuro se não informado."""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)

        super().save(*args, **kwargs)

    def is_expired(self) -> bool:
        """Retorna ``True`` se o convite já passou da data de expiração."""
        return self.expires_at <= timezone.now()

    def has_uses_available(self) -> bool:
        """Retorna ``True`` se ainda há usos disponíveis ou sem limite definido."""
        return self.max_uses is None or self.used_count < self.max_uses

    def can_be_used(self) -> bool:
        """Verifica se o convite pode ser usado no momento atual.

        Returns:
            ``True`` apenas se o convite estiver ativo, não expirado, com
            usos disponíveis e a turma não estiver deletada.
        """
        return (
            self.is_active and
            not self.is_expired() and
            self.group.deleted_at is None and
            self.has_uses_available()
        )

    def __str__(self) -> str:
        return f'Convite para {self.group}'

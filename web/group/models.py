from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone
from datetime import timedelta
import secrets
# Create your models here.


def generate_group_invite_token():
    return secrets.token_urlsafe(32)


class Group(models.Model):
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

    def __str__(self):
        return self.name

    @property
    def active_sharings_count(self):
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

    def __str__(self):
        return f'{self.student} - {self.group}'


class GroupInvite(models.Model):
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

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)

        super().save(*args, **kwargs)

    def is_expired(self):
        return self.expires_at <= timezone.now()

    def has_uses_available(self):
        return self.max_uses is None or self.used_count < self.max_uses

    def can_be_used(self):
        return (
            self.is_active and
            not self.is_expired() and
            self.group.deleted_at is None and
            self.has_uses_available()
        )

    def __str__(self):
        return f'Convite para {self.group}'

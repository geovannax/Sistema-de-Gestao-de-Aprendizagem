from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.db import models
# Create your models here.


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

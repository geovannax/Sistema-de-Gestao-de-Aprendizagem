from __future__ import annotations

import random
from typing import Any

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError

from group.models import Group, GroupSharing


class Command(BaseCommand):  # pragma: no cover
    help = 'Criar usuários de teste'

    def handle(self, *args: Any, **options: Any) -> None:
        self.create_users()
        self.create_groups()
        self.clear_groups_sharing()

    def create_users(self) -> None:
        password = make_password('123Abc!')

        first_names = [
            'Ana', 'Bruno', 'Carlos', 'Diana', 'Eduardo', 'Fernanda',
            'Gabriel', 'Helena', 'Igor', 'Joana', 'Kevin', 'Lúcia',
            'Marcos', 'Natália', 'Otávio', 'Patricia', 'Quintino', 'Rafael'
        ]

        last_names = [
            'Silva', 'Santos', 'Oliveira', 'Souza', 'Costa', 'Ferreira',
            'Gomes', 'Martins', 'Pereira', 'Carvalho', 'Barbosa', 'Ribeiro',
            'Alves', 'Rocha', 'Mendes', 'Campos', 'Neves', 'Monteiro'
        ]

        for i in range(1, 15):
            user, created = User.objects.update_or_create(
                email=f'prof{i}@educatrix.dev',
                defaults={
                    'username': f'prof{i}',
                    'first_name': random.choice(first_names),
                    'last_name': random.choice(last_names),
                    'password': password,
                }
            )
            if created:
                msg = self.style.SUCCESS(f'✓ Usuário criado: prof{i}')
            else:
                msg = self.style.WARNING(f'✓ Usuário atualizado: prof{i}')

            self.stdout.write(msg)

    def create_groups(self) -> None:
        created_by = User.objects.last()

        COURSES = [
            ('ADS', 'Análise e Desenvolvimento de Sistemas'),
            ('ES', 'Engenharia de Software'),
            ('DSI', 'Desenvolvimento de Sistemas para Internet'),
            ('CC', 'Ciência da Computação'),
            ('IR', 'Infraestrutura de Redes'),
        ]

        for i in range(1, 15):
            abbr, course = random.choice(COURSES)

            group, created = Group.objects.update_or_create(
                name=f'{abbr} 2026.3.{i}',
                created_by=created_by,
                defaults={
                    'description': f'{course}.\n Turma: 3.{i} \n Ano: 2026',
                    'shift': random.choice(
                        ['Manhã', 'Tarde', 'Noite', 'Integral']
                    )
                }
            )
            if created:
                msg = self.style.SUCCESS(f'✓ Grupo criado: {abbr} 2026.3.{i}')
            else:
                msg = self.style.WARNING(f'✓ Grupo atualizado: {abbr} 2026.3.{i}')

            self.stdout.write(msg)

    def clear_groups_sharing(self) -> None:
        group = Group.objects.last()
        shared_by = User.objects.last()

        for i in range(1, 14):
            try:
                groupsharing = GroupSharing.objects.create(
                    group=group,
                    shared_with=User.objects.filter(pk=i).first(),
                    shared_by=shared_by
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Grupo compartilhado: {groupsharing.id}'
                    )
                )
            except IntegrityError:
                self.stdout.write(
                    self.style.WARNING(
                        f'Grupo já compartilhado com o usuário {i}!'
                    )
                )
                continue

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from group.models import Group, GroupSharing
from django.db.utils import IntegrityError


class Command(BaseCommand):
    help = 'Criar usuários de teste'

    def handle(self, *args, **options):
        self.create_users()
        self.create_groups()
        self.clear_groups_sharing()

    def create_users(self):
        
        for i in range(1, 15):
            users_data = {
                'email': f'prof{i}@educatrix.dev',
                'username': f'prof{i}',
                'password': '123Abc!',
                'first_name': f'Professor {i}',
                'last_name': 'Test',
                'is_staff': True,
                'is_superuser': True,
            }
                    
            email = users_data.pop('email')
            password = users_data.pop('password')
            
            # Verificar se usuário já existe
            if User.objects.filter(email=email).exists():
                self.stdout.write(
                    self.style.WARNING(f'Usuário {email} já existe!')
                )
                continue

            # Criar usuário
            user = User.objects.create_user(
                email=email,
                password=password,
                **users_data
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Usuário criado: {email}'
                )
            )

    def create_groups(self):

        for i in range(1, 15):
            name = f'IF ADS 2026.3.{i}'
            description = f'Analise e Desenvolvimento de Sistemas.\n Turma: 3.{i} \n Ano: 2026'
            
            # Verificar se grupo já existe
            if Group.objects.filter(name=name).exists():
                self.stdout.write(
                    self.style.WARNING(f'Grupo {name} já existe!')
                )
                continue

            # Criar grupo
            group = Group.objects.create(
                name=name,
                description=description,
                created_by=User.objects.first()
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Grupo criado: {name}'
                )
            )

    def clear_groups_sharing(self):

        for i in range(2, 15):
            try:
                # Criar grupo
                groupsharing = GroupSharing.objects.create(
                    group = Group.objects.last(),
                    shared_with = User.objects.filter(pk=i).first(),
                    shared_by = User.objects.first()
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


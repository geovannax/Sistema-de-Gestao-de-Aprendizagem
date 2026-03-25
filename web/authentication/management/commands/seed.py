from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Criar usuários de teste'

    def handle(self, *args, **options):
        # Dados de teste
        users_data = [
            {
                'email': 'prof@educatrix.dev',
                'username': 'prof',
                'password': '123Abc!',
                'first_name': 'Professor',
                'last_name': 'Test',
                'is_staff': True,
            }
        ]

        for user_data in users_data:
            email = user_data.pop('email')
            password = user_data.pop('password')
            
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
                **user_data
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Usuário criado: {email}'
                )
            )
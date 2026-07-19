from __future__ import annotations

import random
from datetime import timedelta
from typing import Any

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError
from django.utils import timezone

from activity.models import (
    ActivityList,
    ActivityListGroup,
    CodeExercise,
    CodeTestCase,
    CompleteCodeExercise,
    DiscursiveExercise,
    Exercise,
    ExerciseOption,
    MultipleChoiceExercise,
)
from group.models import Group, GroupSharing, GroupStudent


class Command(BaseCommand):  # pragma: no cover
    help = 'Criar usuários de teste'

    def handle(self, *args: Any, **options: Any) -> None:
        self.create_users()
        self.create_groups()
        self.clear_groups_sharing()
        self.create_algorithms_activity()
        self.create_beginner_activity_1()
        self.create_beginner_activity_2()
        self.create_students()

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
            user, created = User.objects.get_or_create(
                username=f'prof{i}',
                defaults={
                    'email': f'prof{i}@educatrix.dev',
                    'first_name': random.choice(first_names),
                    'last_name': random.choice(last_names),
                    'password': password,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Usuário criado: prof{i}'))
            else:
                self.stdout.write(self.style.WARNING(f'~ Usuário já existe: prof{i}'))

    def create_groups(self) -> None:
        created_by = User.objects.last()

        if Group.objects.filter(created_by=created_by, deleted_at__isnull=True).count() >= 14:
            self.stdout.write(self.style.WARNING('~ Grupos já existem, pulando criação.'))
            return

        COURSES = [
            ('ADS', 'Análise e Desenvolvimento de Sistemas'),
            ('ES', 'Engenharia de Software'),
            ('DSI', 'Desenvolvimento de Sistemas para Internet'),
            ('CC', 'Ciência da Computação'),
            ('IR', 'Infraestrutura de Redes'),
        ]

        for i in range(1, 15):
            abbr, course = random.choice(COURSES)
            group, created = Group.objects.get_or_create(
                name=f'{abbr} 2026.3.{i}',
                created_by=created_by,
                defaults={
                    'description': f'{course}.\n Turma: 3.{i} \n Ano: 2026',
                    'shift': random.choice(['Manhã', 'Tarde', 'Noite', 'Integral']),
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Grupo criado: {group.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'~ Grupo já existe: {group.name}'))

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

    def _link_to_all_groups(self, activity: ActivityList, prof14: User) -> None:
        now = timezone.now()
        date_scenarios = [
            (None,                      None),                       # sem início/fim
            (now,                       now + timedelta(days=30)),   # aberta agora
            (now - timedelta(days=31),  now - timedelta(days=1)),    # já vencida
            (now + timedelta(days=60),  now + timedelta(days=90)),   # ainda não abriu
        ]
        groups = Group.objects.filter(created_by=prof14, deleted_at__isnull=True)
        for i, group in enumerate(groups):
            starts, ends = date_scenarios[i % 4]
            _, linked = ActivityListGroup.objects.get_or_create(
                activity_list=activity,
                group=group,
                defaults={'starts_at': starts, 'ends_at': ends},
            )
            status = '✓' if linked else '~'
            self.stdout.write(self.style.SUCCESS(f'{status} Vinculado: {group.name}'))

    def create_algorithms_activity(self) -> None:
        prof14 = User.objects.get(username='prof14')

        activity, created = ActivityList.objects.get_or_create(
            title='Fundamentos de Algoritmos',
            created_by=prof14,
            defaults={
                'description': (
                    'Lista de exercícios sobre algoritmos clássicos: '
                    'análise de complexidade, busca, ordenação e estruturas de dados.'
                ),
                'is_published': True,
                'max_attempts': 3,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Lista criada: Fundamentos de Algoritmos'))
        else:
            self.stdout.write(self.style.WARNING('✓ Lista já existia: Fundamentos de Algoritmos'))

        if not Exercise.objects.filter(activity_list=activity).exists():
            self._create_discursive(activity)
            self._create_code(activity)
            self._create_complete_code(activity)
            self._create_multiple_choice(activity)

        self._link_to_all_groups(activity, prof14)

    def _create_discursive(self, activity: ActivityList) -> None:
        exercise = Exercise.objects.create(
            activity_list=activity,
            type='discursive',
            statement=(
                'Explique o conceito de complexidade de tempo em algoritmos. '
                'Compare as notações O(1), O(log n), O(n) e O(n²), '
                'apresentando exemplos práticos de algoritmos que se enquadram '
                'em cada caso e justificando quando cada complexidade é aceitável '
                'em aplicações reais.'
            ),
            points=25,
            order=1,
        )
        DiscursiveExercise.objects.create(exercise=exercise, min_words=50, max_words=400)
        self.stdout.write(self.style.SUCCESS('  ✓ Exercício discursivo criado'))

    def _create_code(self, activity: ActivityList) -> None:
        exercise = Exercise.objects.create(
            activity_list=activity,
            type='code',
            statement=(
                'Escreva um programa que leia dois números inteiros e imprima a soma deles.'
            ),
            points=25,
            order=2,
        )
        code_ex = CodeExercise.objects.create(
            exercise=exercise,
            language='python',
            max_executions=10,
        )
        CodeTestCase.objects.create(
            exercise=code_ex,
            input='2\n3',
            expected_output='5',
            order=1,
        )
        CodeTestCase.objects.create(
            exercise=code_ex,
            input='10\n20',
            expected_output='30',
            order=2,
        )
        self.stdout.write(self.style.SUCCESS('  ✓ Exercício de código criado'))

    def _create_complete_code(self, activity: ActivityList) -> None:
        exercise = Exercise.objects.create(
            activity_list=activity,
            type='complete_code',
            statement=(
                'Complete o código abaixo para que ele imprima a mensagem "Olá, Mundo!".'
            ),
            points=25,
            order=3,
        )
        CompleteCodeExercise.objects.create(
            exercise=exercise,
            language='python',
            starter_code='___(___)',
            complete_code='print("Olá, Mundo!")',
        )
        self.stdout.write(self.style.SUCCESS('  ✓ Exercício completar código criado'))

    def _create_multiple_choice(self, activity: ActivityList) -> None:
        exercise = Exercise.objects.create(
            activity_list=activity,
            type='multiple_choice',
            statement=(
                'Qual é a complexidade de tempo no pior caso do algoritmo Bubble Sort?'
            ),
            points=25,
            order=4,
        )
        mc = MultipleChoiceExercise.objects.create(exercise=exercise)
        options = [
            ('O(1) — tempo constante, independente do tamanho da entrada', False),
            ('O(n) — proporcional ao número de elementos', False),
            ('O(n log n) — igual ao Merge Sort e Quick Sort no caso médio', False),
            ('O(n²) — dois laços aninhados que percorrem a lista', True),
        ]
        for text, is_correct in options:
            ExerciseOption.objects.create(
                exercise=mc,
                text=text,
                is_correct=is_correct,
            )
        self.stdout.write(self.style.SUCCESS('  ✓ Exercício de múltipla escolha criado'))

    def create_beginner_activity_1(self) -> None:
        prof14 = User.objects.get(username='prof14')
        activity, created = ActivityList.objects.get_or_create(
            title='Programação para Iniciantes — Entrada e Saída',
            created_by=prof14,
            defaults={
                'description': 'Exercícios introdutórios sobre leitura de dados e exibição de resultados em Python.',
                'is_published': True,
                'max_attempts': 3,
            },
        )
        msg = '✓ Lista criada' if created else '~ Lista já existia'
        self.stdout.write(self.style.SUCCESS(f'{msg}: {activity.title}'))

        if not Exercise.objects.filter(activity_list=activity).exists():
            # Code
            ex = Exercise.objects.create(
                activity_list=activity, type='code',
                statement='Leia o nome do usuário e imprima "Olá, [nome]!".',
                points=34, order=1,
            )
            code = CodeExercise.objects.create(exercise=ex, language='python', max_executions=10)
            CodeTestCase.objects.create(exercise=code, input='Maria', expected_output='Olá, Maria!', order=1)
            CodeTestCase.objects.create(exercise=code, input='João', expected_output='Olá, João!', order=2)
            self.stdout.write(self.style.SUCCESS('  ✓ Code criado'))

            # Complete code
            ex2 = Exercise.objects.create(
                activity_list=activity, type='complete_code',
                statement='Complete o programa para calcular e imprimir o dobro de um número inteiro lido da entrada.',
                points=33, order=2,
            )
            CompleteCodeExercise.objects.create(
                exercise=ex2, language='python',
                starter_code='n = ___(input())\nprint(___ * 2)',
                complete_code='n = int(input())\nprint(n * 2)',
            )
            self.stdout.write(self.style.SUCCESS('  ✓ Complete code criado'))

            # Multiple choice
            ex3 = Exercise.objects.create(
                activity_list=activity, type='multiple_choice',
                statement='Qual função Python é usada para exibir texto na tela?',
                points=33, order=3,
            )
            mc = MultipleChoiceExercise.objects.create(exercise=ex3)
            for text, correct in [
                ('input()', False),
                ('print()', True),
                ('output()', False),
                ('show()', False),
            ]:
                ExerciseOption.objects.create(exercise=mc, text=text, is_correct=correct)
            self.stdout.write(self.style.SUCCESS('  ✓ Múltipla escolha criado'))

        self._link_to_all_groups(activity, prof14)

    def create_beginner_activity_2(self) -> None:
        prof14 = User.objects.get(username='prof14')
        activity, created = ActivityList.objects.get_or_create(
            title='Programação para Iniciantes — Condicionais',
            created_by=prof14,
            defaults={
                'description': 'Exercícios introdutórios sobre estruturas condicionais (if/elif/else) em Python.',
                'is_published': True,
                'max_attempts': 3,
            },
        )
        msg = '✓ Lista criada' if created else '~ Lista já existia'
        self.stdout.write(self.style.SUCCESS(f'{msg}: {activity.title}'))

        if not Exercise.objects.filter(activity_list=activity).exists():
            # Code
            ex = Exercise.objects.create(
                activity_list=activity, type='code',
                statement='Leia um número inteiro e imprima "par" se for par ou "impar" se for ímpar.',
                points=34, order=1,
            )
            code = CodeExercise.objects.create(exercise=ex, language='python', max_executions=10)
            CodeTestCase.objects.create(exercise=code, input='4', expected_output='par', order=1)
            CodeTestCase.objects.create(exercise=code, input='7', expected_output='impar', order=2)
            CodeTestCase.objects.create(exercise=code, input='0', expected_output='par', order=3)
            self.stdout.write(self.style.SUCCESS('  ✓ Code criado'))

            # Complete code
            ex2 = Exercise.objects.create(
                activity_list=activity, type='complete_code',
                statement='Complete o programa para classificar um número como positivo, negativo ou zero.',
                points=33, order=2,
            )
            CompleteCodeExercise.objects.create(
                exercise=ex2, language='python',
                starter_code=(
                    'n = int(input())\n'
                    'if n ___ 0:\n'
                    '    print("positivo")\n'
                    'elif n ___ 0:\n'
                    '    print("negativo")\n'
                    'else:\n'
                    '    print("zero")'
                ),
                complete_code=(
                    'n = int(input())\n'
                    'if n > 0:\n'
                    '    print("positivo")\n'
                    'elif n < 0:\n'
                    '    print("negativo")\n'
                    'else:\n'
                    '    print("zero")'
                ),
            )
            self.stdout.write(self.style.SUCCESS('  ✓ Complete code criado'))

            # Multiple choice
            ex3 = Exercise.objects.create(
                activity_list=activity, type='multiple_choice',
                statement='Qual operador é usado para verificar igualdade em Python?',
                points=33, order=3,
            )
            mc = MultipleChoiceExercise.objects.create(exercise=ex3)
            for text, correct in [
                ('= (atribuição)', False),
                ('== (comparação)', True),
                ('=== (idêntico)', False),
                ('!= (diferente)', False),
            ]:
                ExerciseOption.objects.create(exercise=mc, text=text, is_correct=correct)
            self.stdout.write(self.style.SUCCESS('  ✓ Múltipla escolha criado'))

        self._link_to_all_groups(activity, prof14)

    def create_students(self) -> None:
        password = make_password('123Abc!')
        prof14 = User.objects.get(username='prof14')
        groups = Group.objects.filter(created_by=prof14, deleted_at__isnull=True)

        students_data = [
            ('aluno1', 'Lucas',   'Ferreira', 'aluno1@educatrix.dev'),
            ('aluno2', 'Beatriz', 'Oliveira', 'aluno2@educatrix.dev'),
            ('aluno3', 'Rafael',  'Souza',    'aluno3@educatrix.dev'),
            ('aluno4', 'Camila',  'Santos',   'aluno4@educatrix.dev'),
            ('aluno5', 'Thiago',  'Costa',    'aluno5@educatrix.dev'),
        ]

        for username, first, last, email in students_data:
            student, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first,
                    'last_name': last,
                    'password': password,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Aluno criado: {username}'))
            else:
                self.stdout.write(self.style.WARNING(f'~ Aluno já existe: {username}'))

            for group in groups:
                _, enrolled = GroupStudent.objects.get_or_create(
                    group=group,
                    student=student,
                    defaults={'is_active': True},
                )
                status = '✓' if enrolled else '~'
                self.stdout.write(f'  {status} Matriculado em: {group.name}')

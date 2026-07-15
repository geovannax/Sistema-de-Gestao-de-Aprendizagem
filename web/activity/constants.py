"""Constantes de configuração e UI do app activity.

Define os tipos de exercício suportados, seus metadados de exibição (label,
ícone, cor, URLs de criação/edição) e as choices de linguagem de programação
usadas pelos modelos e formulários.
"""
from __future__ import annotations

EXERCISE_TYPES: dict[str, dict[str, str]] = {
    'discursive': {
        'label': 'Discursiva',
        'icon': 'bi-chat-left-text',
        'color': 'text-secondary',
        'description': 'Aluno responde com texto livre',
        'create_url': 'activity:discursive_exercise_create',
        'update_url': 'activity:discursive_exercise_update',
    },
    'code': {
        'label': 'Código',
        'icon': 'bi-code-slash',
        'color': 'text-primary',
        'description': 'Output do aluno é comparado com o esperado',
        'create_url': 'activity:code_exercise_create',
        'update_url': 'activity:code_exercise_update',
    },
    'complete_code': {
        'label': 'Completar Código',
        'icon': 'bi-pencil-square',
        'color': 'text-warning',
        'description': 'Aluno preenche lacunas no código dado',
        'create_url': 'activity:complete_code_exercise_create',
        'update_url': 'activity:complete_code_exercise_update',
    },
    'multiple_choice': {
        'label': 'Múltipla Escolha',
        'icon': 'bi-list-check',
        'color': 'text-success',
        'description': 'Aluno escolhe entre as alternativas',
        'create_url': 'activity:multiple_choice_exercise_create',
        'update_url': 'activity:multiple_choice_exercise_update',
    }
}

# Gerar choices para o banco de dados (apenas label)
EXERCISE_TYPE_CHOICES: list[tuple[str, str]] = [
    (key, data['label']) for key, data in EXERCISE_TYPES.items()
]

LANGUAGE_CHOICES: list[tuple[str, str]] = [
    ('python', 'Python'),
    ('javascript', 'JavaScript'),
    ('java', 'Java'),
    ('c', 'C'),
    ('cpp', 'C++'),
]

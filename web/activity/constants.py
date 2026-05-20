# Constantes de UI e configuração da aplicação activity

EXERCISE_TYPES = {
    'discursive': {
        'label': 'Discursiva',
        'icon': 'bi-chat-left-text',
        'color': 'text-secondary',
        'description': 'Aluno responde com texto livre',
        'create_url': 'activity:discursive_exercise_create'
    },
    'code': {
        'label': 'Código',
        'icon': 'bi-code-slash',
        'color': 'text-primary',
        'description': 'Output do aluno é comparado com o esperado',
        'create_url': 'activity:code_exercise_create'
    },
    'complete_code': {
        'label': 'Completar Código',
        'icon': 'bi-pencil-square',
        'color': 'text-warning',
        'description': 'Aluno preenche lacunas no código dado',
        'create_url': 'activity:complete_code_exercise_create'
    },
    'multiple_choice': {
        'label': 'Múltipla Escolha',
        'icon': 'bi-list-check',
        'color': 'text-success',
        'description': 'Aluno escolhe entre as alternativas',
        'create_url': 'activity:multiple_choice_exercise_create'
    }
}

# Gerar choices para o banco de dados (apenas label)
EXERCISE_TYPE_CHOICES = [
    (key, data['label']) for key, data in EXERCISE_TYPES.items()
]

LANGUAGE_CHOICES = [
    ('python', 'Python'),
    ('javascript', 'JavaScript'),
    ('java', 'Java'),
    ('c', 'C'),
    ('cpp', 'C++'),
]
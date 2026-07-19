from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from collections import defaultdict
from decimal import Decimal
from typing import Any

from activity.models import ActivityListGroup, Exercise, ExerciseOption
from common.mixins import AuthPermissionMixin, ObjectAccessRequiredMixin
from django.contrib.auth.models import User
from django.db.models import Case, Count, DecimalField, Sum, When
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.generic import DetailView, View
from group.models import Group, GroupSharing, GroupStudent
from student.models import CodeExecution, ExerciseAnswer, Submission


def _anon_id(student_pk: int, group_pk: int) -> str:
    return hashlib.sha256(f"student_{student_pk}_{group_pk}".encode()).hexdigest()[:12]


def _can_access_group(user: User, group: Group) -> bool:
    if group.created_by == user:
        return True
    return group.sharings.filter(shared_with=user, is_active=True).exists()


def _get_accessible_groups(user: User) -> tuple[list, list]:
    owned = list(Group.objects.filter(created_by=user, deleted_at__isnull=True).order_by('name'))
    shared_ids = GroupSharing.objects.filter(shared_with=user, is_active=True).values_list('group_id', flat=True)
    shared = list(Group.objects.filter(pk__in=shared_ids, deleted_at__isnull=True).order_by('name'))
    return owned, shared


def _resolve_scope(user: User, group_pks: list[str], activity_pks: list[str]):
    """
    Returns (groups, link_pks, error_response).

    - group_pks: list of Group PKs (empty = all accessible groups)
    - activity_pks: list of ActivityList PKs (empty = all activities in scope)
    - link_pks: list of ActivityListGroup PKs to filter, or None (= all in scope)
    """
    owned, shared = _get_accessible_groups(user)
    accessible_map = {g.pk: g for g in owned + shared}

    if not group_pks:
        groups = list(accessible_map.values())
    else:
        groups = [accessible_map[pk] for pk in
                  (int(s) for s in group_pks if s.isdigit())
                  if pk in accessible_map]

    if not activity_pks:
        return groups, None, None

    al_pks = [int(s) for s in activity_pks if s.isdigit()]
    group_ids = [g.pk for g in groups]
    links = list(
        ActivityListGroup.objects
        .filter(activity_list_id__in=al_pks, group_id__in=group_ids)
        .select_related('group')
    )

    seen: set = set()
    filtered_groups: list = []
    for lk in links:
        if lk.group_id not in seen:
            filtered_groups.append(lk.group)
            seen.add(lk.group_id)

    return filtered_groups, [lk.pk for lk in links], None


# ── Stats / row counts ────────────────────────────────────────────────────────

def _aggregate_stats(groups: list, link_pks: list | None = None) -> dict:
    if not groups:
        return {'students': 0, 'activities': 0, 'submissions': 0, 'answers': 0, 'executions': 0}

    group_ids = [g.pk for g in groups]

    if link_pks is not None:
        subs = Submission.objects.filter(
            activity_link_id__in=link_pks, submitted_at__isnull=False, is_abandoned=False
        )
        return {
            'students': GroupStudent.objects.filter(
                group_id__in=group_ids, is_active=True
            ).values('student_id').distinct().count(),
            'activities': len(link_pks),
            'submissions': subs.count(),
            'answers': ExerciseAnswer.objects.filter(submission__in=subs).count(),
            'executions': CodeExecution.objects.filter(submission__in=subs).count(),
        }

    subs = Submission.objects.filter(
        activity_link__group_id__in=group_ids, submitted_at__isnull=False, is_abandoned=False
    )
    return {
        'students': GroupStudent.objects.filter(
            group_id__in=group_ids, is_active=True
        ).values('student_id').distinct().count(),
        'activities': ActivityListGroup.objects.filter(
            group_id__in=group_ids, activity_list__deleted_at__isnull=True
        ).count(),
        'submissions': subs.count(),
        'answers': ExerciseAnswer.objects.filter(submission__in=subs).count(),
        'executions': CodeExecution.objects.filter(submission__in=subs).count(),
    }


def _build_row_counts(groups: list, link_pks: list | None = None) -> dict:
    if not groups:
        return {ds['key']: 0 for ds in DATASET_CATALOG}

    group_ids = [g.pk for g in groups]

    effective_link_pks = link_pks if link_pks is not None else list(
        ActivityListGroup.objects.filter(
            group_id__in=group_ids, activity_list__deleted_at__isnull=True
        ).values_list('pk', flat=True)
    )

    subs = Submission.objects.filter(
        activity_link_id__in=effective_link_pks, submitted_at__isnull=False, is_abandoned=False
    )
    sub_ids = list(subs.values_list('pk', flat=True))

    return {
        'groups': len(groups),
        'students': GroupStudent.objects.filter(group_id__in=group_ids, is_active=True).count(),
        'activities': len(effective_link_pks),
        'exercises': Exercise.objects.filter(
            activity_list__list_groups__pk__in=effective_link_pks,
            activity_list__deleted_at__isnull=True,
        ).distinct().count(),
        'options': ExerciseOption.objects.filter(
            exercise__exercise__activity_list__list_groups__pk__in=effective_link_pks,
            exercise__exercise__activity_list__deleted_at__isnull=True,
        ).distinct().count(),
        'submissions': subs.count(),
        'answers': ExerciseAnswer.objects.filter(submission_id__in=sub_ids).count(),
        'engagement': subs.values('student_id', 'activity_link_id').distinct().count(),
        'executions': CodeExecution.objects.filter(submission_id__in=sub_ids).count(),
        'code_journey': CodeExecution.objects.filter(
            submission_id__in=sub_ids,
            exercise__type__in=['code', 'complete_code'],
        ).count(),
        'all': None,
    }


DATASET_CATALOG = [
    {
        'key': 'groups', 'title': 'Turmas', 'icon': 'bi-building',
        'description': 'Metadados das turmas incluídas na exportação: nome, turno e data de criação.',
        'cols': 'group_id, name, shift, created_at',
        'modal_description': 'Tabela de dimensão das turmas. Use group_id para cruzar com todos os demais datasets.',
        'questions': [
            'Qual o nome e turno de cada turma?',
            'Quando a turma foi criada?',
        ],
        'columns': [
            {'name': 'group_id',   'type': 'int',      'description': 'ID interno da turma — chave primária usada em todos os datasets.'},
            {'name': 'name',       'type': 'str',      'description': 'Nome da turma (ex: "ADS 2026.3").'},
            {'name': 'shift',      'type': 'str',      'description': 'Turno principal: Manhã, Tarde, Noite ou Integral.'},
            {'name': 'created_at', 'type': 'datetime', 'description': 'Data e hora de criação da turma.'},
        ],
    },
    {
        'key': 'students', 'title': 'Alunos', 'icon': 'bi-people-fill',
        'description': 'Roster anonimizado: ID, data de matrícula e status.',
        'cols': 'group_id, student_anon_id, enrollment_date, is_active',
        'modal_description': 'Base para cruzar a identidade anônima com os demais datasets.',
        'questions': [
            'Quem está matriculado?',
            'Quando entrou na turma?',
            'O aluno ainda está ativo?',
        ],
        'columns': [
            {'name': 'group_id',        'type': 'int',    'description': 'ID interno da turma.'},
            {'name': 'student_anon_id', 'type': 'sha256', 'description': 'Identificador anônimo do aluno gerado por hash — consistente entre todos os datasets da mesma turma.'},
            {'name': 'enrollment_date', 'type': 'date',   'description': 'Data em que o aluno foi matriculado na turma.'},
            {'name': 'is_active',       'type': 'bool',   'description': 'Indica se o aluno ainda está ativo na turma.'},
        ],
    },
    {
        'key': 'activities', 'title': 'Atividades', 'icon': 'bi-journal-text',
        'description': 'Catálogo de atividades com janela de disponibilidade.',
        'cols': 'group_id, activity_id, title, exercise_count, max_points, max_attempts, starts_at, ends_at, assigned_at',
        'modal_description': 'Catálogo de atividades vinculadas a cada turma, com janela de disponibilidade e pontuação máxima.',
        'questions': [
            'Quais atividades foram atribuídas a cada turma?',
            'Qual a janela de disponibilidade (início e fim)?',
            'Quantos exercícios e qual a pontuação máxima?',
        ],
        'columns': [
            {'name': 'group_id',        'type': 'int',          'description': 'ID interno da turma.'},
            {'name': 'activity_id',     'type': 'int',          'description': 'ID da lista de atividades.'},
            {'name': 'title',           'type': 'str',          'description': 'Título da atividade.'},
            {'name': 'exercise_count',  'type': 'int',          'description': 'Quantidade de exercícios ativos (não anulados) na atividade.'},
            {'name': 'max_points',      'type': 'float',        'description': 'Soma dos pesos de todos os exercícios não anulados — pontuação máxima possível.'},
            {'name': 'max_attempts',    'type': 'int | null',   'description': 'Número máximo de tentativas permitidas. Null indica tentativas ilimitadas.'},
            {'name': 'starts_at',       'type': 'datetime | null', 'description': 'Início da janela de disponibilidade. Null significa disponível imediatamente.'},
            {'name': 'ends_at',         'type': 'datetime | null', 'description': 'Encerramento da janela de disponibilidade. Null significa sem prazo.'},
            {'name': 'assigned_at',     'type': 'datetime',     'description': 'Data e hora em que a atividade foi atribuída à turma.'},
        ],
    },
    {
        'key': 'exercises', 'title': 'Exercícios', 'icon': 'bi-list-ol',
        'description': 'Catálogo de exercícios: tipo, enunciado, peso e gabarito para complete_code.',
        'cols': 'exercise_id, activity_id, activity_title, type, order, points, is_annulled, statement, starter_code, complete_code',
        'modal_description': 'Estrutura de cada exercício com enunciado completo. Para complete_code inclui o código incompleto (starter_code) e o gabarito (complete_code). As alternativas de multiple_choice estão no dataset Alternativas.',
        'questions': [
            'Como cada atividade é composta?',
            'Qual o enunciado de cada questão?',
            'Qual o tipo de cada questão (código, múltipla escolha, discursivo, completar código)?',
            'Qual o peso e a ordem de cada questão?',
            'Quais exercícios foram anulados?',
        ],
        'columns': [
            {'name': 'exercise_id',    'type': 'int',        'description': 'ID do exercício.'},
            {'name': 'activity_id',    'type': 'int',        'description': 'ID da atividade à qual o exercício pertence.'},
            {'name': 'activity_title', 'type': 'str',        'description': 'Título da atividade.'},
            {'name': 'type',           'type': 'str',        'description': 'Tipo do exercício: code, complete_code, multiple_choice ou discursive.'},
            {'name': 'order',          'type': 'int',        'description': 'Posição do exercício dentro da atividade (começa em 1).'},
            {'name': 'points',         'type': 'float',      'description': 'Peso do exercício na pontuação total da atividade.'},
            {'name': 'is_annulled',    'type': 'bool',       'description': 'Indica se o exercício foi anulado — exercícios anulados são excluídos de todos os cálculos de pontuação.'},
            {'name': 'statement',      'type': 'str',        'description': 'Enunciado completo do exercício, presente em todos os tipos.'},
            {'name': 'starter_code',   'type': 'str | null', 'description': 'Código incompleto fornecido ao aluno — preenchido apenas para exercícios do tipo complete_code. As lacunas são marcadas com ___.'},
            {'name': 'complete_code',  'type': 'str | null', 'description': 'Gabarito do código — preenchido apenas para exercícios do tipo complete_code. Não é exibido ao aluno.'},
        ],
    },
    {
        'key': 'options', 'title': 'Alternativas', 'icon': 'bi-ui-radios',
        'description': 'Alternativas dos exercícios de múltipla escolha com gabarito.',
        'cols': 'exercise_id, activity_id, option_order, text, is_correct',
        'modal_description': 'Lista de alternativas de cada exercício de múltipla escolha com indicação da opção correta.',
        'questions': [
            'Quais eram as alternativas de cada questão?',
            'Qual alternativa era a correta?',
            'Como enriquecer as respostas dos alunos com o texto de cada opção?',
        ],
        'columns': [
            {'name': 'exercise_id',   'type': 'int',  'description': 'ID do exercício de múltipla escolha ao qual a alternativa pertence.'},
            {'name': 'activity_id',   'type': 'int',  'description': 'ID da atividade — chave de junção com exercises e submissions.'},
            {'name': 'option_order',  'type': 'int',  'description': 'Posição da alternativa dentro do exercício (começa em 1).'},
            {'name': 'text',          'type': 'str',  'description': 'Texto da alternativa exibido ao aluno.'},
            {'name': 'is_correct',    'type': 'bool', 'description': 'True para a alternativa correta. Exatamente uma alternativa por exercício é marcada como correta.'},
        ],
    },
    {
        'key': 'submissions', 'title': 'Submissões', 'icon': 'bi-send-fill',
        'description': 'Todas as tentativas finalizadas: pontuação, percentual e timestamps.',
        'cols': 'submission_id, student_anon_id, activity_id, group_id, attempt_number, started_at, submitted_at, total_earned, total_possible, pct_score',
        'modal_description': 'Registro de cada entrega finalizada com nota, número de tentativas e percentual de acerto.',
        'questions': [
            'Quem entregou a atividade?',
            'Quando entregou e com qual nota?',
            'Quantas tentativas o aluno fez antes de entregar?',
            'Qual o percentual de acerto por tentativa?',
        ],
        'columns': [
            {'name': 'submission_id',   'type': 'int',          'description': 'ID único da submissão.'},
            {'name': 'student_anon_id', 'type': 'sha256',       'description': 'Identificador anônimo do aluno — chave de junção com o dataset students.'},
            {'name': 'activity_id',     'type': 'int',          'description': 'ID da atividade submetida.'},
            {'name': 'group_id',        'type': 'int',          'description': 'ID da turma.'},
            {'name': 'attempt_number',  'type': 'int',          'description': 'Número sequencial da tentativa do aluno nesta atividade (começa em 1).'},
            {'name': 'started_at',      'type': 'datetime',     'description': 'Data e hora em que o aluno iniciou a tentativa.'},
            {'name': 'submitted_at',    'type': 'datetime | null', 'description': 'Data e hora da entrega final. Null indica tentativa ainda em aberto (não entregue).'},
            {'name': 'total_earned',    'type': 'float',        'description': 'Total de pontos obtidos nesta tentativa.'},
            {'name': 'total_possible',  'type': 'float',        'description': 'Pontuação máxima possível da atividade no momento da submissão.'},
            {'name': 'pct_score',       'type': 'float',        'description': 'Percentual de acerto: (total_earned / total_possible) × 100.'},
        ],
    },
    {
        'key': 'answers', 'title': 'Respostas por Exercício', 'icon': 'bi-check2-square',
        'description': 'Respostas individuais: acerto, pontos e tempo gasto.',
        'cols': 'answer_id, submission_id, student_anon_id, activity_id, exercise_id, exercise_type, exercise_order, exercise_points, is_correct, points_earned, time_spent_seconds, answered_at',
        'modal_description': 'Resposta por questão de cada submissão, com resultado de acerto e tempo gasto.',
        'questions': [
            'Quais questões o aluno errou ou acertou?',
            'Quanto tempo gastou em cada questão?',
            'Quais exercícios têm alta taxa de erro na turma?',
        ],
        'columns': [
            {'name': 'answer_id',        'type': 'int',          'description': 'ID único da resposta.'},
            {'name': 'submission_id',    'type': 'int',          'description': 'ID da submissão à qual esta resposta pertence.'},
            {'name': 'student_anon_id',  'type': 'sha256',       'description': 'Identificador anônimo do aluno.'},
            {'name': 'activity_id',      'type': 'int',          'description': 'ID da atividade.'},
            {'name': 'exercise_id',      'type': 'int',          'description': 'ID do exercício respondido — chave de junção com o dataset exercises.'},
            {'name': 'exercise_type',    'type': 'str',          'description': 'Tipo do exercício: code, complete_code, multiple_choice ou discursive.'},
            {'name': 'exercise_order',   'type': 'int',          'description': 'Posição do exercício na atividade.'},
            {'name': 'exercise_points',  'type': 'float',        'description': 'Peso máximo do exercício.'},
            {'name': 'is_correct',       'type': 'bool | null',  'description': 'Se a resposta está correta. Null para exercícios discursivos ainda não corrigidos pelo professor.'},
            {'name': 'points_earned',    'type': 'float',        'description': 'Pontos obtidos neste exercício.'},
            {'name': 'time_spent_seconds', 'type': 'int | null', 'description': 'Tempo em segundos entre a abertura e a gravação da resposta. Null se não rastreado.'},
            {'name': 'answered_at',      'type': 'datetime | null', 'description': 'Data e hora em que a resposta foi gravada.'},
        ],
    },
    {
        'key': 'engagement', 'title': 'Engajamento', 'icon': 'bi-activity',
        'description': 'Métricas agregadas por aluno/atividade: tentativas e acessos.',
        'cols': 'student_anon_id, activity_id, group_id, total_attempts, first_attempt_at, last_attempt_at, submitted_at, completed, total_earned, total_possible, pct_score',
        'modal_description': 'Visão agregada do comportamento do aluno por atividade: tentativas, datas e persistência.',
        'questions': [
            'O aluno começou a atividade mas não entregou?',
            'Quantas vezes tentou?',
            'Quando foi a primeira e a última tentativa?',
            'Como medir o comportamento e a persistência dos alunos?',
        ],
        'columns': [
            {'name': 'student_anon_id',  'type': 'sha256',       'description': 'Identificador anônimo do aluno.'},
            {'name': 'activity_id',      'type': 'int',          'description': 'ID da atividade.'},
            {'name': 'group_id',         'type': 'int',          'description': 'ID da turma.'},
            {'name': 'total_attempts',   'type': 'int',          'description': 'Total de tentativas iniciadas, incluindo as não entregues.'},
            {'name': 'first_attempt_at', 'type': 'datetime',     'description': 'Data e hora da primeira tentativa do aluno nesta atividade.'},
            {'name': 'last_attempt_at',  'type': 'datetime',     'description': 'Data e hora da tentativa mais recente.'},
            {'name': 'submitted_at',     'type': 'datetime | null', 'description': 'Data e hora da entrega final. Null indica que o aluno nunca entregou.'},
            {'name': 'completed',        'type': 'bool',         'description': 'True se o aluno entregou ao menos uma tentativa.'},
            {'name': 'total_earned',     'type': 'float | null', 'description': 'Melhor pontuação obtida entre todas as tentativas entregues. Null se nunca entregou.'},
            {'name': 'total_possible',   'type': 'float',        'description': 'Pontuação máxima possível da atividade.'},
            {'name': 'pct_score',        'type': 'float | null', 'description': 'Percentual de acerto da melhor tentativa. Null se nunca entregou.'},
        ],
    },
    {
        'key': 'executions', 'title': 'Execuções de Código', 'icon': 'bi-terminal-fill',
        'description': 'Cada clique em Executar: casos de teste corretos vs. total.',
        'cols': 'execution_id, submission_id, student_anon_id, exercise_id, created_at, correct_count, total_count, all_correct',
        'modal_description': 'Log de cada clique em Executar com o resultado dos casos de teste.',
        'questions': [
            'A cada clique em Executar, quantos casos de teste passaram?',
            'Quantas execuções foram necessárias até acertar tudo?',
            'Como traçar o processo de depuração do aluno?',
        ],
        'columns': [
            {'name': 'execution_id',   'type': 'int',      'description': 'ID único da execução.'},
            {'name': 'submission_id',  'type': 'int',      'description': 'ID da submissão durante a qual o código foi executado.'},
            {'name': 'student_anon_id','type': 'sha256',   'description': 'Identificador anônimo do aluno.'},
            {'name': 'exercise_id',    'type': 'int',      'description': 'ID do exercício de código executado — chave de junção com exercises.'},
            {'name': 'created_at',     'type': 'datetime', 'description': 'Data e hora do clique em Executar.'},
            {'name': 'correct_count',  'type': 'int',      'description': 'Quantidade de casos de teste que passaram nesta execução.'},
            {'name': 'total_count',    'type': 'int',      'description': 'Total de casos de teste do exercício.'},
            {'name': 'all_correct',    'type': 'bool',     'description': 'True se todos os casos de teste passaram (correct_count == total_count).'},
        ],
    },
    {
        'key': 'code_journey', 'title': 'Jornada de Código', 'icon': 'bi-code-slash',
        'description': 'Todas as execuções de CODE e COMPLETE_CODE em ordem cronológica, com o código enviado.',
        'cols': 'student_anon_id, group_id, activity_id, exercise_id, exercise_type, submission_id, attempt_number, execution_order, created_at, correct_count, total_count, all_correct, delta_correct, source_code',
        'modal_description': 'Narrativa completa da evolução do aluno em cada exercício de código — da primeira execução à última, com o código enviado em cada tentativa.',
        'questions': [
            'Como o código do aluno evoluiu ao longo das tentativas?',
            'Em quais execuções houve progresso ou regressão nos testes?',
            'Quantas execuções foram necessárias até resolver o exercício?',
            'Qual era o código do aluno em cada momento?',
        ],
        'columns': [
            {'name': 'student_anon_id',  'type': 'sha256',       'description': 'Identificador anônimo do aluno.'},
            {'name': 'group_id',         'type': 'int',          'description': 'ID da turma.'},
            {'name': 'activity_id',      'type': 'int',          'description': 'ID da atividade.'},
            {'name': 'exercise_id',      'type': 'int',          'description': 'ID do exercício de código.'},
            {'name': 'exercise_type',    'type': 'str',          'description': 'Tipo do exercício: code ou complete_code.'},
            {'name': 'submission_id',    'type': 'int',          'description': 'ID da submissão (tentativa) à qual esta execução pertence.'},
            {'name': 'attempt_number',   'type': 'int',          'description': 'Número da tentativa da atividade (começa em 1). Útil para identificar quando o aluno reiniciou.'},
            {'name': 'execution_order',  'type': 'int',          'description': 'Posição cronológica desta execução dentro do par (aluno, exercício), contando todas as tentativas. Começa em 1.'},
            {'name': 'created_at',       'type': 'datetime',     'description': 'Data e hora do clique em Executar.'},
            {'name': 'correct_count',    'type': 'int',          'description': 'Casos de teste que passaram nesta execução.'},
            {'name': 'total_count',      'type': 'int',          'description': 'Total de casos de teste do exercício.'},
            {'name': 'all_correct',      'type': 'bool',         'description': 'True se todos os casos de teste passaram.'},
            {'name': 'delta_correct',    'type': 'int | null',   'description': 'Variação de correct_count em relação à execução anterior. Null na primeira execução. Positivo = progresso, negativo = regressão.'},
            {'name': 'source_code',      'type': 'str',          'description': 'Código-fonte enviado pelo aluno nesta execução.'},
        ],
    },
    {
        'key': 'all', 'title': 'Todos os Datasets (ZIP)', 'icon': 'bi-file-zip-fill',
        'description': 'Baixa todos os CSVs em um único arquivo ZIP.',
        'cols': '',
        'modal_description': 'Exporta os 8 datasets em um único arquivo ZIP, pronto para importar em Python, R ou qualquer ferramenta de análise.',
        'questions': [],
        'columns': [],
    },
]


# ── List / filter ─────────────────────────────────────────────────────────────

class DatasetListView(AuthPermissionMixin, View):
    template_name = 'dataset/list.html'

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        owned, shared = _get_accessible_groups(request.user)
        return render(request, self.template_name, {
            'owned_groups': owned,
            'shared_groups': shared,
        })


# ── HTMX partials ─────────────────────────────────────────────────────────────

class DatasetActivitiesPartial(AuthPermissionMixin, View):
    """Returns <option> elements with unique ActivityList titles.

    Accepts group[] (multi). Empty group[] = all accessible groups.
    option value = ActivityList PK.
    """

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        user = request.user
        group_pks = request.GET.getlist('group')

        owned, shared = _get_accessible_groups(user)
        accessible_map = {g.pk: g for g in owned + shared}

        if not group_pks:
            group_ids = list(accessible_map.keys())
        else:
            group_ids = [pk for pk in (int(s) for s in group_pks if s.isdigit()) if pk in accessible_map]

        links = (
            ActivityListGroup.objects
            .filter(group_id__in=group_ids, activity_list__deleted_at__isnull=True)
            .select_related('activity_list')
            .order_by('activity_list__title')
        )
        seen: set = set()
        parts: list = []
        for lk in links:
            if lk.activity_list_id not in seen:
                seen.add(lk.activity_list_id)
                parts.append(f'<option value="{lk.activity_list_id}">{lk.activity_list.title}</option>')

        return HttpResponse('\n'.join(parts))


class DatasetPreviewPartial(AuthPermissionMixin, View):
    """Returns dataset cards HTML for the current group/activity filter."""

    template_name = 'dataset/partials/preview.html'

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        from urllib.parse import urlencode

        user = request.user
        group_pks = request.GET.getlist('group')
        activity_pks = request.GET.getlist('activity')

        groups, link_pks, err = _resolve_scope(user, group_pks, activity_pks)
        if err:
            return err

        row_counts = _build_row_counts(groups, link_pks)
        datasets = [dict(ds, rows=row_counts.get(ds['key'])) for ds in DATASET_CATALOG]

        download_qs = urlencode(
            [('group', pk) for pk in group_pks] + [('activity', pk) for pk in activity_pks]
        )

        return render(request, self.template_name, {
            'datasets': datasets,
            'download_qs': download_qs,
        })


# ── Per-group detail (accessed from group nav tab) ────────────────────────────

class DatasetGroupView(AuthPermissionMixin, ObjectAccessRequiredMixin, DetailView):
    model = Group
    template_name = 'dataset/group.html'

    def has_object_access(self, user: User, obj: Group) -> bool:
        return _can_access_group(user, obj)

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        groups = [self.object]
        stats = _aggregate_stats(groups)
        row_counts = _build_row_counts(groups)
        datasets = [dict(ds, rows=row_counts.get(ds['key'])) for ds in DATASET_CATALOG]
        context['stats'] = stats
        context['datasets'] = datasets
        return context


# ── Download ──────────────────────────────────────────────────────────────────

class DatasetDownloadView(AuthPermissionMixin, View):
    """Generates and returns a CSV or ZIP for the given scope."""

    def get(self, request: HttpRequest, ds_type: str, *args: Any, **kwargs: Any) -> HttpResponse:
        user = request.user
        group_pks = request.GET.getlist('group')
        activity_pks = request.GET.getlist('activity')

        groups, link_pks, err = _resolve_scope(user, group_pks, activity_pks)
        if err:
            return err

        g_label = '-'.join(group_pks) or 'all'
        a_label = '-'.join(activity_pks) or 'all'

        dl_token = request.GET.get('dl', '')

        if ds_type == 'all':
            response = self._download_zip(groups, link_pks, g_label, a_label)
        else:
            buf = self._build_csv(groups, link_pks, ds_type)
            if buf is None:
                return HttpResponse('Dataset inválido.', status=404)
            filename = f"{ds_type}_g{g_label}_a{a_label}.csv"
            response = HttpResponse(buf.getvalue(), content_type='text/csv; charset=utf-8-sig')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

        if dl_token:
            response.set_cookie(f'dl_{dl_token}', '1', max_age=60, samesite='Lax')
        return response

    def _build_csv(self, groups: list, link_pks, ds_type: str) -> io.StringIO | None:
        builders = {
            'groups': self._csv_groups,
            'students': self._csv_students,
            'activities': self._csv_activities,
            'exercises': self._csv_exercises,
            'options': self._csv_options,
            'submissions': self._csv_submissions,
            'answers': self._csv_answers,
            'engagement': self._csv_engagement,
            'executions': self._csv_executions,
            'code_journey': self._csv_code_journey,
        }
        fn = builders.get(ds_type)
        if fn is None:
            return None
        buf = io.StringIO()
        fn(groups, link_pks, csv.writer(buf))
        buf.seek(0)
        return buf

    def _download_zip(self, groups, link_pks, group_pk, activity_pk) -> HttpResponse:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for ds_type in ['groups', 'students', 'activities', 'exercises', 'options', 'submissions', 'answers', 'engagement', 'executions', 'code_journey']:
                buf = self._build_csv(groups, link_pks, ds_type)
                if buf:
                    zf.writestr(f'{ds_type}.csv', buf.read())
        zip_buf.seek(0)
        filename = f"dataset_g{group_pk}_a{activity_pk}.zip"
        response = HttpResponse(zip_buf.read(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    # ── CSV builders (groups = scope, link_pks = ALG pk filter or None) ───────

    def _csv_groups(self, groups: list, link_pks, writer) -> None:
        writer.writerow(['group_id', 'name', 'shift', 'created_at'])
        for group in groups:
            writer.writerow([
                group.pk,
                group.name,
                group.shift,
                group.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])

    def _csv_students(self, groups: list, link_pks, writer) -> None:
        writer.writerow(['group_id', 'student_anon_id', 'enrollment_date', 'is_active'])
        for group in groups:
            for gs in group.students.all().order_by('joined_at'):
                writer.writerow([
                    group.pk, _anon_id(gs.student_id, group.pk),
                    gs.joined_at.strftime('%Y-%m-%d %H:%M:%S'), gs.is_active,
                ])

    def _csv_activities(self, groups: list, link_pks, writer) -> None:
        writer.writerow(['group_id', 'activity_id', 'title', 'exercise_count', 'max_points', 'max_attempts', 'starts_at', 'ends_at', 'assigned_at'])
        group_ids = [g.pk for g in groups]
        qs = (
            ActivityListGroup.objects
            .filter(group_id__in=group_ids, activity_list__deleted_at__isnull=True)
            .select_related('activity_list')
            .order_by('group_id', 'assigned_at')
        )
        if link_pks is not None:
            qs = qs.filter(pk__in=link_pks)

        al_ids = list(qs.values_list('activity_list_id', flat=True))
        ex_count = {r['activity_list_id']: r['total'] for r in
                    Exercise.objects.filter(activity_list_id__in=al_ids)
                    .values('activity_list_id').annotate(total=Count('pk'))}
        max_pts = {r['activity_list_id']: float(r['s'] or 0) for r in
                   Exercise.objects.filter(activity_list_id__in=al_ids, is_annulled=False)
                   .values('activity_list_id').annotate(s=Sum('points', output_field=DecimalField()))}

        for lk in qs:
            al = lk.activity_list
            writer.writerow([
                lk.group_id, lk.pk, al.title,
                ex_count.get(al.pk, 0), max_pts.get(al.pk, 0), al.max_attempts or '',
                lk.starts_at.strftime('%Y-%m-%d %H:%M:%S') if lk.starts_at else '',
                lk.ends_at.strftime('%Y-%m-%d %H:%M:%S') if lk.ends_at else '',
                lk.assigned_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])

    def _csv_exercises(self, groups: list, link_pks, writer) -> None:
        writer.writerow(['exercise_id', 'activity_id', 'activity_title', 'type', 'order', 'points', 'is_annulled', 'statement', 'starter_code', 'complete_code'])
        group_ids = [g.pk for g in groups]
        qs = ActivityListGroup.objects.filter(
            group_id__in=group_ids, activity_list__deleted_at__isnull=True
        )
        if link_pks is not None:
            qs = qs.filter(pk__in=link_pks)
        link_map = {lk.activity_list_id: lk.pk for lk in qs}

        for ex in (Exercise.objects
                   .filter(activity_list_id__in=link_map)
                   .select_related('activity_list', 'complete_code_exercise')
                   .order_by('activity_list_id', 'order')):
            if ex.type == 'complete_code':
                cce = getattr(ex, 'complete_code_exercise', None)
                starter = cce.starter_code if cce else ''
                complete = cce.complete_code if cce else ''
            else:
                starter = ''
                complete = ''
            writer.writerow([
                ex.pk, link_map.get(ex.activity_list_id, ''), ex.activity_list.title,
                ex.type, ex.order, float(ex.points), ex.is_annulled,
                ex.statement, starter, complete,
            ])

    def _csv_options(self, groups: list, link_pks, writer) -> None:
        writer.writerow(['exercise_id', 'activity_id', 'option_order', 'text', 'is_correct'])
        group_ids = [g.pk for g in groups]
        qs = ActivityListGroup.objects.filter(
            group_id__in=group_ids, activity_list__deleted_at__isnull=True
        )
        if link_pks is not None:
            qs = qs.filter(pk__in=link_pks)
        link_map = {lk.activity_list_id: lk.pk for lk in qs}

        option_counters: dict = defaultdict(int)
        for opt in (ExerciseOption.objects
                    .filter(exercise__exercise__activity_list_id__in=link_map)
                    .select_related('exercise__exercise')
                    .order_by('exercise__exercise_id', 'id')):
            ex = opt.exercise.exercise
            option_counters[ex.pk] += 1
            writer.writerow([
                ex.pk,
                link_map.get(ex.activity_list_id, ''),
                option_counters[ex.pk],
                opt.text,
                opt.is_correct,
            ])

    def _csv_submissions(self, groups: list, link_pks, writer) -> None:
        writer.writerow(['submission_id', 'student_anon_id', 'activity_id', 'group_id', 'attempt_number', 'started_at', 'submitted_at', 'total_earned', 'total_possible', 'pct_score'])
        group_ids = [g.pk for g in groups]
        qs = (
            Submission.objects
            .filter(activity_link__group_id__in=group_ids, submitted_at__isnull=False, is_abandoned=False)
            .select_related('student', 'activity_link__group')
            .order_by('activity_link_id', 'student_id', 'attempt_number')
        )
        if link_pks is not None:
            qs = qs.filter(activity_link_id__in=link_pks)

        score_map = {
            s['submission_id']: s for s in
            ExerciseAnswer.objects
            .filter(submission_id__in=qs.values_list('pk', flat=True), exercise__is_annulled=False)
            .values('submission_id')
            .annotate(
                earned=Sum(Case(When(is_correct=True, then='exercise__points'), default=Decimal(0), output_field=DecimalField())),
                total=Sum('exercise__points', output_field=DecimalField()),
            )
        }

        for sub in qs:
            sc = score_map.get(sub.pk, {})
            earned = float(sc.get('earned') or 0)
            total = float(sc.get('total') or 0)
            writer.writerow([
                sub.pk, _anon_id(sub.student_id, sub.activity_link.group_id),
                sub.activity_link_id, sub.activity_link.group_id, sub.attempt_number,
                sub.started_at.strftime('%Y-%m-%d %H:%M:%S'),
                sub.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if sub.submitted_at else '',
                round(earned, 2), round(total, 2),
                round(earned / total * 100, 2) if total else 0,
            ])

    def _csv_answers(self, groups: list, link_pks, writer) -> None:
        writer.writerow(['answer_id', 'submission_id', 'student_anon_id', 'activity_id', 'exercise_id', 'exercise_type', 'exercise_order', 'exercise_points', 'is_correct', 'points_earned', 'time_spent_seconds', 'answered_at'])
        group_ids = [g.pk for g in groups]
        qs = (
            ExerciseAnswer.objects
            .filter(submission__activity_link__group_id__in=group_ids)
            .select_related('submission__student', 'submission__activity_link__group', 'exercise')
            .order_by('submission__activity_link_id', 'submission__student_id', 'exercise__order')
        )
        if link_pks is not None:
            qs = qs.filter(submission__activity_link_id__in=link_pks)

        for ans in qs:
            sub, ex = ans.submission, ans.exercise
            writer.writerow([
                ans.pk, sub.pk, _anon_id(sub.student_id, sub.activity_link.group_id),
                sub.activity_link_id, ex.pk, ex.type, ex.order, float(ex.points),
                '' if ans.is_correct is None else ans.is_correct,
                float(ex.points) if ans.is_correct else 0.0,
                ans.time_spent_seconds,
                ans.answered_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])

    def _csv_engagement(self, groups: list, link_pks, writer) -> None:
        writer.writerow(['student_anon_id', 'activity_id', 'group_id', 'total_attempts', 'first_attempt_at', 'last_attempt_at', 'submitted_at', 'completed', 'total_earned', 'total_possible', 'pct_score'])
        group_ids = [g.pk for g in groups]
        qs = (
            Submission.objects
            .filter(activity_link__group_id__in=group_ids, is_abandoned=False)
            .select_related('student', 'activity_link__group')
            .order_by('student_id', 'activity_link_id', 'attempt_number')
        )
        if link_pks is not None:
            qs = qs.filter(activity_link_id__in=link_pks)

        all_subs = list(qs)
        buckets: dict = defaultdict(list)
        for sub in all_subs:
            buckets[(sub.student_id, sub.activity_link_id)].append(sub)

        final_ids = [s.pk for s in all_subs if s.submitted_at]
        score_map = {
            s['submission_id']: s for s in
            ExerciseAnswer.objects
            .filter(submission_id__in=final_ids, exercise__is_annulled=False)
            .values('submission_id')
            .annotate(
                earned=Sum(Case(When(is_correct=True, then='exercise__points'), default=Decimal(0), output_field=DecimalField())),
                total=Sum('exercise__points', output_field=DecimalField()),
            )
        }

        for (student_id, link_id), slist in sorted(buckets.items()):
            final = next((s for s in slist if s.submitted_at), None)
            group_id = slist[0].activity_link.group_id
            sc = score_map.get(final.pk, {}) if final else {}
            earned = float(sc.get('earned') or 0)
            total = float(sc.get('total') or 0)
            writer.writerow([
                _anon_id(student_id, group_id), link_id, group_id, len(slist),
                slist[0].started_at.strftime('%Y-%m-%d %H:%M:%S'),
                slist[-1].started_at.strftime('%Y-%m-%d %H:%M:%S'),
                final.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if final and final.submitted_at else '',
                final is not None,
                round(earned, 2), round(total, 2),
                round(earned / total * 100, 2) if total else 0,
            ])

    def _csv_executions(self, groups: list, link_pks, writer) -> None:
        writer.writerow(['execution_id', 'submission_id', 'student_anon_id', 'exercise_id', 'created_at', 'correct_count', 'total_count', 'all_correct'])
        group_ids = [g.pk for g in groups]
        qs = (
            CodeExecution.objects
            .filter(submission__activity_link__group_id__in=group_ids)
            .select_related('submission__student', 'submission__activity_link__group', 'exercise')
            .order_by('submission__activity_link_id', 'submission__student_id', 'created_at')
        )
        if link_pks is not None:
            qs = qs.filter(submission__activity_link_id__in=link_pks)

        for ex in qs:
            sub = ex.submission
            writer.writerow([
                ex.pk, sub.pk, _anon_id(sub.student_id, sub.activity_link.group_id),
                ex.exercise_id, ex.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                ex.correct_count, ex.total_count, ex.all_correct,
            ])

    def _csv_code_journey(self, groups: list, link_pks, writer) -> None:
        writer.writerow([
            'student_anon_id', 'group_id', 'activity_id', 'exercise_id', 'exercise_type',
            'submission_id', 'attempt_number', 'execution_order',
            'created_at', 'correct_count', 'total_count', 'all_correct', 'delta_correct',
            'source_code',
        ])
        group_ids = [g.pk for g in groups]
        qs = (
            CodeExecution.objects
            .filter(
                submission__activity_link__group_id__in=group_ids,
                exercise__type__in=['code', 'complete_code'],
            )
            .select_related(
                'submission__student',
                'submission__activity_link__group',
                'submission__activity_link',
                'exercise',
            )
            .order_by('submission__student_id', 'exercise_id', 'created_at')
        )
        if link_pks is not None:
            qs = qs.filter(submission__activity_link_id__in=link_pks)

        exec_counters: dict = defaultdict(int)
        prev_correct: dict = {}

        for ex in qs:
            sub = ex.submission
            student_id = sub.student_id
            exercise_id = ex.exercise_id
            group_id = sub.activity_link.group_id
            key = (student_id, exercise_id)

            exec_counters[key] += 1
            exec_order = exec_counters[key]
            prev = prev_correct.get(key)
            delta = (ex.correct_count - prev) if prev is not None else ''
            prev_correct[key] = ex.correct_count

            writer.writerow([
                _anon_id(student_id, group_id),
                group_id,
                sub.activity_link_id,
                exercise_id,
                ex.exercise.type,
                sub.pk,
                sub.attempt_number,
                exec_order,
                ex.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                ex.correct_count,
                ex.total_count,
                ex.all_correct,
                delta,
                ex.source_code,
            ])

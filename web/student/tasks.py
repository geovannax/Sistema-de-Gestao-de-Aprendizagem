"""Tarefas Celery do app student.

Todas as tasks são registradas com ``max_retries=0`` — falhas são retornadas
como dicts ``{'error': ...}`` em vez de re-enfileiradas, pois erros de
compilação ou de lógica do aluno não se resolvem com retentativas.
"""
from __future__ import annotations

from typing import Any

from celery import shared_task


@shared_task(bind=True, max_retries=0, name='student.execute_code')
def execute_code_task(
    self: Any,
    submission_pk: int,
    exercise_pk: int,
    source_code: str,
) -> dict[str, Any]:
    """Executa o código do aluno contra os casos de teste e persiste o resultado.

    Delega a execução real para ``common.executor.execute_code``, cria um
    ``CodeExecution`` com os resultados e faz ``update_or_create`` no
    ``ExerciseAnswer`` correspondente.

    Falhas de compilação, linguagem não suportada ou erro do executor
    (``common.executor.ExecutorError`` e subclasses) também persistem um
    ``CodeExecution`` (com a mensagem de erro em ``results[0]['stderr']``) e
    marcam ``ExerciseAnswer.is_correct = False`` — sem isso, a submissão ficava
    presa em "Aguardando revisão" para sempre, já que exercícios do tipo
    ``code`` não têm correção manual na tela do professor.

    Para exercícios do tipo ``'complete_code'``, a correção é feita de forma
    síncrona via ``normalize_code`` sem subprocess — mas ainda assim persiste
    um ``CodeExecution`` a cada clique em Executar (resultado sintético de um
    único item, sem casos de teste reais), para alimentar a timeline de
    evolução na tela de correção do professor, igual ao tipo ``code``.
    ``ExerciseAnswer.is_correct`` não é tocado aqui — quem decide a nota final
    é ``StudentSubmitView._auto_grade``, que reavalia com base no texto
    efetivamente entregue.

    Args:
        submission_pk: PK da ``Submission`` do aluno.
        exercise_pk: PK do ``Exercise`` a ser executado.
        source_code: Código-fonte enviado pelo aluno.

    Returns:
        Dict de resultado bem-sucedido com as chaves:

        - ``results`` — lista de dicts por caso de teste (ver ``execute_code``).
        - ``all_correct`` — ``True`` se todos os casos passaram.
        - ``correct_count`` — número de casos corretos.
        - ``total_count`` — total de casos de teste.

        Ou dict de erro com a chave ``'error'`` contendo a mensagem de falha
        (erro de compilação, linguagem não suportada, tipo de exercício inválido
        ou exceção inesperada).

    Note:
        Nunca levanta exceções — qualquer falha é capturada e retornada como
        ``{'error': mensagem}``.
    """
    from activity.models import Exercise
    from common.executor import CompilationError, ExecutorError, execute_code
    from student.models import CodeExecution, ExerciseAnswer, Submission

    try:
        exercise = (
            Exercise.objects
            .select_related('code_exercise', 'complete_code_exercise')
            .prefetch_related('code_exercise__test_cases')
            .get(pk=exercise_pk)
        )
        submission = Submission.objects.get(pk=submission_pk)

        if exercise.type == 'code':
            code_exercise = exercise.code_exercise
            language: str = code_exercise.language
            test_cases: list[dict[str, Any]] = list(
                code_exercise.test_cases.order_by('order').values('input', 'expected_output')  # type: ignore[arg-type]
            )
            if not test_cases:
                return {'error': 'Este exercício não possui casos de teste cadastrados.'}

        elif exercise.type == 'complete_code':
            from activity.utils import normalize_code
            ccx = exercise.complete_code_exercise
            is_correct: bool = (
                normalize_code(source_code, ccx.language)
                == normalize_code(ccx.complete_code, ccx.language)
            )
            CodeExecution.objects.create(
                submission=submission,
                exercise=exercise,
                source_code=source_code,
                results=[{
                    'stdin': '',
                    'expected_output': '',
                    'stdout': '',
                    'stderr': '',
                    'is_correct': is_correct,
                    'status': 'correct' if is_correct else 'wrong_answer',
                }],
            )
            return {
                'complete_code': True,
                'is_correct': is_correct,
            }

        else:
            return {'error': 'Tipo de exercício não suporta execução.'}

        try:
            results: list[dict[str, Any]] = execute_code(language, source_code, test_cases)
        except ExecutorError as exc:
            error_message = (
                f'Erro de compilação:\n{exc.output}' if isinstance(exc, CompilationError) else str(exc)
            )
            CodeExecution.objects.create(
                submission=submission,
                exercise=exercise,
                source_code=source_code,
                results=[{
                    'stdin': '',
                    'expected_output': '',
                    'stdout': '',
                    'stderr': error_message,
                    'is_correct': False,
                    'status': 'execution_error',
                }],
            )
            ExerciseAnswer.objects.update_or_create(
                submission=submission,
                exercise=exercise,
                defaults={
                    'answer_text': source_code,
                    'is_correct': False,
                },
            )
            return {'error': error_message}

        execution = CodeExecution.objects.create(
            submission=submission,
            exercise=exercise,
            source_code=source_code,
            results=results,
        )

        ExerciseAnswer.objects.update_or_create(
            submission=submission,
            exercise=exercise,
            defaults={
                'answer_text': source_code,
                'is_correct': execution.all_correct,
            },
        )

        return {
            'results': results,
            'all_correct': execution.all_correct,
            'correct_count': execution.correct_count,
            'total_count': execution.total_count,
        }

    except Exception as exc:  # noqa: BLE001
        return {'error': f'Erro interno: {exc}'}

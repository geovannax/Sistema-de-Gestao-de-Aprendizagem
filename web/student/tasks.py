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

    Para exercícios do tipo ``'complete_code'``, a correção é feita de forma
    síncrona via ``normalize_code`` sem subprocess.

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
    from common.executor import (
        CompilationError,
        ExecutorError,
        LanguageNotSupportedError,
        execute_code,
    )
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
            return {
                'complete_code': True,
                'is_correct': is_correct,
            }

        else:
            return {'error': 'Tipo de exercício não suporta execução.'}

        try:
            results: list[dict[str, Any]] = execute_code(language, source_code, test_cases)
        except CompilationError as exc:
            return {'error': f'Erro de compilação:\n{exc.output}'}
        except LanguageNotSupportedError as exc:
            return {'error': str(exc)}
        except ExecutorError as exc:
            return {'error': str(exc)}

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

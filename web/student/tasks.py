"""Tarefas Celery do app student."""
from __future__ import annotations

from typing import Any

from celery import shared_task


@shared_task(bind=True, max_retries=0, name='student.execute_code')
def execute_code_task(
    self,
    submission_pk: int,
    exercise_pk: int,
    source_code: str,
) -> dict:
    """Executa o código do aluno contra os casos de teste e salva o resultado.

    Returns:
        Dict com 'results', 'all_correct', 'correct_count', 'total_count'
        ou 'error' em caso de falha.
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
            language = code_exercise.language
            test_cases: list[dict[str, Any]] = list(
                code_exercise.test_cases.order_by('order').values('input', 'expected_output')  # type: ignore[arg-type]
            )
            if not test_cases:
                return {'error': 'Este exercício não possui casos de teste cadastrados.'}

        elif exercise.type == 'complete_code':
            ccx = exercise.complete_code_exercise
            try:
                run_results = execute_code(ccx.language, source_code, [{'input': '', 'expected_output': ''}])
            except CompilationError as exc:
                return {'error': f'Erro de compilação:\n{exc.output}'}
            except LanguageNotSupportedError as exc:
                return {'error': str(exc)}
            except ExecutorError as exc:
                return {'error': str(exc)}
            r = run_results[0]
            return {
                'run_only': True,
                'stdout': r['stdout'],
                'stderr': r['stderr'],
                'status': r['status'],
            }

        else:
            return {'error': 'Tipo de exercício não suporta execução.'}

        try:
            results = execute_code(language, source_code, test_cases)
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

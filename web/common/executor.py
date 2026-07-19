"""Executor de código isolado: nobody + ulimit.

No Linux (container Docker com cap_add: NET_ADMIN): o processo filho roda
como usuário ``nobody`` (uid=65534) sem permissão de escrita no filesystem
e com limites de memória/CPU via ``resource.setrlimit``. O bloqueio de rede
é feito via iptables no startup do container (veja ``compose.yml``).

Em outros sistemas (Windows, macOS — dev local): executa sem isolamento
de usuário nem de recursos, apenas com timeout.

Attributes:
    NOBODY_UID: UID do usuário nobody (65534).
    NOBODY_GID: GID do usuário nobody (65534).
    MEMORY_LIMIT: Limite de memória virtual em bytes (2 GB).
    CPU_LIMIT: Limite de CPU em segundos (5).
    FILE_LIMIT: Limite de tamanho de arquivo de saída em bytes (1 MB).
    PROC_LIMIT: Número máximo de processos filhos (64).
    EXECUTION_TIMEOUT: Timeout wall-clock por caso de teste em segundos (10).
    LANGUAGE_CONFIG: Mapa de linguagem → configuração de execução.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

_IS_LINUX = sys.platform == 'linux'

NOBODY_UID = 65534
NOBODY_GID = 65534

MEMORY_LIMIT   = 2 * 1024 * 1024 * 1024  # 2 GB
CPU_LIMIT      = 5                         # segundos de CPU
FILE_LIMIT     = 1 * 1024 * 1024          # 1 MB por arquivo de saída
PROC_LIMIT     = 64                        # processos filhos máximos
EXECUTION_TIMEOUT = 10                     # wall-clock timeout (segundos)

ExecutionStatus = Literal['correct', 'wrong_answer', 'runtime_error', 'time_limit']


class ExecutionResult(dict[str, Any]):
    """Dict com o resultado de um único caso de teste.

    Chaves presentes: stdin, expected_output, stdout, stderr, is_correct e status.
    O campo status pode ser correct, wrong_answer, runtime_error ou time_limit.
    """


class TestCase(dict[str, str]):
    """Dict de caso de teste com ``input`` e ``expected_output``."""


LANGUAGE_CONFIG: dict[str, dict[str, Any]] = {
    'python': {
        'filename': 'solution.py',
        'run': [sys.executable, 'solution.py'],
        'compile': None,
    },
    'javascript': {
        'filename': 'solution.js',
        'run': ['node', '--jitless', '--no-warnings', '--max-old-space-size=64', 'solution.js'],
        'compile': None,
    },
    'java': {
        'filename': 'Main.java',
        'run': ['java', '-Xmx64m', '-Xms16m', '-XX:ReservedCodeCacheSize=32m',
                '-XX:CompressedClassSpaceSize=32m', '-XX:MaxMetaspaceSize=64m', '-cp', '.', 'Main'],
        'compile': ['javac', 'Main.java'],
    },
    'c': {
        'filename': 'solution.c',
        'run': ['./solution'],
        'compile': ['gcc', '-o', 'solution', 'solution.c', '-lm'],
    },
    'cpp': {
        'filename': 'solution.cpp',
        'run': ['./solution'],
        'compile': ['g++', '-o', 'solution', 'solution.cpp', '-lm'],
    },
}


class ExecutorError(Exception):
    """Erro base para falhas durante a execução de código do aluno."""


class LanguageNotSupportedError(ExecutorError):
    """Linguagem de programação não reconhecida em ``LANGUAGE_CONFIG``."""


class CompilationError(ExecutorError):
    """Falha na etapa de compilação (C, C++ ou Java).

    Attributes:
        output: Saída combinada de stderr/stdout do compilador.
    """

    def __init__(self, output: str) -> None:
        self.output = output
        super().__init__(output)


def _make_preexec(workdir: Path) -> Callable[[], None] | None:
    """Retorna ``preexec_fn`` que troca para nobody e aplica ulimits (Linux only).

    Args:
        workdir: Diretório de trabalho para o processo filho. O processo filho
            faz ``chdir`` para este diretório após aplicar os limites.

    Returns:
        Callable sem argumentos para uso em ``subprocess.Popen(preexec_fn=...)``,
        ou ``None`` quando não estiver rodando em Linux.
    """
    if not _IS_LINUX:
        return None

    import resource as _resource

    def preexec() -> None:
        try:
            os.setgroups([])       # type: ignore[attr-defined]
            os.setgid(NOBODY_GID)  # type: ignore[attr-defined]
            os.setuid(NOBODY_UID)  # type: ignore[attr-defined]
        except OSError:
            pass
        try:
            _resource.setrlimit(_resource.RLIMIT_AS,    (MEMORY_LIMIT, MEMORY_LIMIT))  # type: ignore[attr-defined]
            _resource.setrlimit(_resource.RLIMIT_CPU,   (CPU_LIMIT,    CPU_LIMIT))     # type: ignore[attr-defined]
            _resource.setrlimit(_resource.RLIMIT_FSIZE, (FILE_LIMIT,   FILE_LIMIT))    # type: ignore[attr-defined]
            _resource.setrlimit(_resource.RLIMIT_NPROC, (PROC_LIMIT,   PROC_LIMIT))    # type: ignore[attr-defined]
        except (OSError, ValueError):
            pass
        os.chdir(str(workdir))

    return preexec


def _normalize(text: str) -> str:
    """Remove espaços no fim de cada linha e linhas em branco no final.

    Args:
        text: Texto bruto da saída do processo.

    Returns:
        Texto com trailing whitespace por linha e linhas em branco finais removidos.

    Example:
        >>> _normalize('hello  \\nworld  \\n\\n')
        'hello\\nworld'
    """
    return '\n'.join(line.rstrip() for line in text.splitlines()).rstrip()


def execute_code(
    language: str,
    source_code: str,
    test_cases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Executa ``source_code`` contra cada caso de teste com isolamento de usuário.

    Cria um diretório temporário, escreve o código-fonte, compila quando necessário
    (C, C++, Java) e executa o binário/interpretador para cada caso de teste.
    No Linux, o processo filho roda como ``nobody`` com ulimits aplicados via
    ``_make_preexec``. O diretório temporário é removido ao final, mesmo em caso
    de exceção.

    Args:
        language: Chave em ``LANGUAGE_CONFIG`` — ``'python'``, ``'javascript'``,
            ``'java'``, ``'c'`` ou ``'cpp'``.
        source_code: Código-fonte enviado pelo aluno.
        test_cases: Lista de dicts com as chaves ``'input'`` e ``'expected_output'``.

    Returns:
        Lista de dicts — um por caso de teste — com as chaves:
        stdin, expected_output, stdout, stderr,
        is_correct e status.

    Raises:
        LanguageNotSupportedError: ``language`` não está em ``LANGUAGE_CONFIG``.
        CompilationError: A etapa de compilação falhou (C, C++ ou Java).
        ExecutorError: Erro genérico de execução não categorizado.

    Example:
        >>> results = execute_code('python', 'print("ok")', [{'input': '', 'expected_output': 'ok'}])
        >>> len(results)
        1
    """
    config = LANGUAGE_CONFIG.get(language)
    if config is None:
        raise LanguageNotSupportedError(f'Linguagem não suportada: {language}')

    workdir = Path(tempfile.mkdtemp(prefix='lms_exec_'))
    try:
        code_file = workdir / config['filename']
        code_file.write_text(source_code, encoding='utf-8')
        os.chmod(workdir, 0o755)
        os.chmod(code_file, 0o644)

        if config['compile']:
            result = subprocess.run(
                config['compile'],
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise CompilationError(result.stderr or result.stdout)
            for path in workdir.iterdir():
                if path.suffix not in ('.c', '.cpp', '.java', '.py', '.js'):
                    try:
                        os.chmod(path, 0o755)
                    except OSError:
                        pass

        preexec = _make_preexec(workdir)
        results: list[dict[str, Any]] = []

        for tc in test_cases:
            stdin_data: str = tc.get('input') or ''
            expected: str = _normalize(tc.get('expected_output') or '')

            try:
                proc = subprocess.run(
                    config['run'],
                    input=stdin_data,
                    capture_output=True,
                    text=True,
                    timeout=EXECUTION_TIMEOUT,
                    cwd=str(workdir),
                    preexec_fn=preexec,
                )
                stdout = _normalize(proc.stdout)
                stderr = proc.stderr.strip().replace(str(workdir) + '/', '')
                is_correct = stdout == expected
                if proc.returncode != 0:
                    status: ExecutionStatus = 'runtime_error'
                elif is_correct:
                    status = 'correct'
                else:
                    status = 'wrong_answer'
            except subprocess.TimeoutExpired:
                stdout = ''
                stderr = ''
                is_correct = False
                status = 'time_limit'

            results.append({
                'stdin': stdin_data,
                'expected_output': tc.get('expected_output') or '',
                'stdout': stdout,
                'stderr': stderr,
                'is_correct': is_correct,
                'status': status,
            })

        return results

    finally:
        shutil.rmtree(workdir, ignore_errors=True)

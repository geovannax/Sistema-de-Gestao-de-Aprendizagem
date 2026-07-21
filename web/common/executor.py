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
import re
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


# ---------------------------------------------------------------------------
# Prelúdios de supressão de prompt
#
# Textos de prompt (ex.: "Digite um número: ") escritos no stdout contaminam
# a comparação com expected_output e causam wrong_answer.  Cada prelúdio
# intercepta as primitivas de I/O da linguagem e descarta qualquer saída
# produzida ANTES do primeiro byte consumido do stdin.
#
# Estratégia por linguagem (mark-on-read):
#   Python      — substitui builtins.input por versão que descarta o argumento
#                 prompt e lê stdin diretamente.
#   JavaScript  — patcha readline.createInterface para output:null, silenciando
#                 rl.question() sem afetar stdout do programa.
#   C / C++ / Java — bufferizam TODO o output; a cada leitura de stdin marcam
#                 a posição atual do buffer (_BF em C, _f em C++, _lmsFrom em
#                 Java). No encerramento do programa, apenas buffer[marca:]
#                 é enviado ao stdout real — ou seja, somente o output
#                 produzido APÓS a ÚLTIMA leitura de stdin. Prompts antes de
#                 qualquer leitura (incluindo entre leituras consecutivas) são
#                 descartados. Caso não haja leitura de stdin (ex.: hello
#                 world), marca=0 e todo o output é preservado.
# ---------------------------------------------------------------------------

_PYTHON_PRELUDE = (
    'import sys as _sys, builtins as _bt\n'
    # _s=_sys captura o módulo por valor no momento da criação da lambda;
    # após `del _sys`, o nome some do namespace mas a lambda ainda acessa sys via _s.
    '_bt.input = lambda *_a, _s=_sys, **_kw: _s.stdin.readline().rstrip("\\n")\n'
    'del _sys, _bt\n'
)

# Patcha readline.createInterface para usar output:null, descartando prompts
# de rl.question() sem afetar a leitura do stdin nem o stdout do programa.
_JS_PRELUDE = (
    ';(function(){'
    'var _r=require("readline"),_c=_r.createInterface.bind(_r);'
    '_r.createInterface=function(opts){'
    'var o=opts&&typeof opts==="object"?Object.assign({},opts):{input:opts};'
    'o.output=null;'
    'return _c(o);'
    '};'
    '})();\n'
)

# Funções _lms_* são definidas ANTES das macros: dentro delas "printf" ainda
# é o símbolo real da libc (a macro não existe nesse ponto do texto-fonte).
#
# Estratégia mark-on-read: TODO o output vai para um buffer dinâmico.
# A cada leitura de stdin, _BF recebe o tamanho atual do buffer (marcando o
# início do output real). O destructor descarrega apenas buffer[_BF:].
# Se stdin nunca for lido: _BF=0 → tudo é descarregado (hello world funciona).
# Se há prompts entre várias leituras: _BF avança em cada read, descartando
# todos os prompts e mantendo apenas o output após a última leitura.
_C_PRELUDE = (
    '#include <stdio.h>\n'
    '#include <stdarg.h>\n'
    '#include <stdlib.h>\n'
    '#include <string.h>\n'
    'static char*_B=NULL;static size_t _BL=0,_BC=0,_BF=0;\n'
    'static void _ba(const char*s,size_t n){'
    'if(_BL+n>=_BC){_BC=_BC?_BC*2:256;while(_BC<_BL+n+1)_BC*=2;_B=realloc(_B,_BC);}'
    'memcpy(_B+_BL,s,n);_BL+=n;}\n'
    '__attribute__((destructor)) static void _lms_dtor(void){'
    'if(_B&&_BL>_BF){fwrite(_B+_BF,1,_BL-_BF,stdout);fflush(stdout);}free(_B);}\n'
    'static int _lms_printf(const char*f,...){'
    'va_list a;va_start(a,f);'
    'va_list b;va_copy(b,a);int n=vsnprintf(NULL,0,f,a);va_end(a);'
    'if(n>0){char*t=malloc((size_t)n+1);if(t){vsnprintf(t,(size_t)n+1,f,b);_ba(t,(size_t)n);free(t);}}'
    'va_end(b);return n;}\n'
    'static int _lms_puts(const char*s){size_t n=strlen(s);_ba(s,n);_ba("\\n",1);return(int)n+1;}\n'
    'static int _lms_putchar(int c){char ch=(char)c;_ba(&ch,1);return c;}\n'
    'static int _lms_scanf(const char*f,...){'
    '_BF=_BL;va_list a;va_start(a,f);int r=vscanf(f,a);va_end(a);return r;}\n'
    'static int _lms_getchar(void){_BF=_BL;return getchar();}\n'
    'static char*_lms_fgets(char*s,int n,FILE*f){if(f==stdin)_BF=_BL;return fgets(s,n,f);}\n'
    '#define printf(...) _lms_printf(__VA_ARGS__)\n'
    '#define puts(s) _lms_puts(s)\n'
    '#define putchar(c) _lms_putchar(c)\n'
    '#define scanf(...) _lms_scanf(__VA_ARGS__)\n'
    '#define getchar() _lms_getchar()\n'
    '#define fgets(s,n,f) _lms_fgets(s,n,f)\n'
)

# Mesma estratégia mark-on-read para C++: _LmsOut bufferiza todo o output;
# _LmsIn chama mark() a cada read, avançando _f (flush-from).
# Destructor de _LmsOut descarrega _b[_f:] no streambuf real do cout.
_CPP_PRELUDE = (
    '#include <iostream>\n'
    '#include <streambuf>\n'
    '#include <string>\n'
    'namespace{\n'
    'struct _LmsOut:std::streambuf{\n'
    '  std::streambuf*_r;std::string _b;size_t _f;\n'
    '  _LmsOut(std::streambuf*r):_r(r),_f(0){}\n'
    '  int overflow(int c)override{_b+=(char)c;return c;}\n'
    '  std::streamsize xsputn(const char*s,std::streamsize n)override{'
    '_b.append(s,n);return n;}\n'
    '  ~_LmsOut(){'
    'if(_f<_b.size())_r->sputn(_b.data()+_f,(std::streamsize)(_b.size()-_f));}\n'
    '  void mark(){_f=_b.size();}\n'
    '};\n'
    'struct _LmsIn:std::streambuf{\n'
    '  std::streambuf*_r;_LmsOut*_o;\n'
    '  _LmsIn(std::streambuf*r,_LmsOut*o):_r(r),_o(o){}\n'
    '  int underflow()override{_o->mark();return _r->sgetc();}\n'
    '  int uflow()override{_o->mark();return _r->sbumpc();}\n'
    '  std::streamsize xsgetn(char*s,std::streamsize n)override{'
    '_o->mark();return _r->sgetn(s,n);}\n'
    '};\n'
    'struct _LmsInit{\n'
    '  _LmsOut _ob;_LmsIn _ib;\n'
    '  _LmsInit():_ob(std::cout.rdbuf()),_ib(std::cin.rdbuf(),&_ob){\n'
    '    std::cout.rdbuf(&_ob);std::cin.rdbuf(&_ib);}\n'
    '}_lms_init;\n'
    '}\n'
)

# Mesma estratégia mark-on-read para Java:
# _lmsFrom[0] é atualizado para _lmsBuf.size() a cada read() de System.in.
# Shutdown hook descarrega _lmsBuf[_lmsFrom[0]:] no stdout real.
_JAVA_STATIC_BLOCK = (
    'static{'
    'final java.io.PrintStream _lmsOut=System.out;'
    'final java.io.ByteArrayOutputStream _lmsBuf=new java.io.ByteArrayOutputStream();'
    'final int[]_lmsFrom={0};'
    'Runtime.getRuntime().addShutdownHook(new Thread(()->{'
    'byte[]all=_lmsBuf.toByteArray();int from=_lmsFrom[0];'
    'if(from<all.length)try{_lmsOut.write(all,from,all.length-from);_lmsOut.flush();}catch(Exception ignored){}}));'
    'System.setIn(new java.io.FilterInputStream(System.in){'
    'public int read()throws java.io.IOException{_lmsFrom[0]=_lmsBuf.size();return super.read();}'
    'public int read(byte[]b,int o,int l)throws java.io.IOException{'
    '_lmsFrom[0]=_lmsBuf.size();return super.read(b,o,l);}});'
    'System.setOut(new java.io.PrintStream(new java.io.OutputStream(){'
    'public void write(int b)throws java.io.IOException{_lmsBuf.write(b);}'
    'public void write(byte[]b,int o,int l)throws java.io.IOException{_lmsBuf.write(b,o,l);}},true));'
    '}'
)

_PRELUDES: dict[str, str] = {
    'python': _PYTHON_PRELUDE,
    'javascript': _JS_PRELUDE,
    'c': _C_PRELUDE,
    'cpp': _CPP_PRELUDE,
}


def _inject_java_prelude(source: str) -> str:
    """Injeta ``_JAVA_STATIC_BLOCK`` dentro da classe Main do código Java.

    Localiza ``public class Main`` (seguido de qualquer coisa até ``{``) e
    insere o bloco estático logo após a chave de abertura da classe.  Quando
    o padrão não é encontrado (código malformado), devolve o código sem
    alteração.

    Args:
        source: Código-fonte Java enviado pelo aluno.

    Returns:
        Código-fonte com o bloco estático de supressão injetado, ou o
        original caso ``public class Main`` não seja encontrado.
    """
    pattern = r'(public\s+class\s+Main\b[^{]*\{)'
    injected, n = re.subn(pattern, r'\1\n' + _JAVA_STATIC_BLOCK, source, count=1)
    return injected if n else source

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
        # NODE_NO_WARNINGS suprime warnings do V8 gerados antes do sistema
        # de warnings do Node.js estar ativo (ex.: conflito --jitless/--expose_wasm).
        'env': {'NODE_NO_WARNINGS': '1'},
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


_JS_STDERR_NOISE = (
    'Warning: disabling flag',   # --expose_wasm vs --jitless no V8
)


def _filter_stderr(raw: str, language: str, workdir: Path) -> str:
    """Remove ruído interno do runtime do stderr antes de exibir ao aluno.

    Args:
        raw: Saída bruta de stderr do processo filho.
        language: Linguagem de programação executada.
        workdir: Diretório de trabalho — caminhos absolutos são removidos.

    Returns:
        stderr limpo, sem linhas que sejam avisos internos do runtime.
    """
    text = raw.strip().replace(str(workdir) + '/', '')
    if language == 'javascript':
        lines = [ln for ln in text.splitlines() if not any(ln.startswith(p) for p in _JS_STDERR_NOISE)]
        text = '\n'.join(lines).strip()
    return text


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
        if language == 'java':
            source_to_write = _inject_java_prelude(source_code)
        else:
            source_to_write = _PRELUDES.get(language, '') + source_code
        code_file.write_text(source_to_write, encoding='utf-8')
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
        lang_env = config.get('env')
        run_env = {**os.environ, **lang_env} if lang_env else None

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
                    env=run_env,
                )
                stdout = _normalize(proc.stdout)
                stderr = _filter_stderr(proc.stderr, language, workdir)
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

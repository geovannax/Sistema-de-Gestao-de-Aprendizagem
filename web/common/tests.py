import shutil
import sys
import pytest

# marca de integração: pulado no Windows/macOS, roda só no container Docker
integration = pytest.mark.skipif(
    sys.platform != 'linux',
    reason='requires gcc/g++ — execute via: docker compose exec web pytest common/tests.py -v -k Integration',
)

def _needs(*binaries):
    """Pula o teste se algum binário não estiver disponível no PATH."""
    missing = [b for b in binaries if shutil.which(b) is None]
    return pytest.mark.skipif(bool(missing), reason=f'binário(s) não encontrado(s): {missing}')
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, override_settings

from common.utils import get_btn_action


# ─── get_btn_action ─────────────────────────────────────────────────────────

class TestGetBtnAction:
    def test_returns_actions_for_valid_list(self):
        result = get_btn_action(['update', 'delete'], 'group')
        assert len(result) == 2
        assert result[0]['url'] == 'group:update'
        assert result[1]['url'] == 'group:delete'

    def test_raises_for_non_list(self):
        with pytest.raises(ValueError):
            get_btn_action('update', 'group')

    def test_returns_none_for_unknown_action(self):
        result = get_btn_action(['unknown_action'], 'group')
        assert result == [None]

    def test_all_action_keys(self):
        result = get_btn_action(['archive', 'delete', 'unshare', 'update', 'assign_update'], 'activity')
        assert len(result) == 5
        assert all(r is not None for r in result)


# ─── HomeView ───────────────────────────────────────────────────────────────
# Registrada tanto em '/' quanto em '/home/' — mesmo comportamento nas duas rotas.

@pytest.mark.django_db
class TestHomeView:
    def test_get_authenticated(self, authenticated_client):
        response = authenticated_client.get('/home/')
        assert response.status_code == 200

    def test_get_unauthenticated_redirects(self):
        response = Client().get('/home/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']

    def test_root_get_authenticated(self, authenticated_client):
        response = authenticated_client.get('/')
        assert response.status_code == 200

    def test_root_get_unauthenticated_redirects(self):
        response = Client().get('/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']


# ─── Error handlers ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestErrorHandlers:
    def test_permission_denied_403(self, authenticated_client, user):
        other = User.objects.create_user(username='owner_403', password='pass')
        from group.models import Group
        other_group = Group.objects.create(
            name='Outros', description='x' * 20, shift='Manhã', created_by=other
        )
        response = authenticated_client.get(f'/group/{other_group.pk}/update/')
        assert response.status_code == 403

    @override_settings(DEBUG=False)
    def test_page_not_found_404(self):
        response = Client().get('/pagina-que-nao-existe-jamais-99999/')
        assert response.status_code == 404


# ─── FilteringMixin / OrderingMixin unit tests ──────────────────────────────

class TestFilteringMixin:
    def test_apply_filtering_raises_when_not_configured(self):
        from common.mixins import FilteringMixin
        view = FilteringMixin()
        view.allowed_fields = None
        view.model = None
        with pytest.raises(ImproperlyConfigured):
            view.apply_filtering(queryset=None)


class TestOrderingMixin:
    def test_get_ordering_raises_when_not_configured(self):
        from common.mixins import OrderingMixin
        view = OrderingMixin()
        view.allowed_fields = None
        view.model = None
        with pytest.raises(ImproperlyConfigured):
            view.get_ordering()


# ─── HTMXLoginRequiredMixin ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestHTMXLoginRequiredMixin:
    def test_unauthenticated_htmx_returns_401(self):
        response = Client().post(
            '/activity/exercise/multiple-choice/add-option/',
            {'total_forms': '0'},
            HTTP_HX_REQUEST='true',
        )
        assert response.status_code == 401
        assert 'HX-Redirect' in response

    def test_unauthenticated_non_htmx_redirects(self):
        response = Client().get('/activity/exercise/cancel/1/')
        assert response.status_code == 302


# ─── OrderingMixin.apply_ordering with tuple result ─────────────────────────

class TestOrderingMixinApplyOrdering:
    def test_apply_ordering_with_tuple_calls_order_by_with_unpack(self):
        from common.mixins import OrderingMixin
        from unittest.mock import MagicMock
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.get('/?sort=name&order=asc')
        request.session = {}
        request._navigation = {}

        model = MagicMock()
        model._meta.app_label = 'test'

        class MockView(OrderingMixin):
            ordering = '-id'
            allowed_fields = ['name']

        view = MockView()
        view.model = model
        view.request = request

        ordering = view.get_ordering()
        assert isinstance(ordering, tuple)

        queryset = MagicMock()
        view.apply_ordering(queryset)
        queryset.order_by.assert_called_once()


# ─── Template tag tests ─────────────────────────────────────────────────────

class TestCommonTemplateTags:
    def test_get_attr_with_truncate_long_string(self):
        from common.templatetags.common_filters import get_attr_with_truncate

        class Obj:
            name = 'a' * 100

        result = get_attr_with_truncate(Obj(), 'name')
        assert result.endswith('...')
        assert len(result) <= 70

    def test_get_item_with_dict_key(self):
        from common.templatetags.common_filters import get_item
        result = get_item({'key': 'value'}, 'key')
        assert result == 'value'

    def test_get_item_with_object_attribute(self):
        from common.templatetags.common_filters import get_item

        class Obj:
            name = 'test'

        result = get_item(Obj(), 'name')
        assert result == 'test'

    def test_get_item_non_dict_no_attribute(self):
        from common.templatetags.common_filters import get_item
        result = get_item(object(), 'nonexistent_xyz')
        assert result == '-'


# ─── AuthPermissionMixin HTMX branch ────────────────────────────────────────

@pytest.mark.django_db
class TestAuthPermissionMixinHTMX:
    def test_unauthenticated_htmx_returns_401_with_redirect_header(self):
        response = Client().get('/group/active/', HTTP_HX_REQUEST='true')
        assert response.status_code == 401
        assert 'HX-Redirect' in response

    def test_unauthenticated_non_htmx_does_normal_redirect(self):
        response = Client().get('/group/active/')
        assert response.status_code == 302
        assert '/accounts/login/' in response['Location']


# ─── executor ────────────────────────────────────────────────────────────────

class TestExecutorNormalize:
    def test_strips_trailing_whitespace_per_line(self):
        from common.executor import _normalize
        assert _normalize('hello  \nworld  ') == 'hello\nworld'

    def test_strips_trailing_blank_lines(self):
        from common.executor import _normalize
        assert _normalize('hello\n\n\n') == 'hello'

    def test_preserves_internal_blank_lines(self):
        from common.executor import _normalize
        assert _normalize('a\n\nb') == 'a\n\nb'


class TestExecutorMakePreexec:
    def test_returns_none_on_non_linux(self):
        from unittest.mock import patch
        import common.executor as mod
        from pathlib import Path
        with patch.object(mod, '_IS_LINUX', False):
            result = mod._make_preexec(Path('.'))
        assert result is None

    def test_linux_path_with_mocked_platform(self):
        import os
        from unittest.mock import patch, MagicMock
        from pathlib import Path
        import common.executor as mod

        mock_resource = MagicMock()
        mock_resource.RLIMIT_AS = 0
        mock_resource.RLIMIT_CPU = 1
        mock_resource.RLIMIT_FSIZE = 2
        mock_resource.RLIMIT_NPROC = 3

        with patch.object(mod, '_IS_LINUX', True), \
             patch.dict('sys.modules', {'resource': mock_resource}), \
             patch.object(os, 'setgroups', create=True), \
             patch.object(os, 'setgid', create=True), \
             patch.object(os, 'setuid', create=True), \
             patch.object(os, 'chdir'):
            fn = mod._make_preexec(Path('/tmp'))
            assert callable(fn)
            fn()

        mock_resource.setrlimit.assert_called()

    def test_linux_preexec_os_errors_silenced(self):
        import os
        from unittest.mock import patch, MagicMock
        from pathlib import Path
        import common.executor as mod

        mock_resource = MagicMock()
        mock_resource.RLIMIT_AS = 0
        mock_resource.RLIMIT_CPU = 1
        mock_resource.RLIMIT_FSIZE = 2
        mock_resource.RLIMIT_NPROC = 3
        mock_resource.setrlimit.side_effect = ValueError('not permitted')

        with patch.object(mod, '_IS_LINUX', True), \
             patch.dict('sys.modules', {'resource': mock_resource}), \
             patch.object(os, 'setgroups', create=True, side_effect=OSError('perm')), \
             patch.object(os, 'setgid', create=True), \
             patch.object(os, 'setuid', create=True), \
             patch.object(os, 'chdir'):
            fn = mod._make_preexec(Path('/tmp'))
            fn()  # should not raise despite OSError + ValueError


class TestExecutor:
    def test_unsupported_language_raises(self):
        from common.executor import execute_code, LanguageNotSupportedError
        with pytest.raises(LanguageNotSupportedError):
            execute_code('fortran', 'program x; end program x', [])

    def test_python_correct_output(self):
        from unittest.mock import patch, MagicMock
        from common.executor import execute_code
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = 'hello\n'
        mock_proc.stderr = ''
        with patch('subprocess.run', return_value=mock_proc):
            results = execute_code('python', 'print("hello")', [
                {'input': '', 'expected_output': 'hello'}
            ])
        assert results[0]['is_correct'] is True
        assert results[0]['status'] == 'correct'
        assert results[0]['stdout'] == 'hello'

    def test_python_wrong_output(self):
        from unittest.mock import patch, MagicMock
        from common.executor import execute_code
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = 'world\n'
        mock_proc.stderr = ''
        with patch('subprocess.run', return_value=mock_proc):
            results = execute_code('python', 'print("world")', [
                {'input': '', 'expected_output': 'hello'}
            ])
        assert results[0]['is_correct'] is False
        assert results[0]['status'] == 'wrong_answer'

    def test_python_runtime_error(self):
        from unittest.mock import patch, MagicMock
        from common.executor import execute_code
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ''
        mock_proc.stderr = 'ZeroDivisionError'
        with patch('subprocess.run', return_value=mock_proc):
            results = execute_code('python', '1/0', [
                {'input': '', 'expected_output': ''}
            ])
        assert results[0]['status'] == 'runtime_error'

    def test_run_step_uses_errors_replace(self):
        """Sem errors='replace', bytes inválidos no stdout de um crash de runtime
        (comum em C/C++/Java) derrubam a thread interna de decode do subprocess e
        retornam stdout=None, quebrando _normalize() com AttributeError antes do
        CodeExecution ser salvo — a exceção escapa como 'Erro interno' genérico em
        student.tasks.execute_code_task, sem persistir a execução na timeline."""
        from unittest.mock import patch, MagicMock
        from common.executor import execute_code
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ''
        mock_proc.stderr = ''
        with patch('subprocess.run', return_value=mock_proc) as mock_run:
            execute_code('python', '1/0', [{'input': '', 'expected_output': ''}])
        assert mock_run.call_args.kwargs['errors'] == 'replace'

    def test_compile_step_uses_errors_replace(self):
        from unittest.mock import patch, MagicMock
        from common.executor import execute_code
        mock_compile = MagicMock()
        mock_compile.returncode = 0
        mock_compile.stdout = ''
        mock_compile.stderr = ''
        with patch('subprocess.run', return_value=mock_compile) as mock_run:
            execute_code('c', 'int main() { return 0; }', [])
        assert mock_run.call_args.kwargs['errors'] == 'replace'

    def test_timeout_sets_time_limit_status(self):
        from unittest.mock import patch
        from subprocess import TimeoutExpired
        from common.executor import execute_code
        with patch('subprocess.run', side_effect=TimeoutExpired('python', 10)):
            results = execute_code('python', 'while True: pass', [
                {'input': '', 'expected_output': ''}
            ])
        assert results[0]['status'] == 'time_limit'
        assert results[0]['is_correct'] is False

    def test_compilation_error_raises(self):
        from unittest.mock import patch, MagicMock
        from common.executor import execute_code, CompilationError
        mock_compile = MagicMock()
        mock_compile.returncode = 1
        mock_compile.stderr = 'error: expected ;'
        mock_compile.stdout = ''
        with patch('subprocess.run', return_value=mock_compile):
            with pytest.raises(CompilationError) as exc_info:
                execute_code('c', 'int main() { return 0 }', [
                    {'input': '', 'expected_output': ''}
                ])
        assert 'error: expected ;' in exc_info.value.output

    def test_chmod_oserror_silenced_in_compilation(self):
        import tempfile
        import os
        from unittest.mock import patch, MagicMock
        from pathlib import Path
        from common.executor import execute_code

        original_mkdtemp = tempfile.mkdtemp
        original_chmod = os.chmod

        def mkdtemp_with_binary(*args, **kwargs):
            path = original_mkdtemp(*args, **kwargs)
            (Path(path) / 'solution').touch()
            return path

        def chmod_raise_for_binary(path, mode):
            if Path(str(path)).name == 'solution':
                raise OSError('permission denied')
            return original_chmod(path, mode)

        compile_result = MagicMock()
        compile_result.returncode = 0
        compile_result.stderr = ''
        compile_result.stdout = ''

        run_result = MagicMock()
        run_result.returncode = 0
        run_result.stdout = '42\n'
        run_result.stderr = ''

        with patch('tempfile.mkdtemp', side_effect=mkdtemp_with_binary), \
             patch('subprocess.run', side_effect=[compile_result, run_result]), \
             patch('os.chmod', side_effect=chmod_raise_for_binary):
            results = execute_code('c', 'int main() { return 0; }', [
                {'input': '', 'expected_output': '42'}
            ])
        assert results[0]['is_correct'] is True

    def test_c_compilation_success_covers_chmod_loop(self):
        import tempfile
        import os
        from unittest.mock import patch, MagicMock
        from pathlib import Path
        from common.executor import execute_code

        original_mkdtemp = tempfile.mkdtemp

        def mkdtemp_with_binary(*args, **kwargs):
            path = original_mkdtemp(*args, **kwargs)
            # Create a fake compiled binary (no extension) so the chmod loop runs its body
            (Path(path) / 'solution').touch()
            return path

        compile_result = MagicMock()
        compile_result.returncode = 0
        compile_result.stderr = ''
        compile_result.stdout = ''

        run_result = MagicMock()
        run_result.returncode = 0
        run_result.stdout = '42\n'
        run_result.stderr = ''

        with patch('tempfile.mkdtemp', side_effect=mkdtemp_with_binary), \
             patch('subprocess.run', side_effect=[compile_result, run_result]):
            results = execute_code('c', 'int main() { return 0; }', [
                {'input': '', 'expected_output': '42'}
            ])
        assert results[0]['is_correct'] is True

    def test_multiple_test_cases(self):
        from unittest.mock import patch, MagicMock
        from common.executor import execute_code

        def side_effect(cmd, **kwargs):
            m = MagicMock()
            m.returncode = 0
            inp = kwargs.get('input', '')
            m.stdout = inp.strip() + '\n' if inp else '\n'
            m.stderr = ''
            return m

        with patch('subprocess.run', side_effect=side_effect):
            results = execute_code('python', 'x = input(); print(x)', [
                {'input': 'hello', 'expected_output': 'hello'},
                {'input': 'world', 'expected_output': 'bye'},
            ])
        assert results[0]['is_correct'] is True
        assert results[1]['is_correct'] is False
        assert len(results) == 2


# ─── Supressão de prompt (preludes) ──────────────────────────────────────────

class TestPreludeSuppression:
    """Testa a estrutura dos preludes e a injeção no arquivo fonte."""

    def test_python_and_js_have_preludes(self):
        from common.executor import _PRELUDES
        assert 'python' in _PRELUDES
        assert 'javascript' in _PRELUDES

    def test_java_has_no_file_level_prelude(self):
        """Java usa injeção dentro da classe, não prefixo de arquivo."""
        from common.executor import _PRELUDES
        assert 'java' not in _PRELUDES

    def test_c_and_cpp_have_preludes(self):
        from common.executor import _PRELUDES
        assert 'c' in _PRELUDES
        assert 'cpp' in _PRELUDES

    def test_python_prelude_patches_builtin_input(self):
        from common.executor import _PYTHON_PRELUDE
        assert 'builtins' in _PYTHON_PRELUDE
        assert 'input' in _PYTHON_PRELUDE
        assert 'readline' in _PYTHON_PRELUDE

    def test_js_prelude_sets_readline_output_null(self):
        from common.executor import _JS_PRELUDE
        assert 'readline' in _JS_PRELUDE
        assert 'output' in _JS_PRELUDE
        assert 'null' in _JS_PRELUDE

    def test_python_prelude_is_valid_python_and_cleans_namespace(self):
        """Prelude deve ser Python válido e não vazar variáveis temporárias."""
        from common.executor import _PYTHON_PRELUDE
        ns: dict = {}
        exec(_PYTHON_PRELUDE, ns)  # não deve lançar
        assert '_sys' not in ns
        assert '_bt' not in ns

    def test_python_prelude_prepended_in_written_file(self):
        from pathlib import Path
        from unittest.mock import patch, MagicMock
        from common.executor import execute_code, _PYTHON_PRELUDE

        student_code = 'print("oi")'
        written: dict[str, str] = {}
        orig = Path.write_text

        def spy(self, data, **kw):
            written[str(self)] = data
            return orig(self, data, **kw)

        mock_proc = MagicMock(returncode=0, stdout='oi\n', stderr='')
        with patch.object(Path, 'write_text', spy), \
             patch('subprocess.run', return_value=mock_proc):
            execute_code('python', student_code, [{'input': '', 'expected_output': 'oi'}])

        py_written = [v for k, v in written.items() if k.endswith('.py')]
        assert py_written, 'Nenhum .py foi escrito'
        assert py_written[0].startswith(_PYTHON_PRELUDE)
        assert student_code in py_written[0]

    def test_js_prelude_prepended_in_written_file(self):
        from pathlib import Path
        from unittest.mock import patch, MagicMock
        from common.executor import execute_code, _JS_PRELUDE

        student_code = 'console.log("ok")'
        written: dict[str, str] = {}
        orig = Path.write_text

        def spy(self, data, **kw):
            written[str(self)] = data
            return orig(self, data, **kw)

        mock_proc = MagicMock(returncode=0, stdout='ok\n', stderr='')
        with patch.object(Path, 'write_text', spy), \
             patch('subprocess.run', return_value=mock_proc):
            execute_code('javascript', student_code, [{'input': '', 'expected_output': 'ok'}])

        js_written = [v for k, v in written.items() if k.endswith('.js')]
        assert js_written, 'Nenhum .js foi escrito'
        assert js_written[0].startswith(_JS_PRELUDE)
        assert student_code in js_written[0]

    def test_java_prelude_injected_in_class_body(self):
        """_inject_java_prelude deve inserir o static block dentro de 'public class Main'."""
        from common.executor import _inject_java_prelude, _JAVA_STATIC_BLOCK
        src = 'public class Main {\n  public static void main(String[] a) {}\n}'
        result = _inject_java_prelude(src)
        assert _JAVA_STATIC_BLOCK in result
        assert result.startswith('public class Main {')
        # static block vem antes de main()
        assert result.index(_JAVA_STATIC_BLOCK) < result.index('main')

    def test_java_prelude_not_prepended_to_file(self):
        """Java usa injeção, não prefixo — o arquivo não deve começar com nenhum _PRELUDES."""
        from pathlib import Path
        from unittest.mock import patch, MagicMock
        from common.executor import execute_code, _PRELUDES

        java_src = 'public class Main { public static void main(String[] a) {} }'
        written: dict[str, str] = {}
        orig = Path.write_text

        def spy(self, data, **kw):
            written[str(self)] = data
            return orig(self, data, **kw)

        compile_ok = MagicMock(returncode=0, stderr='', stdout='')
        run_ok = MagicMock(returncode=0, stdout='\n', stderr='')

        with patch.object(Path, 'write_text', spy), \
             patch('subprocess.run', side_effect=[compile_ok, run_ok]):
            execute_code('java', java_src, [{'input': '', 'expected_output': ''}])

        java_written = [v for k, v in written.items() if k.endswith('.java')]
        assert java_written, 'Nenhum .java foi escrito'
        content = java_written[0]
        for prelude in _PRELUDES.values():
            assert not content.startswith(prelude), 'Java não deve começar com prelude de arquivo'

    def test_inject_java_prelude_with_extends(self):
        """Regex deve funcionar mesmo com 'extends' ou 'implements'."""
        from common.executor import _inject_java_prelude, _JAVA_STATIC_BLOCK
        src = 'public class Main extends Object {\n  public static void main(String[] a) {}\n}'
        result = _inject_java_prelude(src)
        assert _JAVA_STATIC_BLOCK in result

    def test_inject_java_prelude_not_found_returns_original(self):
        """Se a classe Main não for encontrada, retorna o código sem alteração."""
        from common.executor import _inject_java_prelude
        src = 'class Foo { void bar() {} }'
        assert _inject_java_prelude(src) == src

    def test_c_prelude_prepended_in_written_file(self):
        from pathlib import Path
        from unittest.mock import patch, MagicMock
        from common.executor import execute_code, _C_PRELUDE

        student_code = '#include <stdio.h>\nint main(){printf("ok\\n");return 0;}'
        written: dict[str, str] = {}
        orig = Path.write_text

        def spy(self, data, **kw):
            written[str(self)] = data
            return orig(self, data, **kw)

        compile_ok = MagicMock(returncode=0, stderr='', stdout='')
        run_ok = MagicMock(returncode=0, stdout='ok\n', stderr='')

        with patch.object(Path, 'write_text', spy), \
             patch('subprocess.run', side_effect=[compile_ok, run_ok]):
            execute_code('c', student_code, [{'input': '', 'expected_output': 'ok'}])

        c_written = [v for k, v in written.items() if k.endswith('.c')]
        assert c_written, 'Nenhum .c foi escrito'
        assert c_written[0].startswith(_C_PRELUDE)
        assert student_code in c_written[0]

    def test_cpp_prelude_prepended_in_written_file(self):
        from pathlib import Path
        from unittest.mock import patch, MagicMock
        from common.executor import execute_code, _CPP_PRELUDE

        student_code = '#include <iostream>\nint main(){std::cout<<"ok"<<std::endl;return 0;}'
        written: dict[str, str] = {}
        orig = Path.write_text

        def spy(self, data, **kw):
            written[str(self)] = data
            return orig(self, data, **kw)

        compile_ok = MagicMock(returncode=0, stderr='', stdout='')
        run_ok = MagicMock(returncode=0, stdout='ok\n', stderr='')

        with patch.object(Path, 'write_text', spy), \
             patch('subprocess.run', side_effect=[compile_ok, run_ok]):
            execute_code('cpp', student_code, [{'input': '', 'expected_output': 'ok'}])

        cpp_written = [v for k, v in written.items() if k.endswith('.cpp')]
        assert cpp_written, 'Nenhum .cpp foi escrito'
        assert cpp_written[0].startswith(_CPP_PRELUDE)
        assert student_code in cpp_written[0]


# ─── duration filter ─────────────────────────────────────────────────────────

class TestDurationFilter:
    def test_none_returns_dash(self):
        from common.templatetags.common_filters import duration
        assert duration(None) == '—'

    def test_zero_returns_dash(self):
        from common.templatetags.common_filters import duration
        assert duration(0) == '—'

    def test_seconds_only(self):
        from common.templatetags.common_filters import duration
        assert duration(45) == '45s'

    def test_minutes_and_seconds(self):
        from common.templatetags.common_filters import duration
        assert duration(90) == '1min 30s'

    def test_minutes_only(self):
        from common.templatetags.common_filters import duration
        assert duration(60) == '1min'

    def test_hours_and_minutes(self):
        from common.templatetags.common_filters import duration
        assert duration(3660) == '1h 1min'

    def test_hours_only(self):
        from common.templatetags.common_filters import duration
        assert duration(3600) == '1h'


# ─── Integração C (sem mock — requer gcc no container) ──────────────────────

@integration
class TestExecutorIntegrationC:
    """Compila e executa programas C reais contra o executor sem nenhum mock."""

    def _run(self, source, test_cases):
        from common.executor import execute_code
        return execute_code('c', source, test_cases)

    def test_hello_world(self):
        src = '#include <stdio.h>\nint main(){printf("hello\\n");return 0;}'
        results = self._run(src, [{'input': '', 'expected_output': 'hello'}])
        assert results[0]['status'] == 'correct'
        assert results[0]['stdout'] == 'hello'

    def test_stdin_to_stdout(self):
        src = '#include <stdio.h>\nint main(){int n;scanf("%d",&n);printf("%d\\n",n);return 0;}'
        results = self._run(src, [{'input': '42', 'expected_output': '42'}])
        assert results[0]['status'] == 'correct'

    def test_sum_multiple_cases(self):
        src = '#include <stdio.h>\nint main(){int a,b;scanf("%d %d",&a,&b);printf("%d\\n",a+b);return 0;}'
        results = self._run(src, [
            {'input': '3 4',  'expected_output': '7'},
            {'input': '10 20','expected_output': '30'},
            {'input': '0 0',  'expected_output': '0'},
        ])
        assert all(r['status'] == 'correct' for r in results)

    def test_math_library(self):
        src = '#include <stdio.h>\n#include <math.h>\nint main(){printf("%.0f\\n",sqrt(9.0));return 0;}'
        results = self._run(src, [{'input': '', 'expected_output': '3'}])
        assert results[0]['status'] == 'correct'

    def test_wrong_answer(self):
        src = '#include <stdio.h>\nint main(){printf("wrong\\n");return 0;}'
        results = self._run(src, [{'input': '', 'expected_output': 'correct'}])
        assert results[0]['status'] == 'wrong_answer'
        assert results[0]['is_correct'] is False

    def test_mixed_results(self):
        src = '#include <stdio.h>\nint main(){int n;scanf("%d",&n);printf("%d\\n",n*2);return 0;}'
        results = self._run(src, [
            {'input': '5', 'expected_output': '10'},
            {'input': '3', 'expected_output': '99'},
        ])
        assert results[0]['status'] == 'correct'
        assert results[1]['status'] == 'wrong_answer'

    def test_compilation_error_raises(self):
        from common.executor import CompilationError
        with pytest.raises(CompilationError) as exc_info:
            self._run('int main() { return 0 }', [{'input': '', 'expected_output': ''}])
        assert exc_info.value.output  # mensagem de erro do gcc não está vazia

    def test_runtime_error(self):
        # divisão por zero gera SIGFPE → returncode != 0
        src = '#include <stdio.h>\nint main(){int x=0;printf("%d\\n",1/x);return 0;}'
        results = self._run(src, [{'input': '', 'expected_output': '42'}])
        assert results[0]['status'] == 'runtime_error'
        assert results[0]['is_correct'] is False

    def test_scanf_without_prompt_reads_stdin_correctly(self):
        """scanf sem printf de prompt: somente o resultado vai para o stdout."""
        src = '#include <stdio.h>\nint main(){int n;scanf("%d",&n);printf("%d\\n",n*2);return 0;}'
        results = self._run(src, [
            {'input': '5',  'expected_output': '10'},
            {'input': '0',  'expected_output': '0'},
            {'input': '21', 'expected_output': '42'},
        ])
        assert all(r['status'] == 'correct' for r in results)

    def test_printf_prompt_suppressed_before_scanf(self):
        """printf("prompt") antes de scanf deve ser suprimido pelo prelude de C."""
        src = (
            '#include <stdio.h>\n'
            'int main(){\n'
            '  int n;\n'
            '  printf("Digite um numero: ");\n'
            '  scanf("%d",&n);\n'
            '  printf("%d\\n",n);\n'
            '  return 0;\n'
            '}'
        )
        results = self._run(src, [{'input': '42', 'expected_output': '42'}])
        assert results[0]['status'] == 'correct'
        assert results[0]['stdout'] == '42'

    def test_multiple_scanf_without_prompts(self):
        """Múltiplos scanf sem prompts leem linhas consecutivas do stdin corretamente."""
        src = (
            '#include <stdio.h>\n'
            'int main(){\n'
            '  int a,b,c;\n'
            '  scanf("%d%d%d",&a,&b,&c);\n'
            '  printf("%d\\n",a+b+c);\n'
            '  return 0;\n'
            '}'
        )
        results = self._run(src, [
            {'input': '1 2 3', 'expected_output': '6'},
            {'input': '10 20 30', 'expected_output': '60'},
        ])
        assert all(r['status'] == 'correct' for r in results)

    def test_two_prompts_both_suppressed(self):
        """Dois printf de prompt (um antes de cada scanf) devem ser ambos suprimidos."""
        src = (
            '#include <stdio.h>\n'
            'int main(){\n'
            '  int a,b;\n'
            '  printf("Digite a: ");\n'
            '  scanf("%d",&a);\n'
            '  printf("Digite b: ");\n'
            '  scanf("%d",&b);\n'
            '  printf("%d\\n",a+b);\n'
            '  return 0;\n'
            '}'
        )
        results = self._run(src, [
            {'input': '3\n4', 'expected_output': '7'},
            {'input': '10\n20', 'expected_output': '30'},
        ])
        assert all(r['status'] == 'correct' for r in results)
        assert results[0]['stdout'] == '7'
        assert results[1]['stdout'] == '30'


# ─── Integração C++ (sem mock — requer g++ no container) ────────────────────

@integration
class TestExecutorIntegrationCpp:
    """Compila e executa programas C++ reais contra o executor sem nenhum mock."""

    def _run(self, source, test_cases):
        from common.executor import execute_code
        return execute_code('cpp', source, test_cases)

    def test_hello_world(self):
        src = '#include <iostream>\nint main(){std::cout<<"hello"<<std::endl;return 0;}'
        results = self._run(src, [{'input': '', 'expected_output': 'hello'}])
        assert results[0]['status'] == 'correct'

    def test_cin_cout(self):
        src = '#include <iostream>\nint main(){int n;std::cin>>n;std::cout<<n*2<<std::endl;return 0;}'
        results = self._run(src, [
            {'input': '5', 'expected_output': '10'},
            {'input': '0', 'expected_output': '0'},
        ])
        assert all(r['status'] == 'correct' for r in results)

    def test_stl_sort(self):
        src = (
            '#include <iostream>\n#include <vector>\n#include <algorithm>\n'
            'int main(){'
            'std::vector<int> v={3,1,2};'
            'std::sort(v.begin(),v.end());'
            'for(int x:v) std::cout<<x<<" ";'
            'std::cout<<std::endl;return 0;}'
        )
        results = self._run(src, [{'input': '', 'expected_output': '1 2 3'}])
        assert results[0]['status'] == 'correct'

    def test_string_length(self):
        src = (
            '#include <iostream>\n#include <string>\n'
            'int main(){std::string s;std::cin>>s;std::cout<<s.length()<<std::endl;return 0;}'
        )
        results = self._run(src, [{'input': 'hello', 'expected_output': '5'}])
        assert results[0]['status'] == 'correct'

    def test_wrong_answer(self):
        src = '#include <iostream>\nint main(){std::cout<<"nope"<<std::endl;return 0;}'
        results = self._run(src, [{'input': '', 'expected_output': 'yes'}])
        assert results[0]['status'] == 'wrong_answer'

    def test_compilation_error_raises(self):
        from common.executor import CompilationError
        with pytest.raises(CompilationError) as exc_info:
            self._run('#include <iostream>\nint main(){std::cout<<"hi" return 0;}', [])
        assert exc_info.value.output

    def test_runtime_error_out_of_range(self):
        src = '#include <vector>\nint main(){std::vector<int> v;return v.at(99);}'
        results = self._run(src, [{'input': '', 'expected_output': ''}])
        assert results[0]['status'] == 'runtime_error'

    def test_cin_without_prompt_reads_stdin_correctly(self):
        """cin sem cout de prompt: somente o resultado vai para o stdout."""
        src = (
            '#include <iostream>\n'
            'int main(){\n'
            '  int n;\n'
            '  std::cin>>n;\n'
            '  std::cout<<n*2<<std::endl;\n'
            '  return 0;\n'
            '}'
        )
        results = self._run(src, [
            {'input': '5',  'expected_output': '10'},
            {'input': '0',  'expected_output': '0'},
            {'input': '21', 'expected_output': '42'},
        ])
        assert all(r['status'] == 'correct' for r in results)

    def test_cout_prompt_suppressed_before_cin(self):
        """cout<<"prompt" antes de cin deve ser suprimido pelo prelude de C++."""
        src = (
            '#include <iostream>\n'
            'int main(){\n'
            '  int n;\n'
            '  std::cout<<"Digite um numero: ";\n'
            '  std::cin>>n;\n'
            '  std::cout<<n<<std::endl;\n'
            '  return 0;\n'
            '}'
        )
        results = self._run(src, [{'input': '42', 'expected_output': '42'}])
        assert results[0]['status'] == 'correct'
        assert results[0]['stdout'] == '42'

    def test_multiple_cin_without_prompts(self):
        """Múltiplos cin sem prompts leem valores consecutivos do stdin corretamente."""
        src = (
            '#include <iostream>\n'
            'int main(){\n'
            '  int a,b,c;\n'
            '  std::cin>>a>>b>>c;\n'
            '  std::cout<<a+b+c<<std::endl;\n'
            '  return 0;\n'
            '}'
        )
        results = self._run(src, [
            {'input': '1 2 3',    'expected_output': '6'},
            {'input': '10 20 30', 'expected_output': '60'},
        ])
        assert all(r['status'] == 'correct' for r in results)

    def test_getline_without_prompt(self):
        """getline lê linha completa do stdin sem poluir o stdout."""
        src = (
            '#include <iostream>\n'
            '#include <string>\n'
            'int main(){\n'
            '  std::string s;\n'
            '  std::getline(std::cin,s);\n'
            '  std::cout<<s.length()<<std::endl;\n'
            '  return 0;\n'
            '}'
        )
        results = self._run(src, [
            {'input': 'hello', 'expected_output': '5'},
            {'input': 'ab',    'expected_output': '2'},
        ])
        assert all(r['status'] == 'correct' for r in results)

    def test_two_cout_prompts_both_suppressed(self):
        """Dois cout de prompt (um antes de cada cin) devem ser ambos suprimidos."""
        src = (
            '#include <iostream>\n'
            'int main(){\n'
            '  int a,b;\n'
            '  std::cout<<"Digite a: ";\n'
            '  std::cin>>a;\n'
            '  std::cout<<"Digite b: ";\n'
            '  std::cin>>b;\n'
            '  std::cout<<a+b<<std::endl;\n'
            '  return 0;\n'
            '}'
        )
        results = self._run(src, [
            {'input': '3\n4',   'expected_output': '7'},
            {'input': '10\n20', 'expected_output': '30'},
        ])
        assert all(r['status'] == 'correct' for r in results)
        assert results[0]['stdout'] == '7'
        assert results[1]['stdout'] == '30'


# ─── Integração Python (sem mock) ───────────────────────────────────────────

@integration
class TestExecutorIntegrationPython:
    """Executa programas Python reais contra o executor sem nenhum mock."""

    def _run(self, source, test_cases):
        from common.executor import execute_code
        return execute_code('python', source, test_cases)

    def test_hello_world(self):
        results = self._run('print("hello")', [{'input': '', 'expected_output': 'hello'}])
        assert results[0]['status'] == 'correct'
        assert results[0]['stdout'] == 'hello'

    def test_stdin_to_stdout(self):
        results = self._run('print(input())', [{'input': 'world', 'expected_output': 'world'}])
        assert results[0]['status'] == 'correct'

    def test_arithmetic_from_stdin(self):
        src = 'a, b = map(int, input().split())\nprint(a + b)'
        results = self._run(src, [
            {'input': '3 4',  'expected_output': '7'},
            {'input': '10 20','expected_output': '30'},
            {'input': '0 0',  'expected_output': '0'},
        ])
        assert all(r['status'] == 'correct' for r in results)

    def test_wrong_answer(self):
        results = self._run('print("errado")', [{'input': '', 'expected_output': 'certo'}])
        assert results[0]['status'] == 'wrong_answer'
        assert results[0]['is_correct'] is False

    def test_mixed_results(self):
        src = 'n = int(input())\nprint(n * 3)'
        results = self._run(src, [
            {'input': '4', 'expected_output': '12'},
            {'input': '2', 'expected_output': '99'},
        ])
        assert results[0]['status'] == 'correct'
        assert results[1]['status'] == 'wrong_answer'

    def test_runtime_error_exception(self):
        results = self._run('print(1 / 0)', [{'input': '', 'expected_output': '42'}])
        assert results[0]['status'] == 'runtime_error'
        assert results[0]['is_correct'] is False
        assert 'ZeroDivisionError' in results[0]['stderr']

    def test_syntax_error(self):
        results = self._run('def f(\nprint("x")', [{'input': '', 'expected_output': '42'}])
        assert results[0]['status'] == 'runtime_error'

    def test_list_comprehension(self):
        src = 'n = int(input())\nprint(sum(i*i for i in range(n+1)))'
        results = self._run(src, [
            {'input': '3', 'expected_output': '14'},
            {'input': '0', 'expected_output': '0'},
        ])
        assert all(r['status'] == 'correct' for r in results)

    def test_input_prompt_suppressed(self):
        """input('prompt') não deve aparecer no stdout; leitura do stdin permanece correta."""
        results = self._run(
            "nome = input('Digite seu nome: ')\nprint(nome)",
            [{'input': 'João', 'expected_output': 'João'}],
        )
        assert results[0]['status'] == 'correct'
        assert results[0]['stdout'] == 'João'

    def test_input_prompt_suppressed_across_test_cases(self):
        """Supressão deve funcionar em todos os casos de teste, não só no primeiro."""
        results = self._run(
            "n = int(input('n: '))\nprint(n * 2)",
            [
                {'input': '3', 'expected_output': '6'},
                {'input': '5', 'expected_output': '10'},
            ],
        )
        assert all(r['status'] == 'correct' for r in results)

    def test_multiple_input_prompts_suppressed(self):
        """Múltiplos input('...') devem ler linhas consecutivas sem poluir o stdout."""
        results = self._run(
            "a = int(input('a: '))\nb = int(input('b: '))\nprint(a + b)",
            [{'input': '3\n4', 'expected_output': '7'}],
        )
        assert results[0]['status'] == 'correct'
        assert results[0]['stdout'] == '7'


# ─── Integração JavaScript (sem mock — requer node no container) ─────────────

@integration
@_needs('node')
class TestExecutorIntegrationJavaScript:
    """Executa programas JavaScript reais com Node.js sem nenhum mock."""

    def _run(self, source, test_cases):
        from common.executor import execute_code
        return execute_code('javascript', source, test_cases)

    def test_hello_world(self):
        results = self._run('console.log("hello")', [{'input': '', 'expected_output': 'hello'}])
        assert results[0]['status'] == 'correct'
        assert results[0]['stdout'] == 'hello'

    def test_stdin_to_stdout(self):
        src = (
            "const fs = require('fs');\n"
            "const input = fs.readFileSync(0, 'utf8').trim();\n"
            "console.log(input);"
        )
        results = self._run(src, [{'input': 'world', 'expected_output': 'world'}])
        assert results[0]['status'] == 'correct'

    def test_arithmetic_from_stdin(self):
        src = (
            "const fs = require('fs');\n"
            "const [a, b] = fs.readFileSync(0, 'utf8').trim().split(' ').map(Number);\n"
            "console.log(a + b);"
        )
        results = self._run(src, [
            {'input': '3 4',  'expected_output': '7'},
            {'input': '10 20','expected_output': '30'},
            {'input': '0 0',  'expected_output': '0'},
        ])
        assert all(r['status'] == 'correct' for r in results)

    def test_wrong_answer(self):
        results = self._run('console.log("errado")', [{'input': '', 'expected_output': 'certo'}])
        assert results[0]['status'] == 'wrong_answer'
        assert results[0]['is_correct'] is False

    def test_mixed_results(self):
        src = (
            "const fs = require('fs');\n"
            "const n = parseInt(fs.readFileSync(0, 'utf8').trim());\n"
            "console.log(n * 3);"
        )
        results = self._run(src, [
            {'input': '4', 'expected_output': '12'},
            {'input': '2', 'expected_output': '99'},
        ])
        assert results[0]['status'] == 'correct'
        assert results[1]['status'] == 'wrong_answer'

    def test_runtime_error(self):
        results = self._run('null.toString()', [{'input': '', 'expected_output': '42'}])
        assert results[0]['status'] == 'runtime_error'
        assert results[0]['is_correct'] is False

    def test_array_operations(self):
        src = (
            "const fs = require('fs');\n"
            "const nums = fs.readFileSync(0, 'utf8').trim().split(' ').map(Number);\n"
            "console.log(nums.sort((a,b)=>a-b).join(' '));"
        )
        results = self._run(src, [
            {'input': '3 1 2', 'expected_output': '1 2 3'},
            {'input': '5 4',   'expected_output': '4 5'},
        ])
        assert all(r['status'] == 'correct' for r in results)

    def test_readline_question_prompt_suppressed(self):
        """rl.question('prompt', cb) não deve escrever o prompt no stdout."""
        src = (
            "const readline = require('readline');\n"
            "const rl = readline.createInterface({input: process.stdin, output: process.stdout});\n"
            "rl.question('Digite seu nome: ', (name) => { console.log(name); rl.close(); });\n"
        )
        results = self._run(src, [{'input': 'João', 'expected_output': 'João'}])
        assert results[0]['status'] == 'correct'
        assert results[0]['stdout'] == 'João'

    def test_readline_question_reads_stdin_correctly_after_suppression(self):
        """Mesmo com prompt suprimido, a resposta do stdin deve chegar ao callback."""
        src = (
            "const readline = require('readline');\n"
            "const rl = readline.createInterface({input: process.stdin, output: process.stdout});\n"
            "rl.question('a: ', (a) => {\n"
            "  rl.question('b: ', (b) => {\n"
            "    console.log(Number(a) + Number(b));\n"
            "    rl.close();\n"
            "  });\n"
            "});\n"
        )
        results = self._run(src, [{'input': '3\n4', 'expected_output': '7'}])
        assert results[0]['status'] == 'correct'
        assert results[0]['stdout'] == '7'


# ─── Integração Java (sem mock — requer javac/java no container) ─────────────

@integration
@_needs('javac', 'java')
class TestExecutorIntegrationJava:
    """Compila e executa programas Java reais sem nenhum mock. Classe deve ser 'Main'."""

    def _run(self, source, test_cases):
        from common.executor import execute_code
        return execute_code('java', source, test_cases)

    def test_hello_world(self):
        src = 'public class Main { public static void main(String[] a) { System.out.println("hello"); } }'
        results = self._run(src, [{'input': '', 'expected_output': 'hello'}])
        assert results[0]['status'] == 'correct'
        assert results[0]['stdout'] == 'hello'

    def test_stdin_to_stdout(self):
        src = (
            'import java.util.Scanner;\n'
            'public class Main {\n'
            '  public static void main(String[] a) {\n'
            '    Scanner sc = new Scanner(System.in);\n'
            '    System.out.println(sc.nextLine());\n'
            '  }\n'
            '}'
        )
        results = self._run(src, [{'input': 'world', 'expected_output': 'world'}])
        assert results[0]['status'] == 'correct'

    def test_arithmetic_from_stdin(self):
        src = (
            'import java.util.Scanner;\n'
            'public class Main {\n'
            '  public static void main(String[] a) {\n'
            '    Scanner sc = new Scanner(System.in);\n'
            '    int x = sc.nextInt(), y = sc.nextInt();\n'
            '    System.out.println(x + y);\n'
            '  }\n'
            '}'
        )
        results = self._run(src, [
            {'input': '3 4',  'expected_output': '7'},
            {'input': '10 20','expected_output': '30'},
            {'input': '0 0',  'expected_output': '0'},
        ])
        assert all(r['status'] == 'correct' for r in results)

    def test_wrong_answer(self):
        src = 'public class Main { public static void main(String[] a) { System.out.println("errado"); } }'
        results = self._run(src, [{'input': '', 'expected_output': 'certo'}])
        assert results[0]['status'] == 'wrong_answer'
        assert results[0]['is_correct'] is False

    def test_mixed_results(self):
        src = (
            'import java.util.Scanner;\n'
            'public class Main {\n'
            '  public static void main(String[] a) {\n'
            '    Scanner sc = new Scanner(System.in);\n'
            '    System.out.println(sc.nextInt() * 3);\n'
            '  }\n'
            '}'
        )
        results = self._run(src, [
            {'input': '4', 'expected_output': '12'},
            {'input': '2', 'expected_output': '99'},
        ])
        assert results[0]['status'] == 'correct'
        assert results[1]['status'] == 'wrong_answer'

    def test_compilation_error_raises(self):
        from common.executor import CompilationError
        with pytest.raises(CompilationError) as exc_info:
            self._run('public class Main { public static void main(String[] a) { System.out.println("hi") } }', [])
        assert exc_info.value.output

    def test_runtime_error(self):
        src = (
            'public class Main {\n'
            '  public static void main(String[] a) {\n'
            '    int[] arr = new int[0];\n'
            '    System.out.println(arr[99]);\n'
            '  }\n'
            '}'
        )
        results = self._run(src, [{'input': '', 'expected_output': '42'}])
        assert results[0]['status'] == 'runtime_error'
        assert results[0]['is_correct'] is False

    def test_arraylist_and_collections(self):
        src = (
            'import java.util.*;\n'
            'public class Main {\n'
            '  public static void main(String[] a) {\n'
            '    List<Integer> l = new ArrayList<>(Arrays.asList(3,1,2));\n'
            '    Collections.sort(l);\n'
            '    for (int x : l) System.out.print(x + " ");\n'
            '    System.out.println();\n'
            '  }\n'
            '}'
        )
        results = self._run(src, [{'input': '', 'expected_output': '1 2 3'}])
        assert results[0]['status'] == 'correct'

    def test_scanner_without_prompt_reads_stdin_correctly(self):
        """Scanner sem System.out.print de prompt: somente o resultado vai para o stdout."""
        src = (
            'import java.util.Scanner;\n'
            'public class Main {\n'
            '  public static void main(String[] a) {\n'
            '    Scanner sc = new Scanner(System.in);\n'
            '    System.out.println(sc.nextInt() * 2);\n'
            '  }\n'
            '}'
        )
        results = self._run(src, [
            {'input': '5',  'expected_output': '10'},
            {'input': '0',  'expected_output': '0'},
            {'input': '21', 'expected_output': '42'},
        ])
        assert all(r['status'] == 'correct' for r in results)

    def test_system_out_prompt_suppressed_before_scanner(self):
        """System.out.print("prompt") antes de Scanner deve ser suprimido pelo prelude Java."""
        src = (
            'import java.util.Scanner;\n'
            'public class Main {\n'
            '  public static void main(String[] a) {\n'
            '    Scanner sc = new Scanner(System.in);\n'
            '    System.out.print("Digite um numero: ");\n'
            '    System.out.println(sc.nextInt());\n'
            '  }\n'
            '}'
        )
        results = self._run(src, [{'input': '42', 'expected_output': '42'}])
        assert results[0]['status'] == 'correct'
        assert results[0]['stdout'] == '42'

    def test_multiple_scanner_reads_without_prompts(self):
        """Múltiplos nextInt() sem prompts leem valores consecutivos do stdin corretamente."""
        src = (
            'import java.util.Scanner;\n'
            'public class Main {\n'
            '  public static void main(String[] a) {\n'
            '    Scanner sc = new Scanner(System.in);\n'
            '    int x = sc.nextInt(), y = sc.nextInt(), z = sc.nextInt();\n'
            '    System.out.println(x + y + z);\n'
            '  }\n'
            '}'
        )
        results = self._run(src, [
            {'input': '1 2 3',    'expected_output': '6'},
            {'input': '10 20 30', 'expected_output': '60'},
        ])
        assert all(r['status'] == 'correct' for r in results)

    def test_two_system_out_prompts_both_suppressed(self):
        """Dois System.out.print de prompt (um antes de cada nextInt) devem ser ambos suprimidos."""
        src = (
            'import java.util.Scanner;\n'
            'public class Main {\n'
            '  public static void main(String[] a) {\n'
            '    Scanner sc = new Scanner(System.in);\n'
            '    System.out.print("Digite a: ");\n'
            '    int x = sc.nextInt();\n'
            '    System.out.print("Digite b: ");\n'
            '    int y = sc.nextInt();\n'
            '    System.out.println(x + y);\n'
            '  }\n'
            '}'
        )
        results = self._run(src, [
            {'input': '3\n4',   'expected_output': '7'},
            {'input': '10\n20', 'expected_output': '30'},
        ])
        assert all(r['status'] == 'correct' for r in results)
        assert results[0]['stdout'] == '7'
        assert results[1]['stdout'] == '30'

    def test_scanner_nextline_without_prompt(self):
        """nextLine() lê linha completa do stdin sem poluir o stdout."""
        src = (
            'import java.util.Scanner;\n'
            'public class Main {\n'
            '  public static void main(String[] a) {\n'
            '    Scanner sc = new Scanner(System.in);\n'
            '    String s = sc.nextLine();\n'
            '    System.out.println(s.length());\n'
            '  }\n'
            '}'
        )
        results = self._run(src, [
            {'input': 'hello', 'expected_output': '5'},
            {'input': 'ab',    'expected_output': '2'},
        ])
        assert all(r['status'] == 'correct' for r in results)

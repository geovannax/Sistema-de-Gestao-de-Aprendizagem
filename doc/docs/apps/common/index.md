# common

O app **common** centraliza todos os componentes reutilizáveis do projeto: a view genérica de listagem, mixins de view, utilitários e filtros de template. É a camada de infraestrutura compartilhada entre os demais apps.

## Estrutura

| Módulo | Conteúdo |
|--------|----------|
| generic | [EnhancedListView](generic/EnhancedListView.md) |
| mixins | [AuthPermissionMixin](mixins/AuthPermissionMixin.md), [HTMXLoginRequiredMixin](mixins/HTMXLoginRequiredMixin.md), [FilteringMixin](mixins/FilteringMixin.md), [OrderingMixin](mixins/OrderingMixin.md), e mais |
| views | [LandingPage](views/LandingPage.md), [HomeView](views/HomeView.md), [permission_denied](views/permission_denied.md), [page_not_found](views/page_not_found.md) |
| utils | [get_btn_action](utils/get_btn_action.md) |
| executor | [execute_code](executor/execute_code.md), [ExecutorError](executor/ExecutorError.md), [CompilationError](executor/CompilationError.md), [LanguageNotSupportedError](executor/LanguageNotSupportedError.md) |
| filters | [get_attr](filters/get_attr.md), [get_attr_with_truncate](filters/get_attr_with_truncate.md), [get_model_only_fields](filters/get_model_only_fields.md), [get_item](filters/get_item.md) |

## Executor de Código

O módulo `executor` implementa a execução segura de código do aluno via subprocess com isolamento de usuário (`nobody`) e `ulimits`. Suporta **Python**, **JavaScript**, **Java**, **C** e **C++**.

```
Aluno envia código
    → execute_code_task (Celery)
        → execute_code (executor)
            → [tmpdir] compilação (C/C++/Java)
            → subprocess como nobody + ulimits
            → list[dict] com status por caso de teste
        → CodeExecution.objects.create(...)
        → ExerciseAnswer.objects.update_or_create(...)
```

### Linguagens suportadas

| Linguagem | Compilador / Interpretador | Compilação |
|-----------|---------------------------|------------|
| `python` | `python` (sys.executable) | Não |
| `javascript` | `node --jitless` | Não |
| `java` | `javac` + `java` | Sim |
| `c` | `gcc -lm` | Sim |
| `cpp` | `g++ -lm` | Sim |

### Limites de execução

| Recurso | Limite |
|---------|--------|
| Memória virtual | 2 GB |
| CPU | 5 s |
| Tamanho de arquivo de saída | 1 MB |
| Processos filhos | 64 |
| Timeout wall-clock | 10 s |

!!! warning "Linux only"
    O isolamento com `nobody` e `ulimits` só é aplicado no Linux (container Docker).
    Em Windows/macOS apenas o timeout wall-clock é garantido.

# Arquitetura e Tecnologias

O sistema é uma aplicação web **server-driven** construída com [Django](https://docs.djangoproject.com/), servida via ASGI, com execução assíncrona de código e documentação como código. A proposta favorece renderização server-side, evitando complexidade desnecessária no frontend e mantendo as regras de negócio no backend.

---

## Stack Principal

### Backend

| Tecnologia | Versão | Função |
|---|---|---|
| [Django](https://docs.djangoproject.com/) | 6.0.3 | Framework web principal |
| [uvicorn](https://www.uvicorn.org/) | 0.42 | Servidor ASGI (substitui Gunicorn) |
| [Celery](https://docs.celeryq.dev/) | 5.4 | Execução assíncrona de código dos alunos |
| [Django ORM](https://docs.djangoproject.com/en/stable/topics/db/) | — | Modelagem e acesso a dados |

### Banco de Dados e Cache

| Tecnologia | Ambiente | Função |
|---|---|---|
| [SQLite](https://www.sqlite.org/) | Desenvolvimento | Banco embutido, sem configuração |
| [PostgreSQL](https://www.postgresql.org/docs/) 18 | Produção | Banco relacional principal |
| [Redis](https://redis.io/docs/latest/) 7 | Produção | Broker do Celery + cache de sessão |

Em desenvolvimento (`WEB_DEBUG=true`), o Django usa SQLite e cache em memória (`LocMemCache`). Em produção, PostgreSQL e Redis são obrigatórios.

### Frontend

| Tecnologia | Função |
|---|---|
| [Django Templates](https://docs.djangoproject.com/en/stable/topics/templates/) | Renderização server-side |
| [HTMX](https://htmx.org/docs/) | Interações dinâmicas progressivas sem SPA |
| [Bootstrap 5](https://getbootstrap.com/docs/) | Componentes e grid (hospedado localmente, sem CDN) |
| [Bootstrap Icons](https://icons.getbootstrap.com/) | Ícones SVG inline |
| [highlight.js](https://highlightjs.org/) | Highlight de código nos templates |
| [django-select2](https://django-select2.readthedocs.io/) | Widget de seleção avançada em formulários |

### Infraestrutura

| Tecnologia | Função |
|---|---|
| [Docker](https://docs.docker.com/) + [Docker Compose](https://docs.docker.com/compose/) | Padronização dos ambientes |
| [Nginx](https://nginx.org/en/docs/) | Proxy reverso, TLS/SSL, arquivos estáticos e documentação |
| [MkDocs](https://www.mkdocs.org/) + [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) | Documentação técnica versionada |
| [mkdocstrings](https://mkdocstrings.github.io/) | Referência de API gerada automaticamente do código Python |

---

## Apps Django

O projeto segue a convenção Django de dividir responsabilidades em apps. Todo o código da aplicação está dentro de `web/`.

| App | Responsabilidade |
|---|---|
| `core` | Settings, URL raiz, ASGI, configuração do Celery |
| `accounts` | Preferências de usuário (`JSONField`), `CookieMiddleware`, signals de login/logout |
| `activity` | Listas de atividades e exercícios polimórficos (4 tipos) |
| `group` | Turmas com soft delete, compartilhamento entre professores, convites por token |
| `student` | Submissão de atividades, respostas, correção pelo professor, execução de código |
| `common` | Mixins reutilizáveis, `EnhancedListView`, template tags, executor de código, comando `seed` |

---

## Exercícios Polimórficos

O app `activity` implementa quatro tipos de exercício a partir de um modelo base `Exercise`, cada um com uma relação `OneToOne`:

| Tipo | Modelo | Correção |
|---|---|---|
| `multiple_choice` | `MultipleChoiceExercise` + `ExerciseOption` | Automática (comparação de opção) |
| `complete_code` | `CompleteCodeExercise` | Automática (comparação de código normalizado) |
| `code` | `CodeExercise` + `TestCase` | Automática via sandbox (Celery) ou manual |
| `discursive` | `DiscursiveExercise` | Sempre manual pelo professor |

---

## Execução de Código (Sandbox)

Exercícios do tipo `code` são corrigidos de forma assíncrona por meio de um sandbox de execução isolado.

### Fluxo

```
Aluno submete código
      ↓
StudentRunCodeView → enfileira execute_code_task (Celery)
      ↓
StudentRunCodePollView → polling HTMX até resultado disponível
      ↓
execute_code_task → common.executor.execute_code()
      ↓
CodeExecution salvo + ExerciseAnswer atualizado
```

### Isolamento (Linux / container Docker)

O processo filho roda com restrições em múltiplas camadas:

| Camada | Mecanismo | Limite |
|---|---|---|
| Usuário | `setuid(nobody)` — uid 65534 | Sem permissão de escrita no filesystem |
| Memória | `RLIMIT_AS` | 256 MB |
| CPU | `RLIMIT_CPU` | 5 segundos de CPU |
| Arquivo | `RLIMIT_FSIZE` | 1 MB por arquivo de saída |
| Processos | `RLIMIT_NPROC` | 64 processos filhos |
| Rede | `iptables` (startup do container) | Bloqueia toda saída de rede do uid 65534 |
| Tempo total | `subprocess.timeout` | 10 segundos wall-clock |

Em ambientes não-Linux (Windows, macOS — dev local), o sandbox roda sem isolamento de usuário nem de recursos, apenas com timeout.

### Linguagens Suportadas

| Linguagem | Runtime |
|---|---|
| Python | CPython (mesmo interpretador do servidor) |
| JavaScript | Node.js |
| Java | OpenJDK (`javac` + `java`) |
| C | GCC (`gcc`) |
| C++ | G++ (`g++`) |

---

## Processamento Assíncrono (Celery)

O Celery é configurado em `core/celery.py` com `autodiscover_tasks()`. As tarefas são definidas no app `student`:

| Tarefa | Módulo | Função |
|---|---|---|
| `student.execute_code` | `student.tasks.execute_code_task` | Executa código do aluno contra os casos de teste e salva `CodeExecution` |

O broker e o backend de resultados usam Redis em produção. Em desenvolvimento, o Celery é opcional — a correção automática de `complete_code` ocorre de forma síncrona na própria view.

---

## Fluxo de Requisição

```
Cliente (browser)
      ↓  HTTPS
    Nginx  ──────────────────→  /static/   (arquivos estáticos)
      │                     └→  /docs/     (MkDocs site)
      ↓  HTTP (proxy_pass)
   uvicorn (ASGI)
      ↓
   Django (middleware stack)
      ↓
   View → ORM → PostgreSQL
      ↓
   Template → HTML
      ↓
   Resposta ao cliente
```

---

## Decisões de Arquitetura

**ASGI em vez de WSGI** — o uvicorn serve a aplicação via ASGI para suportar futuramente WebSockets e Server-Sent Events sem trocar de servidor.

**Server-side rendering + HTMX** — em vez de um SPA separado, o HTMX permite interações dinâmicas (polling, atualizações parciais de página) mantendo todo o estado no servidor e os templates no Django.

**Soft delete** — turmas (`Group`) não são excluídas fisicamente. O campo `deleted_at` preserva o histórico de submissões e resultados dos alunos.

**Bootstrap local** — os arquivos do Bootstrap são servidos pelo próprio Nginx, sem dependência de CDNs externos. Isso garante funcionamento offline e elimina riscos de supply chain.

**Documentação como código** — a documentação vive no mesmo repositório da aplicação e é construída automaticamente pelo container web no startup, ficando disponível em `/docs/`.

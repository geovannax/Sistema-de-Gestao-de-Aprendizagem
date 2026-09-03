# Guia de Início — Desenvolvimento

Este guia descreve como preparar e executar o ambiente de desenvolvimento do **Sistema de Gestão de Aprendizagem**.

O projeto é uma aplicação web construída com [Django](https://docs.djangoproject.com/), organizada em múltiplos apps e preparada para execução local ou via [Docker Compose](https://docs.docker.com/compose/). Durante o desenvolvimento, é possível trabalhar diretamente com o ambiente virtual Python do diretório `web/` ou utilizar os serviços definidos no arquivo `compose.yml`.

---

## Pré-requisitos

Antes de iniciar, verifique se as seguintes ferramentas estão instaladas:

- [Python](https://www.python.org/downloads/)
- [Git](https://git-scm.com/doc)
- [Docker](https://docs.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- editor de código, como [Visual Studio Code](https://code.visualstudio.com/docs)

Para desenvolvimento local sem Docker, também é necessário criar e ativar um ambiente virtual Python, além de ter PostgreSQL e Redis acessíveis — não há mais fallback para SQLite/cache em memória em nenhum modo (ver "Observações Importantes" mais abaixo).

---

## Estrutura Inicial do Projeto

A estrutura principal do repositório é organizada da seguinte forma:

    Sistema-de-Gestao-de-Aprendizagem/
    ├── compose.yml
    ├── .env
    ├── README.md
    ├── nginx/
    ├── web/
    │   ├── manage.py
    │   ├── core/
    │   ├── accounts/
    │   ├── activity/
    │   ├── dataset/
    │   ├── group/
    │   ├── student/
    │   └── common/
    └── doc/
        ├── mkdocs.yml
        ├── requirements.txt
        └── docs/

O diretório `web/` contém a aplicação Django.

O diretório `doc/` contém a documentação construída com [MkDocs](https://www.mkdocs.org/).

O arquivo `compose.yml` define os serviços usados pelo ambiente conteinerizado.

---

## Configuração das Variáveis de Ambiente

O projeto utiliza um arquivo `.env` na raiz do repositório para configurar nomes de containers e variáveis sensíveis.

Exemplo de configuração usada em desenvolvimento:

    POSTGRES_CONTAINER_NAME=lms_postgres

    NGINX_CONTAINER_NAME=lms_nginx

    REDIS_CONTAINER_NAME=lms_redis

    WEB_CONTAINER_NAME=lms_web
    WEB_SECRET_KEY='django-insecure-nf8=t46$_%+0@1g_zn6gy8_q$ksyiwkt@3251_9ls-gl9wc6h@'
    WEB_DEBUG=true

    # cria prof1-14, aluno1-5 e turmas de exemplo automaticamente no startup do container web
    CREATE_SEED=true

Em desenvolvimento, `WEB_DEBUG=true` facilita depuração e visualização de erros.

`WEB_ALLOWED_HOSTS` e `WEB_CSRF_TRUSTED_ORIGINS` não têm default no `core/settings.py` — sem elas o Django quebra no import com `AttributeError`. O `compose.yml` já fornece defaults próprios (`localhost,127.0.0.1` e `https://localhost,https://127.0.0.1`) para rodar via Docker sem configurar nada; só precisam ser definidas manualmente rodando fora do Docker (ver "Opção 2" abaixo).

Em produção, essa configuração deve ser desativada e os secrets devem ser protegidos — ver [Ambiente de Produção](prod.md).

---

## Opção 1 — Executando com Docker Compose

A forma mais próxima da infraestrutura prevista do projeto é utilizar [Docker Compose](https://docs.docker.com/compose/).

A partir da raiz do repositório, execute:

    docker compose up

Esse comando inicializa os principais serviços definidos no `compose.yml`:

- `postgres`: banco de dados PostgreSQL;
- `redis`: serviço Redis;
- `web`: aplicação Django;
- `nginx`: proxy HTTP/HTTPS.

Durante a inicialização, o container `web` executa automaticamente algumas etapas:

    pip install -r requirements.txt
    python manage.py migrate
    python manage.py seed        # só roda se CREATE_SEED=true no .env
    python manage.py collectstatic --noinput
    uvicorn core.asgi:application

`docker compose up` sozinho **não** sobe o serviço `nginx` (ele fica atrás de um profile). Como `STATIC_URL`/`FORCE_SCRIPT_NAME` usam o prefixo fixo `/sistemadegestaodeaprendizagem/` sempre ativo, navegar pelo site direto na porta 8000 sem o Nginx removendo esse prefixo antes resulta em 404 em praticamente qualquer link. Pra testar navegação real, suba com:

    docker compose --profile with_nginx up -d

Após a inicialização, a aplicação deve ficar disponível em:

    http://localhost

ou, dependendo da configuração de portas:

    http://127.0.0.1:8000

---

## Opção 2 — Executando Localmente com Ambiente Virtual

Também é possível executar a aplicação diretamente pelo ambiente local, dentro do diretório `web/`. Como não há mais fallback para SQLite/cache em memória, é preciso ter um PostgreSQL e um Redis acessíveis (local ou via `docker compose up postgres redis`) e exportar `WEB_ALLOWED_HOSTS`/`WEB_CSRF_TRUSTED_ORIGINS` manualmente — sem isso o settings quebra no import.

Entre no diretório da aplicação:

    cd web

Crie um ambiente virtual:

    python -m venv .venv

Ative o ambiente virtual:

    .\.venv\Scripts\activate

Instale as dependências:

    pip install -r requirements.txt

Exporte as variáveis obrigatórias (ajuste os hosts do Postgres/Redis se não forem `localhost`):

    $env:WEB_ALLOWED_HOSTS = "localhost,127.0.0.1"
    $env:WEB_CSRF_TRUSTED_ORIGINS = "http://localhost,http://127.0.0.1"
    $env:POSTGRES_CONTAINER_NAME = "localhost"
    $env:REDIS_CONTAINER_NAME = "localhost"

Execute as migrações:

    python manage.py migrate

Carregue dados iniciais de desenvolvimento:

    python manage.py seed

Inicie o servidor local:

    python manage.py runserver

A aplicação ficará disponível em:

    http://127.0.0.1:8000/

---

## Dados Iniciais de Desenvolvimento

O projeto possui um comando customizado chamado `seed`, localizado no app `common`.

Esse comando cria usuários e turmas de teste para facilitar a navegação durante o desenvolvimento:

    python manage.py seed

O comando cria usuários de exemplo com o padrão:

    prof1
    prof2
    prof3
    ...

A senha definida para os usuários de teste é:

    123Abc!

Esses dados são apenas para desenvolvimento e não devem ser utilizados em ambiente de produção.

---

## Rotas Principais

Após iniciar o servidor, algumas rotas úteis são:

    /

Página inicial da aplicação.

    /home/

Página inicial após autenticação.

    /accounts/login/

Tela de login.

    /accounts/logout/

Logout do sistema.

    /accounts/google/login/

Inicia o login social pelo Google (requer `GOOGLE_OAUTH_CLIENT_ID`/`GOOGLE_OAUTH_CLIENT_SECRET` configurados — ver [Ambiente de Produção](prod.md)).

    /group/active/

Listagem de turmas ativas.

    /group/shared/

Listagem de turmas compartilhadas.

    /group/archived/

Listagem de turmas arquivadas.

    /activity/

Área relacionada às atividades.

    /admin/

Painel administrativo do Django.

---

## Executando a Documentação Localmente

A documentação possui ambiente próprio no diretório `doc/`.

Entre no diretório da documentação:

    cd doc

Ative o ambiente virtual:

    .\.venv\Scripts\activate

Instale as dependências, se necessário:

    pip install -r requirements.txt

Inicie o servidor da documentação:

    mkdocs serve

A documentação ficará disponível em:

    http://127.0.0.1:8000/

Caso a aplicação Django já esteja usando a porta `8000`, execute o MkDocs em outra porta:

    mkdocs serve -a 127.0.0.1:8001

---

## Verificações Úteis

Antes de iniciar uma alteração no código, é recomendável executar a verificação do Django:

    python manage.py check

Esse comando identifica problemas de configuração, modelos, URLs e integrações básicas do projeto.

Também é recomendável conferir se há migrações pendentes:

    python manage.py makemigrations --check --dry-run

---

## Fluxo Recomendado de Desenvolvimento

Um fluxo básico de trabalho para desenvolvimento local é:

1. Atualizar o repositório local.
2. Ativar o ambiente virtual.
3. Instalar dependências, caso tenham sido alteradas.
4. Aplicar migrações.
5. Executar o comando `seed`, se precisar de dados de teste.
6. Rodar `python manage.py check`.
7. Iniciar o servidor.
8. Implementar e testar a alteração.
9. Atualizar a documentação quando houver mudança relevante.

Exemplo:

    cd web
    .\.venv\Scripts\activate
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py check
    python manage.py runserver

---

## Observações Importantes

Não há mais fallback para SQLite ou cache em memória em nenhum ambiente — `core/settings.py` sempre exige PostgreSQL e Redis reais, tanto localmente quanto em produção. `WEB_DEBUG` controla apenas o `DEBUG` do Django, não troca de banco/cache.

Isso significa que o comportamento do banco (constraints, concorrência, locks, performance de consultas) já é o mesmo entre desenvolvimento e produção — não há mais divergência a considerar nesse ponto.

Da mesma forma, o Celery não tem mais modo *eager* em desenvolvimento: exercícios do tipo `code` exigem um worker Celery real (`docker compose up` já sobe o serviço `celery`) mesmo localmente.

---

## Problemas Comuns

### Django não encontrado

Se o comando `python manage.py check` retornar erro informando que o Django não foi encontrado, verifique se o ambiente virtual está ativado:

    .\.venv\Scripts\activate

Depois instale as dependências:

    pip install -r requirements.txt

### Porta 8000 em uso

Se a porta `8000` já estiver ocupada, execute o servidor Django em outra porta:

    python manage.py runserver 8001

Ou execute o MkDocs em outra porta:

    mkdocs serve -a 127.0.0.1:8001

### Containers não iniciam corretamente

Se estiver usando Docker Compose, verifique se o Docker está em execução e se o arquivo `.env` existe na raiz do projeto.

Também é possível reconstruir os serviços com:

    docker compose up --build
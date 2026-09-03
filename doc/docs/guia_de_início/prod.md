# Ambiente de Produção

Este guia descreve como implantar o **Sistema de Gestão de Aprendizagem** em produção via Docker Compose, com Nginx como proxy reverso.

---

## Pré-requisitos

- Servidor Linux com [Docker](https://docs.docker.com/) e [Docker Compose](https://docs.docker.com/compose/) instalados.
- Domínio apontando para o servidor (ex.: `dev-dcomp.ufsj.edu.br`).
- Acesso de escrita ao repositório clonado no servidor (`/opt/Sistema-de-Gestao-de-Aprendizagem` ou similar).

---

## Variáveis de Ambiente (`.env`)

Crie um `.env` na raiz do repositório (mesmo diretório do `compose.yml`) a partir do `.env.example`. As variáveis abaixo **não têm default** em `core/settings.py` — se ausentes, o Django quebra no import com `AttributeError`:

```
WEB_ALLOWED_HOSTS=localhost,127.0.0.1,<seu-dominio>
WEB_CSRF_TRUSTED_ORIGINS=https://localhost,https://127.0.0.1,https://<seu-dominio>
```

Atenção ao formato: `WEB_ALLOWED_HOSTS` são hosts puros (sem `http://`); `WEB_CSRF_TRUSTED_ORIGINS` precisa do `scheme://host` completo (o `Origin` enviado pelo navegador inclui o esquema).

Demais variáveis relevantes em produção:

```
WEB_DEBUG=false
WEB_SECRET_KEY=<chave secreta forte>

POSTGRES_DB=lms
POSTGRES_USER=lms_user
POSTGRES_PASSWORD=<senha forte>

REDIS_PASSWORD=<senha forte>

# Não criar usuários/turmas de teste em produção:
CREATE_SEED=false
```

`CREATE_SEED` controla se o comando `seed` (prof1-14, aluno1-5, turmas de exemplo) roda automaticamente no startup do container `web`. Deixe `false` (ou omitido) em produção.

---

## Nginx é obrigatório em produção

`STATIC_URL`, `MEDIA_URL` e `FORCE_SCRIPT_NAME` usam o prefixo fixo `/sistemadegestaodeaprendizagem/`, sempre ativo — todo link gerado por `reverse()`/`{% url %}` sai com esse prefixo. O Django, porém, roteia contra o path bruto que o servidor recebe: sem algo removendo esse prefixo antes de repassar pro `uvicorn`, **toda navegação do site dá 404** (incluindo o próprio login).

O serviço `nginx` do `compose.yml` já faz essa remoção:

```nginx
location /sistemadegestaodeaprendizagem/ {
    proxy_pass http://web:8000/;
}
```

Por isso, em produção suba com o profile `with_nginx`:

```bash
docker compose --profile with_nginx up -d
```

`docker compose up` sozinho (sem o profile) não sobe o Nginx — útil só pra rodar comandos de manutenção (`migrate`, `pytest`, `shell`) direto no container `web`, não para navegação real.

---

## Login social (Google)

O sistema aceita login/cadastro via Google (`django-allauth`). Pra habilitar:

### 1. Criar credenciais no Google Cloud Console

Em [console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials), crie um **OAuth client ID** do tipo *Web application*.

**Authorized redirect URI** (exato, com o prefixo da aplicação):

```
https://<seu-dominio>/sistemadegestaodeaprendizagem/accounts/google/login/callback/
```

Copie o **Client ID** e o **Client Secret** gerados.

### 2. Configurar no `.env`

```
GOOGLE_OAUTH_CLIENT_ID=<client id>
GOOGLE_OAUTH_CLIENT_SECRET=<client secret>
```

Sem essas variáveis (vazias), o redirect pro Google falha (client_id vazio na URL de autorização).

### 3. Comportamento

- Login com Google só autentica quem já tem `User` cadastrado com o mesmo e-mail (vínculo automático) **ou** permite criar uma conta nova escolhendo o papel (Professor/Aluno) — não há restrição de domínio nem aprovação de admin. Ver [Autenticação](../arquitetura.md) em Arquitetura e Tecnologias para o fluxo completo.
- A dependência `PyJWT[crypto]` (em `requirements.txt`) é obrigatória — o allauth decodifica o `id_token` (JWT) do Google via `PyJWT` + `cryptography`. Sem ela, o callback quebra com `ModuleNotFoundError: No module named 'jwt'` só no momento do login real (nenhum teste/check acusa isso antes).

---

## Deploy

```bash
git pull
docker compose build web celery       # necessário sempre que requirements.txt ou os Dockerfiles mudarem
docker compose --profile with_nginx up -d
```

`docker compose up -d` sozinho **recria** containers cujo `command`/imagem mudou, mas não força rebuild da imagem a partir de um `requirements.txt` alterado — depois de mudar dependências, sempre rode `docker compose build` antes.

Variáveis de ambiente só são lidas na **criação** do container. Editar o `.env` não tem efeito em um container já rodando — depois de qualquer mudança no `.env`, recrie:

```bash
docker compose up -d --force-recreate web
```

---

## Problemas Comuns

### `403 Forbidden` — "Origin checking failed"

`WEB_CSRF_TRUSTED_ORIGINS` não inclui o domínio real, ou o container não foi recriado depois de editar o `.env`. Confirme o valor que o Django realmente carregou:

```bash
docker compose exec web python manage.py shell -c "from django.conf import settings; print(settings.CSRF_TRUSTED_ORIGINS)"
```

Se o valor não bater com o `.env`, suspeite de uma variável de ambiente do shell/sistema sobrescrevendo o `.env` — Docker Compose prioriza o ambiente do processo sobre o arquivo `.env`. Cheque:

```bash
docker compose config | grep WEB_CSRF_TRUSTED_ORIGINS
```

### `404` navegando pelo site

Falta o Nginx na frente (ver seção acima) — suba com `--profile with_nginx`, não só `docker compose up`.

### `ModuleNotFoundError: No module named 'jwt'` no callback do Google

Falta `PyJWT[crypto]` instalado na imagem — confirme que está em `requirements.txt` e rode `docker compose build web`.

### `invalid username-password pair or user is disabled` (Redis)

O container `redis` só lê `--requirepass` uma vez, no startup (não é persistido no volume). Se `redis` já estava rodando de antes de uma mudança em `REDIS_PASSWORD`, ele continua com a senha antiga em memória enquanto os outros serviços tentam autenticar com a nova. Recrie o Redis (e por segurança, o stack todo):

```bash
docker compose down
docker compose --profile with_nginx up -d
```

---

## Verificações Pós-Deploy

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py showmigrations   # confirma que não há migração pendente
docker compose exec web python -m pytest -q                 # requer pytest/pytest-django instalados (ver requirements.txt)
```

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

## Login social (Google e GitHub)

O sistema aceita login/cadastro via Google e via GitHub (`django-allauth`). Cada provedor tem suas próprias credenciais; habilite um, os dois, ou nenhum — o botão de um provedor sem credenciais configuradas simplesmente redireciona pro provedor com `client_id` vazio, que rejeita o pedido.

### Google

Em [console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials), crie um **OAuth client ID** do tipo *Web application*.

**Authorized redirect URI** (exato, com o prefixo da aplicação):

```
https://<seu-dominio>/sistemadegestaodeaprendizagem/accounts/google/login/callback/
```

Copie o **Client ID** e o **Client Secret** gerados, e configure no `.env`:

```
GOOGLE_OAUTH_CLIENT_ID=<client id>
GOOGLE_OAUTH_CLIENT_SECRET=<client secret>
```

### GitHub

Em [github.com/settings/developers](https://github.com/settings/developers) → **OAuth Apps** → **New OAuth App**.

**Authorization callback URL** (exato, com o prefixo da aplicação):

```
https://<seu-dominio>/sistemadegestaodeaprendizagem/accounts/github/login/callback/
```

Copie o **Client ID** e gere um **Client Secret**, e configure no `.env`:

```
GITHUB_OAUTH_CLIENT_ID=<client id>
GITHUB_OAUTH_CLIENT_SECRET=<client secret>
```

Não é necessário marcar nenhum escopo especial na tela do GitHub — o allauth já pede `user:email` automaticamente (`SOCIALACCOUNT_PROVIDERS['github']['SCOPE']`), necessário pra obter o e-mail de usuários com "Keep my email address private" ativado no perfil.

### Comportamento (comum aos dois provedores)

- Login social só autentica quem já tem `User` cadastrado com o mesmo e-mail (vínculo automático) **ou** permite criar uma conta nova escolhendo o papel (Professor/Aluno) — não há restrição de domínio nem aprovação de admin. Ver [Autenticação](../arquitetura.md) em Arquitetura e Tecnologias para o fluxo completo.
- A dependência `PyJWT[crypto]` (em `requirements.txt`) é obrigatória pro Google — o allauth decodifica o `id_token` (JWT) do Google via `PyJWT` + `cryptography`. Sem ela, o callback do Google quebra com `ModuleNotFoundError: No module named 'jwt'` só no momento do login real (nenhum teste/check acusa isso antes). O GitHub não usa JWT, não depende do `PyJWT`.

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

### GitHub/Google recusa o login: "redirect_uri is not associated with this application"

O `redirect_uri` que o Django manda pro provedor saiu com `http://` em vez de `https://` (o provedor recusa por não bater com a URL cadastrada, que é `https://...`). Acontece porque a conexão nginx→uvicorn é HTTP puro internamente — sem `SECURE_PROXY_SSL_HEADER` configurado, o Django não sabe que o cliente real chegou via HTTPS e monta a URL com o scheme errado.

O `core/settings.py` já define `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`, confiando no header que o nginx (`nginx/nginx.conf.template`) sempre define (`proxy_set_header X-Forwarded-Proto $scheme;`, sobrescrevendo qualquer valor que o cliente tenha enviado — seguro confiar). Se isso ainda acontecer, confirme que está navegando através do Nginx (`--profile with_nginx`) e não direto na porta do `web`.

### `500 Internal Server Error` no cadastro via GitHub — `NoReverseMatch: account_confirm_email`

Acontece quando o GitHub não devolve nenhum e-mail verificado utilizável (ex.: perfil com "Keep my email address private" ativado e a API `/user/emails` não retornando nada aproveitável). Nesse caso o allauth tenta mandar um e-mail de confirmação local — mas `allauth.account.urls` não está incluído no roteamento (de propósito, pra não expor login/cadastro por senha do allauth), então a URL `account_confirm_email` não existe e a requisição quebra.

`core/settings.py` já define `SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'`, desligando esse fluxo pro login social — já confiamos no e-mail verificado pelo próprio provedor (é a base do vínculo por e-mail em `pre_social_login`), então não faz sentido pedir confirmação de novo.

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

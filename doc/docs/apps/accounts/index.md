# accounts

O app **accounts** estende o `User` padrão do Django com preferências persistidas em JSON, implementa o middleware responsável por gerenciar cookies entre requisições e conecta os eventos de login e logout a comportamentos específicos da plataforma.

## Estrutura

| Módulo | Conteúdo |
|--------|----------|
| models | [UserPreferences](models/UserPreferences.md) |
| middleware | [CookieMiddleware](middleware/CookieMiddleware.md) |
| signals | [on_login](signals/on_login.md), [on_logout](signals/on_logout.md) |

# accounts

O app **accounts** estende o `User` padrão do Django com preferências persistidas em JSON, implementa o middleware responsável por gerenciar cookies entre requisições, conecta os eventos de login e logout a comportamentos específicos da plataforma e integra o login social via Google e GitHub (`django-allauth`).

## Estrutura

| Módulo | Conteúdo |
|--------|----------|
| models | [UserPreferences](models/UserPreferences.md) |
| middleware | [CookieMiddleware](middleware/CookieMiddleware.md) |
| signals | [on_login](signals/on_login.md), [on_logout](signals/on_logout.md) |
| adapters | [SocialAccountAdapter](adapters/SocialAccountAdapter.md) |
| forms | [SocialSignupForm](forms/SocialSignupForm.md) |
| templatetags | [pop_login_view_mode](templatetags/pop_login_view_mode.md) |

## Login social (Google e GitHub)

Ver [Arquitetura e Tecnologias](../../arquitetura.md) para o fluxo completo (vínculo por e-mail, cadastro com escolha de papel, e como o papel força o modo de visualização no primeiro carregamento após o login).

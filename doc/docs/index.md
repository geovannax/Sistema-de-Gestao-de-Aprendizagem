# Sistema de Gestão de Aprendizagem

Bem-vindo à documentação oficial do **Sistema de Gestão de Aprendizagem**, uma plataforma web em desenvolvimento no contexto de uma pesquisa de mestrado em Ciência da Computação.

O sistema tem como foco apoiar práticas de **avaliação formativa**, organização de atividades educacionais e análise de dados de aprendizagem. A proposta combina desenvolvimento de software, documentação técnica e investigação acadêmica, buscando construir uma base tecnológica capaz de apoiar docentes na observação, acompanhamento e interpretação do processo de aprendizagem dos estudantes.

---

## Visão Geral

O **Sistema de Gestão de Aprendizagem** é uma plataforma desenvolvida com [Django](https://docs.djangoproject.com/) e [Docker](https://docs.docker.com/), projetada para gerenciar turmas, atividades, exercícios, contas de usuários e fluxos relacionados ao acompanhamento educacional.

Diferentemente de um sistema voltado apenas ao registro de conteúdos ou entregas, este projeto está orientado à coleta e análise de dados do processo de aprendizagem. A plataforma busca permitir que informações como tentativas, erros, tempo de resposta, padrões de interação e desempenho sejam utilizadas como subsídios para intervenções pedagógicas mais precisas.

O sistema também se insere em um contexto de pesquisa sobre o impacto das tecnologias digitais e das IAs generativas nos processos avaliativos. Nesse sentido, sua evolução técnica é acompanhada por documentação contínua, registro de decisões arquiteturais e organização incremental das funcionalidades.

Entre os principais objetivos do projeto estão:

- apoiar a avaliação formativa por meio de informações individualizadas para docentes;
- organizar turmas, atividades, exercícios e usuários em uma plataforma web integrada;
- coletar dados de processo relacionados à aprendizagem;
- fornecer subsídios pedagógicos para intervenções educacionais mais eficazes;
- explorar o uso de [Learning Analytics](https://www.solaresearch.org/about/what-is-learning-analytics/) no acompanhamento de estudantes;
- investigar impactos da IA generativa no processo avaliativo;
- documentar decisões de arquitetura, implementação e evolução do sistema;
- adotar práticas profissionais de engenharia de software e documentação como código.

---

## Estrutura do Sistema

O sistema é composto por múltiplos aplicativos [Django](https://docs.djangoproject.com/), cada um responsável por uma parte específica da solução.

- **accounts**: gerenciamento de usuários, preferências e dados relacionados às contas;
- **authentication**: autenticação, login, logout e fluxos de acesso ao sistema;
- **activity**: criação e controle de atividades, listas de atividades, exercícios e alternativas;
- **group**: organização de turmas, compartilhamento, arquivamento e controle de acesso;
- **common**: componentes reutilizáveis, mixins, views genéricas, utilitários e estruturas compartilhadas;
- **core**: configurações principais do projeto Django, URLs globais, ASGI e WSGI.

Essa separação busca manter o projeto organizado por responsabilidades, facilitando manutenção, testes, evolução funcional e documentação técnica.

---

## Arquitetura e Tecnologias

A aplicação é construída com uma arquitetura web baseada em [Django](https://docs.djangoproject.com/), priorizando renderização server-side, simplicidade operacional e evolução progressiva da interface.

A stack principal do projeto inclui:

- [Django](https://docs.djangoproject.com/) como framework backend principal;
- [Django ORM](https://docs.djangoproject.com/en/stable/topics/db/) para modelagem e acesso a dados;
- [Django Templates](https://docs.djangoproject.com/en/stable/topics/templates/) para renderização das páginas;
- [Bootstrap](https://getbootstrap.com/docs/) para composição da interface;
- [HTMX](https://htmx.org/docs/) como estratégia preferencial para interações dinâmicas progressivas;
- [PostgreSQL](https://www.postgresql.org/docs/) como banco de dados previsto para ambientes produtivos;
- [Redis](https://redis.io/docs/latest/) para cenários de cache, filas ou otimizações futuras;
- [Docker](https://docs.docker.com/) e [Docker Compose](https://docs.docker.com/compose/) para padronização dos ambientes;
- [Nginx](https://nginx.org/en/docs/) e [Gunicorn](https://docs.gunicorn.org/en/stable/) como componentes previstos para deploy em produção;
- [MkDocs](https://www.mkdocs.org/) e [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) para documentação técnica versionada;
- [mkdocstrings](https://mkdocstrings.github.io/) para geração de referência técnica a partir do código Python.

A proposta arquitetural favorece uma aplicação server-driven, evitando complexidade desnecessária no frontend e mantendo as regras principais no backend.

---

## Documentação como Código

Esta documentação segue a abordagem **docs-as-code**, sendo mantida no mesmo repositório do sistema. Isso permite que a documentação evolua junto com o código-fonte, registrando decisões técnicas, estrutura do projeto, regras de negócio e instruções de desenvolvimento.

A documentação é construída com [MkDocs](https://www.mkdocs.org/), [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) e [mkdocstrings](https://mkdocstrings.github.io/), permitindo organizar guias, páginas técnicas, referências de código e conteúdos de apoio ao desenvolvimento.

A documentação tem como objetivos:

- orientar a configuração dos ambientes de desenvolvimento e produção;
- registrar a arquitetura do sistema;
- documentar os apps Django e suas responsabilidades;
- descrever regras de negócio relevantes;
- explicar fluxos técnicos e funcionais;
- apoiar futuras manutenções e evoluções do projeto;
- servir como evidência técnica do processo de desenvolvimento da pesquisa.

---

## Primeiros Passos

Para configurar o ambiente e executar o projeto, consulte os guias iniciais:

- [Guia de Início — Desenvolvimento](guia_de_início/dev.md)
- [Guia de Início — Produção](guia_de_início/prod.md)

Esses guias reúnem instruções sobre instalação, dependências, execução local, uso de [Docker](https://docs.docker.com/) e preparação dos ambientes.

---

## Estrutura da Documentação

A documentação está organizada para acompanhar tanto a perspectiva técnica quanto a evolução acadêmica do projeto.

Os principais grupos de conteúdo previstos são:

- guias de início rápido para desenvolvimento e produção;
- documentação dos apps Django;
- descrição da arquitetura e estrutura de pastas;
- regras de negócio e fluxos principais;
- referência técnica de models, forms, views e serviços;
- instruções de deploy e infraestrutura;
- troubleshooting;
- decisões arquiteturais e evolução do sistema.

Explore o menu lateral para navegar pelos tópicos detalhados.

---

## Sobre o Projeto

O **Sistema de Gestão de Aprendizagem** é desenvolvido como parte de uma pesquisa de mestrado vinculada ao [Programa de Pós-Graduação em Ciência da Computação da Universidade Federal de São João del-Rei](https://sig.ufsj.edu.br/sigaa/public/programa/portal.jsf?id=2031&lc=pt_BR), no âmbito do [Departamento de Ciência da Computação](https://ufsj.edu.br/dcomp/) da [Universidade Federal de São João del-Rei](https://www.ufsj.edu.br/).

O projeto é desenvolvido por **Geovanna Vittória de J. Assis**, no contexto do **Laboratório MIC**, sob orientação do professor **Alexandre Bittencourt Pigozzo**. A pesquisa está associada à linha de **Otimização e Inteligência Computacional** e tem como objetivo apoiar investigações relacionadas à avaliação formativa, análise de aprendizagem e uso de dados educacionais em ambientes digitais.

Além de sua finalidade técnica como plataforma web para gestão de turmas, atividades, exercícios e usuários, o sistema também constitui um artefato de pesquisa. Sua evolução busca registrar decisões arquiteturais, práticas de engenharia de software, estratégias de documentação como código e possibilidades de uso de [Learning Analytics](https://www.solaresearch.org/about/what-is-learning-analytics/) para apoiar o trabalho docente.

Este projeto será utilizado como parte da defesa do título de mestre da autora, servindo como base prática e experimental para o desenvolvimento, validação e análise da proposta de pesquisa.

Dúvidas, sugestões e contribuições podem ser encaminhadas por meio do [repositório GitHub do projeto](https://github.com/geovannax/Sistema-de-Gestao-de-Aprendizagem) ou pelo e-mail: geovannaassis@educacao.mg.gov.br.
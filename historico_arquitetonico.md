# Histórico da Arquitetura

## Projeto

**CAGED API – Joinville**

---

# Objetivo

Este documento registra a evolução arquitetural da CAGED API desde o início do desenvolvimento, documentando as principais decisões técnicas, mudanças estruturais, desafios enfrentados e melhorias implementadas.

O objetivo é preservar o histórico da construção da aplicação, permitindo compreender como a arquitetura evoluiu ao longo do projeto.

---

# Linha do Tempo

---

# 16/06/2026 — Recomeço do Projeto

## Situação Inicial

Após aproximadamente dez dias de desenvolvimento, foi constatado que a primeira estrutura do projeto apresentava diversos problemas que inviabilizavam sua continuidade.

Entre os principais problemas identificados estavam:

* arquitetura pouco organizada;
* configuração incorreta do ambiente;
* ausência de ambiente virtual;
* gerenciamento inadequado de dependências;
* estrutura de diretórios inconsistente;
* arquivos corrompidos;
* problemas de importação entre módulos;
* ausência do `uv` como gerenciador do projeto.

### Decisão

Foi decidido reiniciar completamente o desenvolvimento, preservando apenas o conhecimento adquirido durante a primeira tentativa.

### Resultado

Ao final do dia foi possível concluir:

* configuração completa do ambiente;
* instalação das dependências;
* criação do ambiente virtual;
* organização inicial da arquitetura;
* definição da nova estrutura do projeto.

---

# 17/06/2026 — Estrutura Inicial da API

Nesta etapa iniciou-se a implementação da base da aplicação.

Foram desenvolvidos:

* estrutura inicial do FastAPI;
* organização das pastas;
* primeiros módulos da API;
* estrutura inicial do banco de dados;
* documentação inicial.

Também foi realizado um estudo das tecnologias utilizadas, incluindo FastAPI, SQLAlchemy e PostgreSQL.

---

# 18/06/2026 — Planejamento da Arquitetura

Foi definido que o projeto utilizaria uma arquitetura baseada em separação de responsabilidades.

A estrutura planejada passou a seguir o fluxo:

```text
Fonte de Dados
      │
      ▼
Collectors
      │
      ▼
Transformers
      │
      ▼
Repository
      │
      ▼
PostgreSQL
      │
      ▼
FastAPI
      │
      ▼
Swagger
```

Também foi definido que a aplicação utilizaria:

* operações CRUD;
* processo ETL (Extract, Transform and Load);
* atualização automática dos dados;
* documentação automática da API.

---

# 22/06/2026 — Integração com PostgreSQL

Foi concluída a comunicação entre a API e o banco de dados PostgreSQL.

Durante esta etapa foram realizados diversos ajustes relacionados à estrutura do projeto, importações e organização dos módulos.

### Conquistas

* conexão estabelecida entre FastAPI e PostgreSQL;
* criação automática das tabelas;
* preparação para armazenamento dos dados.

---

# 23/06/2026 — Primeira Versão Funcional

O projeto passou a possuir uma estrutura funcional.

### Implementações

* API local funcionando;
* banco conectado;
* criação automática das tabelas;
* persistência correta dos dados;
* documentação Swagger disponível;
* primeiros testes realizados.

Também foi iniciada uma reorganização da arquitetura visando maior escalabilidade.

---

# Julho/2026 — Migração para Novo Ambiente

Durante o desenvolvimento ocorreu a migração completa do projeto para um novo computador.

### Ambiente

* MacBook Pro Apple Silicon (M5);
* Python 3.14;
* Homebrew;
* PostgreSQL 17;
* IntelliJ IDEA;
* uv.

Durante a migração foram novamente configurados:

* ambiente virtual;
* banco PostgreSQL;
* variáveis de ambiente;
* Git;
* GitHub;
* IntelliJ;
* bibliotecas Python.

Essa etapa também serviu para padronizar completamente o ambiente de desenvolvimento.

---

# Julho/2026 — Consolidação da Arquitetura

Após a migração iniciou-se uma revisão completa da arquitetura.

Praticamente todos os módulos do projeto foram revisados.

Entre eles:

* main.py
* app.py
* conexão com banco
* modelos SQLAlchemy
* routers
* scheduler
* services
* collectors
* transformers
* repository
* documentação
* tratamento de exceções
* tipagem
* comentários
* organização dos imports

Grande parte do código foi refatorada para seguir um padrão único.

---

# Outubro/2026 — Segunda Fonte de Dados: CEMPRE (IBGE)

O projeto passou a integrar uma segunda fonte de dados: o **CEMPRE** (Cadastro Central de Empresas), pesquisa anual do IBGE.

Enquanto o CAGED mostra o **fluxo** do emprego (admissões e demissões mês a mês), o CEMPRE mostra o **estoque** (quantas unidades, pessoas ocupadas e salário médio existem em cada setor, uma vez por ano).

### Implementação

* coleta pela API do SIDRA (tabela 9510, por seção da CNAE 2.0);
* transformer com pivot das variáveis e tratamento dos símbolos especiais do IBGE;
* tabela própria (`cempre_emprego`) criada via Alembic;
* repositório, service e router próprios;
* job mensal próprio no scheduler;
* carga histórica de 2022 a 2024.

### Desafios

* escolher a tabela correta do SIDRA: a 9509 não abre os dados por setor;
* diferenciar zero absoluto (`-`) de valor sigiloso (`X`) ou indisponível (`...`);
* evitar que a linha "Total" do IBGE seja somada junto com as seções;
* garantir que um erro no CEMPRE não afete o CAGED.

---

# Principais Decisões Arquiteturais

Durante essa fase foram tomadas decisões importantes.

## Separação em camadas

A aplicação passou a ser organizada em módulos independentes.

```text
Collectors

↓

Transformers

↓

Repository

↓

Database

↓

API
```

Essa decisão reduziu o acoplamento entre os componentes e facilitou futuras manutenções.

---

## Classe Base para Coletores

Foi criada uma classe abstrata responsável por centralizar funcionalidades comuns aos coletores.

Benefícios:

* reutilização de código;
* padronização;
* manutenção simplificada.

---

## Scheduler

O sistema de atualização automática foi isolado em um módulo específico.

Essa separação evita dependências desnecessárias entre a API e as tarefas agendadas.

---

## Repository

Toda a comunicação com o banco passou a ser concentrada em um único módulo.

Essa decisão evita que os Routers executem consultas SQL diretamente.

---

## Padronização

Durante a revisão geral foram definidos padrões para:

* organização dos imports;
* tipagem;
* comentários;
* docstrings;
* tratamento de exceções;
* nomes de funções;
* estrutura dos arquivos.

---

## Isolamento por Fonte de Dados

Cada fonte de dados (CAGED, CEMPRE) possui seus próprios collector, transformer, repositório, service e router.

O router do CEMPRE é registrado de forma protegida na aplicação, e o job do CEMPRE possui tratamento de erro próprio no scheduler.

Essa decisão garante que a falha de uma fonte não derrube a outra, sem a necessidade de manter servidores separados.

---

## Valores Não Divulgados

Valores omitidos pelo IBGE (sigilosos ou indisponíveis) são gravados como `NULL`, e não como `0`.

Essa decisão evita que a ausência de informação seja confundida com um valor real igual a zero.

---

## Migrações com Alembic

A partir do CEMPRE, alterações no banco passaram a ser feitas por migrações versionadas do Alembic.

Essa decisão permite aplicar e desfazer mudanças de forma controlada, mantendo o histórico do schema junto com o código.

---

# Estado Atual da Arquitetura

Atualmente a arquitetura segue o fluxo abaixo.

```text
Cliente

↓

FastAPI

↓

Routers

↓

Services

↓

Collectors

↓

Transformers

↓

Repository

↓

PostgreSQL
```

Essa estrutura facilita manutenção, expansão e testes.

---

# Tecnologias

* Python
* FastAPI
* SQLAlchemy
* PostgreSQL
* Pandas
* APScheduler
* Alembic
* Pydantic
* Uvicorn
* uv

---

# Lições Aprendidas

Durante o desenvolvimento foram obtidos aprendizados importantes.

* Uma boa arquitetura reduz significativamente retrabalho.
* Configurar corretamente o ambiente desde o início economiza tempo.
* Separação de responsabilidades facilita evolução da aplicação.
* Refatorações periódicas aumentam a qualidade do código.
* Documentar decisões técnicas torna a manutenção mais simples.
* Isolar cada fonte de dados permite crescer o projeto sem aumentar o risco de quebrar o que já funciona.
* Dado ausente e dado igual a zero são informações diferentes e precisam ser tratados de formas diferentes.

---

# Próximos Passos

As próximas versões da aplicação deverão contemplar:

* implementação completa da coleta automática do CAGED;
* avaliação dos anos do CEMPRE anteriores a 2022;
* ampliação da cobertura de testes;
* melhoria da documentação técnica;
* Docker;
* CI/CD;
* monitoramento da aplicação;
* preparação para ambiente de produção.

---

# Histórico de Evolução

| Data       | Marco                                                    |
| ---------- | -------------------------------------------------------- |
| 16/06/2026 | Reinício completo do projeto                             |
| 17/06/2026 | Estrutura inicial da API                                 |
| 18/06/2026 | Definição da arquitetura em camadas                      |
| 22/06/2026 | Integração com PostgreSQL                                |
| 23/06/2026 | Primeira versão funcional                                |
| Julho/2026 | Migração para novo ambiente de desenvolvimento           |
| Julho/2026 | Revisão completa da arquitetura e padronização do código |
| Outubro/2026 | Integração do CEMPRE (IBGE) como segunda fonte de dados |

---

# Considerações Finais

A CAGED API evoluiu de uma estrutura inicial experimental para uma aplicação organizada em camadas, com responsabilidades bem definidas e preparada para crescimento.

Além da implementação técnica, o projeto representou uma evolução significativa no estudo de Engenharia de Software, arquitetura de aplicações Python, integração com bancos de dados relacionais, consumo de dados públicos e boas práticas de desenvolvimento.

Este documento deverá ser atualizado continuamente à medida que novas funcionalidades, decisões arquiteturais e mudanças estruturais forem incorporadas ao projeto.

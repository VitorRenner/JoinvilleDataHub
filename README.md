# Joinville Data Hub

**API em Python que coleta, trata e entrega dados públicos oficiais sobre
emprego e empresas de Joinville/SC.**

Os dados vêm de três fontes do governo (Novo Cadastro Geral de Empregados e
Desempregados, Cadastro Central de Empresas e Receita Federal do Brasil),
chegam brutos e em formatos diferentes, e saem daqui limpos, padronizados e
prontos para consumo pelo site "Nexus", dentro do Programa de Iniciação
Científica (PIC).

Meu ideal central foi fazer sozinho um projeto com o nível de qualidade que
uma empresa ou um grupo de desenvolvedores entregaria, com o acompanhamento
do meu orientador.

![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat-square&logo=sqlalchemy&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white)

---

## O problema

Quem quer entender o mercado de trabalho de Joinville precisa baixar arquivos
enormes do governo, compactados, com layouts diferentes e com dados do Brasil
inteiro. Este projeto automatiza isso: baixa, filtra Joinville, trata e
entrega tudo numa API simples.

## Fontes de dados

| Fonte | Órgão | O que mostra | Freq. | Rota |
| --- | --- | --- | --- | --- |
| **CAGED** | MTE | Admissões, demissões e saldo por setor | Mensal | `/caged` |
| **CEMPRE** | IBGE | Unidades, pessoal e salário médio | Anual | `/cempre` |
| **CNPJ** | RFB | Empresas ativas, aberturas, MEI, Simples | Mensal | `/rfb` |
| **Municípios** | IBGE | Dados de localidades | — | `/ibge` |

## Arquitetura

Cada fonte passa pelo mesmo caminho, em arquivos separados:

```text
Fonte oficial ─▶ Collector ─▶ Transformer ─▶ Repositório ─▶ PostgreSQL ─▶ API
 (download)      baixa o      limpa e        grava com                FastAPI
                 arquivo      padroniza      upsert
                                                 ▲
              Scheduler (APScheduler, cron) roda as atualizações sozinho
```

**Decisões que tomei:**

- **Falha isolada:** CAGED, CEMPRE e RFB vivem nos próprios arquivos, inclusive
  os modelos do banco (`src/database/models/`, um arquivo por fonte). Os
  routers do CEMPRE e da RFB são registrados dentro de um `try`: se uma fonte
  quebrar, a API sobe sem ela e as outras continuam no ar.
- **Scheduler em processo próprio:** os jobs agendados rodam num container
  separado da API. Assim os 4 workers do Gunicorn não executam o mesmo job
  4 vezes.
- **Upsert em vez de insert:** rodar a mesma carga de novo atualiza os
  registros sem duplicar dados.
- **Banco versionado:** toda mudança de tabela passa por uma migration do
  Alembic.
- **Configuração tipada:** variáveis de ambiente lidas com
  `pydantic-settings`, nada de senha no código.
- **Sem dados pessoais:** a RFB é gravada agregada por competência e setor,
  nunca empresa por empresa, e o arquivo de sócios não é usado.

O histórico completo das decisões está em
[`docs/historico_arquitetonico.md`](docs/historico_arquitetonico.md).

## Tecnologias

| Camada | Ferramentas |
| --- | --- |
| API | FastAPI, Pydantic, Uvicorn, Gunicorn |
| Dados | Pandas, SQLAlchemy, PostgreSQL, Alembic, py7zr |
| Agendamento | APScheduler (gatilho cron) |
| Qualidade | pytest, Ruff, Black, mypy, GitHub Actions |
| Infra | Docker (multi-stage, usuário não-root), Docker Compose, uv |

## Endpoints principais

| Método | Rota | Descrição |
| --- | --- | --- |
| `GET` | `/docs` | Swagger com todas as rotas |
| `GET` | `/health` | Status da aplicação e do banco |
| `GET` | `/caged/` | CAGED (filtros: `competencia`, `setor`) |
| `POST` | `/caged/` · `/caged/bulk` | Cria ou atualiza um ou vários registros |
| `GET` | `/cempre/` | CEMPRE (filtros: `ano`, `setor`, `incluir_total`) |
| `GET` | `/rfb/` | RFB (filtros: `competencia`, `setor`, `incluir_total`) |
| `GET` | `/{fonte}/stats/resumo` | Resumo de `caged`, `cempre` ou `rfb` |
| `GET` | `/ibge/municipios` | Municípios do IBGE |

## Como rodar

### Com Docker (mais rápido)

```bash
cp .env.example .env.docker   # preencha com os dados do seu PostgreSQL
docker compose up --build
```

Sobem dois containers da mesma imagem: a **API** em
`http://localhost:8000/docs` e o **scheduler** com os jobs agendados.

### Localmente

Com o PostgreSQL rodando e o `.env` configurado a partir do `.env.example`:

```bash
uv sync                          # instala as dependências
uv run alembic upgrade head      # cria/atualiza as tabelas

# carrega os dados
uv run python -c "from src.services.atualizacao_caged import \
atualizar_caged; atualizar_caged(ano=2026, mes=6)"
uv run python -m src.services.atualizacao_cempre 2022 2023 2024
uv run python -m src.services.atualizacao_rfb    # competência mais recente

uv run uvicorn src.api.app:app --reload   # sobe a API
```

A carga da RFB baixa vários GB da Receita Federal e leva cerca de 1h30.
Competências específicas: `atualizacao_rfb 2026-09 2026-10`; para
reprocessar uma competência que já está no banco, acrescente `--forcar`.

Guia completo, passo a passo:
[`docs/COMO_RODAR_O_PROJETO.md`](docs/COMO_RODAR_O_PROJETO.md).

## Testes

```bash
uv run pytest -q
```

Os testes cobrem as rotas do CAGED e do CEMPRE, o collector do CAGED, o
health check e o transformer do CEMPRE. O GitHub Actions roda os testes a
cada push e pull request no `master`.

## Estrutura

```text
src/
├── api/            # app FastAPI e routers (caged, cempre, rfb, ibge)
├── collectors/     # download dos dados de cada fonte
├── transformers/   # limpeza e padronização
├── database/       # conexão, repositórios e models/ (um arquivo por fonte)
├── schemas/        # validação com Pydantic
├── services/       # fluxo completo de atualização de cada fonte
├── scheduler/      # jobs agendados
└── core/           # configurações e logging
alembic/            # migrations do banco
tests/              # testes com pytest
docs/               # documentação de cada integração
```

## Próximos passos

- [ ] Testes do transformer e do router da RFB
- [ ] Zerar os avisos do Ruff e tornar o lint obrigatório no CI
- [ ] Deploy público com link

## Documentação

- [`docs/COMO_RODAR_O_PROJETO.md`](docs/COMO_RODAR_O_PROJETO.md): instalação e
  execução
- [`docs/CEMPRE_API.md`](docs/CEMPRE_API.md): integração do CEMPRE
- [`docs/RFB_API.md`](docs/RFB_API.md): integração da RFB
- [`docs/BACKLOG.md`](docs/BACKLOG.md): evolução técnica e pendências
- [`docs/historico_arquitetonico.md`](docs/historico_arquitetonico.md):
  decisões de arquitetura

## Autor

**Vitor Rogge Renner**, estudante de Engenharia de Software e estagiário de
back-end Python.
[LinkedIn](https://www.linkedin.com/in/vitor-rogge-renner-5367b82b8) ·
[GitHub](https://github.com/VitorRenner)

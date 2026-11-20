# Joinville Data Hub

[![CI](https://github.com/VitorRenner/JoinvilleDataHub/actions/workflows/ci.yml/badge.svg)](https://github.com/VitorRenner/JoinvilleDataHub/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat-square&logo=sqlalchemy&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white)

**The official economic data of Joinville, Brazil (650,000 people) in a single API that keeps itself up to date.**

Anyone who wants to know how many jobs Joinville's industry added this month,
how many new companies opened, or what each sector pays has to dig through
multi-GB government files, each with its own layout and with all of Brazil
inside. Joinville Data Hub does that work on its own: it downloads, filters,
cleans and serves everything through an API.

Undergraduate research project, with a faculty advisor. I own the system end to
end: architecture, data, API, automation and infrastructure.

| | |
| --- | --- |
| 🤖 **AI** | `POST /perguntar` answers questions in plain Portuguese with an LLM agent (Gemini) that can only call read-only tools over this data, with an evaluation set measured against the real database ([details](#ask-in-plain-language)) |
| 🔌 **API** | One FastAPI REST service with 4 data domains (CAGED, CEMPRE, CNPJ and IBGE municipalities), Pydantic validation and Swagger at `/docs` |
| ⚙️ **Automation** | 3 scheduled ETL pipelines (CAGED, CEMPRE and Federal Revenue) that run with no manual steps, in a process separate from the API |
| 🗄️ **Data** | PostgreSQL with SQLAlchemy, 5 versioned Alembic migrations and idempotent loads (upsert): re-running a load updates rows instead of duplicating them |
| 🛡️ **Resilience** | Each source is isolated: if one breaks, the API starts without it and the others stay online |
| 🔐 **Security** | Reads are public, writes need a single-use token that only the server can issue: it expires in minutes, is stored as a hash and never works twice. Strict input validation and locked-down CORS ([SECURITY.md](SECURITY.md)) |
| 🔒 **Privacy** | Federal Revenue data is stored only in aggregate, never company by company; the partners file is not used |
| 🐳 **Infra** | Multi-stage Docker running as non-root, Compose with the API and the scheduler in separate containers, a dedicated server feeding the Nexus website; migration to Google Cloud in progress |
| ✅ **Quality** | 95 Pytest tests, Ruff and GitHub Actions on every push and pull request |

> **How this project was built:** I defined the problem, the data sources, the
> data model and the architecture, and drove every decision (logged in
> [`docs/historico_arquitetonico.md`](docs/historico_arquitetonico.md)).
> I used AI coding agents (Claude Code) as a pair programmer; every change goes
> through my review, automated tests and CI before it reaches `master`.
> More on that in [`docs/AI_USAGE.md`](docs/AI_USAGE.md).

---

## Data sources

| Source | Agency | What it shows | Frequency | Route |
| --- | --- | --- | --- | --- |
| **CAGED** | Ministry of Labor (MTE) | Hires, layoffs and net jobs by sector | Monthly | `/caged` |
| **CEMPRE** | IBGE | Business units, headcount and average wage | Yearly | `/cempre` |
| **CNPJ** | Federal Revenue (RFB) | Active companies, openings, MEI, Simples | Monthly | `/rfb` |
| **Municipalities** | IBGE | Location data | — | `/ibge` |

## Architecture

Every source follows the same path, in its own files:

```text
Official source ─▶ Collector ─▶ Transformer ─▶ Repository ─▶ PostgreSQL ─▶ API
  (download)       fetches the   cleans and     writes with               FastAPI
                   file          standardizes   upsert
                                                    ▲
            Scheduler (APScheduler, cron) runs the updates on its own
```

**Decisions I made:**

- **Isolated failures:** CAGED, CEMPRE and RFB live in their own files,
  including the database models (`src/database/models/`, one file per source).
  The CEMPRE and RFB routers are registered inside a `try`: if one source
  breaks, the API starts without it and the others stay online.
- **Scheduler in its own process:** scheduled jobs run in a container separate
  from the API, so Gunicorn's 4 workers don't run the same job 4 times.
- **Upsert instead of insert:** running the same load again updates records
  without duplicating data.
- **Versioned schema:** every table change goes through an Alembic migration.
- **Typed configuration:** environment variables are read with
  `pydantic-settings`; no passwords in the code.
- **No personal data:** RFB data is stored aggregated by period and sector,
  never company by company, and the partners file is not used.

The full decision log is in
[`docs/historico_arquitetonico.md`](docs/historico_arquitetonico.md) (Portuguese).

## Tech stack

| Layer | Tools |
| --- | --- |
| API | FastAPI, Pydantic, Uvicorn, Gunicorn |
| Data | Pandas, SQLAlchemy, PostgreSQL, Alembic, py7zr |
| Scheduling | APScheduler (cron trigger) |
| Quality | pytest, Ruff, Black, mypy, GitHub Actions |
| Infra | Docker (multi-stage, non-root user), Docker Compose, uv |

## Main endpoints

| Method | Route | Description |
| --- | --- | --- |
| `GET` | `/docs` | Swagger with every route |
| `GET` | `/health` | Application and database status |
| `GET` | `/caged/` | CAGED (filters: `competencia`, `setor`) |
| `POST` | `/caged/` · `/caged/bulk` | Creates or updates one or many records 🔐 |
| `DELETE` | `/caged/{id}` | Deletes a record 🔐 |
| `GET` | `/cempre/` | CEMPRE (filters: `ano`, `setor`, `incluir_total`) |
| `GET` | `/rfb/` | RFB (filters: `competencia`, `setor`, `incluir_total`) |
| `GET` | `/{source}/stats/resumo` | Summary for `caged`, `cempre` or `rfb` |
| `GET` | `/ibge/municipios` | IBGE municipalities |
| `POST` | `/perguntar` | Question in plain Portuguese, answered by the LLM agent 🤖 |

🔐 Needs a single-use token in the `X-API-Token` header. Tokens are issued only
on the server:

```bash
uv run python -m src.scripts.gerar_token --descricao "manual CAGED fix"
```

Details in [SECURITY.md](SECURITY.md).

## Ask in plain language

```bash
curl -X POST http://localhost:8000/perguntar \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "Qual foi o saldo de empregos formais em Joinville em junho de 2026?"}'
```

```json
{
  "resposta": "Em junho de 2026, Joinville registrou um saldo positivo de 254 empregos formais. No período, foram contabilizadas 14.223 admissões e 13.969 demissões. Os dados são provenientes do Novo CAGED (Ministério do Trabalho).",
  "consultas": [{"ferramenta": "consultar_caged", "argumentos": {"competencia": "202606"}, "erro": null}],
  "modelo": "gemini-3.5-flash",
  ...
}
```

How it works:

```text
Question ─▶ Gemini picks a tool ─▶ our code runs a read-only query ─▶ data back to Gemini ─▶ answer
             (tool calling)        (validated args, row cap)
```

- **The model never touches the database.** It can only pick one of 4 read-only
  tools (`listar_periodos`, `consultar_caged`, `consultar_cempre`,
  `consultar_rfb`). Our code validates the arguments, runs the query and caps
  the rows. There's no free-form SQL and no writes.
- **No made-up numbers.** The tools return totals that are already summed, and
  the instructions require answers based only on tool data, with the source
  and period. When the data doesn't exist, the agent says so.
- **Measured, not assumed.** Every answer reports the queries it ran, tokens
  and latency. An [evaluation set](docs/AGENT_EVAL.md) of 20 questions (15
  numeric, 1 that asks for a sector name and 4 that should be declined,
  including a prompt injection) is graded against answers computed from the real database.
- **Guardrails on cost.** Questions are capped at 300 characters and 5
  model ↔ tool steps, with per-IP and daily limits. Without `GEMINI_API_KEY`,
  the route is off (`503`).
- **Model picked by measurement.** `gemini-2.5-flash` turned out to be closed
  to new accounts, and `gemini-3.8-flash` took over 100 s per call in testing.
  In the same quick check, `gemini-3.5-flash` took about 8 s, so it's the default (configurable
  with `GEMINI_MODEL`).

All agent tests use a fake model, so CI never calls the LLM. To run the
evaluation against the real model: `uv run python -m src.scripts.avaliar_agente`.

## Running it

### With Docker (fastest)

```bash
cp .env.example .env.docker   # fill in your PostgreSQL settings
docker compose up --build
```

Two containers start from the same image: the **API** at
`http://localhost:8000/docs` and the **scheduler** with the scheduled jobs.

### Locally

With PostgreSQL running and `.env` set up from `.env.example`:

```bash
uv sync                          # install dependencies
uv run alembic upgrade head      # create/update tables

# load the data
uv run python -c "from src.services.atualizacao_caged import \
atualizar_caged; atualizar_caged(ano=2026, mes=6)"
uv run python -m src.services.atualizacao_cempre 2022 2023 2024
uv run python -m src.services.atualizacao_rfb    # latest period

uv run uvicorn src.api.app:app --reload   # start the API
```

The RFB load downloads several GB from the Federal Revenue and takes about
1h30. Specific periods: `atualizacao_rfb 2026-09 2026-10`; to reprocess a period
that is already in the database, add `--forcar`.

Full step-by-step guide (Portuguese):
[`docs/COMO_RODAR_O_PROJETO.md`](docs/COMO_RODAR_O_PROJETO.md).

## Tests

```bash
uv run pytest -q
```

The tests cover the CAGED, CEMPRE and RFB routes, the CAGED collector, the
health check, the CEMPRE and RFB transformers, and security: single-use tokens
(reuse, expiry, missing or unknown token), input validation, CORS, and the
LLM agent (tools, loop, step limit, error handling, rate limits) with a fake
model.
GitHub Actions runs Ruff and
the tests on every push and pull request to `master`; any Ruff warning fails
the build.

## Project structure

```text
src/
├── agent/          # LLM agent: read-only tools, loop, limits and evaluation set
├── api/            # FastAPI app and routers (caged, cempre, rfb, ibge, perguntar)
├── collectors/     # downloads each source's data
├── transformers/   # cleaning and standardization
├── database/       # connection, repositories and models/ (one file per source)
├── schemas/        # Pydantic validation
├── services/       # full update flow for each source
├── scheduler/      # scheduled jobs
└── core/           # settings, logging and security (single-use tokens)
alembic/            # database migrations
tests/              # pytest tests
docs/               # integrations, how to run, backlog and decision log
```

## Roadmap

- [x] Single-use token authentication on write endpoints (`POST` and `DELETE`)
- [ ] Rate limiting on public routes
- [ ] Tests for the collectors, services and scheduler
- [x] Natural-language questions about Joinville's economy with an LLM agent (tool calling over this API)
- [ ] RAG over the project documentation (methodology questions, not just numbers)
- [ ] Public deployment with a link

## Documentation

- [`SECURITY.md`](SECURITY.md): security model, single-use tokens and known
  limitations
- [`docs/AI_USAGE.md`](docs/AI_USAGE.md): how AI is used in this project

In Portuguese:

- [`docs/COMO_RODAR_O_PROJETO.md`](docs/COMO_RODAR_O_PROJETO.md): setup and
  running
- [`docs/CEMPRE_API.md`](docs/CEMPRE_API.md): CEMPRE integration
- [`docs/RFB_API.md`](docs/RFB_API.md): RFB integration
- [`docs/BACKLOG.md`](docs/BACKLOG.md): technical evolution and open items
- [`docs/historico_arquitetonico.md`](docs/historico_arquitetonico.md):
  architecture decisions

## Author

**Vitor Rogge Renner**, Software Engineering student at UNIVILLE and
undergraduate researcher in Python back-end and data.
[LinkedIn](https://www.linkedin.com/in/vitor-rogge-renner-5367b82b8) ·
[GitHub](https://github.com/VitorRenner)

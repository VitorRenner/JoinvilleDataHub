# Joinville Data Hub — API de Dados de Emprego de Joinville

API que coleta dados públicos oficiais sobre o mercado de trabalho de Joinville/SC, trata esses dados e os disponibiliza para consumo (como o site Nexus).

## Fontes de dados

| Fonte | Órgão | O que mostra | Frequência | Rota |
|---|---|---|---|---|
| 🎬 **Novo CAGED** | Ministério do Trabalho | Admissões, demissões e saldo de empregos formais por setor | Mensal | `/caged` |
| 📸 **CEMPRE** | IBGE | Unidades locais, pessoal ocupado e salário médio por setor (CNAE 2.0) | Anual | `/cempre` |

As duas fontes rodam no mesmo servidor, mas isoladas nos próprios arquivos: um erro em uma não derruba a outra. Detalhes do CEMPRE em [`docs/CEMPRE_API.md`](docs/CEMPRE_API.md).

## Tecnologias

Python 3.14 · FastAPI · SQLAlchemy · PostgreSQL · Alembic · Pandas · APScheduler · Pydantic · uv · pytest

## Como rodar

Guia completo, passo a passo: [`COMO_RODAR_O_PROJETO.md`](COMO_RODAR_O_PROJETO.md).

Resumo (com o PostgreSQL rodando e o `.env` configurado a partir do `.env.example`):

```bash
# instalar as dependências
uv sync

# criar/atualizar as tabelas do banco
uv run alembic upgrade head

# carregar os dados
uv run python -c "from src.services.atualizacao_caged import atualizar_caged; atualizar_caged(ano=2026, mes=6)"
uv run python -m src.services.atualizacao_cempre 2022 2023 2024

# subir a API
uv run uvicorn src.api.app:app --reload
```

## Endpoints principais

| Rota | Descrição |
|---|---|
| `GET /docs` | Swagger com todas as rotas |
| `GET /health` | Status da aplicação e do banco |
| `GET /caged/` | Movimentações do CAGED (filtros: `competencia`, `setor`) |
| `GET /cempre/` | Dados do CEMPRE (filtros: `ano`, `setor`, `incluir_total`) |
| `GET /caged/stats/resumo` · `GET /cempre/stats/resumo` | Total de registros de cada fonte |

## Testes

```bash
uv run pytest -q
```

## Documentação do projeto

- [`COMO_RODAR_O_PROJETO.md`](COMO_RODAR_O_PROJETO.md) — instalação e execução
- [`docs/CEMPRE_API.md`](docs/CEMPRE_API.md) — integração do CEMPRE
- [`BACKLOG.md`](BACKLOG.md) — evolução técnica e pendências
- [`historico_arquitetonico.md`](historico_arquitetonico.md) — decisões de arquitetura

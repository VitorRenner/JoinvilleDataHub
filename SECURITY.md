# Security

Joinville Data Hub serves public data, so most of it is meant to be open.
The job of security here is narrower and very concrete: **nobody but the
maintainer can change the data**, nothing secret lives in the code, and the
API stays well-behaved when someone sends it something odd.

This page explains how that works, what was a deliberate choice, and what is
still on the to-do list.

## What is public and what is protected

| | Access | Why |
| --- | --- | --- |
| `GET` routes (`/caged`, `/cempre`, `/rfb`, `/ibge`, `/health`, `/docs`) | Public | The data comes from official open sources and exists to be read |
| `POST /caged/`, `POST /caged/bulk`, `DELETE /caged/{id}` | Single-use token required | Writes change the data that other people rely on |
| Scheduled ETL loads | No HTTP involved | The scheduler writes straight to the database from inside the server |

## Single-use tokens

Write routes don't accept a fixed password or a long-lived API key. Each write
needs its own token:

- **One token, one write.** After a successful check the token is marked as
  used and never works again, even if someone captures it.
- **Short-lived.** Tokens expire after 15 minutes by default (60 at most).
- **Issued only on the server.** There is no HTTP route that creates tokens.
  You can only get one by running a command on the machine that has the
  database credentials, so in practice only the maintainer can write.
- **Stored as a hash.** The database keeps a SHA-256 hash, never the token
  itself. Someone who reads the table still can't use what's in it.
- **No race conditions.** Checking and consuming happen in a single
  conditional `UPDATE`, so two simultaneous requests with the same token
  can't both succeed.
- **Same answer for every failure.** A missing, unknown, expired or used token
  always returns the same `401`, without saying which case it was.

### How to use it

On the server:

```bash
uv run python -m src.scripts.gerar_token --descricao "manual CAGED fix"
# prints the token once; optional: --minutos 5
```

Then send it in the `X-API-Token` header:

```bash
curl -X POST http://localhost:8000/caged/ \
  -H "Content-Type: application/json" \
  -H "X-API-Token: <token>" \
  -d '{"competencia":"202606","setor":"Indústria","admissoes":10,"demissoes":4,"saldo":6}'
```

Note: the token is consumed as soon as it's checked, before the request body
is validated and before the write runs. So a request that fails for any other
reason still uses up its token: an invalid body (`422`), a record that doesn't
exist (`404`) or a database error (`500`). Just issue a new one. For write
access, failing closed like this is the safer default.

Code: [`src/core/security.py`](src/core/security.py),
[`src/database/repositorio_tokens.py`](src/database/repositorio_tokens.py),
[`src/scripts/gerar_token.py`](src/scripts/gerar_token.py).

## Input validation

Write routes reject bad data with `422` before it reaches the database:

- `competencia` must be `YYYYMM`, and `setor` must be 1 to 100 characters
  (the same limits as the table).
- `admissoes` and `demissoes` can't be negative. `saldo` can be, because a
  month can have more layoffs than hires.
- `/caged/bulk` accepts 1 to 1,000 records per call, so a single request can't
  overload the API or the database.
- Read routes cap `limit` at 1,000 rows.

These rules apply only to input, so older records already in the database
never break a read.

## CORS

- Only the origins listed in `CORS_ORIGINS` (`.env`) are allowed.
- Only `GET`, `POST` and `DELETE`, and only the `Content-Type` and
  `X-API-Token` headers.
- No credentials (`allow_credentials=False`): the API doesn't use cookies or
  sessions, so there's no reason to allow them.

## Secrets

- Every credential (`DATABASE_URL`, `RFB_SHARE_TOKEN`) comes from `.env`,
  which is in `.gitignore`. `.env.example` has only placeholders.
- Settings are typed with `pydantic-settings`, and `DATABASE_URL` has no
  default, so the app refuses to start without it.
- The CI runs with no secrets at all.

## Privacy (LGPD)

Federal Revenue (RFB) data is stored **only in aggregate**, by period and
sector, never company by company. The partners file, which contains personal
data, is never downloaded.

## Infrastructure

- The Docker image is multi-stage and runs as a **non-root** user.
- The scheduler runs in its own container, separate from the API.
- The `/health` check reports whether the database is reachable, without
  exposing connection details.

## LLM agent (`POST /perguntar`)

The agent is public like the read routes, so it's built to be safe even when
someone tries to misuse it:

- **Read-only by design.** The model can only choose from 4 read-only tools.
  Our code runs the queries with validated arguments (period format, CNAE
  section A to U) and a 60-row cap. Unknown tools, extra arguments and bad
  formats come back to the model as errors, never as exceptions.
- **Prompt injection.** The system instructions tell the model to ignore
  instructions inside the question, and the evaluation set includes an
  injection attempt. Even if the model were tricked, the worst it could do is
  read public data, because no tool can write.
- **Cost and abuse limits.** Questions are 3 to 300 characters, with at most 5
  model ↔ tool steps per question, 5 questions per minute per IP and 200 per
  day in total. The limits live in memory, per process (see below).
- **Off without a key.** If `GEMINI_API_KEY` isn't set, the route returns
  `503`. The key comes only from `.env`.
- **No leaks in errors.** If the model provider fails, the client gets a
  generic `502`. Details go only to the server log.

## Known limitations and next steps

Being upfront about what isn't done yet:

- **Agent limits are in memory, per process.** With 4 Gunicorn workers the
  effective ceiling is 4 times higher, and behind a proxy every client shares
  one IP unless the proxy passes the real one. A shared store (for example
  Redis) is the next step.
- **HTTPS** is expected to come from the reverse proxy or the cloud platform
  in deployment. The app itself serves plain HTTP.
- **No rate limiting on the data routes yet** (only on `/perguntar`). Brute-forcing a token isn't realistic (each one
  has 256 random bits), but rate limiting is still on the roadmap to protect
  the public read routes.
- **Used and expired tokens stay in the table.** They can't be used again,
  but they aren't cleaned up yet. A periodic cleanup is on the backlog.
- **Old local password in git history.** An early commit (`0cdd50a`) included
  a `.env` with a password for a local development database. That password
  was already rotated and isn't used anywhere.

## Reporting a problem

Found something? Please reach out privately through the contact on my
[GitHub profile](https://github.com/VitorRenner) instead of opening a public
issue. I'll reply as soon as I can.

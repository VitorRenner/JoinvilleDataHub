# How AI is used in this project

Short version: AI helps me write code faster, and I stay responsible for every
line that lands in `master`.

I'd rather say this openly than leave anyone guessing. Using AI well is part of
how software gets built today, and this page shows how it fits into the work
here.

## What I own

These are mine, start to finish:

- **The problem and the scope.** Which questions about Joinville's economy the
  project should answer, and which official sources can answer them.
- **The data decisions.** What to keep, what to aggregate, and what never to
  store. Leaving personal RFB data out entirely was a privacy call, not a
  technical detail.
- **The architecture.** Isolated sources, a scheduler in its own process,
  idempotent loads and versioned migrations. Each decision and its reasons are
  in [`historico_arquitetonico.md`](historico_arquitetonico.md).
- **Priorities.** What ships now and what waits (see [`BACKLOG.md`](BACKLOG.md)).
- **Review.** Nothing merges until I've read it, understood it and seen it
  pass the checks.

## Where AI helps

I use AI coding agents (Claude Code) as a pair programmer for:

- drafting code that I then review and adjust;
- writing and widening tests;
- reviewing code, especially to spot gaps between what the docs claim and what
  the code does;
- writing and translating documentation.

## The guardrails

AI output goes through the same filters as any other code:

1. **Tests.** 58 automated tests, and new behavior comes with new tests.
2. **CI.** GitHub Actions runs Ruff and Pytest on every push and pull request.
   A lint warning fails the build.
3. **Pull requests.** Today every change goes through a branch and a PR, with
   CI as the gate. Early on I committed straight to `master`, and moving to
   PRs was one of the first habits I fixed.
4. **No secrets in prompts.** Credentials stay in `.env` and are never pasted
   into a conversation with the agent.
5. **Claims checked against the code.** If the README says "3 ETL pipelines",
   I've counted them in the scheduler.

## A real example

While adding the single-use tokens (see [`SECURITY.md`](../SECURITY.md)), the
new tests caught a bug that had been there for a while: `POST /caged/` and
`POST /caged/bulk` always returned a 500 error, because the router passed
dictionaries to a function that expected Pydantic models. Nobody had noticed
because those routes had never been tested.

To me, this is the healthiest way to use AI: it speeds up writing the tests,
the tests catch real problems, and I decide how to fix them.

## What AI is not

It doesn't replace understanding. The rule I follow is simple: if I can't
explain a change, from why the scheduler runs outside Gunicorn to how the RFB
download handles several gigabytes without running out of memory, it doesn't
get merged.

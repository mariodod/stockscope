# AGENTS.md

Instructions for any AI agent working in this repository. These apply to every session and every task, regardless of how small the task looks.

## Non-negotiables

1. **Best practices must always be applied.** Never trade correctness, safety, or maintainability for speed. If a shortcut is unavoidable, record it as a `shortcut:` comment with a reason and open/finish the follow-up issue in the same phase.
2. **Commit after every unit of work.** No batching unrelated changes into one commit, and no leaving finished work uncommitted at the end of a session.

## Project context (read before changing anything)

- `PLAN.md` — phases, architecture, API design, risks, decisions log.
- `docs/metrics.md` — canonical metric vocabulary; update it when metrics change.
- `docs/data-sources.md` — provider strategy and adapter contract.
- `README.md` — user-facing setup and disclaimer.

Follow the repository layout in `PLAN.md` section 6.2. When a change affects a design decision, update the relevant doc and the decisions log in the same unit of work.

## What "best practices" means here

- **Correctness & tests** — add or update tests for every behavior change. Test observable behavior, not implementation details. Prove the change works against the real artifact (run the code), not just "it compiles".
- **Types & boundaries** — keep typing strict end-to-end (mypy on Python, TypeScript strict mode on the frontend). Validate external data at boundaries (Pydantic at API/provider edges); keep business logic in pure functions. Make illegal states unrepresentable where practical.
- **Security** — secrets only via environment variables / `.env` (never committed). Parameterized SQLAlchemy expressions only; no string-built SQL. Keep the `/refresh` endpoint auth-protected. Never log API keys or tokens.
- **Data integrity** — ingestion stays idempotent (upsert on natural keys), preserves nulls (never zero-fill), and stamps every fact with `source` and `as_of_date`. Canonical `metric_key`s come from the registry.
- **Simplicity** — smallest change that fully solves the problem. No speculative abstractions, no dead code, no compatibility shims for code that does not exist yet. Prefer deletion before addition.
- **Consistency** — match existing naming, style, and structure. Run the project's quality gates (ruff, mypy, pytest; ESLint, Prettier, frontend tests) and make them green before committing.
- **Root causes** — fix the first place the system goes wrong, not the symptom. If two fixes for the same premise fail, stop and test the premise itself.

## Unit of work

A unit of work is one coherent change with a one-sentence description that leaves the repository green:

1. Understand the task and the surrounding code.
2. Make the smallest focused change that fully solves it.
3. Verify: run the relevant quality gates and confirm behavior against the real artifact.
4. **Commit immediately** — before starting the next unit, and before ending the session.

If a task turns out to be several units, split it and commit after each verified step. Never end a session with uncommitted completed work.

## Commit rules

- Use Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `build:`, `ci:`.
- One unit of work per commit; the message states the *why*, not just the *what*.
- Include only intentional changes. Never commit secrets, `.env`, API keys, credentials, build output, `node_modules`, databases, or other ignored artifacts.
- Do not amend, rebase, or rewrite history unless explicitly asked.
- Do not push unless explicitly asked or the current phase is complete and verified.
- If a change cannot be verified (missing keys/services), say so explicitly and only then commit — with the limitation stated in the commit body and a follow-up issue if needed.

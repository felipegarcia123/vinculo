# Vínculo technical handoff

## Product and status

Vínculo is an independent digital loyalty MVP for neighborhood stores. The demo supports owner, cashier, and customer roles; short-lived QR challenges; fictional purchases; stamp accrual; reward redemption; and owner-facing loyalty metrics. The cashier flow does not create POS sales or move money or inventory. Campaigns remain drafts. Deterministic rules own all metrics; an optional LLM may explain supplied aggregates and is disabled by default.

The standalone extraction is ready for local team development. No GitHub repository, hosted deployment, or production environment is configured by this baseline.

## Architecture

- `apps/api`: Python 3.12, FastAPI, SQLAlchemy, Psycopg 3, Alembic, and pytest.
- `apps/web`: Node 22, Next.js 16, React 19, TypeScript, and npm lockfile.
- PostgreSQL stores users and hashed sessions, login-rate-limit events, loyalty programs and members, fictional purchases, visits, rewards, redemptions, and append-only stamp entries.
- The web app uses the API through same-origin `/api/v1` when hosted and a loopback API URL locally.
- Session cookies are HttpOnly for the session token; unsafe browser requests require CSRF cookie/header agreement. Hosted deployments must use HTTPS and secure cookies.
- API demo mode enforces an exact route/method allowlist. Unlisted operational POS routes return 404.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the data model and request flow.

## Migration safety

`apps/api/migrations/versions/0001_vinculo_baseline.py` is a frozen, independent baseline for a **new, empty Vínculo database only**. It consolidates Vínculo identity and loyalty entities from the embedded source history. It is not an upgrade path for an existing Vínculo Preview/evaluators database, Comprefácil, `pos_mvp`, or any database that already contains application data. Do not point Alembic at a shared database. Migration tests must use a disposable local PostgreSQL database and explicitly verify host, port, and database name first.

The API container starts the server only. Schema changes and fictional seed operations are explicit operator actions; never run them at application startup.

## Local setup

Follow [INSTALL.md](INSTALL.md). In brief:

1. Install Python 3.12, `uv`, Node.js 22, npm, and a local PostgreSQL 16 or 17 instance.
2. Copy `.env.example` to `.env`, use loopback PostgreSQL and unique fictional passwords, then restrict file permissions to the current user. Copy `apps/web/.env.example` to `apps/web/.env.local`.
3. Install API dependencies with `cd apps/api && uv sync --locked`; install web dependencies with `cd apps/web && npm ci`.
4. Create and verify a dedicated empty `vinculo_local` database on loopback. Apply the baseline only there, then explicitly seed fictional local accounts if needed.
5. Start the API on `127.0.0.1:8000` and web on `127.0.0.1:3000`.

Never copy real credentials into a local environment file or commit it. `.env`, `.env.local`, `.vercel`, build output, Python environments, local databases, and PostgreSQL data directories are ignored.

## Validation evidence

- Python 3.12.16 dependency sync completed from the lockfile.
- API suite: 5 passed on SQLite and 5 passed on isolated PostgreSQL 17.11.
- Migration from an empty temporary PostgreSQL database succeeded. A second `upgrade head` was a no-op, `alembic check` found no drift, and the resulting public schema had 10 Vínculo tables, 45 constraints, 28 indexes, and no POS tables.
- Frontend: `npm ci`, `npm run typecheck`, and `npm run build` passed. Build routes are `/`, `/login`, `/loyalty`, `/loyalty/cashier`, and `/loyalty/owner`.
- Full validation detail is in [EXTRACTION_PROVENANCE.md](EXTRACTION_PROVENANCE.md).

## Current risks and boundaries

- Hosted deployment wiring and a private GitHub repository remain to be configured after review.
- The baseline does not support multiple evaluators with independent simultaneous data, account recovery, or production identity verification.
- Retention, deletion, member analytics consent, and audit history for rule changes need product and privacy decisions.
- PostgreSQL is required for migration validation and realistic rate-limit integration tests. SQLite is only for isolated API tests.
- No paid integrations, external campaign delivery, Alegra, Receipt AI, or real payment processing are in scope.

## Vínculo Intelligence and parallel work

Use [VINCULO_INTELLIGENCE_BACKLOG.md](VINCULO_INTELLIGENCE_BACKLOG.md) as the canonical backlog. Work can proceed in parallel on:

1. Explainable segments and inactivity-risk metrics with sparse-history tests.
2. Owner dashboard filters and evidence presentation.
3. Draft recommendation domain contracts, approval state, cost inputs, and audit history; do not send campaigns.
4. Optional LLM explanation interface with redaction, limits, and deterministic fallback; keep it disabled by default.
5. Account lifecycle, retention, privacy consent, and security review.

Agree on API contracts and fixtures before parallel UI/domain changes. Metrics remain deterministic and authoritative; any model may only explain precomputed aggregates.

## GitHub collaboration proposal

Create a private repository named `Vinculo` (or `vinculo`) containing this project only. Protect `main`: require pull requests, passing CI, one approval, stale-approval dismissal, and no force push or branch deletion. Require a second reviewer for auth, schema, data-retention, or security changes. Use `feat/<area>-<summary>`, `fix/<area>-<summary>`, and `docs/<summary>` branches. Keep deployments and secrets outside GitHub source; developer access should not include production or shared database administration.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the review checklist. Do not include the local-only Comprefácil archive or historical source handoff files in the new repository.

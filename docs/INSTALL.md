# Local installation

## Requirements

- Python 3.12
- `uv`
- Node.js 22 and npm (the repository pins the major version in `.nvmrc`)
- PostgreSQL 16 or 17 on a dedicated local port

Do not use Docker Compose from Comprefácil, `pos_mvp`, Neon, or any remote database for local development.

## API

1. Create a local PostgreSQL role and an empty database named `vinculo_local` on loopback. Use an exclusive local port, for example `55492`.
2. From the repository root, copy `.env.example` to `.env`. Replace the local password, the rate-limit secret, and the three demo passwords with unique fictional values. Use at least 24 characters for each demo password and at least 32 random bytes for `AUTH_RATE_LIMIT_SECRET`. Keep `.env` untracked and user-readable only (`chmod 600 .env`). Copy `apps/web/.env.example` to `apps/web/.env.local` for the two public local frontend settings.
3. Install locked dependencies and migrate only after checking the local target:

   ```sh
   cd apps/api
   uv sync --locked
   DATABASE_URL='postgresql+psycopg://vinculo_local:<local-password>@127.0.0.1:55492/vinculo_local' uv run alembic -c alembic.ini upgrade head
   ```

4. For fictional accounts, set `VINCULO_ALLOW_LOCAL_SEED=true` in the local shell, then run `uv run python -m app.scripts.seed_local`. The script itself rejects non-loopback hosts, databases other than `vinculo_local`, missing migration, non-unique passwords, and an already seeded member/user set. It never prints passwords.
5. Run the API: `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000`.

The API's default local database is SQLite for isolated unit tests. The demo seed intentionally requires PostgreSQL so a developer does not accidentally seed an arbitrary SQLite file.

## Web

1. In another terminal, set `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1` and `NEXT_PUBLIC_VINCULO_DEMO_ONLY=true` (or put these non-secret values in the root `.env`).
2. Run:

   ```sh
   cd apps/web
   npm ci
   npm run dev -- --hostname 127.0.0.1 --port 3000
   ```

3. Open `http://127.0.0.1:3000/login`. Use the fictional credentials entered for the seed. Login requests do not include a password in the URL or logs.

## Tests and build

```sh
cd apps/api
uv run pytest
```

The tests default to an in-memory SQLite database and create/drop only their own tables. For migration validation, use a fresh disposable local PostgreSQL database and check its host, port, and database name before running Alembic.

```sh
cd apps/web
npm ci
npm run typecheck
npm run build
```

## Environment variables

| Name | Purpose |
|---|---|
| `DATABASE_URL` | Local PostgreSQL URL for runtime/migrations; never point at an operational database. |
| `AUTH_RATE_LIMIT_SECRET` | Random HMAC key; required in demo mode. |
| `AUTH_COOKIE_SECURE` | `false` only for loopback; `true` for HTTPS hosting. |
| `VINCULO_DEMO_ONLY` | Enables server-side Vínculo-only API allowlist. |
| `NEXT_PUBLIC_VINCULO_DEMO_ONLY` | Restricts frontend pages to Vínculo routes. |
| `CORS_ORIGINS` | Explicit local frontend origin(s). Hosted same-origin deployments can leave cross-origin access unused. |
| `NEXT_PUBLIC_API_URL` | Local API origin; hosted deployments use `/api/v1` on the same HTTPS origin. |
| `LOYALTY_LLM_ENABLED`, `LOYALTY_LLM_API_KEY` | Optional, off by default; request explanations only, no campaign delivery. |
| `VINCULO_ALLOW_LOCAL_SEED` and role username/password variables | Explicit local-only fictional seed controls. |

For a future isolated hosted demo, see [DEPLOYMENT.md](DEPLOYMENT.md). The
remote one-shot seed is separate from `seed_local.py`, requires a newly
provisioned Neon project/database and interactive hidden password entry, and
does not run migrations.

# Contributing

## Branches and pull requests

- `main` is the reviewed baseline and should be protected with required pull requests and CI.
- Use short branches: `feat/<area>-<summary>`, `fix/<area>-<summary>`, or `docs/<summary>`.
- Keep changes scoped to a contract or feature; avoid bundling analytics, UI, and schema changes without a clear dependency.
- Pull requests describe user behavior, data changes, privacy impact, tests, and rollback/migration implications.
- Require one reviewer for API/security/schema changes and one for Intelligence metric or campaign logic.
- No migration is applied automatically during API startup. Review and run it explicitly against an isolated local database.

## Checks before review

```sh
cd apps/api && uv sync --locked && uv run pytest
cd ../web && npm ci && npm run typecheck && npm run build
```

Run PostgreSQL migration tests from an empty local database. Never point a test command at an operational or shared evaluation database.

## Access boundaries

Developers need repository access and local fictional credentials. They do not need production credentials, shared Neon owner access, Vercel project administration, payment provider credentials, or customer data. Keep deployment secrets in the host secret manager and share evaluator accounts through an approved password manager with expiry/rotation.

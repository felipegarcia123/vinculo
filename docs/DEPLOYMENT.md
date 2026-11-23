# Independent hosted demo

This guide prepares a future, isolated Vínculo deployment. No deployment, Neon
project, or remote migration is performed by this repository setup.

## Architecture

The repository-root Vercel configuration defines two Vercel Services:

- web: Next.js, rooted at apps/web.
- api: FastAPI, rooted at apps/api, ASGI entrypoint app.main:app.
- /api/v1 and /api/v1/* route to the API service before the web catch-all.
- All other paths route to Next.js.

The existing frontend defaults to the relative API base /api/v1 in hosted
builds. This keeps browser requests same-origin: session and CSRF cookies stay
on one HTTPS origin and no cross-origin browser access is needed. No CORS
allowlist is needed for this same-origin topology; do not add a wildcard
origin. If a future
deployment splits the domains, configure the exact HTTPS web origin and retest
credentialed CORS, cookie SameSite, CSRF, and forwarded-protocol handling
before exposing it.

Vercel Services shares project environment variables across services. There is
no complete secret boundary between the web and API services in this single
project: DATABASE_URL and AUTH_RATE_LIMIT_SECRET are available to both server
runtimes when configured on the project. They are not automatically included
in the browser bundle; Next.js only exposes NEXT_PUBLIC_ variables to browser
code. Treat both services and the deployed repository revision as one trusted
server-side boundary. If frontend/backend secret isolation is required, use
separate Vercel projects and design/test the proxy, cookies, and CSRF boundary
before deployment.

The Vercel project must use the Services framework and support the services
configuration. This feature and its project setup must be confirmed in the
target Vercel account before the first deployment. Set the Vercel project root
directory to the repository root so its top-level service configuration can
resolve both apps. The Vercel routing rewrites
preserve the request path, which is required because FastAPI routes already
include /api/v1.

## Hosted environment variables

Configure these only in the new Vínculo deployment, never in Comprefácil or
another Vercel project. Set these for Preview only; leave Production variables
unset. Treat server secrets as sensitive.

| Variable | Service | Value/purpose |
|---|---|---|
| DATABASE_URL | Shared project env; consumed by API | Pooled PostgreSQL URL for the new Vínculo-only Neon database. Use postgresql+psycopg and TLS. Treat it as available to both services' server runtimes. |
| AUTH_RATE_LIMIT_SECRET | Shared project env; consumed by API | At least 32 random bytes, generated uniquely for this deployment. Treat it as available to both services' server runtimes. |
| AUTH_COOKIE_SECURE | Shared project env; consumed by API | Set true for hosted HTTPS. Local loopback HTTP may use false. Vercel runtime also forces Secure cookies through its deployment-controlled `VERCEL=1` system variable. |
| VINCULO_DEMO_ONLY | Shared project env; consumed by API | true; keeps the API allowlist limited to Vínculo functionality. |
| CORS_ORIGINS | Shared project env; consumed by API | Not needed for same-origin routing. If domains split, use only the exact HTTPS web origin(s). |
| LOYALTY_INACTIVE_DAYS | Shared project env; consumed by API | 30 unless the owner configures a different transparent threshold. |
| LOYALTY_LLM_ENABLED | Shared project env; consumed by API | false for the initial public demo. |
| LOYALTY_LLM_API_KEY | Shared project env; consumed by API | Unset. No LLM provider is required for deterministic explanations. |
| NEXT_PUBLIC_API_URL | Web | /api/v1. |
| NEXT_PUBLIC_VINCULO_DEMO_ONLY | Web | true. |

Local development uses the repository's `.env.example` and
`apps/web/.env.example`; the root example has `AUTH_COOKIE_SECURE=false` and
loopback URLs for local-only use. Do not upload either example as a Vercel
environment file. Preview must set its own hosted values, including
`AUTH_COOKIE_SECURE=true`, `VINCULO_DEMO_ONLY=true`, and
`NEXT_PUBLIC_VINCULO_DEMO_ONLY=true`.

DATABASE_URL, AUTH_RATE_LIMIT_SECRET, and any Neon API key must never use a
NEXT_PUBLIC_ name. CI builds with fictional canary values and checks that they
are absent from `.next/static`. This checks browser assets only; it does not
create a secret boundary between the Vercel Services server runtimes.
Vercel Service routing is expected to keep the API internal except for the
explicit /api/v1 rewrite. Confirm that behavior in a protected Preview.

### Cookie and proxy trust boundary

The API does not use `X-Forwarded-Proto` to decide whether to mark cookies
Secure. Although Vercel documents that header as the forwarded protocol, its
request-header documentation does not promise that it overwrites a
client-supplied value. Treat it as untrusted input unless a separately verified
trusted-proxy boundary is configured. Cookie security is based on the ASGI
request scheme, the deployment-controlled `VERCEL=1` system variable, or the
operator-controlled `AUTH_COOKIE_SECURE=true` setting. Vercel documents `VERCEL`
as a runtime system variable; confirm system variables are exposed in the
target project. Keep `AUTH_COOKIE_SECURE=true` in Preview as defense in depth.
Plain local loopback HTTP remains compatible with `AUTH_COOKIE_SECURE=false`.

## Create the isolated demo database later

Do these steps only after the project owner authorizes infrastructure
provisioning:

1. Create a new Neon project named vinculo-public-demo; do not select, branch,
   or reuse any existing Vínculo or Comprefácil project.
2. Create a dedicated database named vinculo_demo on the intended demo branch.
   Record the project ID, branch ID/name, and direct write endpoint host. Verify
   these values in Neon before any command that changes data.
3. Keep a direct TLS URL for one-time migration/seed operations. Use a pooled
   TLS URL for the serverless API runtime. Do not put either URL in Git, shell
   history, tickets, or chat.
4. In a local zsh terminal, read the direct URL with echo disabled, then set
   the migration URL in that terminal session:

       read -s 'VINCULO_SEED_DATABASE_URL?Direct Neon URL: '; echo
       export VINCULO_SEED_DATABASE_URL
       export DATABASE_URL="$VINCULO_SEED_DATABASE_URL"

   The commands entered into shell history contain no secret values. Clear
   both variables when finished. Do not run the migration until the project,
   branch, host, database, and empty state have all been independently checked.
5. Populate the non-secret identifiers from the values independently verified
   in Neon. Check the destination and empty schema with SQL that does not
   display the URL:

       psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c 'SELECT current_database(), current_user'
       psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "SELECT schemaname, tablename FROM pg_tables WHERE schemaname = 'public'"

   Confirm the database name and that the public schema had no application
   tables. Never continue if either output differs. Then, from the repository
   root, run:

       cd apps/api
       uv run --locked alembic -c alembic.ini upgrade head

   The independent
   project has one frozen migration, 0001_vinculo_baseline; it is exclusively
   for a new, empty Vínculo database and must never be applied to Comprefácil or
   an existing database.
6. Set the seed's direct URL, identifiers, and one-shot opt-in. Enter the Neon
   API key through a hidden terminal prompt. Prefer a short-lived,
   project-scoped Neon key if the account supports it:

       export VINCULO_REMOTE_SEED_ENABLED=true
       export VINCULO_SEED_PROJECT_SLUG=vinculo-public-demo
       export VINCULO_SEED_PROJECT_ID='verified-project-id'
       export VINCULO_SEED_BRANCH_ID='verified-branch-id'
       export VINCULO_SEED_BRANCH_NAME='verified-branch-name'
       export VINCULO_SEED_ALLOWED_HOST='verified-direct-host.neon.tech'
       export VINCULO_SEED_ALLOWED_DATABASE=vinculo_demo
       export VINCULO_SEED_DATABASE_URL="$DATABASE_URL"
       read -s 'NEON_API_KEY?Neon API key: '; echo
       export NEON_API_KEY

   Never place a secret literally into a command line or tracked file.
7. Run uv run python -m app.scripts.seed_remote_demo interactively. It checks
   the Neon project, branch, and exact write endpoint through Neon’s API; checks
   the host, TLS, database name, fresh baseline revision, exact table set,
   empty account/activity tables and the expected demo program/reward; then
   asks the operator to confirm project/branch/database and enter three
   unique passwords (minimum 24 characters) twice each without echo. It creates
   only the three fictional role accounts and the customer member. It does not
   migrate, overwrite, retry, print passwords, or log database exception
   details. On any mismatch it stops without seeding.
8. Remove the one-shot environment variables and revoke the temporary Neon API
   key. Verify the three roles with non-secret checks, then deploy only a
   protected Preview and test it before changing public access.

The remote seed deliberately rejects a database that is not exactly the fresh
0001_vinculo_baseline schema or whose initial loyalty program/reward differ
from the frozen fictional template. To reset evaluators later, provision a
separate fresh demo database and repeat the authorized procedure; do not turn
this one-shot seed into an overwrite/reset command.

## Preflight and validation

Before the first deployment:

1. Confirm Vercel Services is enabled for the account and the project is set to
   the Services framework.
2. Configure Deployment Protection for Preview before deploying; use Vercel
   Authentication and verify an anonymous request is redirected to Vercel
   login. Do not add protection exceptions or shareable links.
3. Confirm no Production deployment or existing Vercel project is selected.
4. Confirm Preview-only variables reference the new Vínculo database and the
   `VERCEL` system environment variables are enabled; never populate Production
   variables for this test.
5. Confirm the Neon host belongs to the newly created project and exact branch;
   the seed's control-plane verification is a second guard, not a substitute
   for operator review.
6. Run API tests, frontend proxy tests/typecheck/build, and config/seed safety
   tests. CI runs `npm ci`, `npm run test:proxy`, typecheck, a production build
   with fictional private-value canaries, an asset scan for those canaries, and
   API tests via `uv sync --locked` / `uv run pytest`.
7. Deploy a protected Preview. Verify /api/v1/health, login, roles, QR, one
   fictional purchase/stamp, redemption, replay rejection, and API 404 for any
   route outside the demo allowlist.
8. Verify cookies are Secure, HttpOnly session cookies with CSRF protection,
   login rate limits persist in PostgreSQL, and an anonymous request is denied
   from personal customer data.
9. Only after those checks and separate authorization should an evaluator-facing
   deployment be enabled.

## Failure and rollback procedure

1. If target or protection preflight differs from the approved Vínculo-only
   project/database, stop before changing anything.
2. If migration or seed fails, stop immediately. Preserve sanitized logs, do
   not retry, reseed, or restore automatically, and leave the database intact
   for diagnosis. This baseline migration is only for a new empty database.
3. If runtime checks fail after deployment, keep Deployment Protection active
   and stop sharing the Preview. Redeploy the last known-good Preview revision
   using Vercel's deployment controls; do not promote or alter Production.
4. Do not roll back the database by dropping tables or restoring over it. Keep
   the failed isolated demo database unchanged until its state is reviewed. If
   recovery requires replacing it, provision a separate fresh demo database
   and obtain explicit authorization before any data operation.
5. Revoke any temporary Neon API credential used for the one-shot seed and
   rotate demo passwords if they were exposed. Confirm the old Preview remains
   protected before restarting the checklist.

## Boundaries and remaining risks

- Evaluator data is shared by every deployment connected to the same database.
  The current seed creates one customer account and the model has no
  evaluator/team scope. All visits, purchases, stamps, and redemptions affect
  one shared balance.
- A newly issued QR can invalidate an older outstanding QR for the same
  customer. This is intentional one-use behavior but makes concurrent customer
  sessions interfere.
- Isolation alternatives:
  1. One shared database and one customer account: lowest operational cost;
     suitable for one coordinated evaluation group only.
  2. One Neon branch/database and one Preview deployment per evaluation group:
     recommended for the first multi-team evaluation. It needs no changes to
     loyalty logic, and dropping/recreating a group's isolated demo environment
     can reset its data without affecting another group. Provision each from
     the clean schema baseline, never from a branch already seeded with users
     and activity.
  3. Add evaluator/team identity to the data model and enforce it through every
     query and API operation: supports concurrent groups in one deployment but
     requires schema, authorization, and UI changes, plus dedicated isolation
     tests. Defer this until per-group deployments become operationally costly.
- The demo API is intended to simulate purchases only. Do not connect payment,
  inventory, POS, Alegra, Receipt AI, campaign delivery, or external messaging.
- A public login remains exposed to automated abuse. Validate persistent rate
  limits, rotate demo passwords if shared, monitor platform/database usage, and
  keep the demo dataset fictional.
- Vercel Services availability and Preview settings still require confirmation
  in the target account. Services shares project variables, so use this
  architecture only when both service runtimes are accepted as one trusted
  boundary; separate projects are required for strict backend-only secret
  access.

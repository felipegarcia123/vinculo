# Vínculo

Vínculo is an independent digital loyalty MVP for neighborhood stores. It supports secure role-based access, a digital stamp card, expiring customer QR codes, a fictional cashier purchase flow, reward redemption, owner analytics, and optional AI explanations. The demonstration never processes money or sends campaigns.

## Product scope

- **Customer:** sign in, view stamp balance/history, issue a short-lived visit or redemption QR.
- **Cashier:** simulate a fixed-price fictional purchase from a visit QR and validate a reward QR.
- **Owner:** view loyalty metrics, set program thresholds, and prepare campaign drafts. LLM explanations are optional and user-triggered.
- **Excluded:** POS sales, inventory, cash, supplier purchasing, payment processing, Alegra, Receipt AI, and external campaign delivery.

## Repository layout

- `apps/api`: standalone FastAPI service, SQLAlchemy models, Alembic baseline, and API tests.
- `apps/web`: standalone Next.js experience with login, cartilla, caja ficticia, and owner dashboard.
- `docs/ARCHITECTURE.md`: module boundaries and data model.
- `docs/INSTALL.md`: local setup and safe demo seeding.
- `docs/TECHNICAL_HANDOFF.md`: current onboarding and engineering handoff.
- `docs/VINCULO_INTELLIGENCE_BACKLOG.md`: next product work.

## Quick start

See [docs/INSTALL.md](docs/INSTALL.md). Use a dedicated local PostgreSQL database named `vinculo_local`, a Python 3.12 environment, and fictional credentials. Never point this project at Comprefácil, `pos_mvp`, Neon, or a production URL.

## Validation

```sh
cd apps/api
uv sync --locked
uv run pytest
```

```sh
cd apps/web
npm ci
npm run typecheck
npm run build
```

The extraction and validation record is maintained in [docs/EXTRACTION_PROVENANCE.md](docs/EXTRACTION_PROVENANCE.md). Historical Comprefácil handoff artifacts are local-only and excluded from version control.

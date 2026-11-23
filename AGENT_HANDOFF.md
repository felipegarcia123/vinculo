# Agent handoff

Start with [README.md](README.md), then read [docs/TECHNICAL_HANDOFF.md](docs/TECHNICAL_HANDOFF.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), and [docs/INSTALL.md](docs/INSTALL.md).

Vínculo is an independent loyalty demo. Its API and frontend contain no Comprefácil POS runtime modules. Use only fictional local data. The Alembic revision `0001_vinculo_baseline` is for a brand-new Vínculo database; never apply it to an existing database.

Latest local validation: API tests passed on SQLite and isolated PostgreSQL 17; the fresh-database migration and `alembic check` passed; Next.js typecheck and build passed. See `docs/EXTRACTION_PROVENANCE.md` for details. Do not use Neon, Vercel, Production, `pos_mvp`, or other shared environments for local validation.

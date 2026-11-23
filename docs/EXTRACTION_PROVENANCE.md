# Extraction provenance and validation

## Source and preservation

- Source repository: Comprefácil working tree, branch `feat/smart-purchasing-sprint1-backend`.
- Source commit: `9514c88685d2b0f1d8844fd883b354bf127e2ef2`.
- The source's proposed 81-path manifest and technical handoff remain local-only historical artifacts and are excluded from Git because they describe the embedded Comprefácil implementation and may contain operational references.
- The source workspace was not moved, reset, staged, committed, or pushed. A separate local recovery archive was verified before extraction; it remains outside this project and must not be shared.

## Extraction decisions

- The standalone API has only Vínculo auth and loyalty routes/models. It does not include the POS router tree, cash/inventory/purchase/payment/customer directory modules, or their integrations.
- The cashier demo writes `loyalty_purchases`; it creates no POS sale, payment, cash movement, stock movement, or external call.
- Cookie names are now `vinculo_session` and `vinculo_csrf` to avoid collision with Comprefácil sessions on local hosts.
- The independent Alembic revision is `0001_vinculo_baseline`; it uses explicit, frozen DDL to consolidate the Vínculo entities from source revisions `0033` and `0034` and intentionally does not replay Comprefácil's preceding POS schema history. It must not derive its contents from mutable SQLAlchemy metadata.
- Credentials and connections to Neon/Vercel/Comprefácil were not copied. The historic Preview guide containing a connection string was omitted.
- The two shared POS fixes remain only in the untouched source tree: the optional `active` filter for `/business-accounts` and the `SaleCustomerOut.email` response field. They are not part of Vínculo's standalone code.

## Validation ledger

This extraction was validated in a disposable standalone staging copy; the temporary PostgreSQL instance listened only on loopback and was stopped after checks. Do not treat source-repository results as a substitute for tests in this standalone project.

- Source pre-extraction: API suite 712 passed / 31 skipped; auth-loyalty suite against temporary PostgreSQL 17: 17 passed; source migration chain reached `0034` from empty.
- Python: `uv sync --locked` created a fresh environment with CPython 3.12.16.
- Standalone API suite: 5 passed on SQLite and 5 passed on isolated PostgreSQL 17.
- Migration: the frozen DDL was applied to a new, empty PostgreSQL 17.11 database. The first validation caught a missing `sqlalchemy.dialects.postgresql` import in the baseline's UUID bulk-insert type; the import was corrected and the migration then passed from a separate empty database. A second `upgrade head` was a no-op, and `alembic check` reported no model drift. The schema contains 10 Vínculo tables plus `alembic_version`, 45 constraints, 28 indexes, no POS tables, one default program and reward, and zero users/purchases.
- The separate PostgreSQL test database had zero tables after fixture teardown.
- Web: `npm ci --offline`, `npm run typecheck`, and `npm run build` passed. Build output contains only `/`, `/login`, `/loyalty`, `/loyalty/cashier`, and `/loyalty/owner` plus Next not-found.
- Runtime imports and configured API routers are confined to Vínculo auth/loyalty. POS path strings appear only in tests asserting 404.
- The local-only preservation archive was reconstructed and verified against 87 Git-visible changed files. Its location and hash are intentionally omitted from this shareable document. It is **not part of the Vínculo project** and must not be uploaded.

## Remaining risks and next work

- The standalone `0001` schema is a fresh-database baseline, not an upgrade migration for existing Neon branches or Comprefácil databases.
- Hosted service wiring, deployment configuration, and private GitHub repository creation were intentionally not attempted.
- Account self-registration, production identity recovery, retention controls, and multiple-evaluator data isolation remain out of this extraction scope.
- One upstream Starlette TestClient deprecation warning appears under the pinned test stack; tests pass.

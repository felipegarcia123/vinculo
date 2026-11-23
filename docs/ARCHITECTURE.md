# Architecture

## Runtime

The browser uses the Next.js app in `apps/web`. It calls the FastAPI service over same-origin HTTPS in hosted environments or a local API URL during development. The API owns authentication, session state, QR challenge state, loyalty accounting, rule-based metrics, and the optional explanation request. PostgreSQL is the durable store.

The API imports only Vínculo-owned routes and models. It does not import Comprefácil POS routers, inventory, cash, payment, supplier, Alegra, Receipt AI, or purchasing modules. The demo cashier creates a `loyalty_purchases` record at a fixed fictional amount; no payment or stock ledger is touched.

## Data model

- `users`: username, scrypt password hash, role (`owner`, `cashier`, `customer`), active state.
- `auth_sessions`: SHA-256 hashes of opaque session tokens, CSRF hashes, expiry and revocation. Customer QR challenges use the same table with distinct purpose markers and 90-second expiry.
- `login_attempt_events`: keyed HMAC buckets for username and IP throttling.
- `loyalty_programs`, `loyalty_members`, `loyalty_rewards`: rules and customer membership.
- `loyalty_purchases`: fictional completed receipts; unique idempotency key.
- `loyalty_visits`: one visit per eligible purchase.
- `loyalty_stamp_entries`: append-only positive visit entries or negative redemption entries; unique source constraints prevent duplicate accounting.
- `loyalty_redemptions`: reward, cashier, stamps spent, and unique idempotency key.

The independent migration `0001_vinculo_baseline` is a fresh schema baseline. It consolidates only the Vínculo identity and loyalty schema represented by source revisions `0033` and `0034`; it does not require the Comprefácil migration history.

## Request boundaries

`/api/v1/auth/*` provides login, session inspection, and logout. `/api/v1/loyalty/*` provides customer, cashier, and owner operations with role checks. `VINCULO_DEMO_ONLY=true` applies an exact method/path allowlist at the API boundary; unlisted POS routes remain 404 even if added accidentally. The Next.js proxy independently limits page routes to `/login` and the three loyalty experiences.

Session cookies are `vinculo_session` (HttpOnly) and `vinculo_csrf` (readable by the same-origin client). Unsafe requests require the CSRF cookie and matching header. Hosted configuration must set secure cookies and HTTPS. Local development may disable Secure only on loopback.

## Loyalty flow

1. Customer requests a visit QR. The API stores only a hash of its random token, expires it after 90 seconds, and revokes earlier unused QRs.
2. Cashier submits the QR to the fictional purchase endpoint. The API locks and validates the challenge, creates one fictional purchase, marks the challenge used, and writes the visit and stamp in one transaction.
3. Replaying the same QR returns the already-processed result without another purchase or stamp.
4. At the configured threshold, the customer asks for a reward QR. The cashier validates it; the API writes one redemption and a negative stamp entry in one transaction. Replays return the original result.

Default demo rule: COP 10,000 minimum, one stamp per eligible purchase, reward at five stamps. The fictional checkout amount is COP 12,000 and is not a payment.

## AI boundary

Metrics and inactivity segments are deterministic SQL-backed calculations. With insufficient visits, the API reports insufficient evidence rather than inferring a pattern. Campaign proposals remain drafts. An LLM can only explain returned aggregates or draft copy when explicitly requested; it never computes authoritative metrics, invents customer data, or dispatches campaigns.

# Vínculo Intelligence backlog

## P0 — trustworthy data and product boundaries

- Add data-retention and account deletion rules for loyalty history.
- Add audit events for owner rule changes and reward stock changes.
- Define explicit consent and privacy notice for member-level analytics.
- Add deterministic fixtures for timezone boundaries, sparse histories, and outlier visits.

## P1 — segmentation and visit-risk signals

- Build explainable segments for new, active, near-reward, and inactive members.
- Detect a break in an individual member's visit rhythm only after a minimum observation count; report the baseline and threshold alongside each signal.
- Add a “data insufficient” state and test that it suppresses unsupported risk claims.
- Add owner controls for inactive-day thresholds and segment previews.

## P1 — campaign recommendation drafts

- Rank suggested incentives using observed visit and redemption data plus owner-configured cost limits.
- Show each recommendation's population, evidence window, assumptions, expected cost inputs, and approval state.
- Keep every proposal in draft; add explicit owner approval workflow before any future delivery integration.
- Add a review history and change log for proposals.

## P2 — optional LLM explanation layer

- Define a provider interface with timeout, bounded input/output, redaction, and deterministic fallback.
- Pass aggregated metrics only; do not send customer names, contact information, tokens, or QR data.
- Test hallucination controls by checking that the model cannot override the computed numbers or convert draft status to approved.
- Keep the provider disabled by default and expose cost/availability to the owner.

## Parallel work streams

1. Analytics contracts, SQL metrics, fixtures, and inactivity tests.
2. Owner dashboard segment filters and evidence explanations.
3. Campaign draft and approval domain model (without sending).
4. LLM provider abstraction, privacy review, and deterministic fallback tests.
5. Account lifecycle, retention, and security review.

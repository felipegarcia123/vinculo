"""Persistent, privacy-preserving login throttling for serverless runtimes."""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import LoginAttemptEvent

WINDOW = timedelta(minutes=15)
RETENTION = timedelta(days=1)
USERNAME_LIMIT = 12
IP_LIMIT = 40


def _secret() -> bytes:
    configured = settings.auth_rate_limit_secret
    if settings.vinculo_demo_only:
        placeholder = any(marker in configured.lower() for marker in ("replace", "placeholder", "change-me"))
        if len(configured.encode("utf-8")) >= 32 and not placeholder:
            return configured.encode("utf-8")
        raise HTTPException(status_code=503, detail="Autenticación temporalmente no disponible")
    if configured:
        return configured.encode("utf-8")
    # This fallback is only for local/non-demo operation. Hosted Vínculo requires a configured secret.
    return b"vinculo-local-login-rate-limit-only"


def _hash_bucket(kind: str, value: str) -> str:
    return hmac.new(_secret(), f"{kind}:{value}".encode("utf-8"), hashlib.sha256).hexdigest()


def _client_ip(request: Request) -> str:
    # Vercel sets X-Forwarded-For at its trusted edge; outside Vercel use the ASGI peer address.
    if os.getenv("VERCEL") == "1":
        forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else "unknown"


def login_bucket_hashes(username: str, request: Request) -> tuple[str, str]:
    normalized = username.strip().lower()
    return _hash_bucket("username", normalized), _hash_bucket("ip", _client_ip(request))


def _lock_buckets(db: Session, hashes: tuple[str, str]) -> None:
    if db.get_bind().dialect.name != "postgresql":
        return
    # Transaction-scoped advisory locks serialize concurrent failures across Vercel instances.
    lock_ids = sorted({int(value[:16], 16) - (1 << 64) if int(value[:16], 16) >= (1 << 63)
                       else int(value[:16], 16) for value in hashes})
    for lock_id in lock_ids:
        db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})


def _active_counts(db: Session, hashes: tuple[str, str], now: datetime) -> dict[str, int]:
    since = now - WINDOW
    rows = db.execute(
        select(LoginAttemptEvent.bucket_hash, func.count())
        .where(LoginAttemptEvent.bucket_hash.in_(hashes), LoginAttemptEvent.created_at >= since)
        .group_by(LoginAttemptEvent.bucket_hash)
    ).all()
    return dict(rows)


def enforce_login_limit(db: Session, username: str, request: Request) -> tuple[str, str]:
    hashes = login_bucket_hashes(username, request)
    _lock_buckets(db, hashes)
    counts = _active_counts(db, hashes, datetime.now(timezone.utc))
    if counts.get(hashes[0], 0) >= USERNAME_LIMIT or counts.get(hashes[1], 0) >= IP_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Demasiados intentos. Inténtalo más tarde.",
            headers={"Retry-After": str(int(WINDOW.total_seconds()))},
        )
    return hashes


def record_failed_login(db: Session, hashes: tuple[str, str]) -> None:
    now = datetime.now(timezone.utc)
    db.add_all([
        LoginAttemptEvent(bucket_hash=hashes[0], bucket_kind="username", created_at=now),
        LoginAttemptEvent(bucket_hash=hashes[1], bucket_kind="ip", created_at=now),
    ])
    db.execute(delete(LoginAttemptEvent).where(LoginAttemptEvent.created_at < now - RETENTION))


def clear_username_failures(db: Session, username_hash: str) -> None:
    db.execute(delete(LoginAttemptEvent).where(LoginAttemptEvent.bucket_hash == username_hash))

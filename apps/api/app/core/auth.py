"""Password and opaque database-backed session authentication."""

import hashlib
import hmac
import os
import secrets
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import AuthSession, User

SESSION_COOKIE = "vinculo_session"
CSRF_COOKIE = "vinculo_csrf"
SESSION_HOURS = 12
QR_SESSION_PREFIX = "QR:"
QR_USED_PREFIX = "USED:QR:"
_request_actor: ContextVar[User | None] = ContextVar("vinculo_request_actor", default=None)


def authenticated_actor() -> User | None:
    return _request_actor.get()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=64)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, salt_hex, digest_hex = encoded.split("$", 2)
        if algorithm != "scrypt":
            return False
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1, dklen=64)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(token)))
    now = datetime.now(timezone.utc)
    if (not session or session.revoked_at is not None or _utc(session.expires_at) <= now
            or session.csrf_hash.startswith((QR_SESSION_PREFIX, QR_USED_PREFIX))):
        raise HTTPException(status_code=401, detail="Sesión inválida o vencida")
    user = db.get(User, session.user_id)
    if not user or not user.active or user.role not in {"owner", "cashier", "customer"}:
        raise HTTPException(status_code=401, detail="Cuenta desactivada")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        csrf_cookie = request.cookies.get(CSRF_COOKIE, "")
        csrf_header = request.headers.get("x-csrf-token", "")
        if not csrf_cookie or not hmac.compare_digest(csrf_cookie, csrf_header) \
                or not hmac.compare_digest(token_hash(csrf_cookie), session.csrf_hash):
            raise HTTPException(status_code=403, detail="Token CSRF inválido")
    request.state.auth_session = session
    context_token = _request_actor.set(user)
    try:
        yield user
    finally:
        _request_actor.reset(context_token)


def require_staff(user: User = Depends(get_current_user)) -> User:
    if user.role not in {"owner", "cashier"}:
        raise HTTPException(status_code=403, detail="Se requiere una cuenta de tienda")
    return user


def require_owner(user: User = Depends(get_current_user)) -> User:
    if user.role != "owner":
        raise HTTPException(status_code=403, detail="Se requiere el rol owner")
    return user


def require_role(*roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Permisos insuficientes")
        return user
    return dependency


def new_session(db: Session, user: User) -> tuple[str, str, datetime]:
    raw_token = secrets.token_urlsafe(32)
    raw_csrf = secrets.token_urlsafe(24)
    expires = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
    db.add(AuthSession(token_hash=token_hash(raw_token), csrf_hash=token_hash(raw_csrf),
                       user_id=user.id, expires_at=expires))
    db.commit()
    return raw_token, raw_csrf, expires


def _secure_cookie(request: Request) -> bool:
    from app.core.config import settings
    # Do not trust X-Forwarded-Proto: the app cannot prove every upstream proxy
    # overwrites client-supplied values. Use the ASGI scheme, Vercel's
    # deployment-controlled system variable, or explicit operator config.
    return (
        request.url.scheme.lower() == "https"
        or os.getenv("VERCEL") == "1"
        or settings.auth_cookie_secure
    )


def set_session_cookies(response, request: Request, raw_token: str, raw_csrf: str, expires: datetime) -> None:
    common = {"secure": _secure_cookie(request),
              "samesite": "lax", "path": "/"}
    response.set_cookie(SESSION_COOKIE, raw_token, httponly=True, max_age=SESSION_HOURS * 3600, **common)
    response.set_cookie(CSRF_COOKIE, raw_csrf, httponly=False, max_age=SESSION_HOURS * 3600, **common)


def delete_session_cookies(response, request: Request) -> None:
    secure = _secure_cookie(request)
    response.delete_cookie(SESSION_COOKIE, path="/", secure=secure, httponly=True, samesite="lax")
    response.delete_cookie(CSRF_COOKIE, path="/", secure=secure, httponly=False, samesite="lax")


def revoke_request_session(request: Request, db: Session) -> None:
    session = getattr(request.state, "auth_session", None)
    if session and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()

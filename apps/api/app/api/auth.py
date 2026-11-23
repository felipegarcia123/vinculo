from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import (get_current_user, new_session, revoke_request_session,
                           set_session_cookies, delete_session_cookies, verify_password)
from app.core.db import get_db
from app.core.login_rate_limit import clear_username_failures, enforce_login_limit, record_failed_login
from app.models import User
from app.schemas.auth import LoginIn, SessionOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _session_out(user: User, request: Request | None = None) -> SessionOut:
    session = getattr(request.state, "auth_session", None) if request else None
    return SessionOut(id=str(user.id), name=user.name, username=user.username or "", role=user.role,
                      expires_at=session.expires_at if session else None)


@router.post("/login", response_model=SessionOut)
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    username = body.username.strip().lower()
    username_hash, ip_hash = enforce_login_limit(db, username, request)
    user = db.scalar(select(User).where(User.username == username))
    if not user or not user.active or not verify_password(body.password, user.password_hash):
        record_failed_login(db, (username_hash, ip_hash))
        db.commit()
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    clear_username_failures(db, username_hash)
    raw_token, raw_csrf, expires = new_session(db, user)
    set_session_cookies(response, request, raw_token, raw_csrf, expires)
    return _session_out(user)


@router.get("/me", response_model=SessionOut)
def me(request: Request, user: User = Depends(get_current_user)):
    return _session_out(user, request)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db),
           _: User = Depends(get_current_user)):
    revoke_request_session(request, db)
    delete_session_cookies(response, request)

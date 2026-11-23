"""Short-lived, one-use customer challenges backed by database sessions."""
from datetime import datetime, timedelta, timezone
import secrets
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import QR_SESSION_PREFIX, QR_USED_PREFIX, token_hash
from app.models import AuthSession, LoyaltyMember, LoyaltyRedemption, LoyaltyReward, User
from app.services.loyalty import balance, redeem_reward

QR_TTL = timedelta(seconds=90)
QR_VISIT = "QR:VISIT"
QR_REDEMPTION_PREFIX = "QR:REDEEM:"
USED_VISIT_PREFIX = "USED:QR:VISIT:"
USED_REDEMPTION_PREFIX = "USED:QR:REDEEM:"


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _member_for_user(db: Session, user_id: UUID) -> LoyaltyMember:
    member = db.scalar(select(LoyaltyMember).where(
        LoyaltyMember.user_id == user_id, LoyaltyMember.active.is_(True)))
    if member is None:
        raise HTTPException(404, "Cuenta de fidelización no encontrada")
    return member


def issue_qr(db: Session, user: User, purpose: str, reward_id: UUID | None = None) -> dict:
    member = _member_for_user(db, user.id)
    reward = None
    marker = QR_VISIT
    if purpose == "redemption":
        reward = db.scalar(select(LoyaltyReward).where(
            LoyaltyReward.id == reward_id, LoyaltyReward.active.is_(True)).with_for_update())
        if reward is None:
            raise HTTPException(404, "Premio no encontrado")
        if reward.stock is not None and reward.stock < 1:
            raise HTTPException(409, "Premio agotado")
        if balance(db, member.id) < reward.stamps_cost:
            raise HTTPException(409, "Todavía no tienes suficientes sellos")
        marker = f"{QR_REDEMPTION_PREFIX}{reward.id}"
    elif purpose != "visit" or reward_id is not None:
        raise HTTPException(422, "Tipo de QR inválido")

    now = datetime.now(timezone.utc)
    previous = db.scalars(select(AuthSession).where(
        AuthSession.user_id == user.id, AuthSession.csrf_hash.like(f"{QR_SESSION_PREFIX}%"),
        AuthSession.revoked_at.is_(None)).with_for_update()).all()
    for row in previous:
        row.revoked_at = now
    raw_token = secrets.token_urlsafe(32)
    expires_at = now + QR_TTL
    db.add(AuthSession(token_hash=token_hash(raw_token), csrf_hash=marker, user_id=user.id,
                       expires_at=expires_at))
    db.commit()
    return {"token": raw_token, "purpose": purpose, "expires_at": expires_at.isoformat(),
            "expires_in_seconds": int(QR_TTL.total_seconds()), "reward_name": reward.name if reward else None}


def _identity(db: Session, row: AuthSession) -> tuple[User, LoyaltyMember]:
    user = db.get(User, row.user_id)
    if user is None or not user.active or user.role != "customer":
        raise HTTPException(410, "Código QR vencido")
    return user, _member_for_user(db, user.id)


def consume_redemption_qr(db: Session, raw_token: str, cashier: User) -> dict:
    row = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(raw_token)).with_for_update())
    if row is None:
        raise HTTPException(404, "Código QR no válido")
    now = datetime.now(timezone.utc)
    if row.csrf_hash.startswith(USED_REDEMPTION_PREFIX):
        reward_id = UUID(row.csrf_hash.removeprefix(USED_REDEMPTION_PREFIX))
        _, member = _identity(db, row)
        redemption = db.scalar(select(LoyaltyRedemption).where(
            LoyaltyRedemption.idempotency_key == f"qr-{row.token_hash}"))
        if redemption is None or redemption.member_id != member.id or redemption.reward_id != reward_id:
            raise HTTPException(409, "No se encontró el canje asociado a este código")
        reward = db.get(LoyaltyReward, reward_id)
        return {"redemption_id": str(redemption.id), "member_id": str(member.id),
                "display_name": member.display_name, "reward_name": reward.name if reward else "Premio",
                "stamps_spent": redemption.stamps_spent, "balance": balance(db, member.id),
                "already_consumed": True}
    if not row.csrf_hash.startswith(QR_REDEMPTION_PREFIX) or row.revoked_at is not None:
        raise HTTPException(409, "El código QR no es un canje válido o ya fue usado")
    if _utc(row.expires_at) <= now:
        raise HTTPException(410, "El código QR venció; solicita uno nuevo")
    _, member = _identity(db, row)
    reward_id = UUID(row.csrf_hash.removeprefix(QR_REDEMPTION_PREFIX))
    reward = db.get(LoyaltyReward, reward_id)
    if reward is None or not reward.active:
        raise HTTPException(404, "Premio no encontrado")
    row.csrf_hash = f"{USED_REDEMPTION_PREFIX}{reward_id}"
    row.revoked_at = now
    redemption = redeem_reward(db, member.id, reward.id, cashier, f"qr-{row.token_hash}")
    db.refresh(redemption)
    return {"redemption_id": str(redemption.id), "member_id": str(member.id),
            "display_name": member.display_name, "reward_name": reward.name,
            "stamps_spent": redemption.stamps_spent, "balance": balance(db, member.id),
            "already_consumed": False}

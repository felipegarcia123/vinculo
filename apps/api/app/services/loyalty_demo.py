"""Fixed-price fictional purchases. This module has no POS, payment or inventory dependencies."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import token_hash
from app.models import (AuthSession, LoyaltyMember, LoyaltyProgram, LoyaltyPurchase, LoyaltyReward,
                        LoyaltyVisit, User)
from app.services.loyalty import award_completed_purchase, balance
from app.services.loyalty_qr import QR_VISIT, USED_VISIT_PREFIX, _utc

DEMO_PURCHASE_TOTAL = Decimal("12000.00")
DEMO_PRODUCT_NAME = "Compra ficticia de demostración"


def _program(db: Session) -> LoyaltyProgram:
    program = db.scalar(select(LoyaltyProgram).where(LoyaltyProgram.active.is_(True)).order_by(
        LoyaltyProgram.created_at).limit(1))
    if program is None:
        raise HTTPException(503, "Programa de fidelización no configurado")
    return program


def cashier_config(db: Session) -> dict:
    program = _program(db)
    return {"product_name": DEMO_PRODUCT_NAME, "purchase_total": str(DEMO_PURCHASE_TOTAL),
            "minimum_purchase": str(program.minimum_purchase), "stamps_per_purchase": program.stamps_per_purchase,
            "reward_stamps": program.reward_stamps, "payment_label": "Pago ficticio · sin dinero real"}


def simulate_purchase(db: Session, raw_token: str, cashier: User) -> dict:
    if cashier.role != "cashier":
        raise HTTPException(403, "Esta caja ficticia requiere el rol cashier")
    if len(raw_token) < 24 or len(raw_token) > 128:
        raise HTTPException(422, "Código QR inválido")
    digest = token_hash(raw_token)
    row = db.scalar(select(AuthSession).where(AuthSession.token_hash == digest).with_for_update())
    if row is None:
        raise HTTPException(404, "Código QR no válido")

    if row.csrf_hash.startswith(USED_VISIT_PREFIX):
        try:
            purchase_id = UUID(row.csrf_hash.removeprefix(USED_VISIT_PREFIX))
        except ValueError as exc:
            raise HTTPException(409, "El QR ya se asoció a una operación inválida") from exc
        purchase = db.get(LoyaltyPurchase, purchase_id)
        if (purchase is None or purchase.idempotency_key != f"vinculo-demo-{digest}"
                or purchase.status != "COMPLETED" or purchase.member_id is None):
            raise HTTPException(409, "No se encontró la compra asociada a este QR")
        member = db.get(LoyaltyMember, purchase.member_id)
        if member is None:
            raise HTTPException(409, "No se encontró el miembro de fidelización")
        return _result(db, purchase, member, already_processed=True)

    now = datetime.now(timezone.utc)
    if row.csrf_hash != QR_VISIT or row.revoked_at is not None:
        raise HTTPException(409, "El QR no corresponde a una visita o ya fue usado")
    if _utc(row.expires_at) <= now:
        raise HTTPException(410, "El QR venció; el cliente debe generar otro")
    user = db.get(User, row.user_id)
    if user is None or not user.active or user.role != "customer":
        raise HTTPException(410, "El QR venció")
    member = db.scalar(select(LoyaltyMember).where(
        LoyaltyMember.user_id == user.id, LoyaltyMember.active.is_(True)))
    if member is None:
        raise HTTPException(404, "Cuenta de fidelización no encontrada")
    program = _program(db)
    if DEMO_PURCHASE_TOTAL < Decimal(program.minimum_purchase):
        raise HTTPException(409, "La compra ficticia no alcanza el mínimo configurado")

    purchase_id = uuid4()
    purchase = LoyaltyPurchase(id=purchase_id, reference=f"VD-{purchase_id.hex[:10].upper()}",
        status="COMPLETED", total=DEMO_PURCHASE_TOTAL, cashier_id=cashier.id, member_id=member.id,
        idempotency_key=f"vinculo-demo-{digest}", completed_at=now)
    row.csrf_hash = f"{USED_VISIT_PREFIX}{purchase_id}"
    row.revoked_at = now
    db.add(purchase)
    try:
        db.flush()
        award_completed_purchase(db, purchase, cashier)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = db.scalar(select(LoyaltyPurchase).where(
            LoyaltyPurchase.idempotency_key == f"vinculo-demo-{digest}"))
        if existing and existing.member_id == member.id:
            return _result(db, existing, member, already_processed=True)
        raise HTTPException(409, "La compra ficticia está siendo procesada") from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(purchase)
    return _result(db, purchase, member, already_processed=False)


def _result(db: Session, purchase: LoyaltyPurchase, member: LoyaltyMember, *, already_processed: bool) -> dict:
    program = _program(db)
    visit = db.scalar(select(LoyaltyVisit).where(LoyaltyVisit.purchase_id == purchase.id))
    return {"purchase_id": str(purchase.id), "member_id": str(member.id), "display_name": member.display_name,
            "purchase_total": str(purchase.total), "stamps_awarded": program.stamps_per_purchase if visit else 0,
            "balance": balance(db, member.id), "already_processed": already_processed, "simulated": True}

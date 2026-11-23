from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (LoyaltyMember, LoyaltyProgram, LoyaltyPurchase, LoyaltyRedemption, LoyaltyReward,
                        LoyaltyStampEntry, LoyaltyVisit, User)


def balance(db: Session, member_id: UUID) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(LoyaltyStampEntry.amount), 0)).where(
        LoyaltyStampEntry.member_id == member_id)) or 0)


def award_completed_purchase(db: Session, purchase: LoyaltyPurchase, cashier: User) -> LoyaltyVisit | None:
    if purchase.status != "COMPLETED" or not purchase.member_id:
        return None
    existing = db.scalar(select(LoyaltyVisit).where(LoyaltyVisit.purchase_id == purchase.id))
    if existing:
        return existing
    member = db.scalar(select(LoyaltyMember).where(
        LoyaltyMember.id == purchase.member_id, LoyaltyMember.active.is_(True)))
    program = db.scalar(select(LoyaltyProgram).where(LoyaltyProgram.active.is_(True)).order_by(
        LoyaltyProgram.created_at).limit(1))
    if not member or not program or Decimal(purchase.total) < Decimal(program.minimum_purchase):
        return None
    visit = LoyaltyVisit(program_id=program.id, member_id=member.id, purchase_id=purchase.id,
                         cashier_id=cashier.id, purchase_total=purchase.total)
    db.add(visit)
    db.flush()
    db.add(LoyaltyStampEntry(member_id=member.id, visit_id=visit.id,
                             amount=program.stamps_per_purchase, reason="PURCHASE"))
    return visit


def redeem_reward(db: Session, member_id: UUID, reward_id: UUID, cashier: User,
                  idempotency_key: str) -> LoyaltyRedemption:
    if not idempotency_key or len(idempotency_key) > 80:
        raise HTTPException(422, "Idempotency-Key requerido (máximo 80 caracteres)")
    existing = db.scalar(select(LoyaltyRedemption).where(LoyaltyRedemption.idempotency_key == idempotency_key))
    if existing:
        if existing.member_id != member_id or existing.reward_id != reward_id:
            raise HTTPException(409, "La clave ya se usó para otro canje")
        return existing
    try:
        member = db.scalar(select(LoyaltyMember).where(
            LoyaltyMember.id == member_id, LoyaltyMember.active.is_(True)).with_for_update())
        reward = db.scalar(select(LoyaltyReward).where(
            LoyaltyReward.id == reward_id, LoyaltyReward.active.is_(True)).with_for_update())
        if not member or not reward:
            raise HTTPException(404, "Miembro o premio no encontrado")
        if reward.stock is not None and reward.stock < 1:
            raise HTTPException(409, "Premio agotado")
        if balance(db, member_id) < reward.stamps_cost:
            raise HTTPException(409, "Sellos insuficientes")
        redemption = LoyaltyRedemption(member_id=member.id, reward_id=reward.id, cashier_id=cashier.id,
                                       stamps_spent=reward.stamps_cost, idempotency_key=idempotency_key)
        db.add(redemption)
        db.flush()
        db.add(LoyaltyStampEntry(member_id=member.id, redemption_id=redemption.id,
                                 amount=-reward.stamps_cost, reason="REDEMPTION"))
        if reward.stock is not None:
            reward.stock -= 1
        db.commit()
        db.refresh(redemption)
        return redemption
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        existing = db.scalar(select(LoyaltyRedemption).where(LoyaltyRedemption.idempotency_key == idempotency_key))
        if existing and existing.member_id == member_id and existing.reward_id == reward_id:
            return existing
        raise HTTPException(409, "Canje duplicado o saldo actualizado en paralelo") from exc

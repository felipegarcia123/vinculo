from datetime import datetime, timedelta, timezone
from decimal import Decimal
from statistics import median
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_owner, require_role, require_staff
from app.core.config import settings
from app.core.db import get_db
from app.models import (LoyaltyMember, LoyaltyProgram, LoyaltyRedemption, LoyaltyReward,
                        LoyaltyStampEntry, LoyaltyVisit, User)
from app.schemas.loyalty import (LoyaltyProgramUpdate, LoyaltyQrIssueIn,
                                 LoyaltyQrRedeemIn, LoyaltyInsightRequest, LoyaltyDemoPurchaseIn)
from app.services.loyalty import balance
from app.services.loyalty_demo import cashier_config, simulate_purchase
from app.services.loyalty_qr import consume_redemption_qr, issue_qr

router = APIRouter(prefix="/loyalty", tags=["loyalty"])


@router.get("/program", dependencies=[Depends(require_owner)])
def get_program(db: Session = Depends(get_db)):
    program = db.scalar(select(LoyaltyProgram).where(LoyaltyProgram.active.is_(True)).order_by(
        LoyaltyProgram.created_at).limit(1))
    if not program:
        raise HTTPException(404, "Programa de fidelización no disponible")
    rewards = db.scalars(select(LoyaltyReward).where(LoyaltyReward.program_id == program.id).order_by(
        LoyaltyReward.created_at)).all()
    return {"id": str(program.id), "code": program.code, "name": program.name,
            "active": program.active, "minimum_purchase": program.minimum_purchase,
            "stamps_per_purchase": program.stamps_per_purchase, "reward_stamps": program.reward_stamps,
            "rewards": [{"id": str(row.id), "name": row.name, "stamps_cost": row.stamps_cost,
                         "stock": row.stock, "active": row.active} for row in rewards]}


@router.put("/program", dependencies=[Depends(require_owner)])
def update_program(body: LoyaltyProgramUpdate, db: Session = Depends(get_db)):
    program = db.scalar(select(LoyaltyProgram).where(LoyaltyProgram.active.is_(True)).order_by(
        LoyaltyProgram.created_at).limit(1).with_for_update())
    if not program:
        raise HTTPException(404, "Programa de fidelización no disponible")
    program.minimum_purchase = Decimal(body.minimum_purchase)
    program.stamps_per_purchase = body.stamps_per_purchase
    program.reward_stamps = body.reward_stamps
    reward = db.scalar(select(LoyaltyReward).where(
        LoyaltyReward.program_id == program.id, LoyaltyReward.active.is_(True)).order_by(
            LoyaltyReward.created_at).limit(1).with_for_update())
    if reward:
        reward.stamps_cost = body.reward_stamps
    db.commit()
    return get_program(db)


@router.get("/me", dependencies=[Depends(require_role("customer"))])
def my_loyalty_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    member = db.scalar(select(LoyaltyMember).where(
        LoyaltyMember.user_id == user.id, LoyaltyMember.active.is_(True)))
    if not member:
        raise HTTPException(404, "Cuenta de fidelización no encontrada")
    program = db.scalar(select(LoyaltyProgram).where(LoyaltyProgram.active.is_(True)).order_by(
        LoyaltyProgram.created_at).limit(1))
    if not program:
        raise HTTPException(404, "Programa de fidelización no disponible")
    rewards = db.scalars(select(LoyaltyReward).where(
        LoyaltyReward.program_id == program.id, LoyaltyReward.active.is_(True)).order_by(LoyaltyReward.stamps_cost)).all()
    visits = db.execute(select(LoyaltyVisit, LoyaltyStampEntry.amount).join(
        LoyaltyStampEntry, LoyaltyStampEntry.visit_id == LoyaltyVisit.id).where(
        LoyaltyVisit.member_id == member.id).order_by(LoyaltyVisit.created_at.desc()).limit(30)).all()
    redemptions = db.execute(select(LoyaltyRedemption, LoyaltyReward.name).join(
        LoyaltyReward, LoyaltyReward.id == LoyaltyRedemption.reward_id).where(
        LoyaltyRedemption.member_id == member.id).order_by(LoyaltyRedemption.created_at.desc()).limit(30)).all()
    return {"member_id": str(member.id), "display_name": member.display_name,
            "program": program.name, "balance": balance(db, member.id),
            "reward_stamps": program.reward_stamps,
            "rewards": [{"id": str(row.id), "name": row.name, "stamps_cost": row.stamps_cost,
                         "available": row.stock is None or row.stock > 0} for row in rewards],
            "visits": [{"id": str(visit.id), "created_at": visit.created_at, "purchase_total": visit.purchase_total,
                        "stamps": amount} for visit, amount in visits],
            "redemptions": [{"id": str(item.id), "created_at": item.created_at,
                             "reward_name": name, "stamps_spent": item.stamps_spent}
                            for item, name in redemptions]}


@router.post("/qr", dependencies=[Depends(require_role("customer"))])
def create_loyalty_qr(body: LoyaltyQrIssueIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return issue_qr(db, user, body.purpose, body.reward_id)


@router.post("/qr/redemption/consume", dependencies=[Depends(require_staff)])
def consume_redemption(body: LoyaltyQrRedeemIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return consume_redemption_qr(db, body.token, user)


@router.get("/demo/cashier/config", dependencies=[Depends(require_role("cashier"))])
def demo_cashier_config(db: Session = Depends(get_db)):
    return cashier_config(db)


@router.post("/demo/cashier/purchase", dependencies=[Depends(require_role("cashier"))])
def demo_cashier_purchase(body: LoyaltyDemoPurchaseIn, user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    return simulate_purchase(db, body.token, user)


def _owner_metrics(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=settings.loyalty_inactive_days)
    members = db.scalars(select(LoyaltyMember).where(LoyaltyMember.active.is_(True))).all()
    rows = db.execute(select(LoyaltyVisit.member_id, LoyaltyVisit.created_at).order_by(
        LoyaltyVisit.member_id, LoyaltyVisit.created_at)).all()
    by_member: dict[UUID, list[datetime]] = {}
    for member_id, created_at in rows:
        stamp = created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at
        by_member.setdefault(member_id, []).append(stamp)
    inactive, pattern_breaks, insufficient = [], [], 0
    balances: dict[UUID, int] = {}
    for member in members:
        dates = by_member.get(member.id, [])
        last = dates[-1] if dates else None
        if last is None or last < cutoff:
            inactive.append({"member_id": str(member.id), "display_name": member.display_name,
                             "last_visit": last.isoformat() if last else None,
                             "days_inactive": (now - last).days if last else None,
                             "never_visited": last is None})
        if len(dates) >= 3:
            intervals = [(b - a).total_seconds() / 86400 for a, b in zip(dates, dates[1:])]
            usual_gap = median(intervals)
            if (now - dates[-1]).total_seconds() / 86400 > max(7, usual_gap * 2):
                pattern_breaks.append({"member_id": str(member.id), "display_name": member.display_name,
                                       "last_visit": dates[-1].isoformat(), "usual_interval_days": round(usual_gap, 1),
                                       "days_since_visit": (now - dates[-1]).days})
        else:
            insufficient += 1
        balances[member.id] = balance(db, member.id)
    visits_30 = db.scalar(select(func.count()).select_from(LoyaltyVisit).where(
        LoyaltyVisit.created_at >= now - timedelta(days=30))) or 0
    stamps_30 = db.scalar(select(func.coalesce(func.sum(LoyaltyStampEntry.amount), 0)).where(
        LoyaltyStampEntry.created_at >= now - timedelta(days=30), LoyaltyStampEntry.amount > 0)) or 0
    redemptions_30 = db.scalar(select(func.count()).select_from(LoyaltyRedemption).where(
        LoyaltyRedemption.created_at >= now - timedelta(days=30))) or 0
    program = db.scalar(select(LoyaltyProgram).where(LoyaltyProgram.active.is_(True)).order_by(
        LoyaltyProgram.created_at).limit(1))
    eligible_near_reward = sum(1 for b in balances.values() if program and b == program.reward_stamps - 1)
    never_visited = sum(1 for member in members if not by_member.get(member.id))
    proposals = []
    if never_visited:
        proposals.append({"id": "welcome_members", "status": "DRAFT", "label": "Bienvenida a nuevos miembros",
                          "basis": f"{never_visited} miembros activos aún no tienen visitas registradas.",
                          "suggestion": "Preparar un incentivo de bienvenida pequeño, sujeto a aprobación del propietario.",
                          "message": "Bienvenido a la fidelización de la tienda. En tu próxima compra elegible empiezas a sumar sellos."})
    if inactive:
        proposals.append({"id": "recover_inactive", "status": "DRAFT", "label": "Invitar a volver",
                          "basis": f"{len(inactive)} miembros sin visita en los últimos {settings.loyalty_inactive_days} días o sin visitas registradas.",
                          "suggestion": "Preparar un incentivo pequeño de retorno y revisar el costo antes de aprobar.",
                          "message": "Te extrañamos en la tienda. Vuelve pronto y pregunta por la recompensa de fidelización disponible."})
    if eligible_near_reward:
        proposals.append({"id": "near_reward", "status": "DRAFT", "label": "Reconocer progreso",
                          "basis": f"{eligible_near_reward} miembros están a un sello del premio.",
                          "suggestion": "Agradecer su constancia y recordar el progreso sin regalar sellos.",
                          "message": "¡Gracias por visitarnos! Estás muy cerca de completar tu recompensa."})
    if not proposals:
        proposals.append({"id": "insufficient_evidence", "status": "DRAFT", "label": "Esperar más actividad",
                          "basis": "No hay segmentos con evidencia suficiente para proponer una campaña ahora.",
                          "suggestion": "Registrar visitas elegibles y volver a revisar las métricas.", "message": None})
    return {"as_of": now.isoformat(), "inactive_days": settings.loyalty_inactive_days,
            "members_active": len(members), "visits_last_30_days": int(visits_30),
            "stamps_earned_last_30_days": int(stamps_30), "redemptions_last_30_days": int(redemptions_30),
            "inactive_members": inactive, "pattern_breaks": pattern_breaks,
            "members_without_pattern_data": insufficient, "members_never_visited": never_visited,
            "campaign_drafts": proposals,
            "llm_available": bool(settings.loyalty_llm_enabled and settings.loyalty_llm_api_key)}


@router.get("/analytics", dependencies=[Depends(require_owner)])
def loyalty_analytics(db: Session = Depends(get_db)):
    return _owner_metrics(db)


@router.post("/insights/explain", dependencies=[Depends(require_owner)])
def explain_insights(body: LoyaltyInsightRequest, db: Session = Depends(get_db)):
    metrics = _owner_metrics(db)
    deterministic = {"mode": "deterministic", "explanation": "Las propuestas se basan en visitas, sellos y canjes reales registrados. Permanecen como borradores; no se envían automáticamente.", "campaign_drafts": metrics["campaign_drafts"]}
    if not body.explain_with_llm or not metrics["llm_available"]:
        return deterministic
    try:
        response = httpx.post(f"{settings.loyalty_llm_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.loyalty_llm_api_key}"}, timeout=settings.loyalty_llm_timeout_seconds,
            json={"model": settings.loyalty_llm_model, "temperature": 0.2, "messages": [
                {"role": "system", "content": "Explica en español los hallazgos y propuestas existentes. No inventes métricas, segmentos ni campañas. No incluyas datos personales. No afirmes que se enviarán."},
                {"role": "user", "content": str({k: metrics[k] for k in ("members_active", "visits_last_30_days", "stamps_earned_last_30_days", "redemptions_last_30_days", "inactive_days", "campaign_drafts")})}]})
        response.raise_for_status()
        explanation = response.json()["choices"][0]["message"]["content"]
        return {**deterministic, "mode": "llm", "explanation": str(explanation)[:3000]}
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return {**deterministic, "fallback_reason": "El proveedor no respondió; se muestra explicación determinista."}

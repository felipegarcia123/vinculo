"""Vínculo identity and loyalty ledger; deliberately independent of Comprefácil POS models."""
from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import (Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String,
                        UniqueConstraint, Uuid, func, text)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('owner', 'cashier', 'customer')", name="ck_users_role"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    csrf_hash: Mapped[str] = mapped_column(String(96), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LoginAttemptEvent(Base):
    __tablename__ = "login_attempt_events"
    __table_args__ = (
        CheckConstraint("bucket_kind IN ('ip', 'username')", name="ck_login_attempt_events_bucket_kind"),
        Index("ix_login_attempt_events_bucket_created", "bucket_hash", "created_at"),
        Index("ix_login_attempt_events_created_at", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bucket_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    bucket_kind: Mapped[str] = mapped_column(String(12), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LoyaltyProgram(Base):
    __tablename__ = "loyalty_programs"
    __table_args__ = (
        CheckConstraint("minimum_purchase >= 0", name="ck_loyalty_program_minimum_purchase"),
        CheckConstraint("stamps_per_purchase > 0", name="ck_loyalty_program_stamps_per_purchase"),
        CheckConstraint("reward_stamps > 0", name="ck_loyalty_program_reward_stamps"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    minimum_purchase: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("10000"))
    stamps_per_purchase: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reward_stamps: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LoyaltyMember(Base):
    __tablename__ = "loyalty_members"
    __table_args__ = (UniqueConstraint("user_id", name="uq_loyalty_members_user"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LoyaltyPurchase(Base):
    """Fictional receipt record used by the Vínculo demo; it never moves money or inventory."""
    __tablename__ = "loyalty_purchases"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_loyalty_purchases_idempotency"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reference: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    cashier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    member_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("loyalty_members.id"), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LoyaltyVisit(Base):
    __tablename__ = "loyalty_visits"
    __table_args__ = (
        UniqueConstraint("purchase_id", name="uq_loyalty_visits_purchase"),
        CheckConstraint("purchase_total >= 0", name="ck_loyalty_visits_purchase_total"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loyalty_programs.id"), nullable=False)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loyalty_members.id"), nullable=False, index=True)
    purchase_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loyalty_purchases.id"), nullable=False)
    cashier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    purchase_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LoyaltyReward(Base):
    __tablename__ = "loyalty_rewards"
    __table_args__ = (CheckConstraint("stamps_cost > 0", name="ck_loyalty_rewards_stamps_cost"),
                      CheckConstraint("stock IS NULL OR stock >= 0", name="ck_loyalty_rewards_stock"))
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loyalty_programs.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    stamps_cost: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    stock: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LoyaltyRedemption(Base):
    __tablename__ = "loyalty_redemptions"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_loyalty_redemptions_idempotency"),
                      CheckConstraint("stamps_spent > 0", name="ck_loyalty_redemptions_stamps_spent"))
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loyalty_members.id"), nullable=False, index=True)
    reward_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loyalty_rewards.id"), nullable=False)
    cashier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    stamps_spent: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="REDEEMED", server_default="REDEEMED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LoyaltyStampEntry(Base):
    __tablename__ = "loyalty_stamp_entries"
    __table_args__ = (
        UniqueConstraint("visit_id", name="uq_loyalty_stamp_entries_visit"),
        UniqueConstraint("redemption_id", name="uq_loyalty_stamp_entries_redemption"),
        CheckConstraint("(visit_id IS NOT NULL) <> (redemption_id IS NOT NULL)", name="ck_loyalty_stamp_entries_source"),
        CheckConstraint("amount != 0", name="ck_loyalty_stamp_entries_nonzero"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("loyalty_members.id"), nullable=False, index=True)
    visit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("loyalty_visits.id"), nullable=True)
    redemption_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("loyalty_redemptions.id"), nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

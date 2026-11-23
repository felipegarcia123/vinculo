"""Independent frozen Vínculo schema. Consolidated from source migrations 0033 and 0034."""
from alembic import op
import sqlalchemy as sa
import uuid
from sqlalchemy.dialects import postgresql

revision = "0001_vinculo_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.CheckConstraint("role IN ('owner', 'cashier', 'customer')", name="ck_users_role"),
        sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table("auth_sessions",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_hash", sa.String(length=96), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_hash"))
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])

    op.create_table("login_attempt_events",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("bucket_hash", sa.String(length=64), nullable=False),
        sa.Column("bucket_kind", sa.String(length=12), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("bucket_kind IN ('ip', 'username')", name="ck_login_attempt_events_bucket_kind"),
        sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_login_attempt_events_bucket_created", "login_attempt_events", ["bucket_hash", "created_at"])
    op.create_index("ix_login_attempt_events_created_at", "login_attempt_events", ["created_at"])

    op.create_table("loyalty_programs",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("minimum_purchase", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("stamps_per_purchase", sa.Integer(), nullable=False),
        sa.Column("reward_stamps", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("minimum_purchase >= 0", name="ck_loyalty_program_minimum_purchase"),
        sa.CheckConstraint("reward_stamps > 0", name="ck_loyalty_program_reward_stamps"),
        sa.CheckConstraint("stamps_per_purchase > 0", name="ck_loyalty_program_stamps_per_purchase"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("code"))

    op.create_table("loyalty_members",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("user_id", name="uq_loyalty_members_user"))

    op.create_table("loyalty_purchases",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("reference", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("cashier_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("member_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=80), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["cashier_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["loyalty_members.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_loyalty_purchases_idempotency"),
        sa.UniqueConstraint("reference"))

    op.create_table("loyalty_rewards",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("program_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("stamps_cost", sa.Integer(), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("stamps_cost > 0", name="ck_loyalty_rewards_stamps_cost"),
        sa.CheckConstraint("stock IS NULL OR stock >= 0", name="ck_loyalty_rewards_stock"),
        sa.ForeignKeyConstraint(["program_id"], ["loyalty_programs.id"]),
        sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_loyalty_rewards_program_id", "loyalty_rewards", ["program_id"])

    op.create_table("loyalty_visits",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("program_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("member_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("purchase_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("cashier_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("purchase_total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("purchase_total >= 0", name="ck_loyalty_visits_purchase_total"),
        sa.ForeignKeyConstraint(["cashier_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["loyalty_members.id"]),
        sa.ForeignKeyConstraint(["program_id"], ["loyalty_programs.id"]),
        sa.ForeignKeyConstraint(["purchase_id"], ["loyalty_purchases.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("purchase_id", name="uq_loyalty_visits_purchase"))
    op.create_index("ix_loyalty_visits_member_id", "loyalty_visits", ["member_id"])

    op.create_table("loyalty_redemptions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("member_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("reward_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("cashier_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("stamps_spent", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="REDEEMED", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("stamps_spent > 0", name="ck_loyalty_redemptions_stamps_spent"),
        sa.ForeignKeyConstraint(["cashier_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["loyalty_members.id"]),
        sa.ForeignKeyConstraint(["reward_id"], ["loyalty_rewards.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_loyalty_redemptions_idempotency"))
    op.create_index("ix_loyalty_redemptions_member_id", "loyalty_redemptions", ["member_id"])

    op.create_table("loyalty_stamp_entries",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("member_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("visit_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("redemption_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("(visit_id IS NOT NULL) <> (redemption_id IS NOT NULL)", name="ck_loyalty_stamp_entries_source"),
        sa.CheckConstraint("amount != 0", name="ck_loyalty_stamp_entries_nonzero"),
        sa.ForeignKeyConstraint(["member_id"], ["loyalty_members.id"]),
        sa.ForeignKeyConstraint(["redemption_id"], ["loyalty_redemptions.id"]),
        sa.ForeignKeyConstraint(["visit_id"], ["loyalty_visits.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("redemption_id", name="uq_loyalty_stamp_entries_redemption"),
        sa.UniqueConstraint("visit_id", name="uq_loyalty_stamp_entries_visit"))
    op.create_index("ix_loyalty_stamp_entries_member_id", "loyalty_stamp_entries", ["member_id"])

    program_id = uuid.UUID("00010000-0000-0000-0000-000000000001")
    reward_id = uuid.UUID("00010000-0000-0000-0000-000000000002")
    op.bulk_insert(sa.table("loyalty_programs",
        sa.column("id", postgresql.UUID(as_uuid=True)), sa.column("code", sa.String),
        sa.column("name", sa.String), sa.column("active", sa.Boolean),
        sa.column("minimum_purchase", sa.Numeric), sa.column("stamps_per_purchase", sa.Integer),
        sa.column("reward_stamps", sa.Integer)),
        [{"id": program_id, "code": "DEMO_FIVE_STAMPS", "name": "Cartilla de barrio",
          "active": True, "minimum_purchase": 10000, "stamps_per_purchase": 1, "reward_stamps": 5}])
    op.bulk_insert(sa.table("loyalty_rewards",
        sa.column("id", postgresql.UUID(as_uuid=True)), sa.column("program_id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String), sa.column("stamps_cost", sa.Integer),
        sa.column("stock", sa.Integer), sa.column("active", sa.Boolean)),
        [{"id": reward_id, "program_id": program_id, "name": "Premio de fidelidad",
          "stamps_cost": 5, "stock": None, "active": True}])


def downgrade():
    op.drop_index("ix_loyalty_stamp_entries_member_id", table_name="loyalty_stamp_entries")
    op.drop_table("loyalty_stamp_entries")
    op.drop_index("ix_loyalty_redemptions_member_id", table_name="loyalty_redemptions")
    op.drop_table("loyalty_redemptions")
    op.drop_index("ix_loyalty_visits_member_id", table_name="loyalty_visits")
    op.drop_table("loyalty_visits")
    op.drop_index("ix_loyalty_rewards_program_id", table_name="loyalty_rewards")
    op.drop_table("loyalty_rewards")
    op.drop_table("loyalty_purchases")
    op.drop_table("loyalty_members")
    op.drop_table("loyalty_programs")
    op.drop_index("ix_login_attempt_events_created_at", table_name="login_attempt_events")
    op.drop_index("ix_login_attempt_events_bucket_created", table_name="login_attempt_events")
    op.drop_table("login_attempt_events")
    op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")

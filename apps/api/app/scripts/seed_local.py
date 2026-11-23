"""Seed fictional accounts into a dedicated local database only."""
import os

from sqlalchemy import select, text

from app.core.auth import hash_password
from app.core.config import settings
from app.core.db import SessionLocal
from app.models import LoyaltyMember, LoyaltyProgram, LoyaltyReward, User


def seed() -> None:
    if os.getenv("VINCULO_ALLOW_LOCAL_SEED") != "true":
        raise SystemExit("Set VINCULO_ALLOW_LOCAL_SEED=true to enable the local-only seed")
    from sqlalchemy.engine import make_url
    parsed = make_url(settings.database_url)
    if parsed.get_backend_name() != "postgresql" or parsed.host not in {"localhost", "127.0.0.1"} \
            or parsed.database != "vinculo_local":
        raise SystemExit("Seed accepts only localhost PostgreSQL database vinculo_local")
    accounts = [(os.getenv("VINCULO_OWNER_USERNAME", "owner"), os.getenv("VINCULO_OWNER_PASSWORD", ""), "owner"),
                (os.getenv("VINCULO_CASHIER_USERNAME", "cashier"), os.getenv("VINCULO_CASHIER_PASSWORD", ""), "cashier"),
                (os.getenv("VINCULO_CUSTOMER_USERNAME", "customer"), os.getenv("VINCULO_CUSTOMER_PASSWORD", ""), "customer")]
    if any(len(username.strip()) < 3 or len(password) < 24 for username, password, _ in accounts):
        raise SystemExit("Set fictional usernames and unique passwords of at least 24 characters")
    if len({u.strip().lower() for u, _, _ in accounts}) != 3 or len({p for _, p, _ in accounts}) != 3:
        raise SystemExit("Local demo usernames and passwords must be unique")
    with SessionLocal() as db:
        revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
        if revision != "0001_vinculo_baseline":
            raise SystemExit("Seed requires the Vínculo baseline migration")
        if db.scalar(select(User.id).limit(1)) or db.scalar(select(LoyaltyMember.id).limit(1)):
            raise SystemExit("Refusing to seed a database that already contains demo accounts or members")
        program = db.scalar(select(LoyaltyProgram).where(LoyaltyProgram.code == "DEMO_FIVE_STAMPS"))
        reward = db.scalar(select(LoyaltyReward).where(LoyaltyReward.program_id == program.id).limit(1)) if program else None
        if not program or not reward:
            raise SystemExit("Migration baseline program/reward are missing")
        users = {}
        for username, password, role in accounts:
            user = User(username=username.strip().lower(), name=f"Vínculo demo {role}",
                        password_hash=hash_password(password), role=role, active=True)
            db.add(user); users[role] = user
        db.flush()
        db.add(LoyaltyMember(user_id=users["customer"].id, display_name="Cliente ficticio Vínculo"))
        db.commit()
    print("Vínculo local demo accounts created. Passwords were not printed.")


if __name__ == "__main__":
    seed()

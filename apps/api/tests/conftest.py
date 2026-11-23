from decimal import Decimal
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app.core.auth import CSRF_COOKIE, get_current_user, hash_password
from app.core.config import settings
from app.core.db import Base, get_db
from app.main import app
from app.models import LoyaltyMember, LoyaltyProgram, LoyaltyReward, User


@pytest.fixture
def auth_context(monkeypatch):
    monkeypatch.setattr(settings, "vinculo_demo_only", True)
    monkeypatch.setattr(settings, "auth_cookie_secure", False)
    monkeypatch.setattr(settings, "auth_rate_limit_secret", "fictional-local-rate-limit-secret-32-bytes")
    postgres_url = os.environ.get("TEST_POSTGRES_URL")
    if postgres_url:
        parsed = make_url(postgres_url)
        if (parsed.get_backend_name() != "postgresql" or parsed.host not in {"localhost", "127.0.0.1"}
                or not (parsed.database or "").startswith("vinculo_test_")):
            raise RuntimeError("TEST_POSTGRES_URL only accepts loopback and a vinculo_test_* database")
        engine = create_engine(postgres_url, poolclass=NullPool)
        if inspect(engine).get_table_names():
            engine.dispose()
            raise RuntimeError("PostgreSQL test database must be empty; existing tables will not be dropped")
    else:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = factory()
    users = {role: User(name=f"Prueba {role}", username=f"{role}-test",
                        password_hash=hash_password("fictional-password-for-local-tests-2026"),
                        role=role, active=True) for role in ("owner", "cashier", "customer", "customer2")}
    users["customer2"].role = "customer"
    db.add_all(users.values()); db.flush()
    program = LoyaltyProgram(code="TEST", name="Programa de pruebas", minimum_purchase=Decimal("10000"),
                             stamps_per_purchase=1, reward_stamps=5)
    db.add(program); db.flush()
    reward = LoyaltyReward(program_id=program.id, name="Premio", stamps_cost=5, stock=5, active=True)
    db.add(reward); db.flush()
    members = [LoyaltyMember(user_id=users["customer"].id, display_name="Cliente uno"),
               LoyaltyMember(user_id=users["customer2"].id, display_name="Cliente dos")]
    db.add_all(members); db.commit()

    def override_db():
        yield db

    old_db = app.dependency_overrides.get(get_db)
    old_user = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides.pop(get_current_user, None)
    try:
        yield db, users, members, program, reward
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        if old_db is not None:
            app.dependency_overrides[get_db] = old_db
        if old_user is not None:
            app.dependency_overrides[get_current_user] = old_user
        db.close(); Base.metadata.drop_all(engine); engine.dispose()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def login(client, username):
    return client.post("/api/v1/auth/login", json={
        "username": username, "password": "fictional-password-for-local-tests-2026"})


def csrf_headers(client):
    return {"X-CSRF-Token": client.cookies.get(CSRF_COOKIE, "")}

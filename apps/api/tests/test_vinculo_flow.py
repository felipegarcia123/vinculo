from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.auth import token_hash
from app.models import (AuthSession, LoyaltyPurchase, LoyaltyRedemption, LoyaltyStampEntry,
                        LoyaltyVisit)
from conftest import csrf_headers, login


def test_roles_and_customer_isolation(auth_context, client):
    db, users, members, _, _ = auth_context
    assert client.get("/api/v1/loyalty/me").status_code == 401
    assert login(client, "cashier-test").status_code == 200
    assert client.get("/api/v1/loyalty/demo/cashier/config").status_code == 200
    assert client.get("/api/v1/loyalty/analytics").status_code == 403
    assert client.get("/api/v1/loyalty/me").status_code == 403
    assert client.get("/api/v1/sales/open").status_code == 404
    assert client.get("/api/v1/inventory").status_code == 404
    client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    assert login(client, "customer-test").status_code == 200
    one = client.get("/api/v1/loyalty/me")
    assert one.status_code == 200 and one.json()["member_id"] == str(members[0].id)
    assert client.get("/api/v1/loyalty/demo/cashier/config").status_code == 403
    client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    assert login(client, "customer2-test").status_code == 200
    two = client.get("/api/v1/loyalty/me")
    assert two.status_code == 200 and two.json()["member_id"] == str(members[1].id)
    assert two.json()["member_id"] != one.json()["member_id"]


def test_five_eligible_purchases_stamp_once_redeem_once(auth_context):
    db, _, members, _, reward = auth_context
    from app.main import app
    customer = TestClient(app)
    cashier = TestClient(app)
    assert login(customer, "customer-test").status_code == 200
    assert login(cashier, "cashier-test").status_code == 200
    first_token = None
    for _ in range(5):
        qr = customer.post("/api/v1/loyalty/qr", json={"purpose": "visit"}, headers=csrf_headers(customer))
        assert qr.status_code == 200
        token = qr.json()["token"]
        first_token = first_token or token
        purchase = cashier.post("/api/v1/loyalty/demo/cashier/purchase", json={"token": token},
                                headers=csrf_headers(cashier))
        assert purchase.status_code == 200, purchase.text
        assert purchase.json()["stamps_awarded"] == 1
        assert purchase.json()["simulated"] is True
    replay = cashier.post("/api/v1/loyalty/demo/cashier/purchase", json={"token": first_token},
                          headers=csrf_headers(cashier))
    assert replay.status_code == 200 and replay.json()["already_processed"] is True
    assert replay.json()["balance"] == 5
    assert db.scalar(select(func.count()).select_from(LoyaltyPurchase)) == 5
    assert db.scalar(select(func.count()).select_from(LoyaltyVisit)) == 5
    assert db.scalar(select(func.count()).select_from(LoyaltyStampEntry).where(LoyaltyStampEntry.amount > 0)) == 5

    redemption_qr = customer.post("/api/v1/loyalty/qr", json={
        "purpose": "redemption", "reward_id": str(reward.id)}, headers=csrf_headers(customer))
    assert redemption_qr.status_code == 200
    body = {"token": redemption_qr.json()["token"]}
    first = cashier.post("/api/v1/loyalty/qr/redemption/consume", json=body, headers=csrf_headers(cashier))
    second = cashier.post("/api/v1/loyalty/qr/redemption/consume", json=body, headers=csrf_headers(cashier))
    assert first.status_code == second.status_code == 200
    assert first.json()["already_consumed"] is False
    assert second.json()["already_consumed"] is True and second.json()["balance"] == 0
    assert db.scalar(select(func.count()).select_from(LoyaltyRedemption)) == 1
    assert db.scalar(select(func.sum(LoyaltyStampEntry.amount))) == 0
    another_qr = customer.post("/api/v1/loyalty/qr", json={
        "purpose": "redemption", "reward_id": str(reward.id)}, headers=csrf_headers(customer))
    assert another_qr.status_code == 409
    assert db.scalar(select(func.count()).select_from(LoyaltyRedemption)) == 1
    assert db.scalar(select(func.count()).select_from(LoyaltyStampEntry).where(
        LoyaltyStampEntry.amount < 0)) == 1


def test_zero_balance_cannot_issue_redemption_qr(auth_context):
    db, _, _, _, reward = auth_context
    from app.main import app
    customer = TestClient(app)
    assert login(customer, "customer-test").status_code == 200

    response = customer.post("/api/v1/loyalty/qr", json={
        "purpose": "redemption", "reward_id": str(reward.id)}, headers=csrf_headers(customer))
    assert response.status_code == 409
    assert db.scalar(select(func.count()).select_from(LoyaltyRedemption)) == 0
    assert db.scalar(select(func.count()).select_from(LoyaltyStampEntry)) == 0


def test_expired_qr_does_not_create_purchase_or_stamp(auth_context):
    db, _, _, _, _ = auth_context
    from app.main import app
    customer, cashier = TestClient(app), TestClient(app)
    assert login(customer, "customer-test").status_code == 200
    assert login(cashier, "cashier-test").status_code == 200
    qr = customer.post("/api/v1/loyalty/qr", json={"purpose": "visit"}, headers=csrf_headers(customer))
    row = db.get(AuthSession, token_hash(qr.json()["token"]))
    row.expires_at -= timedelta(minutes=5); db.commit()
    response = cashier.post("/api/v1/loyalty/demo/cashier/purchase", json={"token": qr.json()["token"]},
                            headers=csrf_headers(cashier))
    assert response.status_code == 410
    assert db.scalar(select(func.count()).select_from(LoyaltyPurchase)) == 0
    assert db.scalar(select(func.count()).select_from(LoyaltyStampEntry)) == 0


def test_demo_only_rejects_unknown_operational_paths_even_with_session(auth_context):
    from app.main import app
    client = TestClient(app)
    assert login(client, "owner-test").status_code == 200
    for path in ("/api/v1/sales", "/api/v1/customers", "/api/v1/inventory", "/api/v1/purchases", "/api/v1/cash"):
        assert client.get(path).status_code == 404
        assert client.post(path, headers=csrf_headers(client), json={}).status_code == 404


def test_program_and_campaign_routes_are_owner_only(auth_context):
    from app.main import app
    client = TestClient(app)
    assert login(client, "owner-test").status_code == 200
    assert client.get("/api/v1/loyalty/analytics").status_code == 200
    assert client.get("/api/v1/loyalty/program").status_code == 200
    assert client.post("/api/v1/loyalty/insights/explain", json={"explain_with_llm": True},
                       headers=csrf_headers(client)).status_code == 200

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import settings
from app.main import app
from app.models import AuthSession
from conftest import csrf_headers, login


ALLOWED_ORIGIN = settings.cors_origins.split(",")[0].strip()
UNTRUSTED_ORIGIN = "https://untrusted-vinculo.example"


def preflight(client: TestClient, path: str, method: str, *, origin: str = ALLOWED_ORIGIN,
              headers: str = "content-type"):
    return client.options(path, headers={
        "Origin": origin,
        "Access-Control-Request-Method": method,
        "Access-Control-Request-Headers": headers,
    })


def test_login_preflight_from_allowed_origin(client, monkeypatch):
    monkeypatch.setattr(settings, "vinculo_demo_only", True)
    response = preflight(client, "/api/v1/auth/login", "POST")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "POST" in response.headers["access-control-allow-methods"].split(", ")
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_protected_route_preflight_from_allowed_origin(client, monkeypatch):
    monkeypatch.setattr(settings, "vinculo_demo_only", True)
    response = preflight(client, "/api/v1/loyalty/qr", "POST",
                         headers="content-type,x-csrf-token")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "POST" in response.headers["access-control-allow-methods"].split(", ")
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "content-type" in allowed_headers and "x-csrf-token" in allowed_headers


def test_preflight_cannot_request_a_method_blocked_by_demo(client, monkeypatch):
    monkeypatch.setattr(settings, "vinculo_demo_only", True)
    response = preflight(client, "/api/v1/auth/login", "PUT")

    assert response.status_code == 404
    assert "access-control-allow-origin" not in response.headers


def test_preflight_cannot_open_a_route_blocked_by_demo(client, monkeypatch):
    monkeypatch.setattr(settings, "vinculo_demo_only", True)
    response = preflight(client, "/api/v1/sales", "POST")

    assert response.status_code == 404
    assert "access-control-allow-origin" not in response.headers


def test_preflight_from_untrusted_origin_has_no_cors_authorization(client, monkeypatch):
    monkeypatch.setattr(settings, "vinculo_demo_only", True)
    response = preflight(client, "/api/v1/auth/login", "POST", origin=UNTRUSTED_ORIGIN)

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_preflight_with_untrusted_header_is_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "vinculo_demo_only", True)
    response = preflight(client, "/api/v1/auth/login", "POST", headers="x-untrusted-header")

    assert response.status_code == 400
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "x-untrusted-header" not in response.headers["access-control-allow-headers"].lower()


def test_bare_options_and_actual_blocked_route_stay_unavailable(client, monkeypatch):
    monkeypatch.setattr(settings, "vinculo_demo_only", True)
    assert client.options("/api/v1/auth/login").status_code == 404
    assert client.get("/api/v1/sales").status_code == 404
    assert client.post("/api/v1/sales", json={}).status_code == 404


def test_incomplete_options_do_not_bypass_demo_mode(client, monkeypatch):
    monkeypatch.setattr(settings, "vinculo_demo_only", True)
    for headers in ({"Origin": ALLOWED_ORIGIN},
                    {"Access-Control-Request-Method": "POST"}):
        response = client.options("/api/v1/auth/login", headers=headers)
        assert response.status_code == 404
        assert "access-control-allow-origin" not in response.headers


def test_actual_request_keeps_auth_and_csrf(auth_context, client):
    assert settings.vinculo_demo_only is True
    db, _, _, _, _ = auth_context
    anonymous = client.get("/api/v1/loyalty/me", headers={"Origin": ALLOWED_ORIGIN})
    assert anonymous.status_code == 401
    assert anonymous.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    untrusted = client.get("/api/v1/loyalty/me", headers={"Origin": UNTRUSTED_ORIGIN})
    assert untrusted.status_code == 401
    assert "access-control-allow-origin" not in untrusted.headers

    assert login(client, "customer-test").status_code == 200
    initial_sessions = db.scalar(select(func.count()).select_from(AuthSession))
    assert preflight(client, "/api/v1/loyalty/qr", "POST",
                     headers="content-type,x-csrf-token").status_code == 200
    assert db.scalar(select(func.count()).select_from(AuthSession)) == initial_sessions
    assert client.post("/api/v1/loyalty/qr", json={"purpose": "visit"}).status_code == 403
    assert db.scalar(select(func.count()).select_from(AuthSession)) == initial_sessions
    assert client.post("/api/v1/loyalty/qr", json={"purpose": "visit"},
                       headers={"X-CSRF-Token": "incorrect-token"}).status_code == 403
    assert db.scalar(select(func.count()).select_from(AuthSession)) == initial_sessions
    issued = client.post("/api/v1/loyalty/qr", json={"purpose": "visit"},
                         headers=csrf_headers(client))
    assert issued.status_code == 200
    assert db.scalar(select(func.count()).select_from(AuthSession)) == initial_sessions + 1

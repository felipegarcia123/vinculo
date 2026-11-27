from datetime import datetime, timezone

from starlette.requests import Request
from starlette.responses import Response

from app.core.auth import delete_session_cookies, set_session_cookies
from app.core.config import settings


def make_request(*, scheme="http", forwarded_proto=""):
    headers = []
    if forwarded_proto:
        headers.append((b"x-forwarded-proto", forwarded_proto.encode()))
    return Request({
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": scheme,
        "path": "/api/v1/auth/login",
        "raw_path": b"/api/v1/auth/login",
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 50000),
        "server": ("vinculo.test", 443 if scheme == "https" else 80),
    })


def set_cookie_headers(response):
    return [value.decode() for key, value in response.raw_headers if key.lower() == b"set-cookie"]


def test_client_supplied_forwarded_proto_does_not_enable_secure_cookie(monkeypatch):
    monkeypatch.setattr(settings, "auth_cookie_secure", False)
    monkeypatch.delenv("VERCEL", raising=False)
    request = make_request(forwarded_proto="https")
    response = Response()

    set_session_cookies(response, request, "opaque-session", "csrf-value", datetime.now(timezone.utc))

    headers = set_cookie_headers(response)
    assert len(headers) == 2
    normalized = [header.lower() for header in headers]
    assert all("; secure" not in header for header in normalized)
    assert any(header.startswith("vinculo_session=") and "; httponly" in header for header in normalized)
    assert any(header.startswith("vinculo_csrf=") and "; httponly" not in header for header in normalized)


def test_vercel_runtime_forces_secure_cookies_without_trusting_request_headers(monkeypatch):
    monkeypatch.setattr(settings, "auth_cookie_secure", False)
    monkeypatch.setenv("VERCEL", "1")
    request = make_request()
    response = Response()

    set_session_cookies(response, request, "opaque-session", "csrf-value", datetime.now(timezone.utc))

    headers = set_cookie_headers(response)
    normalized = [header.lower() for header in headers]
    assert len(headers) == 2
    assert all("; secure" in header for header in normalized)
    assert any(header.startswith("vinculo_session=") and "; httponly" in header for header in normalized)
    assert any(header.startswith("vinculo_csrf=") and "; httponly" not in header for header in normalized)
    assert all("samesite=lax" in header for header in normalized)

    deletion = Response()
    delete_session_cookies(deletion, request)
    assert all("; secure" in header.lower() for header in set_cookie_headers(deletion))


def test_https_request_scheme_sets_secure_cookie_even_without_forwarded_header(monkeypatch):
    monkeypatch.setattr(settings, "auth_cookie_secure", False)
    response = Response()

    set_session_cookies(response, make_request(scheme="https"), "opaque-session", "csrf-value",
                        datetime.now(timezone.utc))

    assert all("; secure" in header.lower() for header in set_cookie_headers(response))


def test_local_http_remains_compatible_and_cookie_deletion_matches(monkeypatch):
    monkeypatch.setattr(settings, "auth_cookie_secure", False)
    request = make_request()
    response = Response()
    set_session_cookies(response, request, "opaque-session", "csrf-value", datetime.now(timezone.utc))
    assert all("; secure" not in header.lower() for header in set_cookie_headers(response))

    deletion = Response()
    delete_session_cookies(deletion, request)
    assert all("; secure" not in header.lower() for header in set_cookie_headers(deletion))

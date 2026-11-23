import json
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[3]


def test_vercel_services_route_api_before_web_catch_all():
    config = json.loads((ROOT / "vercel.json").read_text())

    assert config["services"] == {
        "web": {"root": "apps/web"},
        "api": {"root": "apps/api", "entrypoint": "app.main:app"},
    }
    api_project = tomllib.loads((ROOT / "apps/api/pyproject.toml").read_text())
    assert api_project["tool"]["vercel"]["entrypoint"] == "app.main:app"
    assert api_project["project"]["requires-python"] == ">=3.12,<3.13"
    rewrites = config["rewrites"]
    assert rewrites[0] == {"source": "/api/v1", "destination": {"service": "api"}}
    assert rewrites[1] == {"source": "/api/v1/(.*)", "destination": {"service": "api"}}
    assert rewrites[2] == {"source": "/(.*)", "destination": {"service": "web"}}


def test_next_proxy_does_not_intercept_api_service_routes():
    proxy = (ROOT / "apps/web/proxy.ts").read_text()
    assert 'matcher: ["/((?!api/v1|' in proxy

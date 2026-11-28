from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.loyalty import router as loyalty_router
from app.core.config import settings

app = FastAPI(title="Vínculo API", version="1.0.0", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True, allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"])

public = APIRouter()


@public.get("/health")
def health():
    return {"status": "ok", "product": "vinculo"}


app.include_router(public, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(loyalty_router, prefix="/api/v1")

ALLOWED_DEMO_API_EXACT = {
    ("GET", "/api/v1/health"),
    ("POST", "/api/v1/auth/login"),
    ("GET", "/api/v1/auth/me"),
    ("POST", "/api/v1/auth/logout"),
    ("GET", "/api/v1/loyalty/demo/cashier/config"),
    ("POST", "/api/v1/loyalty/demo/cashier/purchase"),
    ("POST", "/api/v1/loyalty/qr"),
    ("POST", "/api/v1/loyalty/qr/redemption/consume"),
    ("GET", "/api/v1/loyalty/me"),
    ("GET", "/api/v1/loyalty/analytics"),
    ("POST", "/api/v1/loyalty/insights/explain"),
    ("GET", "/api/v1/loyalty/program"),
    ("PUT", "/api/v1/loyalty/program"),
}


@app.middleware("http")
async def restrict_demo_surface(request: Request, call_next):
    if settings.vinculo_demo_only and request.url.path.startswith("/api/"):
        method = request.method.upper()
        if method == "OPTIONS" and request.headers.get("origin"):
            method = request.headers.get("access-control-request-method", "").upper()
        key = (method, request.url.path.rstrip("/") or "/")
        if key not in ALLOWED_DEMO_API_EXACT:
            return JSONResponse(status_code=404, content={"detail": "Ruta no disponible en Vínculo"},
                                headers={"Cache-Control": "no-store"})
    response = await call_next(request)
    if request.url.path.startswith("/api/v1/"):
        response.headers["Cache-Control"] = "no-store"
    return response

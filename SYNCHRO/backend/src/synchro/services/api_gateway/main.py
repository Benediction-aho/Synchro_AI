from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from synchro.api.v1.router import router as api_v1_router
from synchro.core.config import get_settings
from synchro.core.logging_config import setup_logging
from synchro.core.security_headers import BodySizeLimitMiddleware, SecurityHeadersMiddleware

settings = get_settings()
setup_logging()

app = FastAPI(
    title=f"{settings.app_name} API Gateway",
    version="0.1.0",
    debug=settings.debug,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)

app.add_middleware(SecurityHeadersMiddleware, hsts=settings.environment == "production")
app.add_middleware(
    BodySizeLimitMiddleware, max_body_bytes=settings.max_body_bytes
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(api_v1_router)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "message": f"Welcome to {settings.app_name}",
        "docs": "/docs" if settings.enable_docs else None,
        "health": "/api/v1/health",
    }

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import Settings, get_settings
from src.infrastructure.auth.jwt_service import JWTService
from src.infrastructure.auth.password import PasswordHasher
from src.infrastructure.db.session import create_engine, create_session_factory
from src.infrastructure.email.providers.logging_provider import LoggingEmailService
from src.infrastructure.email.renderer.engine import EmailTemplateRenderer
from src.interfaces.http.deps import get_app_settings
from src.interfaces.http.routers import animal_statuses, animals, breeds, dashboard, lots, reports
from src.interfaces.http.routers import auth as auth_router
from src.interfaces.http.routers import buyers as buyers_router
from src.interfaces.http.routers import milk_deliveries as deliveries_router
from src.interfaces.http.routers import milk_prices as prices_router
from src.interfaces.http.routers import milk_productions as productions_router
from src.interfaces.http.routers import settings as settings_router
from src.interfaces.middleware.auth_middleware import AuthMiddleware
from src.interfaces.middleware.error_handler import register_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        engine = getattr(app.state, "engine", None)
        if engine is not None:
            await engine.dispose()


def _configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    root = logging.getLogger()
    # Avoid adding duplicate handlers on reload
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)
    root.setLevel(level)
    # Align common libraries
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine", "httpx"):
        logging.getLogger(name).setLevel(level)


def create_app(
    *,
    settings: Settings | None = None,
    password_hasher: PasswordHasher | None = None,
    jwt_service: JWTService | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    _configure_logging(settings.log_level)
    app = FastAPI(
        title="LecheFacil Backend",
        version="0.1.0",
        description="Multi-tenant API for LecheFacil MVP",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = create_engine(settings.database_url)
    app.state.session_factory = create_session_factory(app.state.engine)
    app.state.password_hasher = password_hasher or PasswordHasher()
    app.state.jwt_service = jwt_service or JWTService(
        secret_key=settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
        access_token_expires_minutes=settings.jwt_access_token_expires_minutes,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
    )
    # Email service (always use logging provider for now)
    app.state.email_service = LoggingEmailService()
    # Email template renderer
    app.state.email_renderer = EmailTemplateRenderer.create_default()
    # Storage service (S3 only if configured)
    if settings.s3_bucket and settings.s3_region:
        from src.infrastructure.storage.s3 import S3StorageService

        app.state.storage_service = S3StorageService(
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            prefix=settings.s3_prefix,
            public_url_base=settings.s3_public_url_base,
            signed_url_expires=settings.s3_signed_url_expires,
        )
    register_error_handlers(app)

    # Group all API routes behind a single versioned prefix
    api = APIRouter(prefix="/api/v1")
    api.include_router(auth_router.router)
    api.include_router(animals.router)
    api.include_router(animal_statuses.router)
    api.include_router(breeds.router)
    api.include_router(lots.router)
    api.include_router(buyers_router.router)
    api.include_router(prices_router.router)
    api.include_router(productions_router.router)
    api.include_router(deliveries_router.router)
    api.include_router(settings_router.router)
    api.include_router(dashboard.router)
    api.include_router(reports.router)
    from src.interfaces.http.routers import access_requests as access_requests_router

    api.include_router(access_requests_router.router)

    @api.get("/health", tags=["health"])
    async def health(_: Settings = Depends(get_app_settings)) -> dict[str, str]:  # noqa: ANN001
        return {"status": "ok"}

    app.include_router(api)

    # Add Auth first, then CORS last so CORS runs outermost and can handle preflight OPTIONS
    app.add_middleware(AuthMiddleware, settings=settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


app = create_app()

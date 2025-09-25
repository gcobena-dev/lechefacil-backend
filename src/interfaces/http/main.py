from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import Settings, get_settings
from src.infrastructure.auth.jwt_service import JWTService
from src.infrastructure.auth.password import PasswordHasher
from src.infrastructure.db.session import create_engine, create_session_factory
from src.interfaces.http.deps import get_app_settings
from src.interfaces.http.routers import animals
from src.interfaces.http.routers import auth as auth_router
from src.interfaces.http.routers import buyers as buyers_router
from src.interfaces.http.routers import dashboard
from src.interfaces.http.routers import milk_deliveries as deliveries_router
from src.interfaces.http.routers import milk_prices as prices_router
from src.interfaces.http.routers import milk_productions as productions_router
from src.interfaces.http.routers import reports
from src.interfaces.http.routers import settings as settings_router
from src.interfaces.middleware.auth_middleware import AuthMiddleware
from src.interfaces.middleware.error_handler import register_error_handlers
from src.infrastructure.email.providers.logging_provider import LoggingEmailService
from src.infrastructure.email.providers.smtp_provider import SMTPEmailService
from src.infrastructure.email.renderer.engine import EmailTemplateRenderer


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        engine = getattr(app.state, "engine", None)
        if engine is not None:
            await engine.dispose()


def create_app(
    *,
    settings: Settings | None = None,
    password_hasher: PasswordHasher | None = None,
    jwt_service: JWTService | None = None,
) -> FastAPI:
    settings = settings or get_settings()
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
    # Email service selection (default to logging provider)
    if settings.email_provider == "smtp" and settings.smtp_host:
        app.state.email_service = SMTPEmailService(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
            use_ssl=settings.smtp_use_ssl,
        )
    else:
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
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


app = create_app()

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import Settings, get_settings
from src.infrastructure.auth.jwt_service import JWTService
from src.infrastructure.auth.password import PasswordHasher
from src.infrastructure.db.session import create_engine, create_session_factory
from src.infrastructure.email.providers.logging_provider import LoggingEmailService
from src.infrastructure.email.renderer.engine import EmailTemplateRenderer
from src.interfaces.http.deps import get_app_settings
from src.interfaces.http.routers import (
    animal_certificates,
    animal_events,
    animal_statuses,
    animals,
    breeds,
    dashboard,
    health_records,
    lactations,
    lots,
    mobile,
    notifications,
    reports,
)
from src.interfaces.http.routers import auth as auth_router
from src.interfaces.http.routers import buyers as buyers_router
from src.interfaces.http.routers import inseminations as inseminations_router
from src.interfaces.http.routers import milk_deliveries as deliveries_router
from src.interfaces.http.routers import milk_prices as prices_router
from src.interfaces.http.routers import milk_productions as productions_router
from src.interfaces.http.routers import semen_inventory as semen_inventory_router
from src.interfaces.http.routers import settings as settings_router
from src.interfaces.http.routers import sire_catalog as sire_catalog_router
from src.interfaces.middleware.auth_middleware import AuthMiddleware
from src.interfaces.middleware.error_handler import register_error_handlers


async def _scheduler_loop(app: FastAPI, run_at_hour: int = 6) -> None:
    """Run reproduction scheduled tasks daily at the configured hour (UTC)."""
    from src.infrastructure.scheduler.reproduction_tasks import (
        check_expected_calvings,
        check_pending_pregnancy_checks,
    )

    logger = logging.getLogger("scheduler")
    while True:
        try:
            now = datetime.now(timezone.utc)
            target = datetime.combine(now.date(), time(run_at_hour, 0), tzinfo=timezone.utc)
            if now >= target:
                # Already past today's run time, schedule for tomorrow
                from datetime import timedelta

                target += timedelta(days=1)
            wait_seconds = (target - now).total_seconds()
            logger.info("Scheduler sleeping %.0fs until %s UTC", wait_seconds, target.isoformat())
            await asyncio.sleep(wait_seconds)

            session_factory = getattr(app.state, "session_factory", None)
            if session_factory:
                logger.info("Running scheduled reproduction tasks")
                await check_pending_pregnancy_checks(session_factory)
                await check_expected_calvings(session_factory)
                logger.info("Scheduled reproduction tasks completed")
        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
            break
        except Exception as exc:
            logger.error("Scheduler error: %s", exc, exc_info=True)
            # Sleep 60s before retrying on unexpected errors
            await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_task = asyncio.create_task(_scheduler_loop(app))
    try:
        yield
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
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
    # Email service: select provider
    provider = settings.email_provider.lower()
    if provider == "ses":
        try:
            from src.infrastructure.email.providers.ses_provider import SESEmailService

            # Use default AWS credential/region chain; no custom settings required
            app.state.email_service = SESEmailService()
        except Exception as exc:  # fallback to logging provider
            logging.getLogger(__name__).warning(
                "Failed to init SES provider, " "fallback to logging: %s", exc
            )
            app.state.email_service = LoggingEmailService()
    elif provider == "unione":
        try:
            from src.infrastructure.email.providers.unione_provider import UniOneEmailService

            if not settings.unione_api_key:
                raise ValueError("UNIONE_API_KEY is required when EMAIL_PROVIDER=unione")

            app.state.email_service = UniOneEmailService(
                api_key=settings.unione_api_key.get_secret_value(),
                api_url=settings.unione_api_url,
            )
            logging.getLogger(__name__).info("UniOne email service initialized successfully")
        except Exception as exc:  # fallback to logging provider
            logging.getLogger(__name__).warning(
                "Failed to init UniOne provider, " "fallback to logging: %s", exc
            )
            app.state.email_service = LoggingEmailService()
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
    api.include_router(animal_statuses.router)
    api.include_router(animal_events.router)
    api.include_router(health_records.router)
    api.include_router(lactations.router)
    api.include_router(animal_certificates.router)
    api.include_router(breeds.router)
    api.include_router(lots.router)
    api.include_router(buyers_router.router)
    api.include_router(prices_router.router)
    api.include_router(productions_router.router)
    api.include_router(deliveries_router.router)
    api.include_router(settings_router.router)
    api.include_router(dashboard.router)
    api.include_router(reports.router)
    api.include_router(mobile.router)
    api.include_router(notifications.router)
    api.include_router(sire_catalog_router.router)
    api.include_router(semen_inventory_router.router)
    api.include_router(inseminations_router.router)
    from src.interfaces.http.routers import devices as devices_router

    api.include_router(devices_router.router)
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

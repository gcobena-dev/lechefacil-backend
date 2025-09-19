from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from src.config.settings import Settings, get_settings
from src.infrastructure.auth.jwt_service import JWTService
from src.infrastructure.auth.oidc_jwks import OIDCJWKSClient
from src.infrastructure.auth.password import PasswordHasher
from src.infrastructure.db.session import create_engine, create_session_factory
from src.interfaces.http.deps import get_app_settings
from src.interfaces.http.routers import animals
from src.interfaces.http.routers import auth as auth_router
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


def create_app(
    *,
    settings: Settings | None = None,
    jwks_client: OIDCJWKSClient | None = None,
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
        audience=settings.oidc_audience,
    )
    app.state.jwks_client = jwks_client or OIDCJWKSClient(
        str(settings.jwks_url),
        cache_ttl=settings.jwks_cache_ttl,
    )
    register_error_handlers(app)
    app.include_router(auth_router.router)
    app.include_router(animals.router)

    @app.get("/api/v1/health", tags=["health"])
    async def health(_: Settings = Depends(get_app_settings)) -> dict[str, str]:  # noqa: ANN001
        return {"status": "ok"}

    app.add_middleware(AuthMiddleware, settings=settings)
    return app


app = create_app()

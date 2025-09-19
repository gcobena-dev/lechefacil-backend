from __future__ import annotations

from functools import lru_cache

from pydantic import HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    oidc_issuer: HttpUrl
    jwks_url: HttpUrl
    oidc_audience: str
    tenant_header: str = "X-Tenant-ID"
    log_level: str = "INFO"
    environment: str = "dev"
    jwks_cache_ttl: int = 300
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires_minutes: int = 60
    jwt_issuer: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

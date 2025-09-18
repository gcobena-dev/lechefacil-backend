from __future__ import annotations

from functools import lru_cache

from pydantic import HttpUrl
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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

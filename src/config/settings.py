from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    tenant_header: str = "X-Tenant-ID"
    log_level: str = "INFO"
    environment: str = "dev"
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires_minutes: int = 60
    jwt_issuer: str | None = None
    jwt_audience: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def ensure_asyncpg_scheme(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://") and "+" not in value.split("://", 1)[0]:
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

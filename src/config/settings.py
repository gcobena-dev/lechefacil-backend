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
    jwt_refresh_token_expires_days: int = 30
    jwt_issuer: str | None = None
    jwt_leeway_seconds: int = 10
    # S3 storage (minimal)
    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_prefix: str = ""  # e.g. "dev/" or "prod/"
    s3_public_url_base: str | None = None
    s3_signed_url_expires: int = 600
    # S3 mobile deployments (separate bucket)
    s3_mobile_bucket: str | None = None
    s3_mobile_public_url_base: str | None = None
    jwt_audience: str | None = None
    # CORS
    cors_allow_origins: str = "*"
    # Email (disabled for now)
    email_provider: str = "logging"  # logging only
    email_from_name: str = "LecheFacil"
    email_from_address: str = "no-reply@lechefacil.local"
    email_admin_recipients: str = "gcobena.dev@gmail.com"
    email_default_locale: str = "es"
    # Auth cookies (for refresh token)
    cookie_samesite: str = "lax"  # options: 'lax', 'none', 'strict'
    cookie_secure: bool = False  # set True when served over HTTPS
    # OpenAI
    openai_api_key: SecretStr | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def ensure_asyncpg_scheme(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://") and "+" not in value.split("://", 1)[0]:
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @property
    def cors_allow_origins_list(self) -> list[str]:
        """Convert cors_allow_origins string to list"""
        if isinstance(self.cors_allow_origins, str):
            return [v.strip() for v in self.cors_allow_origins.split(",") if v.strip()]
        return self.cors_allow_origins

    @property
    def email_admin_recipients_list(self) -> list[str]:
        """Convert email_admin_recipients string to list"""
        if not self.email_admin_recipients:
            return []
        return [email.strip() for email in self.email_admin_recipients.split(",") if email.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

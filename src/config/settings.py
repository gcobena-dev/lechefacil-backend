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
    # S3 storage (minimal)
    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_prefix: str = ""  # e.g. "dev/" or "prod/"
    s3_public_url_base: str | None = None
    s3_signed_url_expires: int = 600
    jwt_audience: str | None = None
    # CORS
    cors_allow_origins: list[str] = ["*"]
    # Email
    email_provider: str = "logging"  # logging | smtp
    email_from_name: str = "LecheFacil"
    email_from_address: str = "no-reply@lechefacil.local"
    email_admin_recipients: list[str] = ["gcobena.dev@gmail.com"]
    email_default_locale: str = "es"
    email_brand_logo_url: str | None = None
    email_primary_color: str = "#16a34a"  # Tailwind green-600
    # SMTP provider
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True  # STARTTLS
    smtp_use_ssl: bool = False  # SMTPS (465)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def ensure_asyncpg_scheme(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+asyncpg://", 1)
        if value.startswith("postgresql://") and "+" not in value.split("://", 1)[0]:
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_list(cls, value):  # type: ignore[no-untyped-def]
        if isinstance(value, str):
            # Support comma-separated env values
            return [v.strip() for v in value.split(",") if v.strip()]
        return value

    @field_validator("email_admin_recipients", mode="before")
    @classmethod
    def parse_email_list(cls, value):  # type: ignore[no-untyped-def]
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

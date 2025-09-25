from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from uuid import UUID

from jose import jwt
from jose.exceptions import JWTError

from src.application.errors import AuthError


class JWTService:
    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str,
        access_token_expires_minutes: int,
        issuer: str | None = None,
        audience: str | None = None,
    ) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expires_minutes = access_token_expires_minutes
        self.issuer = issuer
        self.audience = audience

    def create_access_token(
        self,
        *,
        subject: UUID,
        extra_claims: Mapping[str, Any] | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        to_encode: dict[str, Any] = {
            "sub": str(subject),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=self.access_token_expires_minutes)).timestamp()),
            "typ": "access",
        }
        if self.issuer:
            to_encode["iss"] = self.issuer
        if self.audience:
            to_encode["aud"] = self.audience
        if extra_claims:
            to_encode.update(extra_claims)
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience,
            )
        except JWTError as exc:
            raise AuthError("Token validation failed") from exc

    def create_refresh_token(self, *, subject: UUID, expires_days: int = 30) -> str:
        now = datetime.now(timezone.utc)
        to_encode: dict[str, Any] = {
            "sub": str(subject),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=expires_days)).timestamp()),
            "typ": "refresh",
        }
        if self.issuer:
            to_encode["iss"] = self.issuer
        if self.audience:
            to_encode["aud"] = self.audience
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_refresh(self, token: str) -> dict[str, Any]:
        claims = self.decode(token)
        if claims.get("typ") != "refresh":
            raise AuthError("Invalid refresh token")
        return claims

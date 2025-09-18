from __future__ import annotations

import time
from typing import Any

import httpx
from jose import jwt
from jose.exceptions import JWTError

from src.application.errors import AuthError


class OIDCJWKSClient:
    def __init__(
        self,
        jwks_url: str,
        *,
        cache_ttl: int = 300,
        static_jwks: dict[str, Any] | None = None,
    ) -> None:
        self.jwks_url = jwks_url
        self.cache_ttl = cache_ttl
        self._jwks: dict[str, Any] | None = static_jwks
        self._last_fetch: float = 0.0

    async def _load_jwks(self) -> dict[str, Any]:
        if self._jwks and (time.time() - self._last_fetch) < self.cache_ttl:
            return self._jwks
        if self._jwks and self.cache_ttl <= 0:
            return self._jwks
        async with httpx.AsyncClient() as client:
            response = await client.get(self.jwks_url, timeout=10.0)
            response.raise_for_status()
            self._jwks = response.json()
            self._last_fetch = time.time()
            return self._jwks

    async def _get_key(self, kid: str) -> dict[str, Any]:
        jwks = await self._load_jwks()
        keys = jwks.get("keys", [])
        for key in keys:
            if key.get("kid") == kid:
                return key
        raise AuthError("Signing key not found for token")

    async def decode_token(
        self,
        token: str,
        *,
        issuer: str,
        audience: str,
    ) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
        except JWTError as exc:
            raise AuthError("Invalid token header") from exc
        kid = header.get("kid")
        if not kid:
            raise AuthError("Token missing key identifier")
        key = await self._get_key(kid)
        alg = key.get("alg") or header.get("alg")
        if not alg:
            raise AuthError("Token algorithm not provided")
        try:
            return jwt.decode(
                token,
                key,
                algorithms=[alg],
                issuer=issuer,
                audience=audience,
            )
        except JWTError as exc:
            raise AuthError("Token validation failed") from exc

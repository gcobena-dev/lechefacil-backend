from __future__ import annotations

import json
import logging
import time
from typing import Iterable

import httpx
from jose import jwt

logger = logging.getLogger(__name__)


class FCMv1Client:
    """Minimal Firebase Cloud Messaging HTTP v1 client using a Service Account JSON.

    It generates a short-lived OAuth2 access token via JWT assertion and sends messages
    to the v1 endpoint.
    """

    OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
    SCOPE = "https://www.googleapis.com/auth/firebase.messaging"

    def __init__(self, *, project_id: str, service_account_json: str) -> None:
        self.project_id = project_id
        self.sa = json.loads(service_account_json)
        self._cached_token: str | None = None
        self._token_exp: int = 0

    async def send_to_tokens(
        self,
        *,
        tokens: Iterable[str],
        title: str,
        body: str,
        data: dict | None = None,
    ) -> None:
        if not tokens:
            return
        access_token = await self._get_access_token()
        url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=10) as client:
            # Send as multicast by iterating (v1 API lacks registration_ids batch)
            for token in tokens:
                payload = {
                    "message": {
                        "token": token,
                        "notification": {"title": title, "body": body},
                        "data": data or {},
                    }
                }
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code >= 400:
                    logger.error("FCM v1 error %s: %s", resp.status_code, resp.text)
                else:
                    logger.debug("FCM v1 sent: %s", resp.text)

    async def _get_access_token(self) -> str:
        now = int(time.time())
        # Reuse cached token if valid for > 60s
        if self._cached_token and now < (self._token_exp - 60):
            return self._cached_token

        iat = now
        exp = now + 3600
        iss = self.sa["client_email"]
        aud = self.OAUTH_TOKEN_URL
        assertion = jwt.encode(
            {
                "iss": iss,
                "scope": self.SCOPE,
                "aud": aud,
                "iat": iat,
                "exp": exp,
            },
            self.sa["private_key"],
            algorithm="RS256",
        )

        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(self.OAUTH_TOKEN_URL, data=data)
            resp.raise_for_status()
            token = resp.json()["access_token"]
            self._cached_token = token
            self._token_exp = exp
            return token

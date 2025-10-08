from __future__ import annotations

import logging
from typing import Iterable

import httpx

logger = logging.getLogger(__name__)


class FCMClient:
    """Minimal FCM legacy HTTP sender (server key)."""

    def __init__(self, server_key: str) -> None:
        self.server_key = server_key
        self.endpoint = "https://fcm.googleapis.com/fcm/send"

    async def send_to_tokens(
        self,
        *,
        tokens: Iterable[str],
        title: str,
        body: str,
        data: dict | None = None,
    ) -> None:
        headers = {
            "Authorization": f"key={self.server_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "registration_ids": list(tokens),
            "notification": {"title": title, "body": body},
            "data": data or {},
            "priority": "high",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(self.endpoint, headers=headers, json=payload)
            if resp.status_code >= 400:
                logger.error("FCM error %s: %s", resp.status_code, resp.text)
            else:
                logger.debug("FCM sent: %s", resp.text)

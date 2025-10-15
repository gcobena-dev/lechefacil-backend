from __future__ import annotations

import logging
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from src.infrastructure.email.models import EmailMessage, EmailService

logger = logging.getLogger(__name__)


class SESEmailService(EmailService):
    def __init__(
        self,
        *,
        region: str | None = None,
        session_kwargs: dict[str, Any] | None = None,
    ) -> None:
        # Use standard AWS provider chain (env vars, shared config, IAM role, etc.)
        self.session = boto3.session.Session(**(session_kwargs or {}))
        # If region is not provided, let boto3 resolve from its configuration
        if region:
            self.client = self.session.client(
                "ses", region_name=region, config=Config(retries={"max_attempts": 3})
            )
        else:
            self.client = self.session.client("ses", config=Config(retries={"max_attempts": 3}))

    async def send(self, message: EmailMessage) -> None:
        # Prepare addresses
        to_addrs = list(message.to or [])
        bcc_addrs = list(message.bcc or [])
        source = message.from_email or "no-reply@example.com"
        if message.from_name:
            source = f"{message.from_name} <{source}>"
        body: dict[str, Any] = {}
        if message.text:
            body.setdefault("Text", {})["Data"] = message.text
            body["Text"]["Charset"] = "UTF-8"
        if message.html:
            body.setdefault("Html", {})["Data"] = message.html
            body["Html"]["Charset"] = "UTF-8"
        try:
            self.client.send_email(
                Source=source,
                Destination={"ToAddresses": to_addrs, "BccAddresses": bcc_addrs},
                Message={
                    "Subject": {"Data": message.subject, "Charset": "UTF-8"},
                    "Body": body,
                },
            )
        except (BotoCoreError, ClientError) as exc:  # pragma: no cover
            logger.error("SES send failed: %s", exc)
            raise

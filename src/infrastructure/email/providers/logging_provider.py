from __future__ import annotations

import logging

from src.infrastructure.email.models import EmailMessage, EmailService

logger = logging.getLogger(__name__)


class LoggingEmailService(EmailService):
    async def send(self, message: EmailMessage) -> None:  # pragma: no cover - side effect only
        logger.info(
            "Sending email (logging provider): subject=%s "
            "to=%s bcc=%s from=%s <%s> text_len=%s html_len=%s",
            message.subject,
            ",".join(message.to),
            ",".join(message.bcc or []),
            message.from_name or "",
            message.from_email or "",
            len(message.text or ""),
            len(message.html or ""),
        )

from __future__ import annotations

import logging
from typing import Any

import httpx

from src.infrastructure.email.models import EmailMessage, EmailService

logger = logging.getLogger(__name__)


class UniOneEmailService(EmailService):
    """UniOne email service provider for transactional emails."""

    def __init__(
        self,
        *,
        api_key: str,
        api_url: str = "https://us1.unione.io/en/transactional/api/v1/email/send.json",
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize UniOne email service.

        Args:
            api_key: UniOne API key for authentication
            api_url: UniOne API endpoint URL (default: US1 region)
            timeout: HTTP request timeout in seconds
        """
        self.api_key = api_key
        self.api_url = api_url
        self.timeout = timeout

    async def send(self, message: EmailMessage) -> None:
        """
        Send an email message using UniOne API.

        Args:
            message: EmailMessage instance with recipient, subject, and body

        Raises:
            Exception: If the API request fails
        """
        # Build recipients list with simple structure
        recipients = [{"email": email} for email in message.to]

        # Prepare source email and name
        from_email = message.from_email or "no-reply@example.com"
        from_name = message.from_name or "LecheFacil"

        # Build the body
        body: dict[str, Any] = {}
        if message.html:
            body["html"] = message.html
        if message.text:
            body["plaintext"] = message.text

        # Build the payload according to UniOne API spec
        payload = {
            "message": {
                "recipients": recipients,
                "from_email": from_email,
                "from_name": from_name,
                "subject": message.subject,
                "body": body,
                "track_links": 0,  # Disable link tracking
                "track_read": 0,  # Disable open tracking
            }
        }

        # Add BCC if present
        if message.bcc:
            for email in message.bcc:
                recipients.append({"email": email})

        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                )

                # Check response status
                if response.status_code != 200:
                    error_msg = f"UniOne API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

                # Parse response JSON
                result = response.json()

                # Check for API-level errors
                if result.get("status") != "success":
                    error_msg = f"UniOne send failed: {result}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

                logger.info(
                    "Email sent successfully via UniOne: subject=%s to=%s job_id=%s",
                    message.subject,
                    ",".join(message.to),
                    result.get("job_id", "unknown"),
                )

        except httpx.HTTPError as exc:
            logger.error("UniOne HTTP error: %s", exc)
            raise Exception(f"Failed to send email via UniOne: {exc}") from exc
        except Exception as exc:
            logger.error("UniOne send failed: %s", exc)
            raise

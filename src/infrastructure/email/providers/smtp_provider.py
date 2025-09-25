from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.infrastructure.email.models import EmailMessage, EmailService


def _build_mime(message: EmailMessage) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = message.subject
    if message.from_email:
        msg["From"] = f"{message.from_name or ''} <{message.from_email}>".strip()
    # "To" header is informational; envelope is set by SMTP sendmail
    msg["To"] = ", ".join(message.to)
    if message.text:
        msg.attach(MIMEText(message.text, "plain", "utf-8"))
    if message.html:
        msg.attach(MIMEText(message.html, "html", "utf-8"))
    return msg


class SMTPEmailService(EmailService):
    def __init__(
        self,
        *,
        host: str,
        port: int = 587,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        use_ssl: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl

    async def send(self, message: EmailMessage) -> None:
        mime = _build_mime(message)

        def _send_sync():
            if self.use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.host, self.port, context=context) as server:
                    if self.username and self.password:
                        server.login(self.username, self.password)
                    recipients = list(message.to) + list(message.bcc or [])
                    server.sendmail(message.from_email or "", recipients, mime.as_string())
            else:
                with smtplib.SMTP(self.host, self.port) as server:
                    server.ehlo()
                    if self.use_tls:
                        context = ssl.create_default_context()
                        server.starttls(context=context)
                        server.ehlo()
                    if self.username and self.password:
                        server.login(self.username, self.password)
                    recipients = list(message.to) + list(message.bcc or [])
                    server.sendmail(message.from_email or "", recipients, mime.as_string())

        await asyncio.to_thread(_send_sync)

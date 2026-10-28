from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(slots=True)
class EmailMessage:
    subject: str
    to: Sequence[str]
    text: str | None = None
    html: str | None = None
    from_email: str | None = None
    from_name: str | None = None
    bcc: Sequence[str] | None = None


class EmailService:
    async def send(self, message: EmailMessage) -> None:  # pragma: no cover - interface
        raise NotImplementedError

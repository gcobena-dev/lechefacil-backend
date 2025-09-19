from __future__ import annotations

from passlib.context import CryptContext


class PasswordHasher:
    def __init__(self, schemes: tuple[str, ...] = ("bcrypt",)) -> None:
        self._pwd_context = CryptContext(schemes=schemes, deprecated="auto")

    def hash(self, password: str) -> str:
        return self._pwd_context.hash(password)

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        return self._pwd_context.verify(plain_password, hashed_password)

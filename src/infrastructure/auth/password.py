from __future__ import annotations

import bcrypt

# bcrypt only uses the first 72 bytes. passlib truncated silently and bcrypt>=5
# raises instead, so truncate here to keep verifying hashes made before the switch.
_BCRYPT_MAX_BYTES = 72


def _encode(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


class PasswordHasher:
    def hash(self, password: str) -> str:
        return bcrypt.hashpw(_encode(password), bcrypt.gensalt()).decode("ascii")

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(_encode(plain_password), hashed_password.encode("ascii"))
        except ValueError:
            return False

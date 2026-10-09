"""Password hashing helpers with backward-compatible hash upgrades."""
from __future__ import annotations

from typing import Optional, Tuple

from passlib.context import CryptContext


# bcrypt_sha256 pre-hashes passwords before bcrypt, avoiding bcrypt's 72-byte
# input boundary. Plain bcrypt remains available solely to verify and upgrade
# hashes created by earlier versions of the app.
pwd_ctx = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)


def verify_and_update_password(password: str, hashed: str) -> Tuple[bool, Optional[str]]:
    """Return validity and, for legacy hashes, a replacement modern hash."""
    return pwd_ctx.verify_and_update(password, hashed)

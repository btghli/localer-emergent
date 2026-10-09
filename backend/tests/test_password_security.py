"""Unit coverage for password length safety and legacy-hash migration."""
import sys
from pathlib import Path

from passlib.context import CryptContext

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from security import hash_password, verify_and_update_password


def test_long_multibyte_password_round_trips_without_bcrypt_truncation():
    password = "密碼" * 64

    hashed = hash_password(password)
    valid, replacement = verify_and_update_password(password, hashed)

    assert hashed.startswith("$bcrypt-sha256$")
    assert valid is True
    assert replacement is None


def test_legacy_bcrypt_hash_verifies_and_is_upgraded():
    legacy = CryptContext(schemes=["bcrypt"], deprecated="auto")
    old_hash = legacy.hash("legacy-password")

    valid, replacement = verify_and_update_password("legacy-password", old_hash)

    assert valid is True
    assert replacement is not None
    assert replacement.startswith("$bcrypt-sha256$")
    assert verify_and_update_password("legacy-password", replacement)[0] is True


def test_wrong_password_never_generates_replacement_hash():
    hashed = hash_password("correct-password")

    valid, replacement = verify_and_update_password("wrong-password", hashed)

    assert valid is False
    assert replacement is None

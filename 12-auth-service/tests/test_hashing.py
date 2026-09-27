import pytest
from wardenauth.core.hashing import hash_password, hash_secret, verify_password


def test_password_hashing():
    password = "SuperSecurePassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_empty_password_hashing():
    hashed = hash_password("")
    assert verify_password("", hashed) is True
    assert verify_password("a", hashed) is False


def test_invalid_hash_verification():
    assert verify_password("test", "invalid_argon2_hash") is False


def test_secret_hashing():
    secret1 = "api-key-test-123"
    secret2 = "api-key-test-124"
    h1 = hash_secret(secret1)
    h2 = hash_secret(secret2)
    assert h1 != h2
    assert len(h1) == 64
    assert h1 == hash_secret(secret1)

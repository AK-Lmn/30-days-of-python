from datetime import timedelta
import pytest
from wardenauth.core.errors import InvalidTokenError, TokenExpiredError
from wardenauth.core.tokens import (
    create_access_token,
    create_refresh_token,
    decode_jwt,
    generate_api_key_pair,
    generate_secure_random,
)


def test_access_token_creation_and_decoding():
    user_id = "user-123"
    role = "admin"
    scopes = ["users:read", "users:write"]
    session_id = "sess-456"

    token = create_access_token(
        user_id=user_id,
        role=role,
        scopes=scopes,
        session_id=session_id,
    )
    payload = decode_jwt(token)

    assert payload["sub"] == user_id
    assert payload["role"] == role
    assert payload["scopes"] == scopes
    assert payload["sid"] == session_id
    assert payload["type"] == "access"


def test_refresh_token_creation_and_decoding():
    user_id = "user-123"
    session_id = "sess-456"

    token = create_refresh_token(
        user_id=user_id,
        session_id=session_id,
    )
    payload = decode_jwt(token)

    assert payload["sub"] == user_id
    assert payload["sid"] == session_id
    assert payload["type"] == "refresh"


def test_expired_token():
    token = create_access_token(
        user_id="user-123",
        role="user",
        scopes=["profile:read"],
        session_id="sess-123",
        expires_delta=timedelta(seconds=-10),
    )
    with pytest.raises(TokenExpiredError):
        decode_jwt(token)


def test_invalid_token_string():
    with pytest.raises(InvalidTokenError):
        decode_jwt("totally.invalid.token")


def test_api_key_generation():
    prefix, plain_key, key_hash = generate_api_key_pair()
    assert plain_key.startswith("wauth_live_")
    assert prefix == plain_key[:12]
    assert len(key_hash) == 64


def test_generate_secure_random():
    r1 = generate_secure_random(16)
    r2 = generate_secure_random(16)
    assert len(r1) > 10
    assert r1 != r2

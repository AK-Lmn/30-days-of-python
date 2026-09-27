import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
import jwt
from wardenauth.config import get_settings
from wardenauth.core.errors import InvalidTokenError, TokenExpiredError
from wardenauth.core.hashing import hash_secret


def generate_secure_random(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def create_access_token(
    user_id: str,
    role: str,
    scopes: list[str],
    session_id: str,
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire_at = now + expires_delta
    else:
        expire_at = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "scopes": scopes,
        "sid": session_id,
        "jti": str(uuid.uuid4()),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire_at.timestamp()),
        "iss": settings.app_name,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    user_id: str,
    session_id: str,
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire_at = now + expires_delta
    else:
        expire_at = now + timedelta(days=settings.refresh_token_expire_days)

    payload: dict[str, Any] = {
        "sub": user_id,
        "sid": session_id,
        "jti": str(uuid.uuid4()),
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire_at.timestamp()),
        "iss": settings.app_name,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_jwt(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "type"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except jwt.PyJWTError:
        raise InvalidTokenError()


def generate_api_key_pair(prefix: str = "wauth_live_") -> tuple[str, str, str]:
    random_part = secrets.token_hex(24)
    plain_key = f"{prefix}{random_part}"
    short_prefix = plain_key[:12]
    key_hash = hash_secret(plain_key)
    return short_prefix, plain_key, key_hash

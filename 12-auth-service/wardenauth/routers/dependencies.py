from collections.abc import Callable
from typing import Any
from fastapi import Depends, Header, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from wardenauth.core.errors import (
    AccountSuspendedError,
    InsufficientPermissionsError,
    InvalidApiKeyError,
    InvalidTokenError,
)
from wardenauth.core.permissions import has_required_scope, is_role_sufficient
from wardenauth.core.tokens import decode_jwt
from wardenauth.database import get_db_session
from wardenauth.models.entities import User
from wardenauth.services.api_key_service import ApiKeyService
from wardenauth.services.session_service import SessionService
from wardenauth.services.user_service import UserService

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def get_client_user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


async def get_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise InvalidTokenError("Missing or invalid Bearer authentication scheme")
    payload = decode_jwt(credentials.credentials)
    if payload.get("type") != "access":
        raise InvalidTokenError("Expected an access token")
    return payload


async def get_current_user(
    payload: dict[str, Any] = Depends(get_token_payload),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    user_id = payload.get("sub")
    session_id = payload.get("sid")
    if not user_id or not session_id:
        raise InvalidTokenError("Malformed token payload")

    session_service = SessionService(session)
    await session_service.validate_session(session_id)

    user_service = UserService(session)
    user = await user_service.get_user_by_id(user_id)
    if user.status == "suspended":
        raise AccountSuspendedError()
    return user


async def get_current_session_id(
    payload: dict[str, Any] = Depends(get_token_payload),
) -> str:
    session_id = payload.get("sid")
    if not session_id:
        raise InvalidTokenError("Missing session id in token")
    return session_id


async def get_current_user_or_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    api_key_header: str | None = Depends(api_key_header_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    if credentials:
        payload = decode_jwt(credentials.credentials)
        if payload.get("type") != "access":
            raise InvalidTokenError("Expected access token")
        user_id = payload.get("sub")
        session_id = payload.get("sid")
        if not user_id or not session_id:
            raise InvalidTokenError("Malformed token payload")
        session_service = SessionService(session)
        await session_service.validate_session(session_id)
        user_service = UserService(session)
        user = await user_service.get_user_by_id(user_id)
        if user.status == "suspended":
            raise AccountSuspendedError()
        return user

    if api_key_header:
        api_key_service = ApiKeyService(session)
        api_key = await api_key_service.validate_api_key(api_key_header)
        user_service = UserService(session)
        user = await user_service.get_user_by_id(api_key.user_id)
        if user.status == "suspended":
            raise AccountSuspendedError()
        return user

    raise InvalidTokenError("Authentication credentials missing")


def require_role(min_role: str) -> Callable[..., Any]:
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not is_role_sufficient(current_user.role, min_role):
            raise InsufficientPermissionsError(
                f"Role '{current_user.role}' is insufficient. Required: '{min_role}'"
            )
        return current_user

    return role_checker


def require_permission(scope: str) -> Callable[..., Any]:
    async def permission_checker(
        payload: dict[str, Any] = Depends(get_token_payload),
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_scopes = payload.get("scopes", [])
        if not has_required_scope(user_scopes, scope):
            raise InsufficientPermissionsError(f"Missing required permission: '{scope}'")
        return current_user

    return permission_checker

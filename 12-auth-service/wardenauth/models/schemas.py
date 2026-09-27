import re
from datetime import datetime
from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from wardenauth.core.errors import WeakPasswordError

T = TypeVar("T")


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise WeakPasswordError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise WeakPasswordError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise WeakPasswordError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise WeakPasswordError("Password must contain at least one digit")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_+=~\[\]]', password):
        raise WeakPasswordError("Password must contain at least one special character")
    return password


class UserRegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_\-]+$", value):
            raise ValueError("Username can only contain alphanumeric characters, hyphens, and underscores")
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserLoginRequest(BaseModel):
    username_or_email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    session_id: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    username: str
    full_name: str | None
    role: str
    status: str
    created_at: datetime
    updated_at: datetime


class UserProfileUpdateRequest(BaseModel):
    full_name: str | None = None


class UserRoleUpdateRequest(BaseModel):
    role: str


class UserStatusUpdateRequest(BaseModel):
    status: str


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    user_agent: str | None
    ip_address: str | None
    is_revoked: bool
    created_at: datetime
    last_activity_at: datetime
    expires_at: datetime


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: list[str] = Field(default_factory=lambda: ["profile:read"])


class ApiKeyCreatedResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    api_key: str
    scopes: list[str]
    created_at: datetime


class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    key_prefix: str
    scopes: str
    is_revoked: bool
    created_at: datetime
    last_used_at: datetime | None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None
    event_type: str
    ip_address: str | None
    user_agent: str | None
    details: str | None
    created_at: datetime


class SystemStatsResponse(BaseModel):
    total_users: int
    active_users: int
    suspended_users: int
    active_sessions: int
    total_api_keys: int
    recent_events_count: int


class EnvelopeResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int
    has_more: bool

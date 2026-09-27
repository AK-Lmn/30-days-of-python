from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from wardenauth.config import get_settings
from wardenauth.core.errors import (
    AccountLockedError,
    AccountSuspendedError,
    InvalidCredentialsError,
    InvalidTokenError,
    SessionRevokedError,
    TokenExpiredError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from wardenauth.core.hashing import hash_password, hash_secret, verify_password
from wardenauth.core.permissions import get_scopes_for_role
from wardenauth.core.rate_limiter import login_limiter
from wardenauth.core.tokens import (
    create_access_token,
    create_refresh_token,
    decode_jwt,
    generate_secure_random,
)
from wardenauth.models.entities import User
from wardenauth.models.schemas import (
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)
from wardenauth.repositories.user_repo import UserRepo
from wardenauth.services.audit_service import AuditService
from wardenauth.services.session_service import SessionService


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepo(session)
        self.session_service = SessionService(session)
        self.audit_service = AuditService(session)
        self.settings = get_settings()

    async def register(
        self,
        request: UserRegisterRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
        role: str = "user",
    ) -> User:
        existing_email = await self.user_repo.get_by_email(request.email)
        if existing_email:
            raise UserAlreadyExistsError("A user with this email address already exists")

        existing_username = await self.user_repo.get_by_username(request.username)
        if existing_username:
            raise UserAlreadyExistsError("A user with this username already exists")

        hashed_pw = hash_password(request.password)
        user = await self.user_repo.create(
            email=request.email,
            username=request.username,
            password_hash=hashed_pw,
            full_name=request.full_name,
            role=role,
            status="active",
        )

        await self.audit_service.log_event(
            event_type="user.registered",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": user.email, "username": user.username, "role": user.role},
        )
        return user

    async def login(
        self,
        request: UserLoginRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        identifier = request.username_or_email.lower().strip()

        is_locked, remaining = login_limiter.is_locked(identifier)
        if is_locked:
            raise AccountLockedError(
                f"Too many failed login attempts. Account temporarily locked for {remaining} seconds."
            )

        user = await self.user_repo.get_by_username_or_email(identifier)
        if not user:
            login_limiter.record_failure(identifier)
            await self.audit_service.log_event(
                event_type="auth.login.failed",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"identifier": identifier, "reason": "user_not_found"},
            )
            raise InvalidCredentialsError()

        now = datetime.now(timezone.utc)
        if user.locked_until:
            user_locked = user.locked_until
            if user_locked.tzinfo is None:
                user_locked = user_locked.replace(tzinfo=timezone.utc)
            if user_locked > now:
                raise AccountLockedError("Account is locked due to security policy")
            user.locked_until = None
            user.failed_login_attempts = 0
            await self.user_repo.update(user)

        if user.status == "suspended":
            raise AccountSuspendedError("Account has been suspended. Please contact support.")

        if not verify_password(request.password, user.password_hash):
            user.failed_login_attempts += 1
            count, locked = login_limiter.record_failure(identifier)
            if locked or user.failed_login_attempts >= self.settings.max_login_attempts:
                lockout_end = now + timedelta(minutes=self.settings.lockout_duration_minutes)
                user.locked_until = lockout_end
            await self.user_repo.update(user)

            await self.audit_service.log_event(
                event_type="auth.login.failed",
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"identifier": identifier, "reason": "invalid_password"},
            )
            raise InvalidCredentialsError()

        if user.failed_login_attempts > 0 or user.locked_until is not None:
            user.failed_login_attempts = 0
            user.locked_until = None
            await self.user_repo.update(user)
        login_limiter.reset(identifier)

        expires_delta = timedelta(days=self.settings.refresh_token_expire_days)
        refresh_expires_at = now + expires_delta

        temp_session = await self.session_service.create_session(
            user_id=user.id,
            refresh_token="temporary_placeholder",
            expires_at=refresh_expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        refresh_token = create_refresh_token(
            user_id=user.id,
            session_id=temp_session.id,
            expires_delta=expires_delta,
        )

        await self.session_service.rotate_refresh_token(
            user_session=temp_session,
            new_refresh_token=refresh_token,
            new_expires_at=refresh_expires_at,
        )

        scopes = get_scopes_for_role(user.role)
        access_token = create_access_token(
            user_id=user.id,
            role=user.role,
            scopes=scopes,
            session_id=temp_session.id,
        )

        await self.audit_service.log_event(
            event_type="auth.login.success",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"session_id": temp_session.id},
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.settings.access_token_expire_minutes * 60,
            session_id=temp_session.id,
        )

    async def refresh_tokens(
        self,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        payload = decode_jwt(refresh_token)
        if payload.get("type") != "refresh":
            raise InvalidTokenError("Expected a refresh token")

        user_id = payload.get("sub")
        session_id = payload.get("sid")
        if not user_id or not session_id:
            raise InvalidTokenError("Malformed refresh token claims")

        user_session = await self.session_service.validate_session(session_id)
        if user_session.user_id != user_id:
            raise InvalidTokenError("Session mismatch")

        expected_hash = hash_secret(refresh_token)
        if user_session.refresh_token_hash != expected_hash:
            await self.session_service.revoke_session(session_id, is_admin=True)
            await self.audit_service.log_event(
                event_type="auth.token.compromise_detected",
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"session_id": session_id, "reason": "reused_refresh_token"},
            )
            raise SessionRevokedError("Invalid or re-used refresh token. Session terminated.")

        user = await self.user_repo.get_by_id(user_id)
        if not user or user.status == "suspended":
            raise AccountSuspendedError("User is inactive or suspended")

        now = datetime.now(timezone.utc)
        refresh_delta = timedelta(days=self.settings.refresh_token_expire_days)
        new_refresh_expires_at = now + refresh_delta

        new_refresh_token = create_refresh_token(
            user_id=user.id,
            session_id=user_session.id,
            expires_delta=refresh_delta,
        )

        await self.session_service.rotate_refresh_token(
            user_session=user_session,
            new_refresh_token=new_refresh_token,
            new_expires_at=new_refresh_expires_at,
        )

        scopes = get_scopes_for_role(user.role)
        new_access_token = create_access_token(
            user_id=user.id,
            role=user.role,
            scopes=scopes,
            session_id=user_session.id,
        )

        await self.audit_service.log_event(
            event_type="auth.token.refreshed",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"session_id": user_session.id},
        )

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=self.settings.access_token_expire_minutes * 60,
            session_id=user_session.id,
        )

    async def logout(
        self,
        session_id: str,
        user_id: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        await self.session_service.revoke_session(
            session_id=session_id,
            requesting_user_id=user_id,
            is_admin=False,
        )
        await self.audit_service.log_event(
            event_type="auth.logout",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"session_id": session_id},
        )

    async def logout_all(
        self,
        user_id: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> int:
        revoked_count = await self.session_service.revoke_all_sessions(user_id)
        await self.audit_service.log_event(
            event_type="auth.logout_all",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"revoked_sessions_count": revoked_count},
        )
        return revoked_count

    async def change_password(
        self,
        user_id: str,
        request: PasswordChangeRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError()

        if not verify_password(request.current_password, user.password_hash):
            raise InvalidCredentialsError("Current password does not match")

        user.password_hash = hash_password(request.new_password)
        await self.user_repo.update(user)

        await self.session_service.revoke_all_sessions(user_id)

        await self.audit_service.log_event(
            event_type="auth.password.changed",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"action": "password_changed_all_sessions_revoked"},
        )

    async def request_password_reset(
        self,
        email: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> str:
        user = await self.user_repo.get_by_email(email)
        plain_token = generate_secure_random(40)

        if user:
            token_hash = hash_secret(plain_token)
            expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=self.settings.password_reset_expire_minutes
            )
            await self.user_repo.create_password_reset_token(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
            await self.audit_service.log_event(
                event_type="auth.password.reset_requested",
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"email": email},
            )
        return plain_token

    async def confirm_password_reset(
        self,
        request: PasswordResetConfirmRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        token_hash = hash_secret(request.token)
        reset_token = await self.user_repo.get_valid_reset_token(token_hash)
        if not reset_token:
            raise InvalidTokenError("Invalid or expired password reset token")

        user = await self.user_repo.get_by_id(reset_token.user_id)
        if not user:
            raise UserNotFoundError()

        user.password_hash = hash_password(request.new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.user_repo.update(user)

        await self.user_repo.mark_reset_token_used(reset_token)
        await self.session_service.revoke_all_sessions(user.id)

        await self.audit_service.log_event(
            event_type="auth.password.reset_completed",
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"action": "password_reset_success"},
        )

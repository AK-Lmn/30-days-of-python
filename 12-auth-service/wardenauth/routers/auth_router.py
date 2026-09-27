from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from wardenauth.database import get_db_session
from wardenauth.models.entities import User
from wardenauth.models.schemas import (
    EnvelopeResponse,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from wardenauth.routers.dependencies import (
    get_client_ip,
    get_client_user_agent,
    get_current_session_id,
    get_current_user,
)
from wardenauth.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=EnvelopeResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(
    request_data: UserRegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[UserResponse]:
    auth_service = AuthService(session)
    user = await auth_service.register(
        request=request_data,
        ip_address=get_client_ip(request),
        user_agent=get_client_user_agent(request),
    )
    return EnvelopeResponse(data=UserResponse.model_validate(user))


@router.post("/login", response_model=EnvelopeResponse[TokenResponse])
async def login(
    request_data: UserLoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[TokenResponse]:
    auth_service = AuthService(session)
    token_response = await auth_service.login(
        request=request_data,
        ip_address=get_client_ip(request),
        user_agent=get_client_user_agent(request),
    )
    return EnvelopeResponse(data=token_response)


@router.post("/refresh", response_model=EnvelopeResponse[TokenResponse])
async def refresh_tokens(
    request_data: TokenRefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[TokenResponse]:
    auth_service = AuthService(session)
    tokens = await auth_service.refresh_tokens(
        refresh_token=request_data.refresh_token,
        ip_address=get_client_ip(request),
        user_agent=get_client_user_agent(request),
    )
    return EnvelopeResponse(data=tokens)


@router.post("/logout", response_model=EnvelopeResponse[dict[str, str]])
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    session_id: str = Depends(get_current_session_id),
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[dict[str, str]]:
    auth_service = AuthService(session)
    await auth_service.logout(
        session_id=session_id,
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=get_client_user_agent(request),
    )
    return EnvelopeResponse(data={"message": "Successfully logged out"})


@router.post("/logout-all", response_model=EnvelopeResponse[dict[str, int]])
async def logout_all(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[dict[str, int]]:
    auth_service = AuthService(session)
    revoked_count = await auth_service.logout_all(
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=get_client_user_agent(request),
    )
    return EnvelopeResponse(data={"revoked_sessions": revoked_count})


@router.post("/change-password", response_model=EnvelopeResponse[dict[str, str]])
async def change_password(
    request_data: PasswordChangeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[dict[str, str]]:
    auth_service = AuthService(session)
    await auth_service.change_password(
        user_id=current_user.id,
        request=request_data,
        ip_address=get_client_ip(request),
        user_agent=get_client_user_agent(request),
    )
    return EnvelopeResponse(
        data={"message": "Password changed successfully. All active sessions have been terminated."}
    )


@router.post("/forgot-password", response_model=EnvelopeResponse[dict[str, str]])
async def forgot_password(
    request_data: PasswordResetRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[dict[str, str]]:
    auth_service = AuthService(session)
    reset_token = await auth_service.request_password_reset(
        email=request_data.email,
        ip_address=get_client_ip(request),
        user_agent=get_client_user_agent(request),
    )
    return EnvelopeResponse(
        data={
            "message": "If the email is registered, a password reset token has been issued",
            "reset_token": reset_token,
        }
    )


@router.post("/reset-password", response_model=EnvelopeResponse[dict[str, str]])
async def reset_password(
    request_data: PasswordResetConfirmRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[dict[str, str]]:
    auth_service = AuthService(session)
    await auth_service.confirm_password_reset(
        request=request_data,
        ip_address=get_client_ip(request),
        user_agent=get_client_user_agent(request),
    )
    return EnvelopeResponse(
        data={"message": "Password reset successful. You can now login with your new password."}
    )


@router.get("/me", response_model=EnvelopeResponse[UserResponse])
async def get_me(
    current_user: User = Depends(get_current_user),
) -> EnvelopeResponse[UserResponse]:
    return EnvelopeResponse(data=UserResponse.model_validate(current_user))

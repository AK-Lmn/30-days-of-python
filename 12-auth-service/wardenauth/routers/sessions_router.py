from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from wardenauth.database import get_db_session
from wardenauth.models.entities import User
from wardenauth.models.schemas import EnvelopeResponse, SessionResponse
from wardenauth.routers.dependencies import (
    get_client_ip,
    get_client_user_agent,
    get_current_user,
)
from wardenauth.services.audit_service import AuditService
from wardenauth.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("", response_model=EnvelopeResponse[list[SessionResponse]])
async def list_my_sessions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[list[SessionResponse]]:
    session_service = SessionService(session)
    sessions = await session_service.list_user_sessions(current_user.id)
    return EnvelopeResponse(
        data=[SessionResponse.model_validate(s) for s in sessions]
    )


@router.delete("/{session_id}", response_model=EnvelopeResponse[dict[str, str]])
async def revoke_session(
    session_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[dict[str, str]]:
    session_service = SessionService(session)
    audit_service = AuditService(session)
    await session_service.revoke_session(
        session_id=session_id,
        requesting_user_id=current_user.id,
        is_admin=current_user.role == "admin",
    )
    await audit_service.log_event(
        event_type="session.revoked",
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=get_client_user_agent(request),
        details={"session_id": session_id},
    )
    return EnvelopeResponse(data={"message": f"Session '{session_id}' has been revoked"})

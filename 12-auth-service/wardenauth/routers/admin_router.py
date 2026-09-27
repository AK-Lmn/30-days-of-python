from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from wardenauth.core.permissions import Role
from wardenauth.database import get_db_session
from wardenauth.models.entities import User
from wardenauth.models.schemas import (
    AuditLogResponse,
    EnvelopeResponse,
    PaginatedResponse,
    SessionResponse,
    SystemStatsResponse,
    UserResponse,
    UserRoleUpdateRequest,
    UserStatusUpdateRequest,
)
from wardenauth.routers.dependencies import (
    get_client_ip,
    get_client_user_agent,
    require_role,
)
from wardenauth.services.api_key_service import ApiKeyService
from wardenauth.services.audit_service import AuditService
from wardenauth.services.session_service import SessionService
from wardenauth.services.user_service import UserService

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=PaginatedResponse[UserResponse])
async def list_users(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    admin_user: User = Depends(require_role(Role.MANAGER)),
    session: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[UserResponse]:
    user_service = UserService(session)
    users, total = await user_service.list_users(offset=offset, limit=limit, search=search)
    return PaginatedResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        offset=offset,
        limit=limit,
        has_more=(offset + len(users)) < total,
    )


@router.get("/users/{user_id}", response_model=EnvelopeResponse[UserResponse])
async def get_user_details(
    user_id: str,
    admin_user: User = Depends(require_role(Role.MANAGER)),
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[UserResponse]:
    user_service = UserService(session)
    user = await user_service.get_user_by_id(user_id)
    return EnvelopeResponse(data=UserResponse.model_validate(user))


@router.patch("/users/{user_id}/role", response_model=EnvelopeResponse[UserResponse])
async def update_user_role(
    user_id: str,
    request_data: UserRoleUpdateRequest,
    request: Request,
    admin_user: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[UserResponse]:
    user_service = UserService(session)
    audit_service = AuditService(session)
    updated_user = await user_service.update_role(user_id, request_data.role)
    await audit_service.log_event(
        event_type="admin.user.role_updated",
        user_id=admin_user.id,
        ip_address=get_client_ip(request),
        user_agent=get_client_user_agent(request),
        details={"target_user_id": user_id, "new_role": request_data.role},
    )
    return EnvelopeResponse(data=UserResponse.model_validate(updated_user))


@router.patch("/users/{user_id}/status", response_model=EnvelopeResponse[UserResponse])
async def update_user_status(
    user_id: str,
    request_data: UserStatusUpdateRequest,
    request: Request,
    admin_user: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[UserResponse]:
    user_service = UserService(session)
    audit_service = AuditService(session)
    updated_user = await user_service.update_status(user_id, request_data.status)
    if request_data.status == "suspended":
        session_service = SessionService(session)
        await session_service.revoke_all_sessions(user_id)
    await audit_service.log_event(
        event_type="admin.user.status_updated",
        user_id=admin_user.id,
        ip_address=get_client_ip(request),
        user_agent=get_client_user_agent(request),
        details={"target_user_id": user_id, "new_status": request_data.status},
    )
    return EnvelopeResponse(data=UserResponse.model_validate(updated_user))


@router.delete("/users/{user_id}", response_model=EnvelopeResponse[dict[str, str]])
async def delete_user(
    user_id: str,
    request: Request,
    admin_user: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[dict[str, str]]:
    user_service = UserService(session)
    audit_service = AuditService(session)
    await user_service.delete_user(user_id)
    await audit_service.log_event(
        event_type="admin.user.deleted",
        user_id=admin_user.id,
        ip_address=get_client_ip(request),
        user_agent=get_client_user_agent(request),
        details={"deleted_user_id": user_id},
    )
    return EnvelopeResponse(data={"message": f"User '{user_id}' deleted successfully"})


@router.get("/sessions", response_model=PaginatedResponse[SessionResponse])
async def list_all_active_sessions(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin_user: User = Depends(require_role(Role.MANAGER)),
    session: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[SessionResponse]:
    session_service = SessionService(session)
    sessions, total = await session_service.list_active_sessions(offset=offset, limit=limit)
    return PaginatedResponse(
        items=[SessionResponse.model_validate(s) for s in sessions],
        total=total,
        offset=offset,
        limit=limit,
        has_more=(offset + len(sessions)) < total,
    )


@router.delete("/sessions/{session_id}", response_model=EnvelopeResponse[dict[str, str]])
async def admin_revoke_session(
    session_id: str,
    request: Request,
    admin_user: User = Depends(require_role(Role.ADMIN)),
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[dict[str, str]]:
    session_service = SessionService(session)
    audit_service = AuditService(session)
    await session_service.revoke_session(session_id=session_id, is_admin=True)
    await audit_service.log_event(
        event_type="admin.session.revoked",
        user_id=admin_user.id,
        ip_address=get_client_ip(request),
        user_agent=get_client_user_agent(request),
        details={"session_id": session_id},
    )
    return EnvelopeResponse(data={"message": f"Session '{session_id}' revoked by admin"})


@router.get("/audit-logs", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_id: str | None = Query(None),
    event_type: str | None = Query(None),
    admin_user: User = Depends(require_role(Role.MANAGER)),
    session: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[AuditLogResponse]:
    audit_service = AuditService(session)
    logs, total = await audit_service.list_logs(
        offset=offset,
        limit=limit,
        user_id=user_id,
        event_type=event_type,
    )
    return PaginatedResponse(
        items=[AuditLogResponse.model_validate(l) for l in logs],
        total=total,
        offset=offset,
        limit=limit,
        has_more=(offset + len(logs)) < total,
    )


@router.get("/stats", response_model=EnvelopeResponse[SystemStatsResponse])
async def get_system_stats(
    admin_user: User = Depends(require_role(Role.MANAGER)),
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[SystemStatsResponse]:
    user_service = UserService(session)
    session_service = SessionService(session)
    key_service = ApiKeyService(session)
    audit_service = AuditService(session)

    user_stats = await user_service.get_user_stats()
    active_sessions = await session_service.count_active()
    active_keys = await key_service.count_active()
    recent_events = await audit_service.count_recent(60)

    stats = SystemStatsResponse(
        total_users=user_stats["total_users"],
        active_users=user_stats["active_users"],
        suspended_users=user_stats["suspended_users"],
        active_sessions=active_sessions,
        total_api_keys=active_keys,
        recent_events_count=recent_events,
    )
    return EnvelopeResponse(data=stats)

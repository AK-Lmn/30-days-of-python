from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from wardenauth.database import get_db_session
from wardenauth.models.entities import User
from wardenauth.models.schemas import (
    ApiKeyCreatedResponse,
    ApiKeyCreateRequest,
    ApiKeyResponse,
    EnvelopeResponse,
)
from wardenauth.routers.dependencies import (
    get_client_ip,
    get_client_user_agent,
    get_current_user,
)
from wardenauth.services.api_key_service import ApiKeyService
from wardenauth.services.audit_service import AuditService

router = APIRouter(prefix="/keys", tags=["API Keys"])


@router.post("", response_model=EnvelopeResponse[ApiKeyCreatedResponse], status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request_data: ApiKeyCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[ApiKeyCreatedResponse]:
    api_key_service = ApiKeyService(session)
    audit_service = AuditService(session)
    api_key, plain_key = await api_key_service.create_api_key(
        user_id=current_user.id,
        name=request_data.name,
        scopes=request_data.scopes,
    )
    await audit_service.log_event(
        event_type="api_key.created",
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=get_client_user_agent(request),
        details={"key_id": api_key.id, "name": api_key.name},
    )
    return EnvelopeResponse(
        data=ApiKeyCreatedResponse(
            id=api_key.id,
            name=api_key.name,
            key_prefix=api_key.key_prefix,
            api_key=plain_key,
            scopes=api_key.scopes.split(","),
            created_at=api_key.created_at,
        )
    )


@router.get("", response_model=EnvelopeResponse[list[ApiKeyResponse]])
async def list_my_keys(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[list[ApiKeyResponse]]:
    api_key_service = ApiKeyService(session)
    keys = await api_key_service.list_keys_for_user(current_user.id)
    return EnvelopeResponse(
        data=[ApiKeyResponse.model_validate(k) for k in keys]
    )


@router.delete("/{key_id}", response_model=EnvelopeResponse[dict[str, str]])
async def revoke_api_key(
    key_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> EnvelopeResponse[dict[str, str]]:
    api_key_service = ApiKeyService(session)
    audit_service = AuditService(session)
    await api_key_service.revoke_key(
        key_id=key_id,
        requesting_user_id=current_user.id,
        is_admin=current_user.role == "admin",
    )
    await audit_service.log_event(
        event_type="api_key.revoked",
        user_id=current_user.id,
        ip_address=get_client_ip(request),
        user_agent=get_client_user_agent(request),
        details={"key_id": key_id},
    )
    return EnvelopeResponse(data={"message": f"API key '{key_id}' has been revoked"})

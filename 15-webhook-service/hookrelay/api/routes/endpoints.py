from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from hookrelay.api.deps import get_db
from hookrelay.schemas.endpoint import EndpointCreate, EndpointRead, EndpointUpdate
from hookrelay.services.endpoint_service import EndpointService

router = APIRouter(prefix="/api/v1/endpoints", tags=["Endpoints"])


@router.post("", response_model=EndpointRead, status_code=status.HTTP_201_CREATED)
async def create_endpoint(
    data: EndpointCreate,
    db: AsyncSession = Depends(get_db),
) -> EndpointRead:
    existing = await EndpointService.get_by_slug(db, data.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Endpoint slug '{data.slug}' already exists",
        )
    endpoint = await EndpointService.create(db, data)
    return EndpointRead.model_validate(endpoint)


@router.get("", response_model=list[EndpointRead])
async def list_endpoints(
    active_only: bool = False,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[EndpointRead]:
    endpoints = await EndpointService.list_all(
        db, active_only=active_only, limit=limit, offset=offset
    )
    return [EndpointRead.model_validate(ep) for ep in endpoints]


@router.get("/{endpoint_id}", response_model=EndpointRead)
async def get_endpoint(
    endpoint_id: str,
    db: AsyncSession = Depends(get_db),
) -> EndpointRead:
    endpoint = await EndpointService.get_by_id(db, endpoint_id)
    if not endpoint:
        endpoint = await EndpointService.get_by_slug(db, endpoint_id)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint '{endpoint_id}' not found",
        )
    return EndpointRead.model_validate(endpoint)


@router.patch("/{endpoint_id}", response_model=EndpointRead)
async def update_endpoint(
    endpoint_id: str,
    data: EndpointUpdate,
    db: AsyncSession = Depends(get_db),
) -> EndpointRead:
    endpoint = await EndpointService.get_by_id(db, endpoint_id)
    if not endpoint:
        endpoint = await EndpointService.get_by_slug(db, endpoint_id)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint '{endpoint_id}' not found",
        )
    updated = await EndpointService.update(db, endpoint, data)
    return EndpointRead.model_validate(updated)


@router.delete("/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_endpoint(
    endpoint_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    endpoint = await EndpointService.get_by_id(db, endpoint_id)
    if not endpoint:
        endpoint = await EndpointService.get_by_slug(db, endpoint_id)
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Endpoint '{endpoint_id}' not found",
        )
    await EndpointService.delete(db, endpoint)

from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from hookrelay.models.endpoint import Endpoint
from hookrelay.schemas.endpoint import EndpointCreate, EndpointUpdate


class EndpointService:
    @staticmethod
    async def create(db: AsyncSession, data: EndpointCreate) -> Endpoint:
        endpoint = Endpoint(
            slug=data.slug,
            name=data.name,
            description=data.description,
            secret=data.secret,
            verification_strategy=data.verification_strategy,
            is_active=data.is_active,
        )
        db.add(endpoint)
        await db.flush()
        await db.refresh(endpoint)
        return endpoint

    @staticmethod
    async def get_by_id(db: AsyncSession, endpoint_id: str) -> Endpoint | None:
        result = await db.execute(select(Endpoint).where(Endpoint.id == endpoint_id))
        return result.scalars().first()

    @staticmethod
    async def get_by_slug(db: AsyncSession, slug: str) -> Endpoint | None:
        result = await db.execute(select(Endpoint).where(Endpoint.slug == slug))
        return result.scalars().first()

    @staticmethod
    async def list_all(
        db: AsyncSession,
        active_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Endpoint]:
        stmt = select(Endpoint)
        if active_only:
            stmt = stmt.where(Endpoint.is_active.is_(True))
        stmt = stmt.order_by(Endpoint.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update(
        db: AsyncSession,
        endpoint: Endpoint,
        data: EndpointUpdate,
    ) -> Endpoint:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(endpoint, field, value)
        await db.flush()
        await db.refresh(endpoint)
        return endpoint

    @staticmethod
    async def delete(db: AsyncSession, endpoint: Endpoint) -> None:
        await db.delete(endpoint)
        await db.flush()

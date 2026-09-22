from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from nexuspg.core.config import settings
from nexuspg.dependencies import get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check(session: AsyncSession = Depends(get_db)):
    try:
        await session.execute(text("SELECT 1"))
        db_status = "connected"
        status_code = status.HTTP_200_OK
    except Exception as exc:
        db_status = f"unhealthy: {exc}"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if status_code == 200 else "degraded",
            "app_name": settings.app_name,
            "version": settings.app_version,
            "database": db_status,
        },
    )

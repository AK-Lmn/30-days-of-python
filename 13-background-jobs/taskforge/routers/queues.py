from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from taskforge.database import get_db
from taskforge.models.schemas import QueueStatsResponse
from taskforge.repositories.job_repo import JobRepository

router = APIRouter(prefix="/queues", tags=["Queues"])


@router.get("", response_model=QueueStatsResponse)
async def get_queue_statistics(
    session: AsyncSession = Depends(get_db),
) -> QueueStatsResponse:
    repo = JobRepository(session)
    queues = await repo.get_queue_stats()
    total_jobs = sum(q.total for q in queues)
    return QueueStatsResponse(queues=queues, total_jobs=total_jobs)

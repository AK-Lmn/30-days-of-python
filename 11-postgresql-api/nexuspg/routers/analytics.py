from fastapi import APIRouter, Depends
from nexuspg.core.errors import EntityNotFoundError
from nexuspg.dependencies import get_analytics_repo, get_project_repo
from nexuspg.repositories.analytics_repo import AnalyticsRepository
from nexuspg.repositories.project_repo import ProjectRepository
from nexuspg.schemas.analytics import ProjectAnalyticsResponse

router = APIRouter(prefix="/projects/{project_key}/analytics", tags=["Analytics"])


@router.get("", response_model=ProjectAnalyticsResponse)
async def get_project_analytics(
    project_key: str,
    project_repo: ProjectRepository = Depends(get_project_repo),
    analytics_repo: AnalyticsRepository = Depends(get_analytics_repo),
):
    project = await project_repo.get_by_key(project_key)
    if not project:
        raise EntityNotFoundError("Project", project_key)

    return await analytics_repo.get_project_analytics(project.id)

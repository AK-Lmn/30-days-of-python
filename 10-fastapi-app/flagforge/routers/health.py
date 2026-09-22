import time
from fastapi import APIRouter, Depends, Request
from flagforge.config import settings
from flagforge.dependencies import get_flag_repo, get_metrics_tracker
from flagforge.models.metrics import HealthResponse, MetricsResponse
from flagforge.repositories.memory import InMemoryFlagRepository, MetricsTracker

router = APIRouter(tags=["System"])


@router.get("/")
async def root():
    return {
        "service": settings.api_title,
        "version": settings.api_version,
        "docs_url": "/docs",
        "openapi_url": "/openapi.json",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "flags": "/api/v1/flags",
            "evaluate": "/api/v1/evaluate",
            "evaluate_all": "/api/v1/evaluate-all",
            "audit_logs": "/api/v1/audit-logs",
        },
    }


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    start_time = getattr(request.app.state, "start_time", time.time())
    uptime = time.time() - start_time
    return HealthResponse(
        status="ok",
        version=settings.api_version,
        environment=settings.environment,
        uptime_seconds=round(uptime, 2),
    )


@router.get("/metrics", response_model=MetricsResponse)
async def system_metrics(
    request: Request,
    flag_repo: InMemoryFlagRepository = Depends(get_flag_repo),
    metrics_tracker: MetricsTracker = Depends(get_metrics_tracker),
):
    start_time = getattr(request.app.state, "start_time", time.time())
    uptime = time.time() - start_time
    total, enabled, disabled = await flag_repo.count_summary()
    total_evals, flag_evals = await metrics_tracker.get_metrics()

    return MetricsResponse(
        total_flags=total,
        enabled_flags=enabled,
        disabled_flags=disabled,
        total_evaluations=total_evals,
        evaluations_by_flag=flag_evals,
        uptime_seconds=round(uptime, 2),
    )

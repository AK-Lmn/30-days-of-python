from autoflow.routers.actions import router as actions_router
from autoflow.routers.events import router as events_router
from autoflow.routers.health import router as health_router
from autoflow.routers.runs import router as runs_router
from autoflow.routers.workflows import router as workflows_router

__all__ = [
    "actions_router",
    "events_router",
    "health_router",
    "runs_router",
    "workflows_router",
]

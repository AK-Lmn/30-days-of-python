from starlette.requests import Request
from flagforge.repositories.memory import InMemoryFlagRepository, InMemoryAuditRepository, MetricsTracker


def get_flag_repo(request: Request) -> InMemoryFlagRepository:
    return request.app.state.flag_repo


def get_audit_repo(request: Request) -> InMemoryAuditRepository:
    return request.app.state.audit_repo


def get_metrics_tracker(request: Request) -> MetricsTracker:
    return request.app.state.metrics_tracker

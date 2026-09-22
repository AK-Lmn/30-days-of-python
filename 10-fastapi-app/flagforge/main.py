import time
from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from flagforge.config import settings
from flagforge.core.errors import FlagForgeError, FlagNotFoundError, FlagAlreadyExistsError, InvalidRuleError
from flagforge.core.middleware import RequestTrackingMiddleware
from flagforge.models.common import ErrorResponse, ErrorDetail
from flagforge.repositories.memory import InMemoryFlagRepository, InMemoryAuditRepository, MetricsTracker
from flagforge.routers import health, flags, evaluations, audit


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.start_time = time.time()
    storage_path = settings.get_storage_path() if settings.storage_file else None
    if not hasattr(app.state, "flag_repo") or app.state.flag_repo is None:
        app.state.flag_repo = InMemoryFlagRepository(storage_path)
    if not hasattr(app.state, "audit_repo") or app.state.audit_repo is None:
        app.state.audit_repo = InMemoryAuditRepository()
    if not hasattr(app.state, "metrics_tracker") or app.state.metrics_tracker is None:
        app.state.metrics_tracker = MetricsTracker()
    yield


def create_app(persistence_path: Optional[Path] = None) -> FastAPI:
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description=settings.api_description,
        lifespan=lifespan,
    )

    if persistence_path is not None:
        app.state.flag_repo = InMemoryFlagRepository(persistence_path)
        app.state.audit_repo = InMemoryAuditRepository()
        app.state.metrics_tracker = MetricsTracker()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestTrackingMiddleware)

    @app.exception_handler(FlagNotFoundError)
    async def flag_not_found_handler(request: Request, exc: FlagNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(
                error=ErrorDetail(code=exc.code, message=exc.message, details=exc.details)
            ).model_dump(mode="json"),
        )

    @app.exception_handler(FlagAlreadyExistsError)
    async def flag_already_exists_handler(request: Request, exc: FlagAlreadyExistsError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=ErrorResponse(
                error=ErrorDetail(code=exc.code, message=exc.message, details=exc.details)
            ).model_dump(mode="json"),
        )

    @app.exception_handler(InvalidRuleError)
    async def invalid_rule_handler(request: Request, exc: InvalidRuleError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error=ErrorDetail(code=exc.code, message=exc.message, details=exc.details)
            ).model_dump(mode="json"),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        code = "HTTP_ERROR"
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            code = "RESOURCE_NOT_FOUND"
        elif exc.status_code == status.HTTP_409_CONFLICT:
            code = "RESOURCE_CONFLICT"
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=code,
                    message=str(exc.detail),
                    details={"status_code": exc.status_code},
                )
            ).model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="VALIDATION_ERROR",
                    message="Request validation failed",
                    details={"errors": exc.errors()},
                )
            ).model_dump(mode="json"),
        )

    app.include_router(health.router)
    app.include_router(flags.router)
    app.include_router(evaluations.router)
    app.include_router(audit.router)

    return app


app = create_app()

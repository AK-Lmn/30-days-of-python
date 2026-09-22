from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from nexuspg.core.config import settings
from nexuspg.core.errors import AppError
from nexuspg.core.middleware import RequestTrackingMiddleware
from nexuspg.db.session import init_db
from nexuspg.routers.analytics import router as analytics_router
from nexuspg.routers.audit import router as audit_router
from nexuspg.routers.evaluation import router as evaluation_router
from nexuspg.routers.flags import router as flags_router
from nexuspg.routers.health import router as health_router
from nexuspg.routers.projects import router as projects_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    if "sqlite" in settings.database_url:
        await init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(RequestTrackingMiddleware)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": exc.errors(),
                }
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "details": str(exc) if settings.debug else None,
                }
            },
        )

    app.include_router(health_router, prefix=settings.api_v1_prefix)
    app.include_router(projects_router, prefix=settings.api_v1_prefix)
    app.include_router(flags_router, prefix=settings.api_v1_prefix)
    app.include_router(evaluation_router, prefix=settings.api_v1_prefix)
    app.include_router(analytics_router, prefix=settings.api_v1_prefix)
    app.include_router(audit_router, prefix=settings.api_v1_prefix)

    @app.get("/")
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": f"{settings.api_v1_prefix}/health",
        }

    return app


app = create_app()

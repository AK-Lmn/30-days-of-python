import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
        return response

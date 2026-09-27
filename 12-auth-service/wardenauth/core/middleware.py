import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))

        response = await call_next(request)

        process_time = (time.perf_counter() - start_time) * 1000
        response.headers["x-request-id"] = request_id
        response.headers["x-process-time-ms"] = f"{process_time:.2f}"
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["x-xss-protection"] = "1; mode=block"

        return response

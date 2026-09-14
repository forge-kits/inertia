from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .config import _config


class InertiaMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Inertia requires 303 after non-GET so the browser re-issues as GET
        if (
            request.headers.get("X-Inertia")
            and request.method in ("POST", "PUT", "PATCH", "DELETE")
            and response.status_code == 302
        ):
            response.status_code = 303

        # Asset version mismatch → force hard reload on client
        if (
            request.method == "GET"
            and request.headers.get("X-Inertia")
            and _config["version"]
            and request.headers.get("X-Inertia-Version", "") != _config["version"]
        ):
            return Response(
                status_code=409,
                headers={"X-Inertia-Location": str(request.url)},
            )

        return response

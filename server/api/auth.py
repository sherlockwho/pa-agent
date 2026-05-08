from __future__ import annotations

from fastapi import Request
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.responses import Response


class TokenAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        token = request.app.state.settings.server.auth_token
        if not token or request.url.path in {"/health", "/docs", "/openapi.json"}:
            return await call_next(request)
        if request.url.path.startswith("/redoc"):
            return await call_next(request)

        scheme, credentials = get_authorization_scheme_param(request.headers.get("Authorization"))
        if scheme.lower() != "bearer" or credentials != token:
            return JSONResponse({"detail": "Invalid or missing bearer token"}, status_code=401)
        return await call_next(request)

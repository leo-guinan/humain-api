"""Maintained FastAPI adapter for the transport-neutral resolver core."""
from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .models import ValidationError
from .resolver import Resolver


class RequestBoundaryMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_bytes: int):
        super().__init__(app)
        if max_body_bytes <= 0:
            raise ValueError("max_body_bytes must be positive")
        self.max_body_bytes = max_body_bytes

    async def dispatch(self, request: Request, call_next):
        supplied = request.headers.get("X-Request-ID", "")
        request_id = supplied[:128] if supplied else "http:" + uuid.uuid4().hex
        request.state.request_id = request_id
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                too_large = int(content_length) > self.max_body_bytes
            except ValueError:
                too_large = True
            if too_large:
                response = JSONResponse({"error": "request_too_large", "request_id": request_id}, status_code=413)
                response.headers["X-Request-ID"] = request_id
                return response
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def _error(request: Request, status: int, code: str, detail: str | None = None) -> JSONResponse:
    payload: dict[str, Any] = {"error": code, "request_id": request.state.request_id}
    if detail:
        payload["detail"] = detail[:200]
    response = JSONResponse(payload, status_code=status)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


def create_app(resolver: Resolver, projections: dict[str, dict[str, Any]], *, max_body_bytes: int = 1_048_576) -> FastAPI:
    app = FastAPI(title="HumAIn Resolver", version="0.1")
    app.add_middleware(RequestBoundaryMiddleware, max_body_bytes=max_body_bytes)

    @app.exception_handler(ValidationError)
    async def validation_error(request: Request, exc: ValidationError):
        return _error(request, 400, "invalid_request", str(exc))

    @app.exception_handler(json.JSONDecodeError)
    async def json_error(request: Request, exc: json.JSONDecodeError):
        return _error(request, 400, "invalid_request", "valid JSON object required")

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        return _error(request, 500, "internal_error")

    @app.get("/healthz")
    async def healthz(request: Request):
        return {"ok": True, "service": "humain-resolver", "protocol": "0.1"}

    @app.get("/readyz")
    async def readyz(request: Request):
        ready = resolver.mode != "production" or (resolver.verify_signature is not None and resolver.response_signer is not None)
        payload = {"ok": ready, "service": "humain-resolver", "mode": resolver.mode}
        response = JSONResponse(payload, status_code=200 if ready else 503)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.post("/v1/resolve")
    async def resolve(request: Request):
        try:
            raw = await request.body()
            if len(raw) > max_body_bytes:
                return _error(request, 413, "request_too_large")
            value = json.loads(raw)
            if not isinstance(value, dict):
                return _error(request, 422, "invalid_request", "JSON object required")
            result = resolver.resolve(value, projections.get(value.get("pointer", ""), {}))
            return result
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return _error(request, 422, "invalid_request", "valid JSON object required")

    @app.exception_handler(404)
    async def not_found(request: Request, exc):
        return _error(request, 404, "not_found")

    return app

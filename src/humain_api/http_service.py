"""Bounded HTTP transport for the resolver reference and pilot boundary."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
import uuid

from .models import ValidationError
from .resolver import Resolver


class ResolverHandler(BaseHTTPRequestHandler):
    resolver: Resolver | None = None
    projections: dict[str, dict[str, Any]] = {}
    max_body_bytes = 1_048_576

    def _request_id(self) -> str:
        supplied = self.headers.get("X-Request-ID", "")
        return supplied[:128] if supplied else "http:" + uuid.uuid4().hex

    def _json(self, status: int, payload: dict[str, Any], request_id: str | None = None) -> None:
        request_id = request_id or self._request_id()
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Request-ID", request_id)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        request_id = self._request_id()
        if self.path == "/healthz":
            self._json(200, {"ok": True, "service": "humain-resolver", "protocol": "0.1"}, request_id)
        elif self.path == "/readyz":
            resolver = self.resolver
            ready = resolver is not None and (resolver.mode != "production" or (resolver.verify_signature is not None and resolver.response_signer is not None))
            self._json(200 if ready else 503, {"ok": ready, "service": "humain-resolver", "mode": resolver.mode if resolver else None}, request_id)
        else:
            self._json(404, {"error": "not_found", "request_id": request_id}, request_id)

    def do_POST(self) -> None:
        request_id = self._request_id()
        if self.path != "/v1/resolve" or self.resolver is None:
            self._json(404, {"error": "not_found", "request_id": request_id}, request_id)
            return
        try:
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                self._json(411, {"error": "content_length_required", "request_id": request_id}, request_id)
                return
            length = int(raw_length)
            if length < 0 or length > self.max_body_bytes:
                self._json(413, {"error": "request_too_large", "request_id": request_id}, request_id)
                return
            request = json.loads(self.rfile.read(length))
            pointer = request.get("pointer", "")
            result = self.resolver.resolve(request, self.projections.get(pointer, {}))
            self._json(200, result, request_id)
        except (ValueError, json.JSONDecodeError, ValidationError) as exc:
            self._json(400, {"error": "invalid_request", "detail": str(exc), "request_id": request_id}, request_id)
        except Exception:
            self._json(500, {"error": "internal_error", "request_id": request_id}, request_id)

    def log_message(self, format: str, *args: Any) -> None:
        return


def make_server(host: str, port: int, resolver: Resolver, projections: dict[str, dict[str, Any]], *, max_body_bytes: int = 1_048_576) -> ThreadingHTTPServer:
    if max_body_bytes <= 0:
        raise ValueError("max_body_bytes must be positive")
    ResolverHandler.resolver = resolver
    ResolverHandler.projections = projections
    ResolverHandler.max_body_bytes = max_body_bytes
    return ThreadingHTTPServer((host, port), ResolverHandler)

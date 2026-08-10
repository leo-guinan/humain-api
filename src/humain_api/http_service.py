"""Small HTTP transport for the reference resolver."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .resolver import Resolver
from .models import ValidationError


class ResolverHandler(BaseHTTPRequestHandler):
    resolver: Resolver | None = None
    projections: dict[str, dict[str, Any]] = {}

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(200, {"ok": True, "service": "humain-resolver", "protocol": "0.1"})
        else:
            self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/v1/resolve" or self.resolver is None:
            self._json(404, {"error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length))
            pointer = request.get("pointer", "")
            projection = self.projections.get(pointer, {})
            result = self.resolver.resolve(request, projection)
            self._json(200, result)
        except (ValueError, json.JSONDecodeError, ValidationError) as exc:
            self._json(400, {"error": "invalid_request", "detail": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        return


def make_server(host: str, port: int, resolver: Resolver, projections: dict[str, dict[str, Any]]) -> ThreadingHTTPServer:
    ResolverHandler.resolver = resolver
    ResolverHandler.projections = projections
    return ThreadingHTTPServer((host, port), ResolverHandler)

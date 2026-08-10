"""Local voice-tool boundary for ElevenLabs resolve_context calls."""
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any

from .memetic import humanize
from .models import ValidationError, parse_time
from .resolver import Resolver


@dataclass(frozen=True)
class VoiceSession:
    session_id: str
    pointer: str
    allowed_actions: tuple[str, ...]
    capability_expires_at: str
    request: dict[str, Any]

    def active(self, now: datetime | None = None) -> bool:
        return (now or datetime.now(timezone.utc)) <= parse_time(self.capability_expires_at)


class VoiceToolService:
    def __init__(self, resolver: Resolver, projections: dict[str, dict[str, Any]]):
        self.resolver = resolver
        self.projections = projections
        self.sessions: dict[str, VoiceSession] = {}

    def register(self, data: dict[str, Any]) -> VoiceSession:
        required = {"schema", "session_id", "pointer", "allowed_actions", "capability_expires_at", "request"}
        missing = required - data.keys()
        if missing or data["schema"] != "humain.voice.session.v1":
            raise ValidationError("invalid voice session")
        parse_time(data["capability_expires_at"])
        request = data["request"]
        if request.get("pointer") != data["pointer"]:
            raise ValidationError("session pointer does not match request pointer")
        session = VoiceSession(data["session_id"], data["pointer"], tuple(data["allowed_actions"]), data["capability_expires_at"], request)
        self.sessions[session.session_id] = session
        return session

    def resolve_context(self, data: dict[str, Any]) -> dict[str, Any]:
        if data.get("name") != "resolve_context":
            raise ValidationError("unsupported voice tool")
        args = data.get("arguments", {})
        session = self.sessions.get(args.get("session_id", ""))
        if not session or not session.active():
            raise ValidationError("voice session expired or unknown")
        if "resolve" not in session.allowed_actions:
            raise ValidationError("voice session cannot resolve context")
        if args.get("pointer") != session.pointer:
            raise ValidationError("voice pointer is outside session scope")
        response = self.resolver.resolve(session.request, self.projections.get(session.pointer, {}))
        return {
            "schema": "humain.voice.resolve.response.v1",
            "session_id": session.session_id,
            "pointer": session.pointer,
            "memetic": humanize(response),
            "underlying_response": response,
        }


class VoiceToolHandler(BaseHTTPRequestHandler):
    service: VoiceToolService | None = None

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.service is None:
            self._json(503, {"error": "service_unavailable"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length))
            if self.path == "/v1/voice/session":
                session = self.service.register(data)
                self._json(201, {"schema": "humain.voice.session.v1", "session_id": session.session_id, "expires_at": session.capability_expires_at})
            elif self.path == "/v1/voice/resolve":
                self._json(200, self.service.resolve_context(data))
            else:
                self._json(404, {"error": "not_found"})
        except (ValueError, json.JSONDecodeError, ValidationError) as exc:
            self._json(400, {"error": "invalid_voice_request", "detail": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        return


def make_voice_server(host: str, port: int, service: VoiceToolService) -> ThreadingHTTPServer:
    VoiceToolHandler.service = service
    return ThreadingHTTPServer((host, port), VoiceToolHandler)

"""Local-only OpenHome demo bridge.

The bridge accepts a normalized pointer event, not browser contents. It emits a
one-shot, public-only Marvin speech envelope after explicit desk-mode arming.
It is a demo boundary, not an identity provider or production trust service.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import hashlib
import json
from typing import Any

from .memetic import humanize
from .rendezvous import Participant, RendezvousBroker

SCHEMA = "humain.openhome.context-event.v1"
SPEECH_SCHEMA = "humain.openhome.speech-envelope.v1"
ALLOWED_HOSTS = {"story.markets", "www.story.markets", "buildinpublicuniversity.com"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_json_bytes(value)).hexdigest()


def _public_response(pointer: str, event_id: str) -> dict[str, Any]:
    return {
        "schema": "humain.resolve.response.v1",
        "message_id": "response:openhome:" + event_id,
        "message_type": "resolve.response",
        "pointer": pointer,
        "publisher": "public-web-pointer",
        "audience": "openhome-local-demo",
        "resolution_state": "public_only",
        "payload": {"pointer": pointer, "visibility": "public", "actions": []},
        "provenance": {"created_at": _iso(_now()), "method": "openhome-local-public-demo", "parent": _digest({"pointer": pointer, "event_id": event_id})},
        "permissions": {"action": "resolve", "capability_checked": False},
        "error": None,
        "signature": {"algorithm": "demo", "key_ref": "public-web-pointer", "value": "demo:unsigned"},
    }


@dataclass
class DemoArm:
    session_id: str
    expires_at: datetime
    muted: bool = False

    @property
    def active(self) -> bool:
        return _now() < self.expires_at and not self.muted


class OpenHomeBridge:
    def __init__(self, *, max_ttl_seconds: int = 900, debounce_seconds: int = 30, require_presence: bool = True, openhome_identity: Participant | None = None):
        self.max_ttl_seconds = max_ttl_seconds
        self.debounce_seconds = debounce_seconds
        self.require_presence = require_presence
        self.openhome_identity = openhome_identity
        self.arm_state: DemoArm | None = None
        self.presence: dict[str, Any] | None = None
        self.seen_events: dict[str, datetime] = {}
        self.last_pointer: tuple[str, datetime] | None = None
        self.queue: list[dict[str, Any]] = []
        self.rendezvous = RendezvousBroker(require_observation=True)

    def start_rendezvous(self, data: dict[str, Any]) -> dict[str, Any]:
        if not self.arm_state or not self.arm_state.active:
            raise PermissionError("desk mode is not armed")
        required = {"origin", "pathname", "event_id", "browser"}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"invalid rendezvous start: missing {sorted(missing)}")
        if self.openhome_identity is None:
            raise PermissionError("rendezvous_not_configured")
        try:
            browser = Participant("browser", str(data["browser"]["key_ref"]), str(data["browser"]["public_key_b64"]))
        except (KeyError, TypeError):
            raise ValueError("browser participant requires key_ref and public_key_b64")
        return self.rendezvous.start(origin=str(data["origin"]), pathname=str(data["pathname"]), event_id=str(data["event_id"]), browser=browser, openhome=self.openhome_identity)

    def rendezvous_action(self, action: str, data: dict[str, Any]) -> dict[str, Any]:
        rendezvous_id = str(data.get("rendezvous_id", ""))
        if action == "pending":
            if not self.arm_state or not self.arm_state.active:
                raise PermissionError("desk mode is not armed")
            return {"schema": "humain.rendezvous.pending.v1", "rendezvous": self.rendezvous.pending_for_openhome(str(data.get("key_ref", "")))}
        if action == "status":
            return self.rendezvous.status(rendezvous_id)
        if action == "ping":
            return self.rendezvous.issue_ping(rendezvous_id)
        if action == "claim":
            return self.rendezvous.submit_claim(rendezvous_id=rendezvous_id, role=str(data.get("role", "")), nonce=str(data.get("nonce", "")), signature=data.get("signature") or {}, observed_at=str(data.get("observed_at", "")))
        if action == "answer_ping":
            return self.rendezvous.answer_ping(rendezvous_id=rendezvous_id, role=str(data.get("role", "")), ping_id=str(data.get("ping_id", "")), nonce=str(data.get("nonce", "")), signature=data.get("signature") or {}, observed_at=str(data.get("observed_at", "")))
        if action == "receipt":
            return self.rendezvous.submit_shared_receipt(rendezvous_id=rendezvous_id, role=str(data.get("role", "")), receipt_hash=str(data.get("receipt_hash", "")), signature=data.get("signature") or {})
        if action == "observation":
            return self.rendezvous.submit_observation(rendezvous_id=rendezvous_id, scanner=str(data.get("scanner", "")), observed_at=str(data.get("observed_at", "")), service_uuid=str(data.get("service_uuid", "")), advertisement_commitment=str(data.get("advertisement_commitment", "")), rssi_bucket=data.get("rssi_bucket"), sample_count=int(data.get("sample_count", 1)))
        if action == "bind":
            return self.rendezvous.bind(rendezvous_id=rendezvous_id, binding_code=str(data.get("binding_code", "")))
        if action == "grant":
            return self.rendezvous.issue_grant(rendezvous_id)
        raise ValueError("unknown rendezvous action")

    def arm(self, session_id: str, ttl_seconds: int = 300) -> dict[str, Any]:
        if not session_id or not isinstance(session_id, str):
            raise ValueError("session_id is required")
        ttl = max(1, min(int(ttl_seconds), self.max_ttl_seconds))
        self.arm_state = DemoArm(session_id=session_id, expires_at=_now() + timedelta(seconds=ttl))
        return self.status()

    def mute(self) -> dict[str, Any]:
        if self.arm_state:
            self.arm_state.muted = True
        return self.status()

    def update_presence(self, presence: dict[str, Any]) -> dict[str, Any]:
        if presence.get("schema") != "humain.proximity.presence.v1":
            raise ValueError("invalid presence schema")
        try:
            presence_age = (_now() - datetime.fromisoformat(str(presence["observed_at"]).replace("Z", "+00:00"))).total_seconds()
        except (KeyError, TypeError, ValueError):
            raise ValueError("presence observed_at is required")
        if presence_age > 30 or presence_age < -5:
            raise PermissionError("presence receipt is stale")
        if presence.get("presence_state") != "near_verified" or not presence.get("flow_eligible"):
            self.presence = presence
            raise PermissionError("proximity is not near_verified")
        self.presence = presence
        return self.status()

    def status(self) -> dict[str, Any]:
        active = bool(self.arm_state and self.arm_state.active)
        return {"schema": "humain.openhome.bridge.status.v1", "armed": active, "muted": bool(self.arm_state and self.arm_state.muted), "session_id": self.arm_state.session_id if self.arm_state else None, "expires_at": _iso(self.arm_state.expires_at) if self.arm_state else None, "presence_state": (self.presence or {}).get("presence_state", "absent"), "paired_device": (self.presence or {}).get("paired_device"), "flow_eligible": bool(self.presence and self.presence.get("flow_eligible")), "queued": len(self.queue)}

    def submit_event(self, event: dict[str, Any]) -> dict[str, Any]:
        if not self.arm_state or not self.arm_state.active:
            raise PermissionError("desk mode is not armed")
        if self.require_presence and (not self.presence or self.presence.get("presence_state") != "near_verified" or not self.presence.get("flow_eligible")):
            raise PermissionError("paired presence is not near_verified")
        required = {"schema", "event_id", "pointer", "occurred_at", "client_id"}
        missing = required - event.keys()
        if missing or event["schema"] != SCHEMA:
            raise ValueError(f"invalid context event: missing {sorted(missing)}")
        event_id = str(event["event_id"])
        pointer = str(event["pointer"])
        parsed = urlparse(pointer)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or parsed.query or parsed.fragment:
            raise PermissionError("pointer is outside the demo allowlist")
        if event.get("context") or event.get("page_text") or event.get("page_html"):
            raise PermissionError("raw browser context is not accepted")
        if event_id in self.seen_events:
            return {"status": "duplicate", "event_id": event_id, "speech_envelope": None}
        self.seen_events[event_id] = _now()
        if self.last_pointer and self.last_pointer[0] == pointer and (_now() - self.last_pointer[1]).total_seconds() < self.debounce_seconds:
            return {"status": "debounced", "event_id": event_id, "speech_envelope": None}
        self.last_pointer = (pointer, _now())
        response = _public_response(pointer, event_id)
        memetic = humanize(response)
        envelope = {
            "schema": SPEECH_SCHEMA,
            "delivery_id": "speech:" + event_id,
            "session_id": self.arm_state.session_id,
            "pointer": pointer,
            "speech_text": "Welcome to story markets." if parsed.hostname in {"story.markets", "www.story.markets"} else f"You have arrived at {parsed.hostname}. {memetic['surface_text']} This is an AI-generated public-context demo. Say show the receipt if you want the details.",
            "resolution_state": response["resolution_state"],
            "receipt": {"response_message_id": response["message_id"], "provenance": response["provenance"], "underlying_response": response},
            "permissions": {"speech": True, "private_context": False, "actions": []},
        }
        self.queue.append(envelope)
        return {"status": "queued", "event_id": event_id, "speech_envelope": envelope}

    def next_message(self) -> dict[str, Any]:
        if not self.arm_state or not self.arm_state.active:
            return {"status": "disabled", "speech_envelope": None}
        if not self.queue:
            return {"status": "empty", "speech_envelope": None}
        return {"status": "ready", "speech_envelope": self.queue.pop(0)}


class OpenHomeBridgeHandler(BaseHTTPRequestHandler):
    bridge: OpenHomeBridge | None = None

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 32_768:
            raise ValueError("request too large")
        return json.loads(self.rfile.read(length))

    def do_GET(self) -> None:
        if self.bridge is None:
            self._json(503, {"error": "service_unavailable"})
        elif self.path == "/v1/openhome/status":
            self._json(200, self.bridge.status())
        elif self.path == "/v1/openhome/next":
            self._json(200, self.bridge.next_message())
        else:
            self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.bridge is None:
            self._json(503, {"error": "service_unavailable"})
            return
        try:
            data = self._read()
            if self.path == "/v1/openhome/arm":
                self._json(200, self.bridge.arm(data.get("session_id", ""), data.get("ttl_seconds", 300)))
            elif self.path == "/v1/openhome/mute":
                self._json(200, self.bridge.mute())
            elif self.path == "/v1/openhome/presence":
                self._json(200, self.bridge.update_presence(data))
            elif self.path == "/v1/openhome/context-event":
                self._json(202, self.bridge.submit_event(data))
            elif self.path == "/v1/rendezvous/start":
                self._json(201, self.bridge.start_rendezvous(data))
            elif self.path == "/v1/rendezvous/pending":
                self._json(200, self.bridge.rendezvous_action("pending", data))
            elif self.path == "/v1/rendezvous/status":
                self._json(200, self.bridge.rendezvous_action("status", data))
            elif self.path == "/v1/rendezvous/ping":
                self._json(200, self.bridge.rendezvous_action("ping", data))
            elif self.path == "/v1/rendezvous/claim":
                self._json(200, self.bridge.rendezvous_action("claim", data))
            elif self.path == "/v1/rendezvous/answer-ping":
                self._json(200, self.bridge.rendezvous_action("answer_ping", data))
            elif self.path == "/v1/rendezvous/receipt":
                self._json(200, self.bridge.rendezvous_action("receipt", data))
            elif self.path == "/v1/rendezvous/observation":
                self._json(200, self.bridge.rendezvous_action("observation", data))
            elif self.path == "/v1/rendezvous/bind":
                self._json(200, self.bridge.rendezvous_action("bind", data))
            elif self.path == "/v1/rendezvous/grant":
                self._json(200, self.bridge.rendezvous_action("grant", data))
            else:
                self._json(404, {"error": "not_found"})
        except PermissionError as exc:
            self._json(403, {"error": "demo_boundary_rejected", "detail": str(exc)})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._json(400, {"error": "invalid_openhome_request", "detail": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        return


def make_openhome_bridge_server(host: str, port: int, bridge: OpenHomeBridge) -> ThreadingHTTPServer:
    OpenHomeBridgeHandler.bridge = bridge
    return ThreadingHTTPServer((host, port), OpenHomeBridgeHandler)

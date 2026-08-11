"""Server-mediated browser/OpenHome rendezvous verifier.

This module authenticates a bounded rendezvous, not a person or physical
location. Browser and OpenHome claims are independent signed statements. A
short-lived human binding and a shared signed receipt are required before a
single-use public-only grant is issued.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from typing import Any, Callable

from .canonical import content_hash
from .crypto import Ed25519Verifier

SCHEMA = "humain.rendezvous.v1"
GRANT_SCHEMA = "humain.rendezvous.grant.v1"


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _token(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(18)}"


@dataclass(frozen=True)
class Participant:
    role: str
    key_ref: str
    public_key_b64: str


@dataclass
class _Ping:
    ping_id: str
    nonce: str
    issued_at: datetime
    answered: set[str] = field(default_factory=set)


@dataclass
class RendezvousSession:
    rendezvous_id: str
    origin: str
    pathname: str
    event_id: str
    browser: Participant
    openhome: Participant
    browser_nonce: str
    openhome_nonce: str
    binding_code_hash: str
    expires_at: datetime
    state: str = "pending"
    browser_claim: bool = False
    openhome_claim: bool = False
    browser_ping: bool = False
    openhome_ping: bool = False
    shared_receipt_hash: str | None = None
    binding_verified: bool = False
    used: bool = False
    pings: dict[str, _Ping] = field(default_factory=dict)
    observations: dict[str, dict[str, Any]] = field(default_factory=dict)
    corroborated_candidate_near: bool = False
    tripwires: list[dict[str, Any]] = field(default_factory=list)


class RendezvousBroker:
    """Fail-closed verifier for a bounded browser/OpenHome rendezvous."""

    def __init__(self, *, now: Callable[[], datetime] | None = None, ttl_seconds: int = 60, ping_ttl_seconds: int = 10, require_observation: bool = False):
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.ttl_seconds = ttl_seconds
        self.ping_ttl_seconds = ping_ttl_seconds
        self.require_observation = require_observation
        self.sessions: dict[str, RendezvousSession] = {}
        self.used_nonces: set[tuple[str, str, str]] = set()

    def start(self, *, origin: str, pathname: str, event_id: str, browser: Participant, openhome: Participant) -> dict[str, Any]:
        if not origin.startswith("https://"):
            raise ValueError("rendezvous requires an HTTPS origin")
        if not pathname.startswith("/") or "?" in pathname or "#" in pathname:
            raise ValueError("pathname must be normalized and contain no query or fragment")
        if browser.role != "browser" or openhome.role != "openhome":
            raise ValueError("participants must be browser and openhome")
        now = self.now()
        rendezvous_id = _token("rv")
        binding_code = f"{secrets.randbelow(1_000_000):06d}"
        session = RendezvousSession(
            rendezvous_id=rendezvous_id,
            origin=origin,
            pathname=pathname,
            event_id=event_id,
            browser=browser,
            openhome=openhome,
            browser_nonce=_token("bn"),
            openhome_nonce=_token("on"),
            binding_code_hash=hashlib.sha256(binding_code.encode("ascii")).hexdigest(),
            expires_at=now + timedelta(seconds=self.ttl_seconds),
        )
        self.sessions[rendezvous_id] = session
        return {
            "schema": SCHEMA,
            "rendezvous_id": rendezvous_id,
            "browser_challenge": session.browser_nonce,
            "openhome_challenge": session.openhome_nonce,
            "binding_code": binding_code,
            "scope": {"origin": origin, "pathname": pathname, "action": "speak_public_greeting"},
            "expires_at": _iso(session.expires_at),
        }

    def pending_for_openhome(self, key_ref: str) -> list[dict[str, Any]]:
        if not key_ref:
            return []
        pending = []
        for session in self.sessions.values():
            if session.openhome.key_ref != key_ref:
                continue
            if self.now() >= session.expires_at or session.used or session.openhome_claim:
                continue
            pending.append({
                "schema": SCHEMA,
                "rendezvous_id": session.rendezvous_id,
                "openhome_challenge": session.openhome_nonce,
                "scope": {"origin": session.origin, "pathname": session.pathname, "event_id": session.event_id},
                "shared_receipt_hash": session.shared_receipt_hash,
                "expires_at": _iso(session.expires_at),
            })
        return pending

    def _session(self, rendezvous_id: str) -> RendezvousSession:
        session = self.sessions.get(rendezvous_id)
        if not session or self.now() >= session.expires_at:
            raise PermissionError("rendezvous missing or expired")
        return session

    def submit_claim(self, *, rendezvous_id: str, role: str, nonce: str, signature: dict[str, str], observed_at: str) -> dict[str, Any]:
        session = self._session(rendezvous_id)
        participant = session.browser if role == "browser" else session.openhome if role == "openhome" else None
        expected = session.browser_nonce if role == "browser" else session.openhome_nonce if role == "openhome" else None
        if participant is None or nonce != expected:
            raise PermissionError("claim role or nonce mismatch")
        if abs((self.now() - _parse(observed_at)).total_seconds()) > self.ttl_seconds:
            raise PermissionError("stale claim")
        replay_key = (rendezvous_id, role, nonce)
        if replay_key in self.used_nonces:
            raise PermissionError("replayed claim")
        value = {
            "schema": SCHEMA,
            "rendezvous_id": rendezvous_id,
            "role": role,
            "nonce": nonce,
            "origin": session.origin,
            "pathname": session.pathname,
            "event_id": session.event_id,
            "observed_at": observed_at,
        }
        if not Ed25519Verifier({participant.key_ref: participant.public_key_b64})(value, signature):
            raise PermissionError("claim signature was not verified")
        self.used_nonces.add(replay_key)
        if role == "browser":
            session.browser_claim = True
        else:
            session.openhome_claim = True
        return self.status(rendezvous_id)

    def issue_ping(self, rendezvous_id: str) -> dict[str, Any]:
        session = self._session(rendezvous_id)
        ping = _Ping(_token("ping"), _token("nonce"), self.now())
        session.pings[ping.ping_id] = ping
        return {"schema": SCHEMA, "rendezvous_id": rendezvous_id, "ping_id": ping.ping_id, "nonce": ping.nonce, "expires_at": _iso(ping.issued_at + timedelta(seconds=self.ping_ttl_seconds))}

    def answer_ping(self, *, rendezvous_id: str, role: str, ping_id: str, nonce: str, signature: dict[str, str], observed_at: str) -> dict[str, Any]:
        session = self._session(rendezvous_id)
        ping = session.pings.get(ping_id)
        participant = session.browser if role == "browser" else session.openhome if role == "openhome" else None
        if not ping or participant is None or nonce != ping.nonce:
            raise PermissionError("ping mismatch")
        if self.now() > ping.issued_at + timedelta(seconds=self.ping_ttl_seconds):
            raise PermissionError("expired ping")
        if role not in {"browser", "openhome"} or role in ping.answered:
            raise PermissionError("replayed ping")
        value = {"schema": SCHEMA, "rendezvous_id": rendezvous_id, "ping_id": ping_id, "nonce": nonce, "role": role, "observed_at": observed_at}
        if not Ed25519Verifier({participant.key_ref: participant.public_key_b64})(value, signature):
            raise PermissionError("ping signature was not verified")
        ping.answered.add(role)
        if role == "browser":
            session.browser_ping = True
        else:
            session.openhome_ping = True
        return self.status(rendezvous_id)

    def submit_shared_receipt(self, *, rendezvous_id: str, role: str, receipt_hash: str, signature: dict[str, str]) -> dict[str, Any]:
        session = self._session(rendezvous_id)
        participant = session.browser if role == "browser" else session.openhome if role == "openhome" else None
        if participant is None or not receipt_hash.startswith("sha256:"):
            raise PermissionError("invalid receipt")
        value = {"schema": SCHEMA, "rendezvous_id": rendezvous_id, "role": role, "receipt_hash": receipt_hash, "scope": {"origin": session.origin, "pathname": session.pathname}}
        if not Ed25519Verifier({participant.key_ref: participant.public_key_b64})(value, signature):
            raise PermissionError("receipt signature was not verified")
        if session.shared_receipt_hash and not hmac.compare_digest(session.shared_receipt_hash, receipt_hash):
            raise PermissionError("shared receipt mismatch")
        session.shared_receipt_hash = receipt_hash
        return self.status(rendezvous_id)

    def submit_observation(self, *, rendezvous_id: str, scanner: str, observed_at: str, service_uuid: str, advertisement_commitment: str, commitment_quality: str = "payload", rssi_bucket: int | None = None, sample_count: int = 1) -> dict[str, Any]:
        session = self._session(rendezvous_id)
        if scanner not in {"browser", "openhome"}:
            raise PermissionError("unknown observation scanner")
        if not service_uuid or len(service_uuid) > 128 or not advertisement_commitment or len(advertisement_commitment) > 256:
            raise ValueError("observation requires bounded service and advertisement commitment")
        if commitment_quality not in {"payload", "uuid_only"}:
            raise ValueError("invalid commitment quality")
        observed = _parse(observed_at)
        age = abs((self.now() - observed).total_seconds())
        if age > self.ttl_seconds or age > 10:
            self._tripwire(session, "stale_observation", scanner)
            raise PermissionError("stale observation")
        if rssi_bucket is not None and not -127 <= int(rssi_bucket) <= 0:
            raise ValueError("invalid RSSI bucket")
        prior = session.observations.get(scanner)
        if prior and prior.get("advertisement_commitment") == advertisement_commitment and prior.get("observed_at") == observed_at:
            self._tripwire(session, "replayed_observation", scanner)
            raise PermissionError("replayed observation")
        session.observations[scanner] = {"scanner": scanner, "observed_at": _iso(observed), "service_uuid": service_uuid, "advertisement_commitment": advertisement_commitment, "commitment_quality": commitment_quality, "rssi_bucket": rssi_bucket, "sample_count": max(1, min(int(sample_count), 20))}
        browser = session.observations.get("browser")
        openhome = session.observations.get("openhome")
        if browser and openhome:
            if browser["commitment_quality"] != "payload" or openhome["commitment_quality"] != "payload":
                self._tripwire(session, "weak_observation_material", scanner)
            elif browser["service_uuid"] != openhome["service_uuid"] or not hmac.compare_digest(browser["advertisement_commitment"], openhome["advertisement_commitment"]):
                self._tripwire(session, "scanner_observation_mismatch", scanner)
            elif abs((_parse(browser["observed_at"]) - _parse(openhome["observed_at"])).total_seconds()) > 5:
                self._tripwire(session, "scanner_timing_mismatch", scanner)
            elif browser.get("rssi_bucket") is not None and openhome.get("rssi_bucket") is not None and abs(browser["rssi_bucket"] - openhome["rssi_bucket"]) > 35:
                self._tripwire(session, "rssi_disagreement", scanner)
            else:
                session.corroborated_candidate_near = True
        return self.status(rendezvous_id)

    def _tripwire(self, session: RendezvousSession, reason: str, source: str) -> None:
        if len(session.tripwires) < 20:
            session.tripwires.append({"schema": "humain.rendezvous.tripwire.v1", "rendezvous_id": session.rendezvous_id, "severity": "medium", "reason": reason, "source": source, "occurred_at": _iso(self.now()), "action_taken": "quarantined"})
        session.corroborated_candidate_near = False

    def bind(self, *, rendezvous_id: str, binding_code: str) -> dict[str, Any]:
        session = self._session(rendezvous_id)
        digest = hashlib.sha256(binding_code.encode("ascii")).hexdigest()
        if not hmac.compare_digest(session.binding_code_hash, digest):
            raise PermissionError("binding code was not verified")
        session.binding_verified = True
        return self.status(rendezvous_id)

    def status(self, rendezvous_id: str) -> dict[str, Any]:
        session = self._session(rendezvous_id)
        requirements = {
            "browser_claim": session.browser_claim,
            "openhome_claim": session.openhome_claim,
            "browser_ping": session.browser_ping,
            "openhome_ping": session.openhome_ping,
            "shared_receipt": session.shared_receipt_hash is not None,
            "human_binding": session.binding_verified,
        }
        if self.require_observation:
            requirements["corroborated_candidate_near"] = session.corroborated_candidate_near
        if session.tripwires:
            session.state = "quarantined"
        elif all(requirements.values()):
            session.state = "mutual_rendezvous"
        elif session.corroborated_candidate_near:
            session.state = "corroborated_candidate_near"
        elif session.browser_claim or session.openhome_claim:
            session.state = "claims_partial"
        return {"schema": SCHEMA, "rendezvous_id": rendezvous_id, "state": session.state, "requirements": requirements, "scope": {"origin": session.origin, "pathname": session.pathname}, "observations": {role: {key: value for key, value in item.items() if key != "advertisement_commitment"} for role, item in session.observations.items()}, "tripwires": list(session.tripwires)}

    def issue_grant(self, rendezvous_id: str) -> dict[str, Any]:
        session = self._session(rendezvous_id)
        status = self.status(rendezvous_id)
        if status["state"] != "mutual_rendezvous" or session.used:
            raise PermissionError("rendezvous is not grantable")
        session.used = True
        return {
            "schema": GRANT_SCHEMA,
            "rendezvous_id": rendezvous_id,
            "state": "mutual_rendezvous",
            "scope": {"origin": session.origin, "pathname": session.pathname, "action": "speak_public_greeting"},
            "private_context": False,
            "payment_semantics": "link_only_no_transfer",
            "single_use": True,
            "expires_at": _iso(session.expires_at),
            "receipt": content_hash({"rendezvous_id": rendezvous_id, "scope": {"origin": session.origin, "pathname": session.pathname}}),
        }

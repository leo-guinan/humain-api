"""Proximity presence broker: BLE is a signal; signed pairing is proof of possession."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import statistics
from typing import Any, Callable

from .canonical import canonical_bytes
from .crypto import Ed25519Verifier

SCHEMA = "humain.proximity.presence.v1"


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class Pairing:
    alias: str
    key_ref: str
    public_key_b64: str
    purpose: str = "presence_signal"
    revoked: bool = False


@dataclass(frozen=True)
class Observation:
    alias: str
    rssi: float
    observed_at: datetime
    verified: bool
    challenge: str | None = None


class PresenceBroker:
    """State machine for candidate proximity and signed near-presence."""

    def __init__(self, *, now: Callable[[], datetime] | None = None, window_seconds: int = 5, min_observations: int = 3, enter_rssi: float = -65.0, exit_rssi: float = -72.0, freshness_seconds: int = 30):
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.window_seconds = window_seconds
        self.min_observations = min_observations
        self.enter_rssi = enter_rssi
        self.exit_rssi = exit_rssi
        self.freshness_seconds = freshness_seconds
        self.pairings: dict[str, Pairing] = {}
        self.observations: dict[str, deque[Observation]] = {}
        self.used_challenges: set[tuple[str, str]] = set()
        self.state: dict[str, str] = {}

    def pair(self, pairing: Pairing) -> None:
        if not pairing.alias or not pairing.key_ref or not pairing.public_key_b64:
            raise ValueError("pairing requires alias, key_ref, and public key")
        self.pairings[pairing.alias] = pairing
        self.state[pairing.alias] = "absent"

    def revoke(self, alias: str) -> None:
        pairing = self.pairings.get(alias)
        if pairing:
            self.pairings[alias] = Pairing(pairing.alias, pairing.key_ref, pairing.public_key_b64, pairing.purpose, True)
        self.state[alias] = "absent"

    def observe_advertisement(self, alias: str, rssi: float, observed_at: str) -> dict[str, Any]:
        """Record only a radio candidate. It cannot produce near_verified."""
        return self._record(Observation(alias, float(rssi), _parse(observed_at), False))

    def observe_signed_presence(self, *, alias: str, rssi: float, observed_at: str, challenge: str, signature: dict[str, str]) -> dict[str, Any]:
        pairing = self.pairings.get(alias)
        if not pairing or pairing.revoked:
            raise PermissionError("unknown or revoked pairing")
        observed = _parse(observed_at)
        if abs((self.now() - observed).total_seconds()) > self.freshness_seconds:
            raise PermissionError("stale proximity challenge")
        challenge_key = (alias, challenge)
        if challenge_key in self.used_challenges:
            raise PermissionError("replayed proximity challenge")
        signed_value = {"schema": SCHEMA, "alias": alias, "challenge": challenge, "purpose": pairing.purpose, "observed_at": _iso(observed)}
        verifier = Ed25519Verifier({pairing.key_ref: pairing.public_key_b64})
        if not verifier(signed_value, signature):
            raise PermissionError("proximity signature was not verified")
        self.used_challenges.add(challenge_key)
        return self._record(Observation(alias, float(rssi), observed, True, challenge))

    def _record(self, observation: Observation) -> dict[str, Any]:
        if observation.alias not in self.pairings:
            raise PermissionError("unknown pairing")
        queue = self.observations.setdefault(observation.alias, deque())
        queue.append(observation)
        cutoff = observation.observed_at - timedelta(seconds=self.window_seconds)
        while queue and queue[0].observed_at < cutoff:
            queue.popleft()
        previous = self.state.get(observation.alias, "absent")
        verified = [item for item in queue if item.verified]
        rssis = [item.rssi for item in queue]
        median_rssi = round(statistics.median(rssis), 3) if rssis else None
        if len(verified) >= self.min_observations and median_rssi is not None and median_rssi >= self.enter_rssi:
            current = "near_verified"
        elif median_rssi is not None and median_rssi >= self.exit_rssi:
            current = "candidate_near"
        else:
            current = "absent"
        self.state[observation.alias] = current
        return {
            "schema": SCHEMA,
            "presence_state": current,
            "previous_state": previous,
            "paired_device": observation.alias,
            "observation_count": len(queue),
            "verified_observation_count": len(verified),
            "rssi_median": median_rssi,
            "window_seconds": self.window_seconds,
            "challenge_verified": bool(verified),
            "flow_eligible": current == "near_verified",
            "observed_at": _iso(observation.observed_at),
            "provenance": {"method": "signed-proximity-window", "falsifier": "an unsigned, stale, replayed, revoked, or unpaired observation must never become near_verified"},
        }

    def status(self, alias: str) -> dict[str, Any]:
        return {"schema": SCHEMA, "paired_device": alias, "presence_state": self.state.get(alias, "absent"), "flow_eligible": self.state.get(alias) == "near_verified"}


def sign_challenge(signer: Any, *, alias: str, challenge: str, purpose: str, observed_at: str) -> dict[str, str]:
    """Simulator/device helper; private keys stay with the paired device."""
    value = {"schema": SCHEMA, "alias": alias, "challenge": challenge, "purpose": purpose, "observed_at": _iso(_parse(observed_at))}
    return signer.sign(value)

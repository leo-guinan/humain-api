"""OpenHome-side adapter for the signed rendezvous protocol.

The caller owns the signer/private key. This client receives only bounded
rendezvous metadata and never requests browser contents or browsing history.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from urllib.request import Request, urlopen
from typing import Any

from humain_api.crypto import Ed25519Signer


class RendezvousClient:
    def __init__(self, endpoint: str, signer: Ed25519Signer, *, timeout: float = 5.0):
        self.endpoint = endpoint.rstrip("/")
        self.signer = signer
        self.timeout = timeout

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = Request(self.endpoint + path, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def pending(self) -> list[dict[str, Any]]:
        result = self._post("/v1/rendezvous/pending", {"key_ref": self.signer.key_ref})
        return list(result.get("rendezvous") or [])

    def claim(self, rendezvous: dict[str, Any]) -> dict[str, Any]:
        observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        value = {
            "schema": "humain.rendezvous.v1",
            "rendezvous_id": rendezvous["rendezvous_id"],
            "role": "openhome",
            "nonce": rendezvous["openhome_challenge"],
            "origin": rendezvous["scope"]["origin"],
            "pathname": rendezvous["scope"]["pathname"],
            "event_id": rendezvous["scope"]["event_id"],
            "observed_at": observed_at,
        }
        return self._post("/v1/rendezvous/claim", {"rendezvous_id": rendezvous["rendezvous_id"], "role": "openhome", "nonce": rendezvous["openhome_challenge"], "observed_at": observed_at, "signature": self.signer.sign(value)})

    def answer_ping(self, *, rendezvous_id: str, ping_id: str, nonce: str) -> dict[str, Any]:
        observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        value = {"schema": "humain.rendezvous.v1", "rendezvous_id": rendezvous_id, "ping_id": ping_id, "nonce": nonce, "role": "openhome", "observed_at": observed_at}
        return self._post("/v1/rendezvous/answer-ping", {"rendezvous_id": rendezvous_id, "role": "openhome", "ping_id": ping_id, "nonce": nonce, "observed_at": observed_at, "signature": self.signer.sign(value)})

    def observation(self, *, rendezvous_id: str, observed_at: str, service_uuid: str, advertisement_commitment: str, commitment_quality: str = "payload", rssi_bucket: int | None = None, sample_count: int = 1) -> dict[str, Any]:
        return self._post("/v1/rendezvous/observation", {"rendezvous_id": rendezvous_id, "scanner": "openhome", "observed_at": observed_at, "service_uuid": service_uuid, "advertisement_commitment": advertisement_commitment, "commitment_quality": commitment_quality, "rssi_bucket": rssi_bucket, "sample_count": sample_count})

    def receipt(self, *, rendezvous_id: str, receipt_hash: str, origin: str, pathname: str) -> dict[str, Any]:
        value = {"schema": "humain.rendezvous.v1", "rendezvous_id": rendezvous_id, "role": "openhome", "receipt_hash": receipt_hash, "scope": {"origin": origin, "pathname": pathname}}
        return self._post("/v1/rendezvous/receipt", {**value, "signature": self.signer.sign(value)})

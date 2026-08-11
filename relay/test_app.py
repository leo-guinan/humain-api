import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from relay.app import app


def test_health_and_auth(monkeypatch):
    monkeypatch.setenv("RELAY_DEVKIT_TOKEN", "test-token")
    monkeypatch.delenv("RELAY_OPENHOME_KEY_REF", raising=False)
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["openhome_identity_configured"] is False
        assert client.post("/v1/rendezvous/pending", json={"key_ref": "x"}).status_code == 401


def test_start_pending_and_observation(monkeypatch):
    monkeypatch.setenv("RELAY_DEVKIT_TOKEN", "test-token")
    monkeypatch.setenv("RELAY_OPENHOME_KEY_REF", "openhome:test")
    monkeypatch.setenv("RELAY_OPENHOME_PUBLIC_KEY_B64", "not-used-until-claim")
    with TestClient(app) as client:
        started = client.post("/v1/rendezvous/start", json={"origin": "https://story.markets", "pathname": "/", "event_id": "evt-1", "browser_key_ref": "browser:test", "browser_public_key_b64": "not-used"})
        assert started.status_code == 200
        session = started.json()
        pending = client.post("/v1/rendezvous/pending", headers={"Authorization": "Bearer test-token"}, json={"key_ref": "openhome:test"})
        assert pending.status_code == 200
        assert pending.json()["rendezvous"][0]["rendezvous_id"] == session["rendezvous_id"]
        observation = client.post("/v1/rendezvous/observation", headers={"Authorization": "Bearer test-token"}, json={"rendezvous_id": session["rendezvous_id"], "scanner": "openhome", "observed_at": session["expires_at"], "service_uuid": "service", "advertisement_commitment": "hmac:test", "commitment_quality": "payload", "rssi_bucket": -45})
        assert observation.status_code == 403

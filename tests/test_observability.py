import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from fastapi.testclient import TestClient
from relay.app import app


def test_observability_is_authenticated_and_redacted(monkeypatch):
    monkeypatch.setenv("RELAY_DEVKIT_TOKEN", "test-token")
    with TestClient(app) as client:
        assert client.post("/v1/observability/events", json={"run_id": "r1", "source": "devkit", "stage": "x"}).status_code == 401
        response = client.post("/v1/observability/events", headers={"Authorization": "Bearer test-token"}, json={"run_id": "r1", "source": "devkit", "stage": "entry", "detail": {"secret": "not retained"}, "unexpected": "dropped"})
        assert response.status_code == 200
        event = response.json()["event"]
        assert event["sequence"] >= 1
        assert "unexpected" not in event
        assert "detail" not in event
        events = client.get("/v1/observability/events?run_id=r1", headers={"Authorization": "Bearer test-token"})
        assert events.status_code == 200
        assert events.json()["events"][-1]["stage"] == "entry"
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from humain_api.fastapi_service import create_app
from humain_api import Ed25519Signer, Ed25519Verifier, Resolver


class FastAPIBoundaryTests(unittest.TestCase):
    def setUp(self):
        agent = Ed25519Signer.generate("did:key:agent")
        publisher = Ed25519Signer.generate("did:key:publisher")
        resolver = Resolver(
            publisher="did:key:publisher", mode="production",
            verify_signature=Ed25519Verifier({"did:key:agent": agent.public_key_b64}),
            response_signer=publisher,
        )
        self.client = TestClient(create_app(resolver, {}, max_body_bytes=128))

    def test_health_and_readiness_have_distinct_contracts(self):
        with self.client as client:
            health = client.get("/healthz")
            ready = client.get("/readyz")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["ok"], True)
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json()["mode"], "production")

    def test_request_id_is_preserved_and_invalid_body_is_bounded(self):
        with self.client as client:
            response = client.post("/v1/resolve", content=b"{}", headers={"X-Request-ID": "req:fastapi"})
            oversized = client.post("/v1/resolve", content=b"x" * 129, headers={"X-Request-ID": "req:large"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.headers["X-Request-ID"], "req:fastapi")
        self.assertEqual(response.json()["error"], "invalid_request")
        self.assertEqual(oversized.status_code, 413)
        self.assertEqual(oversized.headers["X-Request-ID"], "req:large")

    def test_unknown_route_uses_standard_error(self):
        with self.client as client:
            response = client.get("/nope", headers={"X-Request-ID": "req:nope"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers["X-Request-ID"], "req:nope")
        self.assertEqual(response.json()["error"], "not_found")


if __name__ == "__main__":
    unittest.main()

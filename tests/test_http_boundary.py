import json
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from humain_api import Ed25519Signer, Ed25519Verifier, Resolver
from humain_api.http_service import make_server


class HTTPBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.agent = Ed25519Signer.generate("did:key:agent")
        self.publisher = Ed25519Signer.generate("did:key:publisher")
        self.resolver = Resolver(
            publisher="did:key:publisher", mode="production",
            verify_signature=Ed25519Verifier({"did:key:agent": self.agent.public_key_b64}),
            response_signer=self.publisher,
        )
        self.server = make_server("127.0.0.1", 0, self.resolver, {}, max_body_bytes=256)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def get(self, path):
        return urlopen(self.base + path, timeout=2)

    def test_healthz_is_liveness_and_readyz_reports_production_readiness(self):
        health = json.loads(self.get("/healthz").read())
        ready = json.loads(self.get("/readyz").read())
        self.assertEqual(health, {"ok": True, "service": "humain-resolver", "protocol": "0.1"})
        self.assertEqual(ready["ok"], True)
        self.assertEqual(ready["mode"], "production")

    def test_request_id_is_returned_and_body_limit_is_enforced(self):
        request = Request(self.base + "/v1/resolve", data=b"{}", headers={"Content-Type": "application/json", "X-Request-ID": "req:test"})
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=2)
        self.assertEqual(raised.exception.code, 400)
        self.assertEqual(raised.exception.headers["X-Request-ID"], "req:test")
        oversized = Request(self.base + "/v1/resolve", data=b"x" * 257, headers={"Content-Type": "application/json", "X-Request-ID": "req:large"})
        with self.assertRaises(HTTPError) as raised:
            urlopen(oversized, timeout=2)
        self.assertEqual(raised.exception.code, 413)
        self.assertEqual(raised.exception.headers["X-Request-ID"], "req:large")

    def test_unknown_path_has_standard_error_envelope(self):
        with self.assertRaises(HTTPError) as raised:
            self.get("/nope")
        self.assertEqual(raised.exception.code, 404)
        payload = json.loads(raised.exception.read())
        self.assertEqual(payload["error"], "not_found")
        self.assertIn("request_id", payload)


if __name__ == "__main__":
    unittest.main()

import json
import sys
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from humain_api import Receipt, Resolver, ValidationError, canonical_bytes, content_hash
from humain_api.crypto import Ed25519Signer, Ed25519Verifier
from humain_api.http_service import make_server


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        now = datetime.now(timezone.utc)
        self.issued = (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
        self.expires = (now + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
        self.request = {
            "schema": "humain.resolve.request.v1", "message_id": "request:1",
            "pointer": "https://example.com/article/123", "requester": "did:key:z6MkAgent",
            "audience": "did:key:z6MkPublisher", "action": "resolve",
            "nonce": "nonce-1", "created_at": now.isoformat().replace("+00:00", "Z"),
            "capabilities": [{
                "capability_id": "cap:1", "issuer": "did:key:z6MkPublisher", "subject": "did:key:z6MkAgent",
                "audience": "did:key:z6MkPublisher", "pointer": "https://example.com/article/123",
                "action": "resolve", "issued_at": self.issued, "expires_at": self.expires, "revoked": False
            }],
            "signature": {"algorithm": "test", "key_ref": "did:key:z6MkAgent", "value": "test:verified"}
        }

    def test_canonical_bytes_are_stable(self):
        self.assertEqual(canonical_bytes({"b": 2, "a": 1}), b'{"a":1,"b":2}')
        self.assertTrue(content_hash({"a": 1}).startswith("sha256:"))

    def test_authorized_resolution_returns_projection(self):
        result = Resolver(publisher="did:key:z6MkPublisher", verify_signature=lambda _: True).resolve(self.request, {"claims": ["hello"]})
        self.assertEqual(result["resolution_state"], "trusted_projection")
        self.assertEqual(result["payload"]["claims"], ["hello"])
        self.assertTrue(result["permissions"]["capability_checked"])

    def test_replay_is_rejected(self):
        resolver = Resolver(publisher="did:key:z6MkPublisher", verify_signature=lambda _: True)
        resolver.resolve(self.request, {})
        with self.assertRaises(ValidationError): resolver.resolve(self.request, {})

    def test_missing_capability_denies_without_leaking_projection(self):
        request = dict(self.request, capabilities=[])
        result = Resolver(publisher="did:key:z6MkPublisher", verify_signature=lambda _: True).resolve(request, {"secret": "no"})
        self.assertEqual(result["resolution_state"], "denied")
        self.assertEqual(result["payload"], {})

    def test_revocation_denies_later_resolution(self):
        resolver = Resolver(publisher="did:key:z6MkPublisher", verify_signature=lambda _: True)
        resolver.revoke("cap:1")
        result = resolver.resolve(self.request, {"secret": "no"})
        self.assertEqual(result["resolution_state"], "denied")

    def test_receipts_close_without_overwriting_history(self):
        receipt = Receipt("receipt:1", "https://example.com/article/123", "Resolve the pointer.", None, "open")
        closed = receipt.close("Resolved a public projection.", evidence=("sha256:example",))
        self.assertEqual(receipt.status, "open")
        self.assertEqual(closed.status, "closed")
        with self.assertRaises(ValidationError): closed.close("overwrite")

    def test_signed_ed25519_request_and_http_resolution(self):
        signer = Ed25519Signer.generate("did:key:agent")
        unsigned = dict(self.request)
        unsigned.pop("signature")
        unsigned["nonce"] = "signed-http-nonce"
        unsigned["signature"] = signer.sign({k: unsigned[k] for k in unsigned})
        resolver = Resolver(
            publisher="did:key:publisher",
            verify_signature=Ed25519Verifier({"did:key:agent": signer.public_key_b64}),
        )
        server = make_server("127.0.0.1", 0, resolver, {self.request["pointer"]: {"message": "resolved"}})
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            body = json.dumps(unsigned).encode()
            request = Request(f"http://127.0.0.1:{server.server_address[1]}/v1/resolve", data=body, headers={"Content-Type": "application/json"})
            response = json.loads(urlopen(request, timeout=2).read())
            self.assertEqual(response["resolution_state"], "trusted_projection")
            self.assertEqual(response["payload"]["message"], "resolved")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_demo_signature_fails_closed_by_default(self):
        request = dict(self.request, signature={"algorithm": "demo", "key_ref": "x", "value": "demo:unsigned"})
        with self.assertRaises(ValidationError): Resolver(publisher="did:key:z6MkPublisher").resolve(request, {})


if __name__ == "__main__": unittest.main()

import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from humain_api import Ed25519Signer, Ed25519Verifier, Resolver, ValidationError
from humain_api.state import SQLiteStateStore


class DurableStateTests(unittest.TestCase):
    def setUp(self):
        now = datetime.now(timezone.utc)
        self.issued = (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
        self.expires = (now + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
        self.agent = Ed25519Signer.generate("did:key:agent")
        self.publisher = Ed25519Signer.generate("did:key:publisher")
        self.request: dict[str, object] = {
            "schema": "humain.resolve.request.v1", "message_id": "request:durable",
            "pointer": "https://example.com/durable", "requester": "did:key:agent",
            "audience": "did:key:publisher", "action": "resolve", "nonce": "durable-1",
            "created_at": now.isoformat().replace("+00:00", "Z"),
            "capabilities": [{
                "capability_id": "cap:durable", "issuer": "did:key:publisher",
                "subject": "did:key:agent", "audience": "did:key:publisher",
                "pointer": "https://example.com/durable", "action": "resolve",
                "issued_at": self.issued, "expires_at": self.expires, "revoked": False,
            }],
        }
        self.request["signature"] = self.agent.sign(dict(self.request))

    def _resolver(self, store):
        return Resolver(
            publisher="did:key:publisher", mode="production",
            verify_signature=Ed25519Verifier({"did:key:agent": self.agent.public_key_b64}),
            response_signer=self.publisher, state_store=store,
        )

    def test_nonce_survives_resolver_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "state.sqlite")
            first = self._resolver(SQLiteStateStore(path))
            first.resolve(self.request, {"ok": True})
            second = self._resolver(SQLiteStateStore(path))
            with self.assertRaises(ValidationError):
                second.resolve(self.request, {"ok": True})

    def test_concurrent_duplicate_nonce_has_one_winner(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteStateStore(str(Path(directory) / "state.sqlite"))
            resolvers = [self._resolver(store), self._resolver(store)]
            results = []
            lock = threading.Lock()

            def run(resolver):
                try:
                    result = resolver.resolve(self.request, {"ok": True})
                    value = result["resolution_state"]
                except ValidationError:
                    value = "rejected"
                with lock:
                    results.append(value)

            threads = [threading.Thread(target=run, args=(resolver,)) for resolver in resolvers]
            for thread in threads: thread.start()
            for thread in threads: thread.join()
            self.assertEqual(sorted(results), ["rejected", "trusted_projection"])

    def test_revocation_and_receipt_survive_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "state.sqlite")
            store = SQLiteStateStore(path)
            first = self._resolver(store)
            first.revoke("cap:durable")
            revoked_request = dict(self.request, nonce="revoked-nonce")
            revoked_request["signature"] = self.agent.sign({k: revoked_request[k] for k in revoked_request if k != "signature"})
            denied = first.resolve(revoked_request, {"secret": "hidden"})
            self.assertEqual(denied["resolution_state"], "denied")
            self.assertEqual(len(SQLiteStateStore(path).receipts()), 1)
            second = self._resolver(SQLiteStateStore(path))
            revoked_request_again = dict(self.request, nonce="revoked-nonce-2")
            revoked_request_again["signature"] = self.agent.sign({k: revoked_request_again[k] for k in revoked_request_again if k != "signature"})
            denied_again = second.resolve(revoked_request_again, {"secret": "hidden"})
            self.assertEqual(denied_again["resolution_state"], "denied")


if __name__ == "__main__": unittest.main()

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from humain_api.capability import CapabilityIssuer, CapabilityRegistry
from humain_api.crypto import Ed25519Signer
from humain_api.models import Capability, ValidationError
from humain_api.resolver import Resolver


class CapabilityAuthorityTests(unittest.TestCase):
    def setUp(self):
        now = datetime.now(timezone.utc)
        self.issued = (now - timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
        self.expires = (now + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
        self.capability = {
            "capability_id": "cap:signed-1",
            "issuer": "did:key:issuer",
            "subject": "did:key:agent",
            "audience": "did:key:publisher",
            "pointer": "https://example.com/article/123",
            "action": "resolve",
            "issued_at": self.issued,
            "expires_at": self.expires,
            "revoked": False,
        }

    def test_issuer_signs_and_registry_verifies_capability(self):
        signer = Ed25519Signer.generate("did:key:issuer")
        issued = CapabilityIssuer(signer).issue(self.capability)
        self.assertEqual(issued["schema"], "humain.capability.v1")
        self.assertTrue(CapabilityRegistry({"did:key:issuer": signer.public_key_b64}).verify(issued))

    def test_registry_rejects_tampered_or_unknown_issuer(self):
        signer = Ed25519Signer.generate("did:key:issuer")
        issued = CapabilityIssuer(signer).issue(self.capability)
        tampered = dict(issued, action="act")
        registry = CapabilityRegistry({"did:key:issuer": signer.public_key_b64})
        self.assertFalse(registry.verify(tampered))
        unknown = dict(issued, issuer="did:key:other")
        self.assertFalse(registry.verify(unknown))

    def test_resolver_requires_registry_when_configured(self):
        issuer = Ed25519Signer.generate("did:key:issuer")
        agent = Ed25519Signer.generate("did:key:agent")
        issued = CapabilityIssuer(issuer).issue(self.capability)
        request = {
            "schema": "humain.resolve.request.v1", "message_id": "request:authority",
            "pointer": self.capability["pointer"], "requester": self.capability["subject"],
            "audience": self.capability["audience"], "action": "resolve", "nonce": "authority-nonce",
            "created_at": self.issued, "capabilities": [issued],
        }
        request["signature"] = agent.sign({k: request[k] for k in request})
        resolver = Resolver(
            publisher=self.capability["audience"],
            verify_signature=lambda value, signature: agent.verify(value, signature),
            capability_registry=CapabilityRegistry({issuer.key_ref: issuer.public_key_b64}),
        )
        result = resolver.resolve(request, {"message": "ok"})
        self.assertEqual(result["resolution_state"], "trusted_projection")

        forged = dict(issued, action="act")
        request["nonce"] = "authority-forged-nonce"
        request["capabilities"] = [forged]
        request["signature"] = agent.sign({k: request[k] for k in request if k != "signature"})
        denied = resolver.resolve(request, {"message": "no"})
        self.assertEqual(denied["resolution_state"], "denied")


if __name__ == "__main__":
    unittest.main()

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from humain_api.crypto import Ed25519Signer
from humain_api.rendezvous import Participant, RendezvousBroker


class TestRendezvous(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
        self.broker = RendezvousBroker(now=lambda: self.now, ttl_seconds=60, ping_ttl_seconds=10)
        self.browser = Ed25519Signer.generate("browser:test")
        self.openhome = Ed25519Signer.generate("openhome:test")
        self.start = self.broker.start(
            origin="https://story.markets",
            pathname="/",
            event_id="evt-1",
            browser=Participant("browser", "browser:test", self.browser.public_key_b64),
            openhome=Participant("openhome", "openhome:test", self.openhome.public_key_b64),
        )
        self.rid = self.start["rendezvous_id"]

    def claim(self, role, signer, nonce):
        observed = "2026-08-11T12:00:00Z"
        return {
            "schema": "humain.rendezvous.v1",
            "rendezvous_id": self.rid,
            "role": role,
            "nonce": nonce,
            "origin": "https://story.markets",
            "pathname": "/",
            "event_id": "evt-1",
            "observed_at": observed,
        }, observed, signer.sign({
            "schema": "humain.rendezvous.v1",
            "rendezvous_id": self.rid,
            "role": role,
            "nonce": nonce,
            "origin": "https://story.markets",
            "pathname": "/",
            "event_id": "evt-1",
            "observed_at": observed,
        })

    def complete_claims(self):
        for role, signer, nonce in (
            ("browser", self.browser, self.start["browser_challenge"]),
            ("openhome", self.openhome, self.start["openhome_challenge"]),
        ):
            _, observed, signature = self.claim(role, signer, nonce)
            self.broker.submit_claim(rendezvous_id=self.rid, role=role, nonce=nonce, signature=signature, observed_at=observed)

    def complete_pings(self):
        ping = self.broker.issue_ping(self.rid)
        for role, signer in (("browser", self.browser), ("openhome", self.openhome)):
            observed = "2026-08-11T12:00:00Z"
            value = {"schema": "humain.rendezvous.v1", "rendezvous_id": self.rid, "ping_id": ping["ping_id"], "nonce": ping["nonce"], "role": role, "observed_at": observed}
            self.broker.answer_ping(rendezvous_id=self.rid, role=role, ping_id=ping["ping_id"], nonce=ping["nonce"], signature=signer.sign(value), observed_at=observed)

    def complete_receipt(self):
        receipt_hash = "sha256:" + "a" * 64
        for role, signer in (("browser", self.browser), ("openhome", self.openhome)):
            value = {"schema": "humain.rendezvous.v1", "rendezvous_id": self.rid, "role": role, "receipt_hash": receipt_hash, "scope": {"origin": "https://story.markets", "pathname": "/"}}
            self.broker.submit_shared_receipt(rendezvous_id=self.rid, role=role, receipt_hash=receipt_hash, signature=signer.sign(value))

    def test_complete_flow_issues_public_single_use_grant(self):
        self.complete_claims()
        self.complete_pings()
        self.complete_receipt()
        self.broker.bind(rendezvous_id=self.rid, binding_code=self.start["binding_code"])
        grant = self.broker.issue_grant(self.rid)
        self.assertEqual(grant["scope"]["action"], "speak_public_greeting")
        self.assertFalse(grant["private_context"])
        with self.assertRaises(PermissionError):
            self.broker.issue_grant(self.rid)

    def test_claim_replay_is_rejected(self):
        _, observed, signature = self.claim("browser", self.browser, self.start["browser_challenge"])
        self.broker.submit_claim(rendezvous_id=self.rid, role="browser", nonce=self.start["browser_challenge"], signature=signature, observed_at=observed)
        with self.assertRaises(PermissionError):
            self.broker.submit_claim(rendezvous_id=self.rid, role="browser", nonce=self.start["browser_challenge"], signature=signature, observed_at=observed)

    def test_scope_tampering_and_wrong_binding_fail(self):
        with self.assertRaises(ValueError):
            self.broker.start(origin="https://story.markets", pathname="/?private=1", event_id="evt", browser=Participant("browser", "b", self.browser.public_key_b64), openhome=Participant("openhome", "o", self.openhome.public_key_b64))
        self.complete_claims()
        with self.assertRaises(PermissionError):
            self.broker.bind(rendezvous_id=self.rid, binding_code="000000")

    def test_mismatched_shared_receipts_fail(self):
        self.complete_claims()
        for role, signer, receipt_hash in (("browser", self.browser, "sha256:" + "a" * 64), ("openhome", self.openhome, "sha256:" + "b" * 64)):
            value = {"schema": "humain.rendezvous.v1", "rendezvous_id": self.rid, "role": role, "receipt_hash": receipt_hash, "scope": {"origin": "https://story.markets", "pathname": "/"}}
            if role == "browser":
                self.broker.submit_shared_receipt(rendezvous_id=self.rid, role=role, receipt_hash=receipt_hash, signature=signer.sign(value))
            else:
                with self.assertRaises(PermissionError):
                    self.broker.submit_shared_receipt(rendezvous_id=self.rid, role=role, receipt_hash=receipt_hash, signature=signer.sign(value))

    def test_corroborated_observations_are_required_in_tripwire_mode(self):
        broker = RendezvousBroker(now=lambda: self.now, ttl_seconds=60, ping_ttl_seconds=10, require_observation=True)
        start = broker.start(origin="https://story.markets", pathname="/", event_id="evt-tripwire", browser=Participant("browser", "browser:test", self.browser.public_key_b64), openhome=Participant("openhome", "openhome:test", self.openhome.public_key_b64))
        rid = start["rendezvous_id"]
        browser_observation = {"rendezvous_id": rid, "scanner": "browser", "observed_at": "2026-08-11T12:00:01Z", "service_uuid": "12345678-1234-5678-1234-56789abcdef0", "advertisement_commitment": "hmac:rotating-token", "rssi_bucket": -45, "sample_count": 3}
        openhome_observation = {**browser_observation, "scanner": "openhome", "observed_at": "2026-08-11T12:00:02Z"}
        broker.submit_observation(**browser_observation)
        result = broker.submit_observation(**openhome_observation)
        self.assertEqual(result["state"], "corroborated_candidate_near")
        self.assertTrue(result["requirements"]["corroborated_candidate_near"])

        mismatched = broker.start(origin="https://story.markets", pathname="/", event_id="evt-tripwire-2", browser=Participant("browser", "browser:test", self.browser.public_key_b64), openhome=Participant("openhome", "openhome:test", self.openhome.public_key_b64))
        broker.submit_observation(rendezvous_id=mismatched["rendezvous_id"], scanner="browser", observed_at="2026-08-11T12:00:01Z", service_uuid="service-a", advertisement_commitment="hmac:a", rssi_bucket=-45)
        flagged = broker.submit_observation(rendezvous_id=mismatched["rendezvous_id"], scanner="openhome", observed_at="2026-08-11T12:00:02Z", service_uuid="service-a", advertisement_commitment="hmac:b", rssi_bucket=-45)
        self.assertEqual(flagged["state"], "quarantined")
        self.assertEqual(flagged["tripwires"][0]["reason"], "scanner_observation_mismatch")
        with self.assertRaises(PermissionError):
            broker.issue_grant(mismatched["rendezvous_id"])

    def test_expired_ping_is_rejected(self):
        ping = self.broker.issue_ping(self.rid)
        self.now += timedelta(seconds=11)
        value = {"schema": "humain.rendezvous.v1", "rendezvous_id": self.rid, "ping_id": ping["ping_id"], "nonce": ping["nonce"], "role": "browser", "observed_at": "2026-08-11T12:00:11Z"}
        with self.assertRaises(PermissionError):
            self.broker.answer_ping(rendezvous_id=self.rid, role="browser", ping_id=ping["ping_id"], nonce=ping["nonce"], signature=self.browser.sign(value), observed_at="2026-08-11T12:00:11Z")


if __name__ == "__main__":
    unittest.main()

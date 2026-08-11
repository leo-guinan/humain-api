import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from humain_api.crypto import Ed25519Signer
from humain_api.proximity import Pairing, PresenceBroker, sign_challenge


class ProximityTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.fromisoformat("2026-08-10T11:59:30+00:00")
        self.signer = Ed25519Signer.generate("device:leo-phone")
        self.broker = PresenceBroker(now=lambda: self.now, window_seconds=5, min_observations=3, enter_rssi=-65, exit_rssi=-72, freshness_seconds=30)
        self.broker.pair(Pairing("leo-phone", "device:leo-phone", self.signer.public_key_b64))

    def signed(self, index, rssi=-55, minute=0):
        timestamp = f"2026-08-10T11:59:0{index}Z"
        signature = sign_challenge(self.signer, alias="leo-phone", challenge=f"nonce-{index}", purpose="presence_signal", observed_at=timestamp)
        return self.broker.observe_signed_presence(alias="leo-phone", rssi=rssi, observed_at=timestamp, challenge=f"nonce-{index}", signature=signature)

    def test_unsigned_candidate_never_becomes_verified(self):
        result = self.broker.observe_advertisement("leo-phone", -50, "2026-08-10T11:59:00Z")
        self.assertEqual(result["presence_state"], "candidate_near")
        self.assertFalse(result["flow_eligible"])

    def test_three_fresh_signed_observations_become_verified(self):
        self.signed(0)
        self.signed(1)
        result = self.signed(2)
        self.assertEqual(result["presence_state"], "near_verified")
        self.assertTrue(result["challenge_verified"])
        self.assertTrue(result["flow_eligible"])

    def test_replay_stale_unknown_and_revoked_are_rejected(self):
        signature = sign_challenge(self.signer, alias="leo-phone", challenge="replay", purpose="presence_signal", observed_at="2026-08-10T11:59:00Z")
        self.broker.observe_signed_presence(alias="leo-phone", rssi=-55, observed_at="2026-08-10T11:59:00Z", challenge="replay", signature=signature)
        with self.assertRaises(PermissionError):
            self.broker.observe_signed_presence(alias="leo-phone", rssi=-55, observed_at="2026-08-10T11:59:00Z", challenge="replay", signature=signature)
        with self.assertRaises(PermissionError):
            self.broker.observe_signed_presence(alias="leo-phone", rssi=-55, observed_at="2026-08-10T11:57:00Z", challenge="stale", signature=sign_challenge(self.signer, alias="leo-phone", challenge="stale", purpose="presence_signal", observed_at="2026-08-10T11:57:00Z"))
        with self.assertRaises(PermissionError):
            self.broker.observe_signed_presence(alias="unknown", rssi=-55, observed_at="2026-08-10T11:59:00Z", challenge="x", signature=signature)
        self.broker.revoke("leo-phone")
        with self.assertRaises(PermissionError):
            self.broker.observe_signed_presence(alias="leo-phone", rssi=-55, observed_at="2026-08-10T11:59:00Z", challenge="revoked", signature=sign_challenge(self.signer, alias="leo-phone", challenge="revoked", purpose="presence_signal", observed_at="2026-08-10T11:59:00Z"))

    def test_weak_signal_does_not_verify_and_departure_is_absent(self):
        for index in range(3):
            result = self.signed(index, rssi=-75)
        self.assertEqual(result["presence_state"], "absent")
        self.assertFalse(result["flow_eligible"])


if __name__ == "__main__":
    unittest.main()

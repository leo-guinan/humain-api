import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from humain_api.ble_adapter import advertisement_commitment, advertisement_material


class BleCommitmentTests(unittest.TestCase):
    def advertisement(self, payload=b"device-a"):
        return SimpleNamespace(
            service_uuids=["12345678-1234-5678-1234-56789abcdef0"],
            manufacturer_data={76: payload},
            service_data={},
        )

    def test_commitment_is_stable_and_hides_raw_payload(self):
        commitment, quality = advertisement_commitment(self.advertisement(), b"rendezvous-secret")
        again, again_quality = advertisement_commitment(self.advertisement(), b"rendezvous-secret")
        self.assertEqual(commitment, again)
        self.assertEqual(quality, "payload")
        self.assertEqual(again_quality, "payload")
        self.assertNotIn("device-a", commitment)
        self.assertNotIn("76", commitment)

    def test_payload_change_changes_commitment(self):
        first, _ = advertisement_commitment(self.advertisement(b"device-a"), b"rendezvous-secret")
        second, _ = advertisement_commitment(self.advertisement(b"device-b"), b"rendezvous-secret")
        self.assertNotEqual(first, second)

    def test_uuid_only_material_is_marked_weak(self):
        advertisement = SimpleNamespace(service_uuids=["service"], manufacturer_data={}, service_data={})
        material = advertisement_material(advertisement)
        commitment, quality = advertisement_commitment(advertisement, b"rendezvous-secret")
        self.assertEqual(material["commitment_quality"], "uuid_only")
        self.assertEqual(quality, "uuid_only")
        self.assertTrue(commitment.startswith("hmac:"))


if __name__ == "__main__":
    unittest.main()

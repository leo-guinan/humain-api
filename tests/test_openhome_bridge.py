import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from humain_api.openhome_bridge import OpenHomeBridge, SCHEMA


def context_event(event_id="evt-1", pointer="https://story.markets/"):
    return {
        "schema": SCHEMA,
        "event_id": event_id,
        "pointer": pointer,
        "occurred_at": "2026-08-10T17:00:00Z",
        "client_id": "bipu-extension-demo",
    }


class OpenHomeBridgeTests(unittest.TestCase):
    def test_requires_explicit_arm_and_emits_public_only_speech(self):
        bridge = OpenHomeBridge()
        with self.assertRaises(PermissionError):
            bridge.submit_event(context_event())
        bridge.arm("desk-demo", ttl_seconds=60)
        result = bridge.submit_event(context_event())
        self.assertEqual(result["status"], "queued")
        envelope = bridge.next_message()["speech_envelope"]
        self.assertEqual(envelope["resolution_state"], "public_only")
        self.assertFalse(envelope["permissions"]["private_context"])
        self.assertEqual(envelope["permissions"]["actions"], [])
        self.assertIn("AI-generated", envelope["speech_text"])
        self.assertIn("underlying_response", envelope["receipt"])

    def test_rejects_unknown_pointer_and_raw_context(self):
        bridge = OpenHomeBridge()
        bridge.arm("desk-demo")
        with self.assertRaises(PermissionError):
            bridge.submit_event(context_event(pointer="https://evil.example/"))
        raw = context_event(event_id="evt-raw")
        raw["page_text"] = "private page content"
        with self.assertRaises(PermissionError):
            bridge.submit_event(raw)

    def test_duplicate_and_debounce_do_not_speak_twice(self):
        bridge = OpenHomeBridge()
        bridge.arm("desk-demo")
        self.assertEqual(bridge.submit_event(context_event())["status"], "queued")
        self.assertEqual(bridge.submit_event(context_event())["status"], "duplicate")
        bridge.next_message()
        self.assertEqual(bridge.submit_event(context_event("evt-2"))["status"], "debounced")
        self.assertEqual(bridge.next_message()["status"], "empty")

    def test_mute_stops_delivery(self):
        bridge = OpenHomeBridge()
        bridge.arm("desk-demo")
        bridge.mute()
        self.assertEqual(bridge.next_message()["status"], "disabled")
        with self.assertRaises(PermissionError):
            bridge.submit_event(context_event())


if __name__ == "__main__":
    unittest.main()

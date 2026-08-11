import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from humain_api.openhome_bridge import OpenHomeBridge, SCHEMA
from humain_api.crypto import Ed25519Signer
from humain_api.rendezvous import Participant


def context_event(event_id="evt-1", pointer="https://story.markets/"):
    return {
        "schema": SCHEMA,
        "event_id": event_id,
        "pointer": pointer,
        "occurred_at": "2026-08-10T17:00:00Z",
        "client_id": "bipu-extension-demo",
    }


def near_presence():
    return {
        "schema": "humain.proximity.presence.v1",
        "presence_state": "near_verified",
        "flow_eligible": True,
        "paired_device": "leo-phone",
        "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


class OpenHomeBridgeTests(unittest.TestCase):
    def test_requires_explicit_arm_and_emits_public_only_speech(self):
        bridge = OpenHomeBridge()
        with self.assertRaises(PermissionError):
            bridge.submit_event(context_event())
        bridge.arm("desk-demo", ttl_seconds=60)
        bridge.update_presence(near_presence())
        result = bridge.submit_event(context_event())
        self.assertEqual(result["status"], "queued")
        envelope = bridge.next_message()["speech_envelope"]
        self.assertEqual(envelope["resolution_state"], "public_only")
        self.assertFalse(envelope["permissions"]["private_context"])
        self.assertEqual(envelope["permissions"]["actions"], [])
        self.assertEqual(envelope["speech_text"], "Welcome to story markets.")
        self.assertIn("underlying_response", envelope["receipt"])

    def test_presence_is_required_before_pointer_flow(self):
        bridge = OpenHomeBridge()
        bridge.arm("desk-demo")
        with self.assertRaises(PermissionError):
            bridge.submit_event(context_event())
        stale = near_presence()
        stale["observed_at"] = "2020-01-01T00:00:00Z"
        with self.assertRaises(PermissionError):
            bridge.update_presence(stale)

    def test_rejects_unknown_pointer_and_raw_context(self):
        bridge = OpenHomeBridge()
        bridge.arm("desk-demo")
        bridge.update_presence(near_presence())
        with self.assertRaises(PermissionError):
            bridge.submit_event(context_event(pointer="https://evil.example/"))
        raw = context_event(event_id="evt-raw")
        raw["page_text"] = "private page content"
        with self.assertRaises(PermissionError):
            bridge.submit_event(raw)

    def test_duplicate_and_debounce_do_not_speak_twice(self):
        bridge = OpenHomeBridge()
        bridge.arm("desk-demo")
        bridge.update_presence(near_presence())
        self.assertEqual(bridge.submit_event(context_event())["status"], "queued")
        self.assertEqual(bridge.submit_event(context_event())["status"], "duplicate")
        bridge.next_message()
        self.assertEqual(bridge.submit_event(context_event("evt-2"))["status"], "debounced")
        self.assertEqual(bridge.next_message()["status"], "empty")

    def test_rendezvous_requires_server_provisioned_openhome_identity(self):
        browser = Ed25519Signer.generate("browser:test")
        bridge = OpenHomeBridge()
        bridge.arm("desk-demo")
        request = {"origin": "https://story.markets", "pathname": "/", "event_id": "evt-rv", "browser": {"key_ref": browser.key_ref, "public_key_b64": browser.public_key_b64}, "openhome": {"key_ref": "attacker", "public_key_b64": browser.public_key_b64}}
        with self.assertRaises(PermissionError):
            bridge.start_rendezvous(request)

        device = Ed25519Signer.generate("openhome:test")
        configured = OpenHomeBridge(openhome_identity=Participant("openhome", device.key_ref, device.public_key_b64))
        configured.arm("desk-demo")
        started = configured.start_rendezvous({"origin": "https://story.markets", "pathname": "/", "event_id": "evt-rv", "browser": {"key_ref": browser.key_ref, "public_key_b64": browser.public_key_b64}})
        self.assertEqual(started["scope"]["origin"], "https://story.markets")
        pending = configured.rendezvous_action("pending", {"key_ref": device.key_ref})
        self.assertEqual(len(pending["rendezvous"]), 1)

    def test_mute_stops_delivery(self):
        bridge = OpenHomeBridge()
        bridge.arm("desk-demo")
        bridge.update_presence(near_presence())
        bridge.mute()
        self.assertEqual(bridge.next_message()["status"], "disabled")
        with self.assertRaises(PermissionError):
            bridge.submit_event(context_event())


if __name__ == "__main__":
    unittest.main()

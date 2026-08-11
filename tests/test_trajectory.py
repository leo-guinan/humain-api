import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from humain_api.trajectory import compare_trajectories, compress_events


BASE = [
    {"event_type": "resolve.request", "occurred_at": "2026-08-10T12:00:00Z", "nonce": "n1"},
    {"event_type": "resolve.response", "occurred_at": "2026-08-10T12:00:03Z", "nonce": "n1"},
    {"event_type": "memetic.render", "occurred_at": "2026-08-10T12:00:04Z", "nonce": "n1"},
    {"event_type": "receipt.close", "occurred_at": "2026-08-10T12:01:00Z", "nonce": "n1"},
]


class TrajectoryTests(unittest.TestCase):
    def test_compression_is_deterministic_and_ordered(self):
        first = compress_events(BASE, window_id="w1").to_dict()
        second = compress_events(BASE, window_id="w1").to_dict()
        self.assertEqual(first, second)
        self.assertEqual(first["event_type_runs"], [["resolve.request", 1], ["resolve.response", 1], ["memetic.render", 1], ["receipt.close", 1]])
        self.assertGreater(first["compression_ratio"], 0)
        self.assertIn(first["compression_status"], {"compressed", "expanded"})
        self.assertTrue(first["provenance"]["falsifier"])

    def test_payload_change_does_not_create_drift(self):
        current = [dict(event, payload={"different": True}) for event in BASE]
        comparison = compare_trajectories(compress_events(current, window_id="w2"), compress_events(BASE, window_id="w1"))
        self.assertEqual(comparison["classification"], "replay_suspect")
        self.assertTrue(comparison["features"]["nonce_overlap"])

    def test_self_comparison_is_continuation(self):
        capsule = compress_events(BASE, window_id="w1")
        comparison = compare_trajectories(capsule, capsule)
        self.assertEqual(comparison["classification"], "continuation")

    def test_new_branch_is_not_silently_trusted(self):
        current = [
            {"event_type": "resolve.request", "occurred_at": "2026-08-10T13:00:00Z", "nonce": "n2"},
            {"event_type": "capability.refresh", "occurred_at": "2026-08-10T13:00:01Z", "nonce": "n2"},
            {"event_type": "resolve.response", "occurred_at": "2026-08-10T13:00:02Z", "nonce": "n2"},
            {"event_type": "human.confirm", "occurred_at": "2026-08-10T13:01:00Z", "nonce": "n2"},
        ]
        comparison = compare_trajectories(compress_events(current, window_id="w2"), compress_events(BASE, window_id="w1"))
        self.assertIn(comparison["classification"], {"novel_branch", "drift"})
        self.assertNotEqual(comparison["classification"], "continuation")

    def test_long_repeated_window_compresses(self):
        events = []
        for index in range(40):
            events.append({"event_type": "resolve.request", "occurred_at": f"2026-08-10T14:{index:02d}:00Z", "nonce": f"n{index}"})
        for index in range(40, 80):
            events.append({"event_type": "resolve.response", "occurred_at": f"2026-08-10T15:{index - 40:02d}:00Z", "nonce": f"n{index}"})
        capsule = compress_events(events, window_id="long")
        self.assertEqual(capsule.value["compression_status"], "compressed")
        self.assertLess(len(capsule.value["event_type_runs"]), capsule.value["event_count"])

    def test_timing_shift_is_measured(self):
        shifted = [
            {"event_type": "resolve.request", "occurred_at": "2026-08-10T12:00:00Z", "nonce": "shift"},
            {"event_type": "resolve.response", "occurred_at": "2026-08-10T12:20:00Z", "nonce": "shift"},
            {"event_type": "memetic.render", "occurred_at": "2026-08-10T12:40:00Z", "nonce": "shift"},
            {"event_type": "receipt.close", "occurred_at": "2026-08-10T13:00:00Z", "nonce": "shift"},
        ]
        comparison = compare_trajectories(compress_events(shifted, window_id="timing"), compress_events(BASE, window_id="w1"))
        self.assertGreater(comparison["features"]["timing_distance"], 0)

    def test_cold_start_is_insufficient_pattern(self):
        short = compress_events(BASE[:2], window_id="short")
        comparison = compare_trajectories(short, short)
        self.assertEqual(comparison["classification"], "insufficient_pattern")

    def test_reordered_path_is_not_identical(self):
        reordered = [BASE[0], BASE[2], BASE[1], BASE[3]]
        comparison = compare_trajectories(compress_events(reordered, window_id="w2"), compress_events(BASE, window_id="w1"))
        self.assertGreater(comparison["novelty"], 0)


if __name__ == "__main__":
    unittest.main()

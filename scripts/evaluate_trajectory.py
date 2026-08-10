#!/usr/bin/env python3
"""Evaluate trajectory signals on a deterministic mixed movement fixture."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from humain_api.trajectory import compare_trajectories, compress_events


def event(kind: str, minute: int, nonce: str, *, state: str = "public_only") -> dict:
    return {
        "event_type": kind,
        "occurred_at": f"2026-08-10T16:{minute:02d}:00Z",
        "pointer_class": "public-web",
        "state": state,
        "action": "resolve" if kind.startswith("resolve") else "render",
        "scope": "public",
        "nonce": nonce,
    }


def paths() -> dict[str, list[dict]]:
    return {
        "baseline": [
            event("resolve.request", 0, "base-1"),
            event("resolve.response", 1, "base-1"),
            event("memetic.render", 2, "base-1"),
            event("receipt.close", 3, "base-1"),
        ],
        "continuation": [
            event("resolve.request", 10, "cont-1"),
            event("resolve.response", 11, "cont-1"),
            event("memetic.render", 12, "cont-1"),
            event("receipt.close", 13, "cont-1"),
        ],
        "novel_branch": [
            event("resolve.request", 20, "novel-1"),
            event("capability.refresh", 21, "novel-1", state="denied"),
            event("human.confirm", 22, "novel-1", state="denied"),
            event("resolve.response", 23, "novel-1", state="public_only"),
            event("memetic.render", 24, "novel-1"),
        ],
        "recovery": [
            event("resolve.request", 30, "recover-1"),
            event("resolve.response", 31, "recover-1"),
            event("memetic.render", 32, "recover-1"),
            event("receipt.close", 33, "recover-1"),
        ],
        "replay": [
            event("resolve.request", 0, "base-1"),
            event("resolve.response", 1, "base-1"),
            event("memetic.render", 2, "base-1"),
            event("receipt.close", 3, "base-1"),
        ],
    }


def main() -> None:
    raw = paths()
    capsules = {name: compress_events(events, window_id=name, source_label="mixed-fixture") for name, events in raw.items()}
    comparisons = {}
    for name in ("continuation", "novel_branch", "recovery", "replay"):
        comparisons[name] = compare_trajectories(capsules[name], capsules["baseline"])

    expected = {
        "continuation": "continuation",
        "novel_branch": {"novel_branch", "drift"},
        "recovery": "continuation",
        "replay": "replay_suspect",
    }
    normal_cases = {"continuation", "recovery"}
    abnormal_cases = {"novel_branch", "replay"}
    false_friction_cases = [name for name in normal_cases if comparisons[name]["classification"] != "continuation"]
    missed_drift_cases = [name for name in abnormal_cases if comparisons[name]["classification"] == "continuation"]
    expectation_misses = [
        name for name, expected_value in expected.items()
        if comparisons[name]["classification"] not in (expected_value if isinstance(expected_value, set) else {expected_value})
    ]
    report = {
        "schema": "humain.trajectory.evaluation.v1",
        "fixture": "mixed-normal-novel-recovery-replay.v1",
        "baseline_capsule": capsules["baseline"].to_dict(),
        "cases": {name: {"comparison": comparisons[name], "capsule": capsules[name].to_dict()} for name in comparisons},
        "metrics": {
            "normal_case_count": len(normal_cases),
            "abnormal_case_count": len(abnormal_cases),
            "false_friction_count": len(false_friction_cases),
            "false_friction_rate": len(false_friction_cases) / len(normal_cases),
            "missed_drift_count": len(missed_drift_cases),
            "missed_drift_rate": len(missed_drift_cases) / len(abnormal_cases),
            "expectation_misses": expectation_misses,
        },
        "provenance": {
            "method": "deterministic-trajectory-evaluator",
            "falsifier": "a matched normal continuation or recovery path must not be challenged, and a known novel/replay path must not be accepted as continuation",
            "synthetic": True,
        },
    }
    output = ROOT / "reports" / "trajectory-evaluation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"output": str(output), "metrics": report["metrics"], "classifications": {name: result["classification"] for name, result in comparisons.items()}}, sort_keys=True))
    if expectation_misses:
        raise SystemExit("trajectory evaluation expectations failed")


if __name__ == "__main__":
    main()

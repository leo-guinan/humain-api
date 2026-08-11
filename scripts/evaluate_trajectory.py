#!/usr/bin/env python3
"""Evaluate trajectory signals on a deterministic adversarial movement fixture."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from humain_api.trajectory import compare_trajectories, compress_events


def event(kind: str, minute: int, nonce: str, *, state: str = "public_only") -> dict:
    hour, minute = divmod(minute, 60)
    return {
        "event_type": kind,
        "occurred_at": f"2026-08-10T{16 + hour:02d}:{minute:02d}:00Z",
        "pointer_class": "public-web",
        "state": state,
        "action": "resolve" if kind.startswith("resolve") else "render",
        "scope": "public",
        "nonce": nonce,
    }


def sequence(nonce: str, start: int = 0, *, spacing: int = 1) -> list[dict]:
    return [
        event("resolve.request", start, nonce),
        event("resolve.response", start + spacing, nonce),
        event("memetic.render", start + spacing * 2, nonce),
        event("receipt.close", start + spacing * 3, nonce),
    ]


def paths() -> dict[str, list[dict]]:
    baseline = sequence("base-1")
    return {
        "baseline": baseline,
        "continuation": sequence("cont-1", 10),
        "payload_mutation": [dict(item, payload={"changed": True}) for item in sequence("payload-1", 20)],
        "timing_shift": sequence("timing-1", 30, spacing=20),
        "partial_replay": [
            dict(item, nonce="base-1" if index == 0 else f"partial-{index}")
            for index, item in enumerate(sequence("partial-unused", 50))
        ],
        "mimicry": sequence("mimic-1", 60),
        "novel_branch": [
            event("resolve.request", 70, "novel-1"),
            event("capability.refresh", 71, "novel-1", state="denied"),
            event("human.confirm", 72, "novel-1", state="denied"),
            event("resolve.response", 73, "novel-1", state="public_only"),
            event("memetic.render", 74, "novel-1"),
        ],
        "drift": [
            event("observe.external", 80, "drift-1", state="unavailable"),
            event("attest.request", 81, "drift-1", state="denied"),
            event("action.preview", 82, "drift-1", state="denied"),
            event("human.confirm", 83, "drift-1", state="denied"),
        ],
        "recovery": sequence("recover-1", 90),
        "replay": [dict(item, nonce="base-1") for item in sequence("replay-unused", 0)],
        "cold_start": sequence("cold-1", 100)[:2],
    }


EXPECTED = {
    "continuation": {"classification": "continuation", "policy": "normal"},
    "payload_mutation": {"classification": "continuation", "policy": "normal"},
    "timing_shift": {"classification": "novel_branch", "policy": "review"},
    "partial_replay": {"classification": "continuation", "policy": "crypto_recheck"},
    "mimicry": {"classification": "continuation", "policy": "crypto_recheck"},
    "novel_branch": {"classification": "novel_branch_or_drift", "policy": "review"},
    "drift": {"classification": "drift", "policy": "review"},
    "recovery": {"classification": "continuation", "policy": "normal"},
    "replay": {"classification": "replay_suspect", "policy": "reject_or_reissue"},
    "cold_start": {"classification": "insufficient_pattern", "policy": "public_only"},
}


def main() -> None:
    raw = paths()
    capsules = {name: compress_events(events, window_id=name, source_label="adversarial-fixture") for name, events in raw.items()}
    comparisons = {
        name: compare_trajectories(capsules[name], capsules["baseline"])
        for name in raw
        if name != "baseline"
    }
    expectation_misses = []
    for name, expected in EXPECTED.items():
        actual = comparisons[name]["classification"]
        allowed = {"novel_branch", "drift"} if expected["classification"] == "novel_branch_or_drift" else {expected["classification"]}
        if actual not in allowed:
            expectation_misses.append({"case": name, "expected": sorted(allowed), "actual": actual})

    normal_cases = {name for name, expected in EXPECTED.items() if expected["classification"] == "continuation"}
    drift_cases = {name for name, expected in EXPECTED.items() if expected["policy"] in {"review", "reject_or_reissue"}}
    false_friction = [name for name in normal_cases if comparisons[name]["classification"] != "continuation"]
    missed_drift = [name for name in drift_cases if comparisons[name]["classification"] in {"continuation", "insufficient_pattern"} and EXPECTED[name]["policy"] != "public_only"]
    report = {
        "schema": "humain.trajectory.evaluation.v2",
        "fixture": "adversarial-movement-matrix.v1",
        "baseline_capsule": capsules["baseline"].to_dict(),
        "cases": {
            name: {"expected": EXPECTED[name], "comparison": comparisons[name], "capsule": capsules[name].to_dict()}
            for name in comparisons
        },
        "metrics": {
            "normal_case_count": len(normal_cases),
            "review_or_reject_case_count": len(drift_cases),
            "false_friction_cases": false_friction,
            "false_friction_rate": len(false_friction) / len(normal_cases),
            "missed_drift_cases": missed_drift,
            "missed_drift_rate": len(missed_drift) / len(drift_cases),
            "expectation_misses": expectation_misses,
        },
        "provenance": {
            "method": "deterministic-trajectory-adversarial-evaluator",
            "falsifier": "normal movement must not be challenged, and known drift/replay must not be accepted as ordinary continuation",
            "synthetic": True,
            "policy_note": "trajectory similarity never grants access; crypto_recheck remains required for mimicry-shaped paths",
        },
    }
    output = ROOT / "reports" / "trajectory-adversarial-evaluation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"output": str(output), "metrics": report["metrics"], "classifications": {name: result["classification"] for name, result in comparisons.items()}}, sort_keys=True))
    if expectation_misses:
        raise SystemExit("trajectory adversarial evaluation expectations failed")


if __name__ == "__main__":
    main()

"""Deterministic trajectory compression and comparison.

This module observes movement after the fact. It does not grant capabilities,
make authorization decisions, or call an LLM.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
from typing import Any, Iterable

SCHEMA = "humain.trajectory.capsule.v1"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _bucket_seconds(seconds: float) -> str:
    if seconds < 1:
        return "<1s"
    if seconds < 10:
        return "1-9s"
    if seconds < 60:
        return "10-59s"
    if seconds < 300:
        return "1-4m"
    if seconds < 1800:
        return "5-29m"
    if seconds < 3600:
        return "30-59m"
    if seconds < 86400:
        return "1-23h"
    return "1d+"


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return 1.0 if not union else len(left & right) / len(union)


def _levenshtein(left: list[str], right: list[str]) -> int:
    row = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        next_row = [i]
        for j, b in enumerate(right, 1):
            next_row.append(min(next_row[-1] + 1, row[j] + 1, row[j - 1] + (a != b)))
        row = next_row
    return row[-1]


def _sequence_distance(left: list[str], right: list[str]) -> float:
    size = max(len(left), len(right), 1)
    return _levenshtein(left, right) / size


def _entropy(values: Iterable[str]) -> float:
    counts = Counter(values)
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def _normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    required = {"event_type", "occurred_at"}
    missing = required - event.keys()
    if missing:
        raise ValueError(f"trajectory event missing fields: {sorted(missing)}")
    normalized = {
        "event_type": str(event["event_type"]),
        "occurred_at": str(event["occurred_at"]),
        "pointer_class": str(event.get("pointer_class", "unknown")),
        "state": str(event.get("state", "unknown")),
        "action": str(event.get("action", "none")),
        "scope": str(event.get("scope", "unknown")),
    }
    if "nonce" in event:
        normalized["nonce_hash"] = _hash(str(event["nonce"]))
    if "payload" in event:
        normalized["payload_hash"] = _hash(event["payload"])
    return normalized


def _runs(values: list[str]) -> list[list[Any]]:
    result: list[list[Any]] = []
    for value in values:
        if result and result[-1][0] == value:
            result[-1][1] += 1
        else:
            result.append([value, 1])
    return result


def _expand_runs(runs: list[list[Any]]) -> list[str]:
    return [value for value, count in runs for _ in range(int(count))]


@dataclass(frozen=True)
class TrajectoryCapsule:
    value: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.value)


def compress_events(events: list[dict[str, Any]], *, window_id: str, source_label: str = "local") -> TrajectoryCapsule:
    if not events:
        raise ValueError("cannot compress an empty trajectory")
    normalized = [_normalize_event(event) for event in events]
    sequence = [event["event_type"] for event in normalized]
    transitions = [f"{left}>{right}" for left, right in zip(sequence, sequence[1:])]
    timing = []
    for left, right in zip(normalized, normalized[1:]):
        delta = (_parse_time(right["occurred_at"]) - _parse_time(left["occurred_at"])).total_seconds()
        timing.append(_bucket_seconds(max(0.0, delta)))
    source_bytes = sum(len(_canonical(event)) for event in events)
    source_hash = _hash(events)
    nonce_hashes = sorted({event["nonce_hash"] for event in normalized if "nonce_hash" in event})
    capsule = {
        "schema": SCHEMA,
        "capsule_id": "capsule:" + hashlib.sha256(_canonical({"window_id": window_id, "source_hash": source_hash})).hexdigest()[:24],
        "window_id": window_id,
        "source_label": source_label,
        "event_count": len(normalized),
        "event_type_runs": _runs(sequence),
        "event_type_counts": dict(sorted(Counter(sequence).items())),
        "transitions": dict(sorted(Counter(transitions).items())),
        "transition_entropy_bits": round(_entropy(transitions), 6),
        "timing_buckets": dict(sorted(Counter(timing).items())),
        "path_digest": _hash(normalized),
        "source_hash": source_hash,
        "source_event_bytes": source_bytes,
        "capsule_bytes": 0,
        "compression_ratio": 0.0,
        "compression_status": "pending",
        "nonce_count": len(nonce_hashes),
        "nonce_set_hash": _hash(nonce_hashes),
        "provenance": {"method": "deterministic-trajectory-compressor", "falsifier": "a known normal path must not be classified as drift solely because its payload changed"},
    }
    capsule["capsule_bytes"] = len(_canonical(capsule))
    capsule["compression_ratio"] = round(source_bytes / max(capsule["capsule_bytes"], 1), 6)
    capsule["compression_status"] = "compressed" if capsule["compression_ratio"] >= 1 else "expanded"
    return TrajectoryCapsule(capsule)


def compare_trajectories(current: TrajectoryCapsule, baseline: TrajectoryCapsule) -> dict[str, Any]:
    left, right = current.value, baseline.value
    if left["event_count"] < 3 or right["event_count"] < 3:
        return {"schema": "humain.trajectory.comparison.v1", "classification": "insufficient_pattern", "novelty": None, "reasons": ["minimum event count is three"], "baseline_capsule": right["capsule_id"], "current_capsule": left["capsule_id"]}
    type_distance = 1 - _jaccard(set(left["event_type_counts"]), set(right["event_type_counts"]))
    transition_distance = 1 - _jaccard(set(left["transitions"]), set(right["transitions"]))
    sequence_distance = _sequence_distance(_expand_runs(left["event_type_runs"]), _expand_runs(right["event_type_runs"]))
    timing_distance = 1 - _jaccard(set(left["timing_buckets"]), set(right["timing_buckets"]))
    novelty = round((type_distance + transition_distance + sequence_distance + timing_distance) / 4, 6)
    nonce_overlap = left["nonce_set_hash"] == right["nonce_set_hash"] and left["nonce_count"] > 0
    if nonce_overlap and left["capsule_id"] != right["capsule_id"] and novelty <= 0.2:
        classification = "replay_suspect"
    elif novelty <= 0.2:
        classification = "continuation"
    elif novelty <= 0.5:
        classification = "novel_branch"
    else:
        classification = "drift"
    return {
        "schema": "humain.trajectory.comparison.v1",
        "classification": classification,
        "novelty": novelty,
        "similarity": round(1 - novelty, 6),
        "features": {"event_type_distance": round(type_distance, 6), "transition_distance": round(transition_distance, 6), "sequence_distance": round(sequence_distance, 6), "timing_distance": round(timing_distance, 6), "nonce_overlap": nonce_overlap},
        "thresholds": {"continuation_max_novelty": 0.2, "novel_branch_max_novelty": 0.5, "minimum_event_count": 3},
        "baseline_capsule": right["capsule_id"],
        "current_capsule": left["capsule_id"],
        "provenance": {"method": "deterministic-trajectory-comparison", "falsifier": "matched normal trajectories should remain continuation across changed payloads"},
    }

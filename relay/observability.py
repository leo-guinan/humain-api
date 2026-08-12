"""Small redacted event ledger for correlating the OpenHome demo."""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import json
import os
from threading import Lock
from typing import Any
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class EventLedger:
    def __init__(self, *, max_events: int = 2000, path: str = "") -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._lock = Lock()
        self.path = path

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        allowed = {"run_id", "source", "stage", "status", "ability", "function"}
        clean = {key: event[key] for key in allowed if key in event}
        detail = event.get("detail")
        if isinstance(detail, dict):
            safe_detail = {
                key: detail[key]
                for key in {"pending_count", "submitted_count", "error_type"}
                if key in detail
            }
            if safe_detail:
                clean["detail"] = safe_detail
        clean["event_id"] = "obs_" + uuid.uuid4().hex
        clean["occurred_at"] = _now()
        with self._lock:
            clean["sequence"] = len(self._events) + 1
            self._events.append(clean)
            if self.path:
                parent = os.path.dirname(self.path)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                with open(self.path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(clean, separators=(",", ":")) + "\n")
        return clean

    def recent(self, run_id: str = "", limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            events = list(self._events)
        if run_id:
            events = [event for event in events if event.get("run_id") == run_id]
        return events[-max(1, min(limit, 500)):]
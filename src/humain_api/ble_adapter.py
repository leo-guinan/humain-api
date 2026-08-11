"""Optional macOS BLE discovery adapter.

This module deliberately exposes candidates without exposing or persisting BLE
addresses. A device-specific signed GATT challenge must promote a candidate to
PresenceBroker.near_verified.
"""
from __future__ import annotations

from dataclasses import dataclass
import asyncio
from typing import Any, Callable

OPENHOME_DEVKIT_SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"


@dataclass(frozen=True)
class BleCandidate:
    alias: str
    rssi: float
    service_uuids: tuple[str, ...]
    observed_at: str


class BleakDiscoveryAdapter:
    """Thin optional adapter around bleak's macOS CoreBluetooth backend."""

    def __init__(self, alias_for: Callable[[Any], str | None]):
        self.alias_for = alias_for

    async def discover_once(self, timeout: float = 5.0) -> list[BleCandidate]:
        try:
            from bleak import BleakScanner
        except ImportError as exc:
            raise RuntimeError("BLE discovery requires optional dependency: pip install 'humain-api[ble]'") from exc
        from datetime import datetime, timezone

        discovered = await asyncio.wait_for(BleakScanner.discover(timeout=timeout, return_adv=True), timeout=timeout + 2.0)
        observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        candidates: list[BleCandidate] = []
        for device, advertisement in discovered.values():
            alias = self.alias_for(advertisement)
            if not alias:
                continue
            candidates.append(BleCandidate(alias=alias, rssi=float(advertisement.rssi), service_uuids=tuple(advertisement.service_uuids or ()), observed_at=observed_at))
        return candidates

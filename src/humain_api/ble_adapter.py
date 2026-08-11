"""Optional macOS BLE discovery adapter.

This module deliberately exposes candidates without exposing or persisting BLE
addresses. A device-specific signed GATT challenge must promote a candidate to
PresenceBroker.near_verified.
"""
from __future__ import annotations

from dataclasses import dataclass
import asyncio
import base64
import hashlib
import hmac
import json
from typing import Any, Callable

from .canonical import canonical_bytes

OPENHOME_DEVKIT_SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"


@dataclass(frozen=True)
class BleCandidate:
    alias: str
    rssi: float
    service_uuids: tuple[str, ...]
    observed_at: str
    advertisement_commitment: str | None = None
    commitment_quality: str = "none"


def _hex_map(values: Any) -> dict[str, str]:
    if not isinstance(values, dict):
        return {}
    output = {}
    for key, value in values.items():
        raw = bytes(value) if isinstance(value, (bytes, bytearray)) else str(value).encode("utf-8")
        output[str(key)] = raw.hex()
    return dict(sorted(output.items()))


def advertisement_material(advertisement: Any) -> dict[str, Any]:
    """Return stable, non-address advertisement material for commitment."""
    service_uuids = sorted(str(value).lower() for value in (getattr(advertisement, "service_uuids", None) or ()))
    manufacturer_data = _hex_map(getattr(advertisement, "manufacturer_data", None))
    service_data = _hex_map(getattr(advertisement, "service_data", None))
    quality = "payload" if manufacturer_data or service_data else "uuid_only"
    return {"service_uuids": service_uuids, "manufacturer_data": manufacturer_data, "service_data": service_data, "commitment_quality": quality}


def advertisement_commitment(advertisement: Any, key: bytes) -> tuple[str, str]:
    if not key:
        raise ValueError("commitment key is required")
    material = advertisement_material(advertisement)
    digest = hmac.new(key, canonical_bytes(material), hashlib.sha256).digest()
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return "hmac:" + encoded, material["commitment_quality"]

class BleakDiscoveryAdapter:
    """Thin optional adapter around bleak's macOS CoreBluetooth backend."""

    def __init__(self, alias_for: Callable[[Any], str | None], commitment_key: bytes | None = None):
        self.alias_for = alias_for
        self.commitment_key = commitment_key

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
            commitment = None
            quality = "none"
            if self.commitment_key:
                commitment, quality = advertisement_commitment(advertisement, self.commitment_key)
            candidates.append(BleCandidate(alias=alias, rssi=float(advertisement.rssi), service_uuids=tuple(advertisement.service_uuids or ()), observed_at=observed_at, advertisement_commitment=commitment, commitment_quality=quality))
        return candidates

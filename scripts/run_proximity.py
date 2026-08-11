#!/usr/bin/env python3
"""Run the local BLE proximity broker.

Simulator mode proves the complete policy path without persisting a private key.
Real mode performs candidate discovery only until a device-specific signed GATT
challenge adapter is configured.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
from datetime import datetime, timezone
import json
import os
from urllib.request import Request, urlopen

from humain_api.ble_adapter import BleakDiscoveryAdapter, OPENHOME_DEVKIT_SERVICE_UUID
from humain_api.crypto import Ed25519Signer
from humain_api.proximity import Pairing, PresenceBroker, sign_challenge


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def post_json(url: str, value: dict) -> tuple[int, dict]:
    body = json.dumps(value, separators=(",", ":")).encode("utf-8")
    request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return 0, {"error_type": type(exc).__name__, "error": str(exc)[:160]}


def decode_key(value: str | None) -> bytes | None:
    if not value:
        return None
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except Exception as exc:
        raise ValueError("observation key must be base64url") from exc


def post_observation(bridge_url: str, rendezvous_id: str, candidate, service_uuid: str) -> tuple[int, dict]:
    payload = {"rendezvous_id": rendezvous_id, "scanner": "browser", "observed_at": candidate.observed_at, "service_uuid": service_uuid, "advertisement_commitment": candidate.advertisement_commitment, "commitment_quality": candidate.commitment_quality, "rssi_bucket": int(round(candidate.rssi / 5.0) * 5), "sample_count": 1}
    return post_json(f"{bridge_url.rstrip('/')}/v1/rendezvous/observation", payload)


def simulator(bridge_url: str, alias: str) -> dict:
    now = datetime.now(timezone.utc)
    signer = Ed25519Signer.generate(f"simulator:{alias}")
    broker = PresenceBroker(now=lambda: now, min_observations=3, enter_rssi=-65)
    broker.pair(Pairing(alias, f"simulator:{alias}", signer.public_key_b64))
    presence = None
    for index in range(3):
        observed = now.replace(microsecond=min(999999, now.microsecond + index * 1000)).isoformat().replace("+00:00", "Z")
        presence = broker.observe_signed_presence(
            alias=alias,
            rssi=-55,
            observed_at=observed,
            challenge=f"demo-nonce-{index}",
            signature=sign_challenge(signer, alias=alias, challenge=f"demo-nonce-{index}", purpose="presence_signal", observed_at=observed),
        )
    assert presence is not None
    status, response = post_json(f"{bridge_url.rstrip('/')}/v1/openhome/presence", presence)
    return {"mode": "simulator", "presence_state": presence["presence_state"], "challenge_verified": presence["challenge_verified"], "bridge_status": status, "bridge_response": response}


async def real_scan(bridge_url: str, alias: str, service_uuid: str, rendezvous_id: str | None = None, commitment_key: bytes | None = None) -> dict:
    def alias_for(advertisement):
        return alias if service_uuid.lower() in {value.lower() for value in (advertisement.service_uuids or ())} else None

    adapter = BleakDiscoveryAdapter(alias_for, commitment_key=commitment_key)
    try:
        candidates = await adapter.discover_once(timeout=5)
    except Exception as exc:
        return {"mode": "real", "result": "failed_closed", "error_type": type(exc).__name__}
    results = []
    for candidate in candidates:
        broker = PresenceBroker()
        broker.pair(Pairing(alias, "unconfigured-device-key", "[REDACTED]"))
        result = broker.observe_advertisement(candidate.alias, candidate.rssi, candidate.observed_at)
        item = {"presence_state": result["presence_state"], "rssi_median": result["rssi_median"], "service_uuids": list(candidate.service_uuids), "commitment_quality": candidate.commitment_quality, "observation_submitted": False}
        if rendezvous_id and candidate.advertisement_commitment:
            status, response = post_observation(bridge_url, rendezvous_id, candidate, service_uuid)
            item.update({"observation_submitted": status == 200, "observation_status": status, "observation_response": response})
        results.append(item)
    return {"mode": "real", "result": "candidate_only", "candidates": results, "note": "No candidate is promoted without a device-specific signed GATT challenge."}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge-url", default="http://127.0.0.1:8790")
    parser.add_argument("--alias", default="openhome-speaker")
    parser.add_argument("--simulator", action="store_true")
    parser.add_argument("--service-uuid", default=os.environ.get("HUMAIN_BLE_SERVICE_UUID", OPENHOME_DEVKIT_SERVICE_UUID))
    parser.add_argument("--rendezvous-id", default=os.environ.get("HUMAIN_RENDEZVOUS_ID"))
    parser.add_argument("--commitment-key", default=os.environ.get("HUMAIN_OBSERVATION_KEY_B64"))
    args = parser.parse_args()
    commitment_key = decode_key(args.commitment_key)
    if args.rendezvous_id and not commitment_key:
        result = {"mode": "real", "result": "not_configured", "note": "Rendezvous observation submission requires HUMAIN_OBSERVATION_KEY_B64 or --commitment-key."}
    elif args.simulator:
        result = simulator(args.bridge_url, args.alias)
    elif args.service_uuid:
        result = asyncio.run(real_scan(args.bridge_url, args.alias, args.service_uuid, args.rendezvous_id, commitment_key))
    else:
        result = {"mode": "real", "result": "not_configured", "note": "Pass --service-uuid for candidate discovery; signed GATT challenge remains required."}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

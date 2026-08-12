import asyncio
import base64
import hashlib
import hmac
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

try:
    from devkit_utils.devkit_logging import web_logger as log
except ImportError:
    class _Log:
        def info(self, *_args, **_kwargs):
            pass
        def exception(self, *_args, **_kwargs):
            pass
    log = _Log()

DEFAULT_SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _post(url, payload, bearer_token=""):
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "humain-proximity-observer/1.0"}
    if bearer_token:
        headers["Authorization"] = "Bearer " + bearer_token
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _hex_map(values):
    if not isinstance(values, dict):
        return {}
    result = {}
    for key, value in values.items():
        raw = bytes(value) if isinstance(value, (bytes, bytearray)) else str(value).encode("utf-8")
        result[str(key)] = raw.hex()
    return dict(sorted(result.items()))


def _material(advertisement):
    uuids = sorted(str(value).lower() for value in (getattr(advertisement, "service_uuids", None) or ()))
    manufacturer = _hex_map(getattr(advertisement, "manufacturer_data", None))
    service_data = _hex_map(getattr(advertisement, "service_data", None))
    quality = "payload" if manufacturer or service_data else "uuid_only"
    return {"service_uuids": uuids, "manufacturer_data": manufacturer, "service_data": service_data, "commitment_quality": quality}


def _commitment(advertisement, key):
    material = _material(advertisement)
    encoded = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hmac.new(key, encoded, hashlib.sha256).digest()
    return "hmac:" + base64.urlsafe_b64encode(digest).decode("ascii").rstrip("="), material["commitment_quality"]


async def _scan(service_uuid, key):
    from bleak import BleakScanner
    discovered = await asyncio.wait_for(BleakScanner.discover(timeout=4, return_adv=True), timeout=6)
    matches = []
    for _device, advertisement in discovered.values():
        uuids = {str(value).lower() for value in (advertisement.service_uuids or ())}
        if service_uuid.lower() not in uuids:
            continue
        commitment, quality = _commitment(advertisement, key)
        matches.append({"service_uuid": service_uuid, "advertisement_commitment": commitment, "commitment_quality": quality, "rssi_bucket": int(round(float(advertisement.rssi) / 5.0) * 5), "sample_count": 1})
    matches.sort(key=lambda item: item["rssi_bucket"], reverse=True)
    return matches[:1]


def _config(args=None):
    args = list(args or [])
    relay = (args[0] if len(args) > 0 else os.environ.get("HUMAIN_RENDEZVOUS_URL", "")).rstrip("/")
    key_ref = args[1] if len(args) > 1 else os.environ.get("HUMAIN_OPENHOME_KEY_REF", "")
    service_uuid = args[2] if len(args) > 2 else os.environ.get("HUMAIN_BLE_SERVICE_UUID", DEFAULT_SERVICE_UUID)
    token = os.environ.get("HUMAIN_RENDEZVOUS_AUTH_TOKEN", "")
    if not relay or not key_ref or not token:
        raise RuntimeError("rendezvous URL, DevKit runtime auth token, and OpenHome key reference are required")
    return relay, key_ref, service_uuid, token


def scan_pending(*args):
    """Scan only pending rendezvous for this enrolled OpenHome key reference."""
    log.info("[humain-proximity-local] scan_pending entered")
    try:
        relay, key_ref, service_uuid, token = _config(args)
        pending = _post(relay + "/v1/rendezvous/pending", {"key_ref": key_ref}, token).get("rendezvous", [])
        submitted = []
        for item in pending[:3]:
            key_text = item.get("observation_key_b64", "")
            key = base64.urlsafe_b64decode(key_text + "=" * (-len(key_text) % 4))
            matches = asyncio.run(_scan(service_uuid, key))
            for match in matches:
                result = _post(relay + "/v1/rendezvous/observation", {"rendezvous_id": item["rendezvous_id"], "scanner": "openhome", "observed_at": _now(), **match}, token)
                submitted.append({"rendezvous_id": item["rendezvous_id"], "commitment_quality": match["commitment_quality"], "status": result.get("state", "submitted")})
        payload = {"success": True, "schema": "humain.rendezvous.devkit-observation.v1", "pending_count": len(pending), "submitted": submitted, "private_context": False, "raw_devices": False, "error": None}
        log.info("[humain-proximity-local] bounded scan completed")
    except Exception as error:
        log.exception("scan_pending failed")
        payload = {"success": False, "schema": "humain.rendezvous.devkit-observation.v1", "pending_count": 0, "submitted": [], "private_context": False, "raw_devices": False, "error": {"code": "devkit_scan_unavailable", "message": str(error)[:200]}}
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")


FUNCTION_REGISTRY = {"scan_pending": scan_pending}

if __name__ == "__main__":
    function_name = sys.argv[1] if len(sys.argv) > 1 else ""
    if function_name not in FUNCTION_REGISTRY:
        sys.stdout.write(json.dumps({"success": False, "error": {"code": "unknown_function"}}) + "\n")
        sys.exit(1)
    FUNCTION_REGISTRY[function_name](*sys.argv[2:])

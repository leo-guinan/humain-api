import json
import sys
import urllib.request
from datetime import datetime, timezone
from devkit_utils.devkit_logging import web_logger as log

BRIDGE_STATUS_URL = "http://127.0.0.1:8790/v1/openhome/status"


def get_presence():
    """Return only the bounded presence state from the local bridge."""
    try:
        request = urllib.request.Request(BRIDGE_STATUS_URL, headers={"User-Agent": "humain-proximity-presence/1.0"})
        with urllib.request.urlopen(request, timeout=3) as response:
            status = json.loads(response.read().decode("utf-8"))
        payload = {
            "success": True,
            "schema": "humain.proximity.capability-result.v1",
            "presence_state": status.get("presence_state", "absent"),
            "flow_eligible": bool(status.get("flow_eligible", False)),
            "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "paired_device": status.get("paired_device"),
            "error": None,
        }
    except Exception as error:
        log.exception("get_presence failed")
        payload = {
            "success": False,
            "schema": "humain.proximity.capability-result.v1",
            "presence_state": "unavailable",
            "flow_eligible": False,
            "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "paired_device": None,
            "error": {"code": "presence_unavailable", "message": str(error)[:200]},
        }
    print(json.dumps(payload, separators=(",", ":")))


FUNCTION_REGISTRY = {"get_presence": get_presence}


if __name__ == "__main__":
    function_name = sys.argv[1] if len(sys.argv) > 1 else ""
    if function_name not in FUNCTION_REGISTRY:
        print(json.dumps({"success": False, "error": {"code": "unknown_function"}}))
        sys.exit(1)
    FUNCTION_REGISTRY[function_name]()

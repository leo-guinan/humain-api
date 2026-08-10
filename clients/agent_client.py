"""Minimal agent-side HTTP client; preserves the full resolver response."""
import json
from urllib.request import Request, urlopen


def resolve(endpoint: str, request: dict, *, timeout: float = 10.0) -> dict:
    body = json.dumps(request, ensure_ascii=False).encode("utf-8")
    http_request = Request(endpoint.rstrip("/") + "/v1/resolve", data=body, headers={"Content-Type": "application/json"})
    with urlopen(http_request, timeout=timeout) as response:
        return json.loads(response.read())

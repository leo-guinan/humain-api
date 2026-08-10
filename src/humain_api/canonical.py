import hashlib
import json
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes for signing adapters."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def content_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()

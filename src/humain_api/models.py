from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse


class ValidationError(ValueError):
    pass


def parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"invalid timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise ValidationError("timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def valid_pointer(pointer: str) -> bool:
    parsed = urlparse(pointer)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


@dataclass(frozen=True)
class Capability:
    capability_id: str
    issuer: str
    subject: str
    audience: str
    pointer: str
    action: str
    issued_at: str
    expires_at: str
    revoked: bool = False

    def allows(self, *, requester: str, audience: str, pointer: str, action: str, now: datetime) -> bool:
        if self.revoked or self.subject != requester or self.audience != audience:
            return False
        if self.action != action or self.pointer != pointer:
            return False
        return parse_time(self.issued_at) <= now <= parse_time(self.expires_at)


@dataclass(frozen=True)
class ResolutionRequest:
    schema: str
    message_id: str
    pointer: str
    requester: str
    audience: str
    action: str
    nonce: str
    created_at: str
    capabilities: tuple[Capability, ...]
    signature: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResolutionRequest":
        required = {"schema", "message_id", "pointer", "requester", "audience", "action", "nonce", "created_at", "capabilities", "signature"}
        missing = required - data.keys()
        if missing:
            raise ValidationError(f"missing request fields: {sorted(missing)}")
        if data["schema"] != "humain.resolve.request.v1":
            raise ValidationError("unsupported request schema")
        if not valid_pointer(data["pointer"]):
            raise ValidationError("pointer must be an absolute HTTP(S) URL")
        parse_time(data["created_at"])
        capabilities = tuple(Capability(**item) for item in data["capabilities"])
        return cls(capabilities=capabilities, **{k: data[k] for k in required - {"capabilities"}})

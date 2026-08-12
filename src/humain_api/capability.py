"""Signed capability issuance and resolver-side authority registry."""
from __future__ import annotations

from typing import Any

from .crypto import Ed25519Signer, Ed25519Verifier
from .models import Capability, ValidationError

SCHEMA = "humain.capability.v1"


def capability_without_signature(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "signature"}


class CapabilityIssuer:
    def __init__(self, signer: Ed25519Signer):
        self.signer = signer

    def issue(self, capability: dict[str, Any]) -> dict[str, Any]:
        value = {"schema": SCHEMA, **capability}
        if "issuer" not in value or value["issuer"] != self.signer.key_ref:
            raise ValidationError("capability issuer does not match signing key")
        Capability(**{key: value[key] for key in Capability.__dataclass_fields__ if key != "signature"})
        value["signature"] = self.signer.sign(value)
        return value


class CapabilityRegistry:
    def __init__(self, public_keys: dict[str, str]):
        self.public_keys = dict(public_keys)
        self._revoked: set[str] = set()

    def revoke(self, capability_id: str) -> None:
        self._revoked.add(capability_id)

    def verify(self, value: dict[str, Any]) -> bool:
        if value.get("schema") != SCHEMA:
            return False
        signature = value.get("signature")
        if not isinstance(signature, dict):
            return False
        issuer = value.get("issuer", "")
        if signature.get("key_ref") != issuer:
            return False
        if value.get("capability_id") in self._revoked:
            return False
        try:
            capability = Capability(**{key: value[key] for key in Capability.__dataclass_fields__ if key != "signature"})
        except (KeyError, TypeError, ValidationError):
            return False
        if capability.revoked:
            return False
        return Ed25519Verifier(self.public_keys)(capability_without_signature(value), signature)

    def to_capability(self, value: dict[str, Any]) -> Capability:
        if not self.verify(value):
            raise ValidationError("capability signature was not verified")
        return Capability(**{key: value[key] for key in Capability.__dataclass_fields__})

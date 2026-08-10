"""Ed25519 signing adapter. Private keys never belong in protocol envelopes."""
import base64
import json
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .canonical import canonical_bytes


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@dataclass
class Ed25519Signer:
    private_key: Ed25519PrivateKey
    key_ref: str

    @classmethod
    def generate(cls, key_ref: str) -> "Ed25519Signer":
        return cls(Ed25519PrivateKey.generate(), key_ref)

    @property
    def public_key_b64(self) -> str:
        return _b64(self.private_key.public_key().public_bytes_raw())

    def sign(self, value: dict[str, Any]) -> dict[str, str]:
        signature = self.private_key.sign(canonical_bytes(value))
        return {"algorithm": "ed25519", "key_ref": self.key_ref, "value": _b64(signature)}

    def verify(self, value: dict[str, Any], signature: dict[str, str]) -> bool:
        if signature.get("algorithm") != "ed25519" or signature.get("key_ref") != self.key_ref:
            return False
        try:
            self.private_key.public_key().verify(_unb64(signature["value"]), canonical_bytes(value))
            return True
        except (KeyError, ValueError):
            return False


class Ed25519Verifier:
    def __init__(self, public_keys: dict[str, str]):
        self.public_keys = public_keys

    def __call__(self, value: dict[str, Any], signature: dict[str, str]) -> bool:
        if signature.get("algorithm") != "ed25519":
            return False
        encoded = self.public_keys.get(signature.get("key_ref", ""))
        if not encoded:
            return False
        try:
            Ed25519PublicKey.from_public_bytes(_unb64(encoded)).verify(_unb64(signature["value"]), canonical_bytes(value))
            return True
        except (KeyError, ValueError):
            return False

from datetime import datetime, timezone
from typing import Any, Callable

from .canonical import content_hash
from .capability import CapabilityRegistry
from .crypto import Ed25519Signer
from .models import ResolutionRequest, ValidationError


class Resolver:
    """Local resolver core. Transport and cryptographic verification are adapters."""

    def __init__(
        self,
        *,
        publisher: str,
        verify_signature: Callable[..., bool] | None = None,
        response_signer: Ed25519Signer | None = None,
        capability_registry: CapabilityRegistry | None = None,
    ):
        self.publisher = publisher
        self.verify_signature = verify_signature or (lambda _value, signature: signature.get("algorithm") != "demo")
        self.response_signer = response_signer
        self.capability_registry = capability_registry
        self._seen_nonces: set[tuple[str, str]] = set()
        self._revoked: set[str] = set()

    def revoke(self, capability_id: str) -> None:
        self._revoked.add(capability_id)

    def resolve(self, request_data: dict[str, Any], projection: dict[str, Any]) -> dict[str, Any]:
        request = ResolutionRequest.from_dict(request_data)
        nonce_key = (request.requester, request.nonce)
        if nonce_key in self._seen_nonces:
            raise ValidationError("replayed nonce")
        self._seen_nonces.add(nonce_key)
        if not verify_request_signature(self.verify_signature, request, request.signature):
            raise ValidationError("request signature was not verified")
        now = datetime.now(timezone.utc)
        allowed = any(
            (self.capability_registry is None or self.capability_registry.verify({"schema": "humain.capability.v1", **{key: item for key, item in cap.__dict__.items() if item is not None}}))
            and cap.capability_id not in self._revoked
            and cap.allows(
                requester=request.requester, audience=request.audience,
                pointer=request.pointer, action=request.action, now=now
            )
            for cap in request.capabilities
        )
        if not allowed:
            return self._response(request, "denied", {}, "no matching active capability")
        return self._response(request, "trusted_projection", projection, None)

    def _response(self, request: ResolutionRequest, state: str, payload: dict[str, Any], error: str | None) -> dict[str, Any]:
        response = {
            "schema": "humain.resolve.response.v1",
            "message_id": f"response:{request.message_id}",
            "message_type": "resolve.response",
            "pointer": request.pointer,
            "publisher": self.publisher,
            "audience": request.requester,
            "resolution_state": state,
            "payload": payload,
            "provenance": {
                "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "method": "local-reference-resolver",
                "parent": content_hash(request_data_without_signature(request)),
            },
            "permissions": {"action": request.action, "capability_checked": state == "trusted_projection"},
            "error": error,
        }
        response["signature"] = (
            self.response_signer.sign(response_without_signature(response))
            if self.response_signer is not None
            else {"algorithm": "demo", "key_ref": self.publisher, "value": "demo:unsigned"}
        )
        return response


def response_without_signature(response: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in response.items() if key != "signature"}


def verify_request_signature(verifier: Callable[..., bool], request: ResolutionRequest, signature: dict[str, Any]) -> bool:
    value = request_data_without_signature(request)
    try:
        return bool(verifier(value, signature))
    except TypeError:
        # Backward-compatible test hook; real verifiers should inspect the signed value.
        return bool(verifier(signature))


def request_data_without_signature(request: ResolutionRequest) -> dict[str, Any]:
    capabilities = []
    for cap in request.capabilities:
        value = {key: item for key, item in cap.__dict__.items() if item is not None}
        if cap.signature is not None:
            value = {"schema": "humain.capability.v1", **value}
        capabilities.append(value)
    return {
        "schema": request.schema, "message_id": request.message_id, "pointer": request.pointer,
        "requester": request.requester, "audience": request.audience, "action": request.action,
        "nonce": request.nonce, "created_at": request.created_at,
        "capabilities": capabilities,
    }

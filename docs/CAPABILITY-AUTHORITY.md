# Capability authority

Status: local reliability slice, 2026-08-12. This is not a production issuer service.

## Purpose

A capability is authorization only when its issuer is both explicit and cryptographically verifiable. A structurally valid capability supplied by a requester is not enough.

The reference implementation now supports:

```text
issuer key
  → signed humain.capability.v1 envelope
  → resolver-side public-key registry
  → signature and issuer binding check
  → capability matching
```

## Python API

```python
from humain_api import CapabilityIssuer, CapabilityRegistry, Ed25519Signer

issuer = Ed25519Signer.generate("did:key:issuer")
capability = CapabilityIssuer(issuer).issue({
    "capability_id": "cap:example",
    "issuer": "did:key:issuer",
    "subject": "did:key:agent",
    "audience": "did:key:publisher",
    "pointer": "https://example.com/article/123",
    "action": "resolve",
    "issued_at": "2026-08-12T00:00:00Z",
    "expires_at": "2026-08-13T00:00:00Z",
    "revoked": False,
})

registry = CapabilityRegistry({"did:key:issuer": issuer.public_key_b64})
assert registry.verify(capability)
```

A resolver configured with `capability_registry=registry` rejects unsigned, unknown-issuer, revoked, or tampered capabilities by denying the resolution.

## Boundaries

This slice does not yet provide:

- durable issuer or key storage;
- key rotation or emergency revocation distribution;
- an HTTP issuer service;
- capability parent/child delegation or limits beyond the existing pointer/action/audience fields;
- production configuration refusal for demo signatures.

Those remain roadmap work. The registry is an in-process authority adapter, not a trust oracle descended from the heavens.

# Resolver modes

The resolver has two explicit modes:

- `reference` (default): preserves the local protocol fixtures and may emit the `demo:unsigned` response signature when no response signer is supplied. This mode is for examples and tests only.
- `production`: refuses construction unless both a real request verifier and a real Ed25519 response signer are supplied.

```python
from humain_api import Ed25519Signer, Ed25519Verifier, Resolver

agent = Ed25519Signer.generate("did:key:agent")
publisher = Ed25519Signer.generate("did:key:publisher")
resolver = Resolver(
    publisher="did:key:publisher",
    mode="production",
    verify_signature=Ed25519Verifier({"did:key:agent": agent.public_key_b64}),
    response_signer=publisher,
)
```

This is intentionally an explicit constructor boundary rather than an inferred environment variable. The deployment layer still needs to load the authoritative key registry, signer, and mode from a durable configuration/secrets source. Until then, production mode exists as a fail-closed primitive, not as a complete deployment policy.

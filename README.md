# HumAIn API

A transport-neutral foundation for resolving contextual information against shared public pointers.

> The URL is a coordinate, not the whole world.

HumAIn is a proposed protocol architecture. This repository is the first reference substrate, not a production identity service, message bus, wallet, private channel, or security guarantee.

## Core model

```text
(pointer, identity, context) -> trusted information
```

The protocol separates three planes:

- **Pointer plane** — public URLs and object identifiers.
- **Trust plane** — identities, signatures, capabilities, relationships, provenance, consent, and revocation.
- **Information plane** — messages, observations, claims, annotations, predictions, outcomes, and interfaces.

The same pointer may have a public representation and one or more trusted projections. The pointer does not become private merely because a resolver can access another projection.

## Repository status

Status: **protocol substrate / v0.1**

Implemented:

- versioned `RESOLVE` request and response envelopes;
- canonical JSON bytes for hashing/signing adapters;
- Ed25519 request signing and verification adapter;
- local HTTP `/health` and `/v1/resolve` transport;
- capability matching with expiry, audience, pointer, action, and revocation checks;
- append-only parent/hash linkage validation;
- explicit open/closed receipt shape;
- JSON Schema documents and examples;
- local standard-library test suite.

Not implemented:

- production cryptographic key handling;
- a network transport or message bus;
- account creation, wallet connection, custody, payment, or token settlement;
- authorization based on a browser installation alone;
- automatic private-content delivery;
- a voice agent integration.

## Quickstart

```bash
cd /Users/leoguinan/Projects/humain-api
python3 -m unittest discover -s tests -v
python3 verify.py
```

The implementation uses only the Python standard library. The test result is a local protocol receipt, not proof of interoperability with an external service.

## Protocol documents

- [`docs/PROTOCOL.md`](docs/PROTOCOL.md) — normative v0.1 protocol draft.
- [`docs/SECURITY.md`](docs/SECURITY.md) — threat model and boundaries.
- [`docs/CLIENTS.md`](docs/CLIENTS.md) — browser extension, agent resolver, and voice client contracts.
- [`docs/ADAPTER-PATTERNS.md`](docs/ADAPTER-PATTERNS.md) — reusable browser and ElevenLabs voice adapter patterns.
- [`docs/MEMETIC-LAYER.md`](docs/MEMETIC-LAYER.md) — persona projections that compress protocol state without changing evidence.
- [`schemas/`](schemas/) — machine-readable envelope schemas.
- [`examples/`](examples/) — valid example envelopes.
- [`src/humain_api/`](src/humain_api/) — small reference validator/resolver substrate.

## Design rule

A message is a claim with provenance, not an unquestionable fact. A receipt keeps the promise and result visible. Corrections append; they do not silently rewrite history.

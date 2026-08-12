# HumAIn API

A transport-neutral foundation for resolving contextual information against shared public pointers.

> The URL is a coordinate, not the whole world.

HumAIn is a proposed protocol architecture. This repository is a reference substrate and local demonstration surface — not a production identity service, message bus, wallet, private channel, or security guarantee.

## Core model

```text
(pointer, identity, context) -> trusted information
```

The protocol separates three planes:

- **Pointer plane** — public URLs and object identifiers.
- **Trust plane** — identities, signatures, capabilities, relationships, provenance, consent, and revocation.
- **Information plane** — messages, observations, claims, annotations, predictions, outcomes, and interfaces.

A pointer does not become private merely because a resolver can access another projection.

## Current status

Status: **protocol substrate / v0.1 / reliability hardening in progress**

Implemented and locally verified:

- versioned `RESOLVE` request and response envelopes;
- canonical JSON bytes and content hashes;
- Ed25519 signing and verification adapters;
- optional real Ed25519 response signing in the resolver;
- local HTTP `/health` and `/v1/resolve` transport;
- capability matching with expiry, audience, pointer, action, and revocation checks;
- append-only parent/hash linkage validation;
- explicit open/closed receipt shape;
- signed BLE proximity commitments and corroboration tripwires;
- authenticated browser/OpenHome rendezvous flow;
- trajectory compression and adversarial movement evaluation;
- local OpenHome bridge with explicit arm state, presence gating, public-only output, and mute controls;
- OpenHome capability packages, including a clean-room DevKit diagnostic under `openhome/minimal-local-ping/`.

The local verification receipt currently is:

```text
39 tests passed
8 example envelopes verified
sha256:416059fe7adee96d399e8d7ccb2f037b1a122e2ebb8d1bd8f5fd7971badf0281
```

This proves the reference fixtures and local tests. It does not prove interoperability with an external resolver, a physical OpenHome device, or production cryptographic key management.

## Not production-ready

The following remain explicitly outside the reliable pilot boundary:

- durable replay, revocation, session, projection, and receipt state;
- signed capability issuance and an issuer key registry;
- production key lifecycle and secret management;
- TLS-terminated production ASGI transport with rate limits and readiness checks;
- deployment, backup/restore, and rollback evidence;
- authenticated voice-provider webhooks and reconciliation;
- private-content delivery, payments, custody, token settlement, or automatic actions.

The resolver still emits demo response signatures unless a real `response_signer` is configured. The roadmap treats that as a hard boundary, not a cosmetic detail.

## Quickstart

```bash
cd /Users/leoguinan/Projects/humain-api
python3 -m unittest discover -s tests -v
python3 verify.py
```

The implementation uses Python’s standard library for the reference transport and `cryptography` for Ed25519.

For the local OpenHome bridge:

```bash
PYTHONPATH=src python3 run_openhome_bridge.py
PYTHONPATH=src python3 scripts/run_proximity.py --simulator
```

See `docs/OPENHOME-DEMO.md` before attempting a physical-device run. The physical-device path requires a correlated runtime/DevKit receipt; a spoken sentence alone is not proof that the local action executed.

## Protocol and implementation documents

- [`docs/PROTOCOL.md`](docs/PROTOCOL.md) — normative v0.1 protocol draft.
- [`docs/SECURITY.md`](docs/SECURITY.md) — threat model and boundaries.
- [`docs/RELIABILITY-ROADMAP.md`](docs/RELIABILITY-ROADMAP.md) — pilot gates and production hardening order.
- [`docs/CLIENTS.md`](docs/CLIENTS.md) — browser extension, agent resolver, and voice client contracts.
- [`docs/ADAPTER-PATTERNS.md`](docs/ADAPTER-PATTERNS.md) — browser and voice adapter patterns.
- [`docs/RENDEZVOUS.md`](docs/RENDEZVOUS.md) — authenticated browser/OpenHome rendezvous protocol.
- [`docs/OPENHOME-DEMO.md`](docs/OPENHOME-DEMO.md) — local browser-to-OpenHome demonstration runbook.
- [`docs/PROXIMITY-PAIRING.md`](docs/PROXIMITY-PAIRING.md) — BLE presence, pairing, challenge, RSSI, and activation policy.
- [`docs/TRAJECTORY-COMPRESSION.md`](docs/TRAJECTORY-COMPRESSION.md) — movement-pattern compression and scrutiny escalation.
- [`docs/MEMETIC-LAYER.md`](docs/MEMETIC-LAYER.md) — persona projections that do not change evidence.
- [`schemas/`](schemas/) — machine-readable envelope schemas.
- [`examples/`](examples/) — synthetic example envelopes.
- [`src/humain_api/`](src/humain_api/) — reference validator/resolver substrate.
- [`relay/`](relay/) — authenticated rendezvous relay implementation.
- [`openhome/`](openhome/) — local OpenHome capability packages.

## Reliability roadmap: first slice

The roadmap begins with real signatures, not more surface area:

1. Verify request signatures against registered public keys over canonical request bytes.
2. Sign resolver responses with a publisher key and verify them independently.
3. Add signed capability issuance and an issuer registry.
4. Move replay, revocation, session, projection, and receipt state into durable storage.
5. Replace the reference HTTP server with a hardened production transport.
6. Add deployment, readiness, rollback, backup, and restore evidence.
7. Harden voice sessions and browser resolver boundaries.
8. Permit a read-only private pilot only after every exit criterion in `docs/RELIABILITY-ROADMAP.md` is evidenced.

A capability is not authorization merely because it parses. A receipt in a Python object is not an audit trail. A message is a claim with provenance, not an unquestionable fact. Corrections append; they do not silently rewrite history.

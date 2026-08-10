# HumAIn reliability roadmap

Status: infrastructure audit, 2026-08-10

## Executive assessment

The current repository is a protocol reference slice, not a reliable network service. The core resolution model and fail-closed tests are useful. The transport, authority, persistence, and operations layers are not yet strong enough for private production data, a real phone number, or automatic actions.

The first reliability target should be a bounded private pilot:

- one resolver deployment;
- one known publisher key;
- browser public projections only;
- voice read-only context only;
- no payments, custody, private corpus, or automatic actions;
- durable receipts and explicit rollback.

Do not start with multi-region or a message bus. That would distribute the uncertainty before removing it.

## P0 — required before a private pilot

### 1. Make cryptographic verification real

Current boundary: `run_resolver.py` accepts a callback that checks `signature.algorithm == "ed25519"`; the resolver response is emitted with `demo:unsigned`.

Required:

- verify Ed25519 bytes over canonical request data, not a label;
- sign resolver responses with a publisher key;
- publish a key reference and key status;
- reject unknown, expired, revoked, malformed, or algorithm-confused signatures;
- add negative tests with altered pointer, capability, audience, nonce, and payload;
- keep demo keys and demo signatures impossible to enable through a production config.

Exit evidence:

```text
valid request signature        PASS
changed request field          REJECT
valid response signature       PASS
rotated/revoked key            REJECT
production mode with demo key  REFUSE TO START
```

### 2. Add an authority for capabilities

Current boundary: a request carries capabilities, but there is no issuer/key registry that proves the capability was issued by an authorized authority. A requester can currently present a structurally valid capability.

Required:

- capability issuer service or offline issuer process;
- issuer signature over canonical capability data;
- resolver-side issuer allowlist/key registry;
- capability IDs, parent IDs, issuance, expiry, audience, pointer, action, and limits;
- revocation records with durable distribution;
- key rotation and emergency revocation procedure.

A capability is not authorization merely because it parses.

### 3. Move security state out of process memory

Current boundary:

- replay nonces live in `Resolver._seen_nonces`;
- revoked capabilities live in `Resolver._revoked`;
- voice sessions live in `VoiceToolService.sessions`;
- projections are process-local dictionaries.

Required durable stores:

- PostgreSQL for authoritative capabilities, revocations, sessions, receipts, and audit events;
- Redis only for bounded TTL/idempotency acceleration, never as the sole receipt store;
- unique constraint on `(requester, nonce)`;
- transactionally recorded resolution attempt before response;
- durable session status and expiry;
- projection version/content hash.

For the first pilot, a single PostgreSQL instance with encrypted backups is sufficient. SQLite is acceptable for local tests, not for a multi-process public resolver.

### 4. Replace the reference HTTP server

Current boundary: `ThreadingHTTPServer` has no TLS, request-size limit, structured access logs, graceful deployment contract, or production health model.

Required:

- FastAPI/uvicorn or another maintained HTTP stack;
- nginx/Caddy or managed TLS termination;
- loopback binding behind the proxy;
- body-size and header-size limits;
- request timeout and concurrency limits;
- `healthz` for process health and `readyz` for database/key/issuer readiness;
- graceful shutdown and connection draining;
- standard error envelope with request ID;
- rate limiting per requester/IP/session;
- no sensitive request bodies in access logs.

### 5. Add a real deployment boundary

Required:

- dedicated non-root service user;
- pinned Python/dependency lock file;
- systemd unit or container with restart policy;
- environment/secrets provided by a secret manager or mode-600 file outside the release directory;
- immutable release directory and symlinked `current` deployment;
- pre-deploy migration check;
- health-gated cutover;
- one-command rollback to the previous release;
- backup/restore drill for the authoritative database.

A process that starts after SSH disconnect is not yet an operations model.

### 6. Define receipt durability and auditability

Required receipt fields:

- receipt ID and schema version;
- request ID/message ID;
- pointer and content hash;
- requester/audience;
- capability ID and issuer key reference;
- resolution state;
- response hash and signature reference;
- created/closed/corrected timestamps;
- transport and client reference;
- error class without private payload leakage.

Receipts must be append-only, queryable, exportable, and backed up. A receipt in a Python object is a mood, not an audit trail.

### 7. Harden voice sessions before connecting ElevenLabs

Required before a real number:

- session creation endpoint authenticated by the call trigger;
- random high-entropy session IDs with bounded TTL;
- one-time or nonce-bound tool calls;
- session/pointer/action binding in durable storage;
- idempotency key for each tool call;
- call-start record containing provider conversation ID;
- raw webhook capture plus timestamp/signature verification;
- transcript retention policy and deletion path;
- reconciliation job for calls whose post-call webhook is delayed or missing;
- explicit recording/transcription disclosure;
- read-only action set for the pilot.

The LLM must never mint or widen its own session capability.

## P1 — required before broader public use

### Key lifecycle

- KMS/HSM-backed signing where available;
- separate issuer, resolver, and client keys;
- rotation without downtime;
- revocation cache refresh with freshness bounds;
- key compromise runbook and incident receipt;
- no private keys in browser extension storage.

### Origin and publisher control

- verified publisher/domain binding;
- origin change detection;
- content-addressed projections;
- explicit distinction between publisher control and claim truth;
- cache invalidation when a projection version is revoked.

### Browser reliability

- background-worker resolver transport rather than content-script network calls;
- real request signing with browser-appropriate key boundaries;
- resolver timeout/fallback state machine;
- SPA navigation and back/forward invalidation;
- extension update/rollback path;
- extension-local receipt export;
- tests with resolver unavailable, invalid signature, stale capability, and malformed response.

The current Marvin extension is a verified public/static adapter. It is not yet a signed resolver client.

### Observability

Emit metrics for:

- resolution attempts by state;
- signature failures;
- capability denials;
- replay rejects;
- latency percentiles;
- provider/tool failures;
- webhook lag and reconciliation rate;
- receipt write failures;
- database pool saturation.

Add structured logs with request IDs and redaction tests. Add alerts for denial spikes, signature failures, readiness loss, receipt-write failures, and webhook backlog.

### Testing and recovery

- schema compatibility tests across extension, agent, voice tool, and resolver;
- property tests for canonicalization/signature boundaries;
- concurrency test for duplicate nonces;
- restart test during an active voice session;
- backup restore test into a clean environment;
- deploy rollback test;
- dependency and secret scanning in CI;
- load test with bounded rate and known fixtures;
- fault injection for database unavailable, key registry stale, resolver timeout, and provider webhook loss.

## P2 — required before automatic actions

Do not add `ACT` because `RESOLVE` works.

Before any external action:

- separate action service and credential boundary;
- capability scoped to one action, one pointer, one audience, and one expiry;
- explicit user confirmation receipt;
- idempotency key and action deduplication;
- dry-run/preview response;
- independent settlement or completion receipt;
- compensation/rollback policy where possible;
- rate, budget, and blast-radius limits;
- human kill switch;
- adversarial red-team test suite.

Payments, custody, token issuance, and phone-triggered commitments remain outside the pilot.

## Recommended order of work

1. Replace algorithm-label verification with real request and response signatures.
2. Add signed capability issuance and a key registry.
3. Introduce PostgreSQL-backed replay, revocation, session, projection, and receipt state.
4. Move behind TLS with a production ASGI server, readiness checks, rate limits, and request IDs.
5. Add systemd/container deployment, backup, restore, and rollback evidence.
6. Build authenticated ElevenLabs call trigger and webhook reconciliation.
7. Wire the browser extension to the resolver with a genuinely supported client key boundary.
8. Add observability, CI, compatibility tests, and fault-injection tests.
9. Run a read-only private pilot with synthetic/public data.
10. Publish a reliability receipt with measured latency, recovery time, denial behavior, and known limits.

## Pilot exit criteria

A private pilot is allowed only when all are true:

- [ ] production cannot start with demo signatures;
- [ ] invalid signatures fail closed;
- [ ] replay protection survives restart and two concurrent requests;
- [ ] revocation survives restart and reaches every resolver instance;
- [ ] response signatures verify independently;
- [ ] sessions survive process restart without widening scope;
- [ ] receipts survive process restart and database restore;
- [ ] TLS endpoint has health/readiness checks;
- [ ] deployment rollback has been exercised;
- [ ] voice webhook verification has been exercised with a captured fixture;
- [ ] browser resolver timeout preserves the original site;
- [ ] no private data, payment authority, custody, or automatic action is in the pilot;
- [ ] a human can inspect the underlying receipt behind Marvin's surface.

Until then, HumAIn is a promising reference implementation. That is not an insult. It is a much safer sentence than "production-ready".

# HumAIn API Protocol v0.1

Status: draft. Normative language is limited to this document and the JSON Schemas.

## 1. Resolution

A resolver asks what information is available at a public pointer for a requester with a stated identity, capabilities, and context.

```text
RESOLVE(pointer, requester, capabilities, context, nonce, signature)
```

A response identifies the publisher, representation, provenance, permissions, timestamp, and signature material required by the selected signing adapter.

The protocol does not prescribe HTTP, WebSockets, relays, libp2p, local IPC, or any other transport.

## 2. Envelope

Every protocol message has:

- `schema` — versioned schema identifier;
- `message_id` — stable identifier for this message;
- `message_type` — request, response, observation, attestation, connection, action, or receipt;
- `pointer` — the public coordinate being discussed;
- `publisher` — the node making the message;
- `audience` — public, capability, node, or group scope;
- `payload` — typed message content;
- `provenance` — time, parent, source, and method;
- `signature` — algorithm, key reference, and signature value.

A signature field with a value such as `demo:unsigned` is an explicit fixture marker. It is not an authentication result.

## 3. Capability

A capability is a narrow, time-bounded permission. At minimum it names:

- capability ID;
- issuer;
- subject;
- audience;
- allowed pointer or pointer prefix;
- action;
- issued and expiry times;
- nonce or grant version;
- revocation status.

A capability grants only the action named. A reader capability is not a write capability. A browser extension installation is not, by itself, an identity or capability.

## 4. Message graph

Messages may reference a prior message through `provenance.parent`. The parent is a content hash, not an instruction to trust the transport. A validator can detect broken linkage; it cannot infer truth from linkage.

Recommended message types:

1. `resolve.request`
2. `resolve.response`
3. `observation`
4. `attestation`
5. `connection`
6. `action`
7. `receipt`

These are intentionally small. A client may add application-specific payloads under a versioned schema without changing the envelope.

## 5. Receipt

A receipt records a promise and a result:

```json
{
  "promise": "What was intended or claimed before resolution.",
  "result": "What was observed after resolution, or null while open."
}
```

A receipt does not prove that the promise was wise, that the result was caused by the actor, or that a financial outcome occurred.

## 6. Resolution states

A resolver should distinguish:

- `public_only` — only the ordinary public representation is available;
- `trusted_projection` — a capability-authorized projection is available;
- `mutual_trust` — origin and requester proofs both passed under a named policy;
- `denied` — the request was rejected;
- `unavailable` — the resolver could not determine the state.

Do not collapse `unavailable` into `denied`, and do not present `trusted_projection` as proof of publisher truth.

## 7. Compatibility

Schemas are versioned independently. A breaking change creates a new schema identifier. Clients must reject unknown required fields or explicitly operate in a declared compatibility mode.

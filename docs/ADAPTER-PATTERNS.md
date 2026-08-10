# HumAIn adapter patterns

Status: design pattern draft, v0.1

The browser extension and phone agent are not separate trust systems. They are two clients of the same resolver protocol:

```text
public pointer
     |
     v
HumAIn resolver
     |
     +--> browser projection
     +--> agent context
     +--> voice turn context
```

The resolver decides what a node may receive. The client decides how to represent that response. A client must never upgrade `public_only`, `denied`, or `unavailable` into a trusted projection by itself.

## Pattern A: browser extension as human resolver

### Purpose

Replace or augment the visible presentation of a public page while preserving the original served DOM and giving the user an obvious restoration path.

### Components

```text
page URL
  |
  v
content script: capture pointer + mount reversible shell
  |
  v
MV3 service worker: sign request + call resolver
  |
  v
HumAIn resolver: verify signature + capability + provenance
  |
  v
content script: render allowed projection or public fallback
```

### Sequence

1. `document_start` content script records the public pointer.
2. It mounts a clearly labelled BIPU/HumAIn shell, but does not delete the original DOM.
3. The service worker constructs a `humain.resolve.request.v1` request with:
   - pointer;
   - requester identity;
   - one-use nonce;
   - requested action (`resolve`);
   - narrow capability;
   - request signature.
4. The service worker calls the configured resolver endpoint.
5. The content script receives the complete response, including state and provenance.
6. Rendering rules:
   - `trusted_projection` or `mutual_trust`: render the permitted projection;
   - `public_only`: show public page or a clearly marked public view;
   - `denied`: show the original page and a reason that does not leak hidden content;
   - `unavailable`: show a local unavailable state and keep the original restore path.
7. The extension stores only a local receipt of the resolution decision unless the user explicitly exports it.

### Browser-specific rules

- Installation is not proof of a human identity.
- `chrome.storage.local` is not a hardware-backed key vault.
- Never put a long-lived private signing key in content-script source.
- Prefer the background worker for network calls and key use.
- Keep host matches narrow; begin with explicitly supported sites.
- Never hide the original page without a visible `Show original site` control and a keyboard fallback.
- Do not turn a payment link into a payment receipt.
- Do not expose a trusted projection merely because the resolver endpoint returned HTTP 200; inspect `resolution_state` and signature/provenance.

### Extension failure modes

| Failure | Required behavior |
|---|---|
| resolver timeout | preserve/restore public page; mark unavailable |
| invalid response signature | fail closed; do not render trusted projection |
| capability expired | request a fresh capability; do not silently reuse |
| SPA navigation | recompute pointer and invalidate prior projection |
| extension disabled | server page remains intact |
| user presses restore | stop projection rendering until explicit re-enable |

## Pattern B: ElevenLabs phone agent as voice resolver

### Purpose

Let a voice agent discuss the same pointer/context graph without making the agent a permanent authority or placing secrets in the phone platform.

### Components

```text
call trigger service
  |
  +--> creates short-lived call session + scoped capability
  |
  +--> starts ElevenLabs Convai call
             |
             v
       ElevenLabs voice agent
             |
             v
       resolver tool /v1/voice/resolve
             |
             v
       HumAIn resolver
             |
             v
       structured context returned to the agent
             |
             v
       post-call transcript + action receipts
```

### Call-start contract

The trigger service supplies only call-scoped dynamic variables:

- `humain_session_id`;
- `pointer`;
- `allowed_actions`;
- `capability_expires_at`;
- `disclosure_text`;
- human callback context when necessary.

It does not place API keys, private keys, seed phrases, wallet credentials, or unrestricted capabilities into ElevenLabs dynamic variables.

The agent must disclose at the start that it is an AI agent, identify who it represents, name the pointer under discussion, and ask permission before any action beyond reading context.

### Voice tool contract

The voice agent gets one narrow resolver tool, conceptually:

```json
{
  "name": "resolve_context",
  "arguments": {
    "session_id": "call-session:...",
    "pointer": "https://example.com/foo",
    "question": "What trusted context is available here?"
  }
}
```

The tool service checks the session, pointer allowlist, capability expiry, and action scope before calling HumAIn. The LLM does not decide whether a capability is valid.

### Sequence

1. Trigger service creates a short-lived session and stores the session ID.
2. Trigger service starts the ElevenLabs call using the selected integration path.
3. Agent discloses identity and recording/transcription policy.
4. User names or confirms a pointer.
5. Agent calls `resolve_context`.
6. Tool service requests a HumAIn resolution.
7. Agent summarizes only the returned projection and cites its pointer/publisher/provenance.
8. If the user requests an action, the agent repeats the action, scope, and consequence and asks for explicit confirmation.
9. Only a separately authorized action service may execute it.
10. On call completion, store `conversation_id`, transcript receipt, resolver response hashes, action attempts, and unresolved questions.

### ElevenLabs integration choice

For a first controlled experiment, use the register-call/BYO-Twilio path when preserving ownership of Twilio webhooks matters. Use native ElevenLabs phone-number import only when deliberately accepting ElevenLabs webhook ownership and the number lock-in that follows.

This choice affects transport ownership, not HumAIn trust. The HumAIn resolver remains the authority for contextual access either way.

### Voice-specific rules

- A natural-sounding answer is not evidence.
- The agent must preserve uncertainty and say when resolution failed.
- The agent must not claim that a link was paid, a call was successful, or a commitment settled without an independent receipt.
- DTMF is an action and needs an explicit capability plus an action receipt.
- Limit menu-navigation retries and call duration.
- Verify ElevenLabs post-call webhooks using the raw request body, timestamp, and signature before accepting transcripts.
- Store `conversation_id` at call start for reconciliation if the webhook fails.

## Shared state machine

Both clients use the same state machine:

```text
unknown pointer
      |
      v
public_only ---> unavailable
      |
      v
capability checked
      |
      +--> denied
      |
      +--> trusted_projection
                    |
                    v
              mutual_trust
```

`mutual_trust` is not synonymous with 2FA. If the extension and site share a device, their proofs may not be independent authentication factors. The protocol should describe what each party proved, not inflate the label.

## Shared receipts

A browser decision and a phone conversation should produce compatible receipts:

```text
pointer
requester
publisher
resolution_state
capability_id
provenance_hash
created_at
transport
conversation_or_tab_reference
observed_result
```

A receipt records what happened. It does not upgrade a proposal into a commitment, a commitment into settlement, or an AI statement into truth.

## First experiments

1. Browser: replace the existing static story.markets fixture with a local resolver response and verify restore behavior across reload and SPA navigation.
2. Voice: use a synthetic local pointer and a mock `resolve_context` tool before any real outbound call.
3. Cross-client: send the same signed request fixture through the extension client and the voice tool service; compare canonical response hashes.
4. Falsifier: if the two clients produce different pointer, provenance, or resolution-state semantics, they are not clients of one protocol yet.

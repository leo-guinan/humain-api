# Client contracts

## Browser extension

The extension is a human presentation client. It can:

1. read a public pointer;
2. request a resolver projection;
3. render a simpler view;
4. expose structured context to an agent;
5. restore the original page.

The extension must not treat installation as proof of a human identity, connect a wallet by default, or hide the original page without a visible restoration path.

See `docs/ADAPTER-PATTERNS.md`, Pattern A.

## Agent resolver

An agent should receive structured messages directly:

```text
pointer -> resolver request -> capability decision -> signed response -> structured context
```

It should not need to render a browser page to discover the graph. It must preserve pointer, publisher, provenance, permissions, and unresolved fields in its own response.

## Voice client

A voice client is another resolver client. It may render the same structured context conversationally. It should cite the pointer and provenance used, ask for explicit authorization before actions, and record an action receipt when an action is actually attempted.

The detailed ElevenLabs pattern is [`ADAPTER-PATTERNS.md`](ADAPTER-PATTERNS.md#pattern-b-elevenlabs-phone-agent-as-voice-resolver).
Voice is not a second source of truth. It is a different representation of the same graph.

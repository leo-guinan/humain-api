# OpenHome website-context demo

Status: local demonstration slice, not production deployment.

## What the demo proves

```text
BIPU browser extension
  → normalized HTTPS pointer event
  → loopback HumAIn/OpenHome bridge
  → public-only resolution envelope
  → Marvin speech envelope
  → OpenHome local context-speaker ability
```

The extension sends only:

- normalized pointer (`origin + pathname`);
- event ID;
- client ID;
- event timestamp.

It does not send page text, HTML, query strings, fragments, browser history, credentials, or private resolver projections.

## Run locally

From this repository:

```bash
PYTHONPATH=src python3 run_openhome_bridge.py
```

The bridge binds to `127.0.0.1:8790` only.

Arm the demo explicitly for five minutes:

```bash
curl -X POST http://127.0.0.1:8790/v1/openhome/arm \\
  -H 'Content-Type: application/json' \\
  -d '{"session_id":"desk-demo","ttl_seconds":300}'
```

Load the rebuilt extension on `https://story.markets/`. The bridge queues one speech envelope. The local OpenHome ability polls:

```text
GET http://127.0.0.1:8790/v1/openhome/next
```

Mute immediately:

```bash
curl -X POST http://127.0.0.1:8790/v1/openhome/mute \\
  -H 'Content-Type: application/json' \\
  -d '{}'
```

## What Marvin says

The first public-only demo line is equivalent to:

> You have arrived at story.markets. The bodega cat checked the public shelf. The back room is not open to this node. This is an AI-generated public-context demo. Say show the receipt if you want the details.

The envelope carries the underlying response and provenance for a receipt view. The voice surface is not the evidence surface.

## OpenHome setup

The ability package is under `openhome/context-speaker/`. It is designed for a local OpenHome ability client and is not deployed by this repository.

Before deployment:

1. confirm the OpenHome client can reach the Mac loopback bridge or replace the URL with an explicitly paired local bridge address;
2. use a fresh OpenHome authentication session;
3. validate the ability with the OpenHome CLI;
4. deploy only after inspecting the exact ability archive and target agent;
5. verify one delivery and then mute it.

The stored local JWT was expired during initial setup inspection. No credential refresh or external deployment was performed.

## Boundaries

- Home-network presence is not identity.
- Desk mode is an explicit, short-lived demo consent gate.
- Only public projections are emitted.
- No actions, payments, wallet operations, or private context exist in this slice.
- Unknown pointer, raw page content, duplicate event, debounce, unavailable bridge, and mute states fail closed or stay silent.
- The current public-only response uses a demo signature and is not production cryptographic proof.

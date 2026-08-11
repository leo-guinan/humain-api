# OpenHome website-context demo

Status: local demonstration slice, not production deployment.

## What the demo proves

```text
BIPU browser extension
  → normalized HTTPS pointer event
  → loopback presence + consent gate
  → public-only HumAIn response
  → Marvin speech envelope
  → OpenHome one-shot delivery
```

The bridge now requires a fresh `near_verified` presence receipt in addition to explicit desk-mode arming. Candidate BLE sightings are insufficient.

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

The local proximity runner supports a complete simulator path:

```bash
PYTHONPATH=src python3 scripts/run_proximity.py --simulator
```

Real discovery is deliberately candidate-only until a device-specific signed GATT challenge is implemented:

```bash
PYTHONPATH=src python3 scripts/run_proximity.py \\
  --service-uuid YOUR_PAIRED_SERVICE_UUID
```

No BLE address is persisted or treated as identity. A candidate cannot become `near_verified` from RSSI alone.
A proximity broker must post a fresh `humain.proximity.presence.v1` receipt before the pointer event is accepted:

```text
POST http://127.0.0.1:8790/v1/openhome/presence
```

The receipt must have `presence_state=near_verified`, `flow_eligible=true`, and an `observed_at` timestamp no older than 30 seconds. Install the optional scanner adapter with:

```bash
python3 -m pip install -e '.[ble]'
```

The macOS adapter uses CoreBluetooth through `bleak`. If CoreBluetooth hangs or permissions are unavailable, it fails closed and emits no presence proof.

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

The reusable presence capability package is available at `openhome/proximity-presence.zip`. Other OpenHome abilities can call its `get_presence` DevKit function without implementing BLE or handling paired identifiers.

The speech consumer ability remains under `openhome/context-speaker/`; it polls the bridge's one-shot speech queue.

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

# Proximity pairing for the OpenHome demo

Status: proposed design, local demo first.

## Recommendation

Use Bluetooth as a proximity signal, not as the identity or authorization primitive.

For the demo, the strongest practical arrangement is:

```text
paired personal device (phone/watch/token)
        +
paired OpenHome/desk device
        +
short-lived signed challenge
        +
RSSI proximity confidence
        +
explicit local speech policy
        → bounded website-context flow
```

If only the OpenHome device is available, its presence may activate public-only speech. It must not unlock private context or actions.

## Why not a Bluetooth address

A BLE MAC address is a poor long-term identity:

- modern devices rotate private addresses;
- addresses can be observed and spoofed;
- RSSI is noisy and environment-dependent;
- a detected beacon proves radio reachability, not user presence;
- a replayed advertisement can look like the same device.

Pair a public key or platform pairing identity instead. Treat the observed BLE identifier as a lookup hint, not proof.

## Protocol

### Pairing ceremony

Pairing is explicit and local:

1. User puts the OpenHome device and personal device into pairing mode.
2. The broker displays a short code or requires an NFC/button confirmation.
3. The devices exchange public keys through the authenticated pairing channel.
4. The broker stores only:
   - device alias;
   - public key or platform identity;
   - allowed purpose (`presence_signal` or `desk_output`);
   - creation and expiry metadata;
   - revocation state.
5. No raw Bluetooth address becomes the durable identity.

The pairing receipt should include key fingerprints, not private material.

### Presence loop

```text
BLE advertisement detected
  → ephemeral identifier maps to paired candidate
  → broker samples RSSI for a short window
  → broker sends a fresh nonce challenge
  → paired device signs nonce + broker ID + purpose + timestamp
  → broker verifies signature and freshness
  → trajectory capsule records the movement
  → state becomes near_verified or remains candidate_only
```

A single advertisement must never trigger speech.

Recommended initial state machine:

```text
absent
  → candidate_near       # advertisement observed
  → near_verified        # challenge verified and RSSI window passes
  → flow_eligible        # local policy + consent + site event pass
  → active_flow
  → cooldown
  → absent
```

### RSSI policy

Do not use one magic threshold. Calibrate per room.

Use:

- median RSSI over a 5–10 second window;
- variance and packet count;
- hysteresis for enter/exit thresholds;
- a minimum dwell time;
- a cooldown per pointer and session.

Example demo policy:

```text
near candidate:    ≥ 3 observations in 5 seconds
near verified:     signed challenge + median RSSI above calibrated threshold
activate:          near_verified + site event + desk mode enabled
depart:            below exit threshold for 20 seconds
cooldown:          no repeat speech for 60 seconds per pointer
```

The numbers are starting points, not universal security constants.

## Activation policy

Proximity should activate only the lowest-risk flow by default:

```text
near_verified + public pointer
  → public_only Marvin context
```

For private projections:

```text
near_verified
  + explicit user consent
  + scoped capability
  + fresh signed request
  → permitted projection
```

For actions:

```text
near_verified
  + explicit spoken/physical confirmation
  + action capability
  + receipt
  → action
```

No private content should be spoken merely because a familiar device is nearby.

## Best demo sequence

1. Pair the Mac broker with the OpenHome device.
2. Pair a personal phone/watch if available.
3. Arm a five-minute desk session using a local button, NFC tap, or explicit command.
4. Browser extension emits the normalized site pointer.
5. Broker confirms both proximity and recent challenge.
6. HumAIn produces a `public_only` response.
7. OpenHome speaks the Marvin envelope.
8. User says “show the receipt.”
9. Browser or terminal displays the underlying pointer, state, provenance, and permissions.
10. Leaving the desk causes a verified departure and disables speech.

This demonstrates ambient context without pretending the room is a cryptographic factor.

## Where the code belongs

### Minimum demo

The Mac is the proximity broker:

```text
CoreBluetooth / BLE scanner
  → local proximity broker
  → HumAIn OpenHome bridge
  → browser event + OpenHome speech queue
```

The existing loopback bridge remains the policy boundary. Add a `presence_state` field to its status and require `near_verified` in addition to desk mode.

### OpenHome DevKit path

If the DevKit exposes compatible BLE hardware through a Local Ability, move scanning and challenge verification into `devkit_functions.py`. Keep the standard `main.py`/background daemon limited to receiving a bounded presence result and speaking a signed envelope.

Do not assume the standard cloud Ability runtime can scan the Mac's Bluetooth adapter. The DevKit-side path is hardware-specific and must be tested on the physical device.

### Separate-device path

If OpenHome runs on another device, `127.0.0.1` refers to that device, not the Mac. Use an explicitly paired LAN address or Local Link tunnel. Do not expose the bridge by binding to all interfaces without authentication.

## Trajectory integration

Presence is another movement stream, not a new trust system. Record only:

- paired device alias;
- candidate/verified/departed state;
- bounded RSSI statistics;
- challenge result class;
- transition timestamp;
- capsule and receipt hashes.

Do not retain raw BLE scans by default.

Useful movement patterns include:

- repeated arrival at the desk before website navigation;
- device appearing but challenge failing;
- rapid near/far oscillation;
- site events occurring while presence is only candidate-level;
- speech requested after departure;
- repeated pointer events during one verified session.

These patterns should change scrutiny and debounce behavior. They do not replace capabilities.

## Threat model

| Signal | What it proves | What it does not prove |
|---|---|---|
| BLE advertisement | a radio-visible candidate exists | identity or consent |
| RSSI window | approximate proximity | a specific person is present |
| signed challenge | possession of the paired key | that the key holder is the user |
| OpenHome device presence | output device is reachable | user authorization |
| desk mode | explicit local demo consent | permanent permission |
| trajectory continuity | movement resembles baseline | truth or authority |
| capability signature | scoped authorization | correctness of the underlying claim |

## Falsifiers

The design is failing if:

- a stale advertisement triggers speech;
- an unpaired device passes the challenge;
- a copied BLE identifier activates a flow;
- RSSI oscillation causes repeated speech;
- departure does not stop queued delivery;
- private content is spoken without a fresh capability;
- a familiar trajectory bypasses cryptographic verification;
- pairing survives revocation or key rotation;
- the system cannot explain why it activated.

The receipt for every activation should make the answer inspectable.

# HumAIn browser/OpenHome rendezvous

Status: implemented local verifier; browser and OpenHome transport adapters are not yet wired.

## Purpose

A rendezvous binds two independently authenticated claims to one short-lived,
public-only action. It does not claim to prove a person, attention, or physical
proximity.

```text
browser signature
  + OpenHome signature
  + fresh randomized ping from both sides
  + same signed bounded receipt
  + explicit human binding
  -> mutual_rendezvous
```

## Required evidence

- Browser and OpenHome use distinct registered Ed25519 keys.
- The server issues independent one-use nonces.
- Claims bind the rendezvous, normalized HTTPS origin/pathname, event ID, and expiry.
- A randomized ping is answered by both participants before its short TTL expires.
- Both participants sign the same bounded receipt hash.
- The user completes an explicit six-digit binding ceremony. In production, deliver
  this code through separate browser and OpenHome interfaces; do not put it in a
  public URL or stable user identifier.
- The resulting grant is single-use, public-only, and action-scoped.

## Tripwire mode

The bridge enables low-value tripwire mode for rendezvous grants. The browser
and OpenHome sides may submit bounded passive-scan observations, but never raw
Bluetooth addresses or device lists. Matching service UUID, short-lived
advertisement commitments, timestamps, and coarse RSSI values produce:

```text
corroborated_candidate_near
```

A mismatch, replay, stale observation, timing divergence, or large RSSI
 disagreement appends a `humain.rendezvous.tripwire.v1` receipt and permanently
quarantines that rendezvous. A tripwire never authorizes an action.

This is corroboration, not proof of physical proximity. The stock DevKit still
cannot produce `near_verified` without a signed runtime BLE challenge.


The local bridge exposes the verifier under `/v1/rendezvous/`.

Each rendezvous also receives a short-lived `observation_key_b64`. The browser
start response and the OpenHome pending response contain the same key so both
scanners can derive the same HMAC commitment. It expires with the rendezvous
and is not a durable credential.


```text
POST /start
POST /pending
POST /claim
POST /ping
POST /answer-ping
POST /receipt
POST /bind
POST /grant
```

The bridge must be started with the OpenHome public identity provisioned out of
band:

```bash
export HUMAIN_OPENHOME_KEY_REF=openhome:device-name
export HUMAIN_OPENHOME_PUBLIC_KEY_B64='...public-key-only...'
PYTHONPATH=src python3 run_openhome_bridge.py
```

The browser extension stores only `HUMAIN_OPENHOME_KEY_REF` in its local
configuration. The OpenHome private key remains on the OpenHome/DevKit side and
is used by `clients/rendezvous_client.py` or a Local Ability adapter to sign
claims, pings, and the shared receipt.

The browser never submits an OpenHome public key to `/start`. If the bridge has
no provisioned OpenHome identity, `/start` returns `rendezvous_not_configured`.

The laptop scanner can submit a bounded observation when the rendezvous service
has provisioned the same short-lived commitment key to both scanner sides:

```bash
export HUMAIN_RENDEZVOUS_ID=rv_...
export HUMAIN_OBSERVATION_KEY_B64='...short-lived-key...'
PYTHONPATH=src python3 scripts/run_proximity.py \
  --service-uuid 12345678-1234-5678-1234-56789abcdef0
```

The key is not printed by the runner. If the advertisement has no
manufacturer-data or service-data payload, the observation is marked
`uuid_only` and cannot promote a rendezvous; a shared service UUID is not a
device identity.


The protocol challenges receipt hashes, not semantic questions about a user's
recent behavior. A receipt can prove both parties know the same protocol event
without turning the server into a private browsing-history oracle.

## Failure rules

- Missing, stale, mismatched, or replayed claims fail closed.
- A BLE advertisement or RSSI observation cannot satisfy an OpenHome claim.
- A valid OpenHome claim does not prove that the device is near the browser.
- A shared receipt without explicit binding is insufficient.
- Query strings, fragments, page contents, and private projections are out of scope.
- A grant cannot be reused after consumption.

## VPS relay

The standalone rendezvous relay is deployed at:

```text
https://rendezvous.metaspn.network
```

It owns short-lived rendezvous state and exposes only the bounded rendezvous
routes. `/v1/rendezvous/pending` and `/v1/rendezvous/observation` require the
DevKit bearer token stored in the relay's root-only systemd EnvironmentFile.
The token is not in source, the browser extension, or this repository.

The relay does not hold an OpenHome API key, private signing key, raw BLE data,
or an arbitrary proxy route. It remains fail-closed until
`RELAY_OPENHOME_KEY_REF` and `RELAY_OPENHOME_PUBLIC_KEY_B64` are provisioned
from the enrolled OpenHome identity. The public key may be copied; the private
key must remain with the signer.

The DevKit observer must receive the corresponding runtime values:

```text
HUMAIN_RENDEZVOUS_URL=https://rendezvous.metaspn.network
HUMAIN_RENDEZVOUS_AUTH_TOKEN=<relay secret configured out-of-band>
HUMAIN_OPENHOME_KEY_REF=<same enrolled key reference>
```

A healthy relay is transport evidence, not proximity evidence. Matching
payload commitments remain `corroborated_candidate_near`, never
`near_verified`.

## Current implementation

`src/humain_api/rendezvous.py` implements the verifier and state machine.
`tests/test_rendezvous.py` covers the complete path and adversarial cases.
The transport adapters remain separate so a browser extension or OpenHome Local
Ability cannot weaken the verifier by changing network behavior.

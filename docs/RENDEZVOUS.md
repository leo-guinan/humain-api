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

## Adapter endpoints

The local bridge exposes the verifier under `/v1/rendezvous/`:

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

## Current implementation

`src/humain_api/rendezvous.py` implements the verifier and state machine.
`tests/test_rendezvous.py` covers the complete path and adversarial cases.
The transport adapters remain separate so a browser extension or OpenHome Local
Ability cannot weaken the verifier by changing network behavior.

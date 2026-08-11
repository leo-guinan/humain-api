# HumAIn Proximity Observer

OpenHome Local Ability that scans Bluetooth from the DevKit and submits only a
bounded observation for pending HumAIn rendezvous sessions.

## Runtime configuration

Configure these values in the DevKit runtime, not in the ZIP:

```text
HUMAIN_RENDEZVOUS_URL=https://your-relay.example
HUMAIN_OPENHOME_KEY_REF=openhome:device-name
HUMAIN_BLE_SERVICE_UUID=12345678-1234-5678-1234-56789abcdef0
```

The short-lived `observation_key_b64` is issued by the rendezvous service and
returned only in the pending rendezvous response. It is not persisted by the
ability.

The service URL must be reachable from the DevKit. `127.0.0.1` on the DevKit
is not the Mac bridge.

## Behavior

`scan_pending`:

1. asks the service for pending rendezvous sessions for the configured key
   reference;
2. scans only for the configured service UUID;
3. derives an HMAC commitment from service UUID, manufacturer data, and service
   data;
4. submits at most one strongest matching candidate per rendezvous;
5. returns counts and bounded states, never raw Bluetooth addresses or device
   lists.

If an advertisement contains only the shared service UUID, it is submitted as
`uuid_only`. The service will quarantine rather than promote that observation.
A device-specific payload is required for corroboration.

## Deployment boundary

This is a Local Ability. `main.py` runs the background polling wrapper;
`devkit_functions.py` runs the BLE scan on the actual DevKit. The package does
not contain an OpenHome API key, private key, relay secret, or fixed public
endpoint.

The result is still `corroborated_candidate_near`, not cryptographic physical
presence. The stock DevKit firmware has no signed runtime BLE challenge.

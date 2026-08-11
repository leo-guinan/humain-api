# HumAIn Proximity Presence

Reusable OpenHome Local Ability for other abilities to query the bounded local
presence result without implementing Bluetooth themselves.

## Contract

`get_presence` returns only:

- `presence_state`: `absent`, `candidate_near`, `near_verified`, or `unavailable`;
- `flow_eligible`;
- receipt timestamp;
- paired alias when available;
- structured error when unavailable.

It never returns a Bluetooth address, raw scan data, private context, or an
authorization capability.

## Architecture

```text
Mac BLE broker / OpenHome DevKit scanner
  → signed challenge + RSSI policy
  → loopback HumAIn bridge
  → this Local Ability: get_presence
  → consuming OpenHome abilities
```

The bridge must already be running on the same local device at
`http://127.0.0.1:8790`. If the ability runs on a separate DevKit, replace the
URL only with an explicitly paired local bridge address.

## Cross-ability use

Other abilities call the installed Local Ability through:

```python
result = await self.capability_worker.send_devkit_capability_action(
    function_name="get_presence",
    args=[],
    timeout=5,
    capability_name="humain-proximity-presence",
)
```

A consuming ability must treat `unavailable`, `absent`, and
`candidate_near` as non-authorizing states. `near_verified` only means that
the local policy may consider a bounded public flow; it does not unlock private
context or external actions.

## Validation

This package is intended to be uploaded as a Local Ability with `main.py`,
`devkit_functions.py`, `requirements.txt`, and `__init__.py`. The OpenHome
platform supplies `src.*` and `devkit_utils.*`; those imports are not expected
to resolve in the HumAIn repository's local Python environment.

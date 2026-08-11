# HumAIn Context Bootstrap

Boot capability for Marvin. It loads bounded HumAIn session context and invokes one authenticated proximity-observer pass through the installed Local Ability. It does not speak, infer identity, or grant proximity.

Required OpenHome API keys:

- `humain_rendezvous_url`
- `humain_rendezvous_auth_token`
- `humain_openhome_key_ref`

The provider/reference URL for each dashboard key is `https://rendezvous.metaspn.network`. The BLE service UUID is fixed public configuration in `main.py`.

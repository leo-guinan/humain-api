#!/usr/bin/env python3
"""Run the local-only HumAIn/OpenHome demo bridge on loopback."""
import os

from humain_api.openhome_bridge import OpenHomeBridge, make_openhome_bridge_server
from humain_api.rendezvous import Participant


if __name__ == "__main__":
    key_ref = os.environ.get("HUMAIN_OPENHOME_KEY_REF")
    public_key_b64 = os.environ.get("HUMAIN_OPENHOME_PUBLIC_KEY_B64")
    identity = Participant("openhome", key_ref, public_key_b64) if key_ref and public_key_b64 else None
    bridge = OpenHomeBridge(openhome_identity=identity)
    server = make_openhome_bridge_server("127.0.0.1", 8790, bridge)
    print("HumAIn OpenHome demo bridge: http://127.0.0.1:8790")
    print("Rendezvous identity: " + (key_ref if key_ref else "not configured"))
    server.serve_forever()

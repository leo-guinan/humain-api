#!/usr/bin/env python3
"""Run the local-only HumAIn/OpenHome demo bridge on loopback."""
from humain_api.openhome_bridge import OpenHomeBridge, make_openhome_bridge_server


if __name__ == "__main__":
    bridge = OpenHomeBridge()
    server = make_openhome_bridge_server("127.0.0.1", 8790, bridge)
    print("HumAIn OpenHome demo bridge: http://127.0.0.1:8790")
    server.serve_forever()

#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from humain_api.crypto import Ed25519Signer
from humain_api.http_service import make_server
from humain_api.resolver import Resolver

publisher = "did:key:humain-demo-publisher"
signer = Ed25519Signer.generate(publisher)
resolver = Resolver(publisher=publisher, verify_signature=lambda signature: signature.get("algorithm") == "ed25519")
server = make_server("127.0.0.1", 8787, resolver, {
    "https://story.markets/": {
        "schema": "humain.projection.story-markets.beginner.v1",
        "mode": "beginner",
        "projects": [],
        "source": "extension-owned-fixture"
    }
})
print(f"HumAIn resolver listening on http://127.0.0.1:8787 (publisher={publisher})")
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()

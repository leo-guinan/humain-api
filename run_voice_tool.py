#!/usr/bin/env python3
"""Start the local voice tool boundary. Sessions are registered by the call trigger."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from humain_api import Resolver, VoiceToolService, make_voice_server

resolver = Resolver(publisher="did:key:humain-demo-publisher", verify_signature=lambda signature: signature.get("algorithm") == "ed25519")
service = VoiceToolService(resolver, {})
server = make_voice_server("127.0.0.1", 8788, service)
print("HumAIn voice tool listening on http://127.0.0.1:8788")
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.shutdown()
    server.server_close()

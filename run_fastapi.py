"""Run the maintained resolver adapter with uvicorn."""
from __future__ import annotations

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from humain_api import Ed25519Signer, Ed25519Verifier, Resolver
from humain_api.fastapi_service import create_app
from humain_api.state import SQLiteStateStore


publisher_ref = os.environ.get("HUMAIN_PUBLISHER_KEY_REF", "")
publisher_private = os.environ.get("HUMAIN_PUBLISHER_PRIVATE_KEY_B64", "")
agent_ref = os.environ.get("HUMAIN_AGENT_KEY_REF", "")
agent_public = os.environ.get("HUMAIN_AGENT_PUBLIC_KEY_B64", "")
mode = os.environ.get("HUMAIN_RESOLVER_MODE", "production")
state_path = os.environ.get("HUMAIN_STATE_PATH", "")

if mode == "production" and (not publisher_ref or not publisher_private or not agent_ref or not agent_public):
    raise RuntimeError("production requires publisher and agent key configuration")

publisher = getattr(Ed25519Signer, "from_" + "private_key_b64")(publisher_ref, publisher_private) if publisher_private else None
verifier = Ed25519Verifier({agent_ref: agent_public}) if agent_public else None
resolver = Resolver(
    publisher=publisher_ref or "reference-publisher",
    verify_signature=verifier,
    response_signer=publisher,
    mode=mode,
    state_store=SQLiteStateStore(state_path) if state_path else None,
)
app = create_app(resolver, {}, max_body_bytes=int(os.environ.get("HUMAIN_MAX_BODY_BYTES", "1048576")))

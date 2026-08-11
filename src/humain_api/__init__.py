"""Small, transport-neutral HumAIn API reference substrate."""

from .canonical import canonical_bytes, content_hash
from .crypto import Ed25519Signer, Ed25519Verifier
from .models import Capability, ResolutionRequest, ValidationError
from .memetic import MARVIN_BODEGA_CAT, MemeticProfile, humanize, unwrap
from .openhome_bridge import OpenHomeBridge, make_openhome_bridge_server
from .receipt import Receipt
from .resolver import Resolver
from .trajectory import TrajectoryCapsule, compare_trajectories, compress_events
from .voice_service import VoiceToolService, make_voice_server

__all__ = ["Capability", "Ed25519Signer", "Ed25519Verifier", "MARVIN_BODEGA_CAT", "MemeticProfile", "OpenHomeBridge", "Receipt", "ResolutionRequest", "Resolver", "TrajectoryCapsule", "ValidationError", "VoiceToolService", "canonical_bytes", "compare_trajectories", "compress_events", "content_hash", "humanize", "make_openhome_bridge_server", "make_voice_server", "unwrap"]

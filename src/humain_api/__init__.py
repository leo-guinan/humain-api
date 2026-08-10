"""Small, transport-neutral HumAIn API reference substrate."""

from .canonical import canonical_bytes, content_hash
from .crypto import Ed25519Signer, Ed25519Verifier
from .models import Capability, ResolutionRequest, ValidationError
from .memetic import MARVIN_BODEGA_CAT, MemeticProfile, humanize, unwrap
from .receipt import Receipt
from .resolver import Resolver
from .voice_service import VoiceToolService, make_voice_server

__all__ = ["Capability", "Ed25519Signer", "Ed25519Verifier", "MARVIN_BODEGA_CAT", "MemeticProfile", "Receipt", "ResolutionRequest", "Resolver", "ValidationError", "VoiceToolService", "canonical_bytes", "content_hash", "humanize", "make_voice_server", "unwrap"]

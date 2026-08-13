"""Small, transport-neutral HumAIn API reference substrate."""

from .ble_adapter import BleCandidate, BleakDiscoveryAdapter, OPENHOME_DEVKIT_SERVICE_UUID
from .capability import CapabilityIssuer, CapabilityRegistry
from .canonical import canonical_bytes, content_hash
from .crypto import Ed25519Signer, Ed25519Verifier
from .models import Capability, ResolutionRequest, ValidationError
from .rendezvous import Participant, RendezvousBroker
from .memetic import MARVIN_BODEGA_CAT, MemeticProfile, humanize, unwrap
from .openhome_bridge import OpenHomeBridge, make_openhome_bridge_server
from .proximity import Pairing, PresenceBroker, sign_challenge
from .receipt import Receipt
from .resolver import Resolver
from .state import SQLiteStateStore
from .trajectory import TrajectoryCapsule, compare_trajectories, compress_events
from .voice_service import VoiceToolService, make_voice_server

__all__ = ["BleCandidate", "BleakDiscoveryAdapter", "Capability", "CapabilityIssuer", "CapabilityRegistry", "Ed25519Signer", "Ed25519Verifier", "MARVIN_BODEGA_CAT", "MemeticProfile", "OpenHomeBridge", "Pairing", "PresenceBroker", "Receipt", "ResolutionRequest", "Resolver", "SQLiteStateStore", "TrajectoryCapsule", "ValidationError", "VoiceToolService", "canonical_bytes", "compare_trajectories", "compress_events", "content_hash", "humanize", "make_openhome_bridge_server", "make_voice_server", "sign_challenge", "unwrap"]

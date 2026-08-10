"""Memetic presentation layer: compress protocol state without changing it."""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MemeticProfile:
    profile_id: str
    persona_name: str
    detail_label: str
    voice: str


MARVIN_BODEGA_CAT = MemeticProfile(
    profile_id="marvin.bodega-cat.v1",
    persona_name="Marvin, the AI bodega cat",
    detail_label="show the receipt",
    voice="dry, sleepy, specific, protective of the register",
)


_MESSAGES = {
    "public_only": "The bodega cat checked the public shelf. The back room is not open to this node.",
    "trusted_projection": "The bodega cat checked the shelf. There is a permitted note behind the counter.",
    "mutual_trust": "The bodega cat and the other shop both recognized the pass. The back room is open for this request.",
    "denied": "The bodega cat knocked on the back door. Nobody let it in.",
    "unavailable": "The bodega cat is asleep behind the register. The resolver did not answer.",
}


def humanize(response: dict[str, Any], profile: MemeticProfile = MARVIN_BODEGA_CAT) -> dict[str, Any]:
    """Return a human-facing projection while preserving the underlying state."""
    state = response.get("resolution_state", "unavailable")
    message = _MESSAGES.get(state, _MESSAGES["unavailable"])
    return {
        "schema": "humain.memetic.response.v1",
        "profile": profile.profile_id,
        "persona": profile.persona_name,
        "surface_text": message,
        "resolution_state": state,
        "detail_label": profile.detail_label,
        "details_available": state in {"trusted_projection", "mutual_trust", "public_only"},
        "provenance": response.get("provenance", {}),
        "underlying_response": response,
    }


def unwrap(memetic_response: dict[str, Any]) -> dict[str, Any]:
    """Return the preserved protocol response, never a reconstructed summary."""
    return memetic_response["underlying_response"]

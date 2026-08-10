from dataclasses import asdict, dataclass
from typing import Any

from .models import ValidationError


@dataclass(frozen=True)
class Receipt:
    receipt_id: str
    pointer: str
    promise: str
    result: str | None
    status: str
    evidence: tuple[str, ...] = ()
    visibility: str = "private"

    def __post_init__(self):
        if self.status not in {"open", "closed"}:
            raise ValidationError("receipt status must be open or closed")
        if self.status == "closed" and not self.result:
            raise ValidationError("closed receipts require an observed result")
        if not self.promise.strip():
            raise ValidationError("receipt promise cannot be empty")
        if self.visibility not in {"private", "shared", "public"}:
            raise ValidationError("invalid receipt visibility")

    def close(self, result: str, *, evidence: tuple[str, ...] = ()) -> "Receipt":
        if self.status == "closed":
            raise ValidationError("closed receipts cannot be overwritten; append a correction")
        return Receipt(self.receipt_id, self.pointer, self.promise, result, "closed", evidence, self.visibility)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence"] = list(self.evidence)
        value["schema"] = "humain.receipt.v1"
        return value

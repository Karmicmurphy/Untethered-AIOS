from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
import hashlib
import json

@dataclass(frozen=True)
class Receipt:
    kind: str
    actor: str
    action: str
    detail: dict[str, Any]
    created_at: str
    sha256: str

class AuditLog:
    def __init__(self) -> None:
        self.receipts: list[Receipt] = []

    def emit(self, kind: str, actor: str, action: str, detail: dict[str, Any] | None = None) -> Receipt:
        created_at = datetime.now(timezone.utc).isoformat()
        body = {
            "kind": kind,
            "actor": actor,
            "action": action,
            "detail": detail or {},
            "created_at": created_at,
        }
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        receipt = Receipt(**body, sha256=digest)
        self.receipts.append(receipt)
        return receipt

    def as_dicts(self) -> list[dict[str, Any]]:
        return [asdict(r) for r in self.receipts]

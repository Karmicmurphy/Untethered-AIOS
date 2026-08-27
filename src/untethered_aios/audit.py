from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Callable, Protocol


class ReceiptSink(Protocol):
    def append_receipt(self, receipt: dict[str, Any]) -> None: ...

    def list_receipts(self) -> list[dict[str, Any]]: ...


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def hash_value(value: Any) -> str:
    if isinstance(value, bytes):
        payload = value
    else:
        payload = _canonical_json(value)
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class Receipt:
    sequence: int
    kind: str
    actor: str
    action: str
    target: str | None
    pid: int | None
    parent_pid: int | None
    detail: dict[str, Any]
    created_at: str
    previous_sha256: str | None
    sha256: str


class AuditLog:
    def __init__(
        self,
        *,
        sink: ReceiptSink | None = None,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self._sink = sink
        self._clock = clock or _utc_now
        persisted = sink.list_receipts() if sink is not None else []
        self.receipts: list[Receipt] = [Receipt(**item) for item in persisted]
        valid, errors = self.verify_chain()
        if not valid:
            raise ValueError("persisted receipt chain is invalid: " + "; ".join(errors))

    def emit(
        self,
        kind: str,
        actor: str,
        action: str,
        detail: dict[str, Any] | None = None,
        *,
        target: str | None = None,
        pid: int | None = None,
        parent_pid: int | None = None,
    ) -> Receipt:
        body = {
            "sequence": len(self.receipts) + 1,
            "kind": kind,
            "actor": actor,
            "action": action,
            "target": target,
            "pid": pid,
            "parent_pid": parent_pid,
            "detail": detail or {},
            "created_at": self._clock(),
            "previous_sha256": self.receipts[-1].sha256 if self.receipts else None,
        }
        digest = hashlib.sha256(_canonical_json(body)).hexdigest()
        receipt = Receipt(**body, sha256=digest)
        if self._sink is not None:
            self._sink.append_receipt(asdict(receipt))
        self.receipts.append(receipt)
        return receipt

    def as_dicts(self) -> list[dict[str, Any]]:
        return [asdict(receipt) for receipt in self.receipts]

    def verify_chain(self) -> tuple[bool, tuple[str, ...]]:
        errors: list[str] = []
        previous = None
        for expected_sequence, receipt in enumerate(self.receipts, start=1):
            body = asdict(receipt)
            claimed = body.pop("sha256")
            calculated = hashlib.sha256(_canonical_json(body)).hexdigest()
            if receipt.sequence != expected_sequence:
                errors.append(f"receipt {expected_sequence}: sequence mismatch")
            if receipt.previous_sha256 != previous:
                errors.append(f"receipt {expected_sequence}: previous hash mismatch")
            if claimed != calculated:
                errors.append(f"receipt {expected_sequence}: hash mismatch")
            previous = claimed
        return not errors, tuple(errors)

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from companion.foundation.path_policy import WindowsPathPolicy

WORKER_ID = "reference-metadata-worker"
WORKER_VERSION = "0.1.0"
OUTPUT_SCHEMA_VERSION = "0.1"
MAX_INPUT_BYTES = 256 * 1024
MAX_OUTPUT_BYTES = 32 * 1024
MAX_REQUEST_BYTES = 64 * 1024
MAX_HEADINGS = 100


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def _metadata(input_path: Path, content: str, raw: bytes) -> dict[str, Any]:
    headings: list[dict[str, Any]] = []
    for line in content.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match and len(headings) < MAX_HEADINGS:
            headings.append({"level": len(match.group(1)), "text": match.group(2)[:300]})
    words = re.findall(r"\b[\w'-]+\b", content, flags=re.UNICODE)
    return {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "worker_id": WORKER_ID,
        "worker_version": WORKER_VERSION,
        "input_filename": input_path.name,
        "input_sha256": _sha256_bytes(raw),
        "size_bytes": len(raw),
        "line_count": len(content.splitlines()),
        "word_count": len(words),
        "headings": headings,
    }


def run_request(request: dict[str, Any]) -> dict[str, Any]:
    policy = WindowsPathPolicy(
        read_roots=request["read_roots"],
        write_roots=request["write_roots"],
        blocked_roots=request.get("blocked_roots", []),
    )
    input_path = policy.decide(request["input_path"], mode="read").require_allowed()
    output_path = policy.decide(request["output_path"], mode="write").require_allowed()
    if input_path.suffix.casefold() not in {".txt", ".md"}:
        raise ValueError("reference worker accepts only .txt or .md input")
    if output_path.suffix.casefold() != ".json":
        raise ValueError("reference worker output must be JSON")
    if input_path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("reference worker input exceeds 256 KiB")
    raw = input_path.read_bytes()
    content = raw.decode("utf-8", errors="strict")
    result = _metadata(input_path, content, raw)

    fault_mode = request.get("fault_mode")
    if fault_mode == "sleep":
        time.sleep(float(request.get("fault_seconds", 5)))
    elif fault_mode == "worker_failure":
        raise RuntimeError("test-only simulated worker failure")
    elif fault_mode == "invalid_output":
        result.pop("input_sha256")
    elif fault_mode == "declared_test_failure":
        result["word_count"] += 1
    elif fault_mode == "unexpected_file":
        unexpected = policy.decide(output_path.parent / "unexpected.txt", mode="write").require_allowed()
        _atomic_write(unexpected, b"test-only unexpected output\n")
    elif fault_mode == "malformed_json":
        _atomic_write(output_path, b"{malformed")
        return {"ok": True, "fault_mode": fault_mode}
    elif fault_mode == "oversized_output":
        result["padding"] = "x" * MAX_OUTPUT_BYTES
    elif fault_mode == "oversized_capture":
        sys.stdout.write("x" * (128 * 1024))
        sys.stdout.flush()

    encoded = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    _atomic_write(output_path, encoded)
    print("reference worker completed", flush=True)
    return {"ok": True, "output_sha256": _sha256_bytes(encoded), "size_bytes": len(encoded)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fixed harmless Twis Holo reference worker")
    parser.add_argument("--request", required=True)
    parser.add_argument("--request-sha256", required=True)
    args = parser.parse_args(argv)
    request_path = Path(args.request).resolve(strict=True)
    if request_path.suffix.casefold() != ".json" or request_path.stat().st_size > MAX_REQUEST_BYTES:
        print("invalid reference worker request", file=sys.stderr)
        return 2
    try:
        request_bytes = request_path.read_bytes()
        if not re.fullmatch(r"[A-Fa-f0-9]{64}", args.request_sha256) or _sha256_bytes(request_bytes) != args.request_sha256.upper():
            print("reference worker request hash mismatch", file=sys.stderr)
            return 2
        request = json.loads(request_bytes.decode("utf-8"))
        run_request(request)
        return 0
    except Exception as exc:
        print(f"reference worker failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 7


if __name__ == "__main__":
    raise SystemExit(main())

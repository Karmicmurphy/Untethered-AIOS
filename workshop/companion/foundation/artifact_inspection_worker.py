from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from companion.foundation.path_policy import WindowsPathPolicy


WORKER_ID = "artifact-compass-inspection-worker"
WORKER_VERSION = "0.4.0"
OUTPUT_SCHEMA_VERSION = "0.4"
SUPPORTED_EXTENSIONS = {".txt", ".md", ".json", ".py", ".js", ".html", ".css"}
FILE_TYPES = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".json": "application/json",
    ".py": "text/x-python",
    ".js": "text/javascript",
    ".html": "text/html",
    ".css": "text/css",
}
MAX_INPUT_BYTES = 512 * 1024
MAX_OUTPUT_BYTES = 128 * 1024
MAX_ITEMS_PER_FIELD = 256
SHA256_PATTERN = re.compile(r"^[A-Fa-f0-9]{64}$")
WORD_PATTERN = re.compile(r"\b[\w'-]+\b", re.UNICODE)
MARKDOWN_HEADING_PATTERN = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$")
HTML_HEADING_PATTERN = re.compile(r"<h([1-6])\b[^>]*>(.*?)</h\1\s*>", re.IGNORECASE | re.DOTALL)
MARKDOWN_LINK_PATTERN = re.compile(r"!?\[([^\]]*)\]\(([^)\s]+)(?:\s+[^)]*)?\)")
HTML_LINK_PATTERN = re.compile(r"\b(?:href|src)\s*=\s*(['\"])(.*?)\1", re.IGNORECASE | re.DOTALL)
URL_PATTERN = re.compile(r"https?://[^\s<>\"')\]]+")
TAG_PATTERN = re.compile(r"<[^>]+>")
TODO_PATTERN = re.compile(r"\b(TODO|FIXME)\b", re.IGNORECASE)
PYTHON_SYMBOL_PATTERN = re.compile(r"^\s*(async\s+def|def|class)\s+([A-Za-z_]\w*)", re.MULTILINE)
JAVASCRIPT_SYMBOL_PATTERN = re.compile(
    r"^\s*(?:export\s+)?(?:(async)\s+)?(function|class|const|let|var)\s+([A-Za-z_$][\w$]*)",
    re.MULTILINE,
)
CSS_SELECTOR_PATTERN = re.compile(r"^\s*([^@\s][^{]{0,200})\s*\{", re.MULTILINE)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


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


def _bounded(items: list[dict[str, Any]], warning: str, warnings: list[str]) -> list[dict[str, Any]]:
    if len(items) > MAX_ITEMS_PER_FIELD:
        warnings.append(warning)
    return items[:MAX_ITEMS_PER_FIELD]


def _headings(content: str, suffix: str, warnings: list[str]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    if suffix == ".md":
        for line_number, line in enumerate(content.splitlines(), start=1):
            match = MARKDOWN_HEADING_PATTERN.match(line)
            if match:
                values.append(
                    {"level": len(match.group(1)), "line": line_number, "text": match.group(2).strip()[:300]}
                )
    elif suffix == ".html":
        for match in HTML_HEADING_PATTERN.finditer(content):
            line_number = content.count("\n", 0, match.start()) + 1
            text = TAG_PATTERN.sub("", match.group(2)).strip()
            values.append({"level": int(match.group(1)), "line": line_number, "text": text[:300]})
    return _bounded(values, "headings_truncated_to_256", warnings)


def _code_symbols(content: str, suffix: str, warnings: list[str]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    if suffix == ".py":
        for match in PYTHON_SYMBOL_PATTERN.finditer(content):
            values.append(
                {
                    "kind": match.group(1).replace(" ", "_"),
                    "name": match.group(2),
                    "line": content.count("\n", 0, match.start()) + 1,
                }
            )
    elif suffix == ".js":
        for match in JAVASCRIPT_SYMBOL_PATTERN.finditer(content):
            values.append(
                {
                    "kind": ("async_" if match.group(1) else "") + match.group(2),
                    "name": match.group(3),
                    "line": content.count("\n", 0, match.start()) + 1,
                }
            )
    elif suffix == ".css":
        for match in CSS_SELECTOR_PATTERN.finditer(content):
            selector = " ".join(match.group(1).split())
            values.append(
                {
                    "kind": "selector",
                    "name": selector[:200],
                    "line": content.count("\n", 0, match.start()) + 1,
                }
            )
    return _bounded(values, "code_symbols_truncated_to_256", warnings)


def _links(content: str, warnings: list[str]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    for kind, pattern, target_group in (
        ("markdown", MARKDOWN_LINK_PATTERN, 2),
        ("html_attribute", HTML_LINK_PATTERN, 2),
        ("url", URL_PATTERN, 0),
    ):
        for match in pattern.finditer(content):
            target = match.group(target_group).strip()[:500]
            line = content.count("\n", 0, match.start()) + 1
            identity = (kind, target, line)
            if identity in seen:
                continue
            seen.add(identity)
            values.append({"kind": kind, "target": target, "line": line})
    values.sort(key=lambda item: (item["line"], item["kind"], item["target"]))
    return _bounded(values, "links_truncated_to_256", warnings)


def _todo_markers(content: str, warnings: list[str]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        for match in TODO_PATTERN.finditer(line):
            values.append(
                {
                    "marker": match.group(1).upper(),
                    "line": line_number,
                    "excerpt": line.strip()[:160],
                }
            )
    return _bounded(values, "todo_fixme_markers_truncated_to_256", warnings)


def _likely_purpose(path: Path, suffix: str, content: str, headings: list[dict[str, Any]]) -> dict[str, Any]:
    filename = path.name.casefold()
    heading_text = " ".join(str(item.get("text", "")) for item in headings).casefold()
    prefix = content[:8192].casefold()
    if filename.startswith("readme"):
        label, rule = "project_overview", "filename_starts_with_readme"
    elif any(token in filename for token in ("receipt", "ledger")):
        label, rule = "receipt_or_ledger", "filename_contains_receipt_or_ledger"
    elif any(token in filename for token in ("release", "debug_report", "audit", "report")):
        label, rule = "status_or_verification_report", "filename_contains_release_report_audit_or_debug_report"
    elif suffix in {".py", ".js", ".html", ".css"}:
        label, rule = "source_code", f"file_extension_is_{suffix[1:]}"
    elif suffix == ".json":
        label, rule = "structured_data", "file_extension_is_json"
    elif "api" in filename or "api" in heading_text:
        label, rule = "api_documentation", "filename_or_heading_contains_api"
    elif "plan" in filename or "roadmap" in prefix:
        label, rule = "planning_document", "filename_contains_plan_or_opening_text_contains_roadmap"
    elif "handoff" in filename or "handoff" in heading_text:
        label, rule = "handoff_document", "filename_or_heading_contains_handoff"
    else:
        label, rule = "general_text_document", "no_more_specific_rule_matched"
    return {"label": label, "classification": "heuristic_not_fact", "rule": rule}


def _validate_text_bytes(raw: bytes) -> str:
    if b"\x00" in raw:
        raise ValueError("binary content is not accepted: NUL byte detected")
    if raw:
        control_count = sum(byte < 32 and byte not in {9, 10, 13} for byte in raw)
        if control_count / len(raw) > 0.01:
            raise ValueError("binary content is not accepted: excessive control bytes detected")
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("artifact must be valid UTF-8 text") from exc


def inspect_content(
    *,
    artifact: dict[str, Any],
    source_path: Path,
    content: str,
    raw: bytes,
    inspection_timestamp: str,
) -> dict[str, Any]:
    suffix = source_path.suffix.lower()
    warnings: list[str] = []
    lowered = content.casefold()
    if "ignore previous instructions" in lowered or "system prompt" in lowered:
        warnings.append("instruction_like_content_treated_as_inert_text")
    if suffix in {".html", ".md"} and ("<script" in lowered or "javascript:" in lowered):
        warnings.append("active_markup_treated_as_inert_text")
    headings = _headings(content, suffix, warnings)
    report = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "artifact_id": artifact["artifact_id"],
        "source_path": str(source_path),
        "source_sha256": _sha256_bytes(raw),
        "file_type": FILE_TYPES[suffix],
        "byte_count": len(raw),
        "line_count": len(content.splitlines()),
        "word_count": len(WORD_PATTERN.findall(content)),
        "headings": headings,
        "code_symbols": _code_symbols(content, suffix, warnings),
        "links": _links(content, warnings),
        "likely_document_purpose": _likely_purpose(source_path, suffix, content, headings),
        "todo_fixme_markers": _todo_markers(content, warnings),
        "duplicate_hash_group": artifact.get("duplicate_hash_group", []),
        "provenance_references": artifact.get("provenance_references", []),
        "review_status": artifact.get("review_status", "unreviewed"),
        "warnings": sorted(set(warnings)),
        "inspection_timestamp": inspection_timestamp,
        "inspector_version": WORKER_VERSION,
    }
    return report


def run_request(request: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "artifact",
        "input_path",
        "output_path",
        "read_roots",
        "write_roots",
        "blocked_roots",
        "max_input_bytes",
        "max_output_bytes",
        "inspection_timestamp",
    }
    optional = {"fault_mode", "fault_seconds"}
    if set(request) - required - optional or not required.issubset(request):
        raise ValueError("inspection request fields do not match the fixed contract")
    if request["schema_version"] != OUTPUT_SCHEMA_VERSION:
        raise ValueError("unsupported inspection request schema")
    if request["max_input_bytes"] != MAX_INPUT_BYTES or request["max_output_bytes"] != MAX_OUTPUT_BYTES:
        raise ValueError("inspection size limits differ from the fixed worker contract")
    artifact = request["artifact"]
    if not isinstance(artifact, dict):
        raise ValueError("artifact descriptor must be an object")
    artifact_required = {
        "artifact_id",
        "source_sha256",
        "review_status",
        "duplicate_hash_group",
        "provenance_references",
    }
    if set(artifact) != artifact_required:
        raise ValueError("artifact descriptor fields do not match the fixed contract")
    if not isinstance(artifact["artifact_id"], str) or not artifact["artifact_id"].strip() or len(artifact["artifact_id"]) > 200:
        raise ValueError("artifact ID is required")
    if not isinstance(artifact["source_sha256"], str) or not SHA256_PATTERN.fullmatch(artifact["source_sha256"]):
        raise ValueError("artifact source SHA-256 is invalid")
    if not isinstance(artifact["review_status"], str) or not artifact["review_status"].strip():
        raise ValueError("artifact review status is required")
    for field in ("duplicate_hash_group", "provenance_references"):
        if not isinstance(artifact[field], list) or len(artifact[field]) > 100:
            raise ValueError(f"artifact {field} is invalid or excessive")
    try:
        parsed_timestamp = datetime.fromisoformat(str(request["inspection_timestamp"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("inspection timestamp must be ISO-8601") from exc
    if parsed_timestamp.tzinfo is None:
        raise ValueError("inspection timestamp must include a timezone")

    policy = WindowsPathPolicy(
        read_roots=request["read_roots"],
        write_roots=request["write_roots"],
        blocked_roots=request["blocked_roots"],
    )
    source_path = policy.decide(request["input_path"], mode="read").require_allowed()
    output_path = policy.decide(request["output_path"], mode="write", require_exists=False).require_allowed()
    suffix = source_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"unsupported artifact extension: {suffix or '<none>'}")
    if output_path.suffix.lower() != ".json":
        raise ValueError("inspection output must be a JSON file")
    if not source_path.is_file():
        raise ValueError("selected artifact is not a file")
    if source_path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("selected artifact exceeds the 512 KiB input limit")

    expected_hash = artifact["source_sha256"].upper()
    before_hash = _sha256_file(source_path)
    if before_hash != expected_hash:
        raise ValueError("selected artifact hash changed before reading")
    raw = source_path.read_bytes()
    if _sha256_bytes(raw) != expected_hash:
        raise ValueError("selected artifact changed while being read")
    content = _validate_text_bytes(raw)

    fault_mode = request.get("fault_mode")
    if fault_mode == "sleep_after_read":
        time.sleep(float(request.get("fault_seconds", 1)))
    after_hash = _sha256_file(source_path)
    if after_hash != expected_hash:
        raise ValueError("selected artifact changed during inspection")

    report = inspect_content(
        artifact=artifact,
        source_path=source_path,
        content=content,
        raw=raw,
        inspection_timestamp=request["inspection_timestamp"],
    )
    if fault_mode == "invalid_output":
        report.pop("artifact_id")
    elif fault_mode == "oversized_output":
        report["warnings"] = ["x" * (MAX_OUTPUT_BYTES + 1)]
    elif fault_mode == "unexpected_file":
        (output_path.parent / "unexpected-inspection.txt").write_text("unexpected", encoding="utf-8")
    elif fault_mode == "worker_failure":
        raise RuntimeError("test-only artifact inspection failure")

    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    if len(encoded) > MAX_OUTPUT_BYTES:
        raise ValueError("inspection output exceeds the 128 KiB output limit")
    _atomic_write(output_path, encoded)
    final_hash = _sha256_file(source_path)
    if final_hash != expected_hash:
        raise ValueError("selected artifact changed before inspection completed")
    return {
        "ok": True,
        "output_sha256": _sha256_bytes(encoded),
        "size_bytes": len(encoded),
        "source_sha256_before": before_hash,
        "source_sha256_after": final_hash,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fixed read-only Artifact Compass inspection worker")
    parser.add_argument("--request", required=True)
    parser.add_argument("--request-sha256", required=True)
    arguments = parser.parse_args(argv)
    try:
        request_path = Path(arguments.request)
        request_bytes = request_path.read_bytes()
        if not SHA256_PATTERN.fullmatch(arguments.request_sha256) or _sha256_bytes(request_bytes) != arguments.request_sha256.upper():
            raise ValueError("request file SHA-256 mismatch")
        request = json.loads(request_bytes.decode("utf-8"))
        if not isinstance(request, dict):
            raise ValueError("request must be a JSON object")
        result = run_request(request)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(f"artifact inspection worker rejected request: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

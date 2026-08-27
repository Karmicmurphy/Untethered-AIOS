from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

EXCLUDED_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".pytest_cache", "cache", "caches", "tmp", "temp", "logs",
    "data", "private_source_artifacts",
}
EXCLUDED_SUFFIXES = {
    ".db", ".sqlite", ".sqlite3", ".wal", ".shm", ".pyc", ".zip",
    ".exe", ".pdb", "-wal", "-shm", "-journal",
}
EXCLUDED_NAMES = {
    ".env", ".env.local", ".env.production", "flashriver_receipt.json",
}

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def tree_digest(entries: list[dict]) -> str:
    h = hashlib.sha256()
    for entry in sorted(entries, key=lambda item: item["path"]):
        h.update(
            f'{entry["path"]}\0{entry["size"]}\0{entry["sha256"]}\n'.encode("utf-8")
        )
    return h.hexdigest()

def safe_files(root: Path):
    excluded = []
    included = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        parts_lower = {p.lower() for p in rel.parts}
        if any(d.lower() in parts_lower for d in EXCLUDED_DIRS):
            if path.is_file():
                excluded.append((str(rel), "excluded directory"))
            continue
        if not path.is_file():
            continue
        name_lower = path.name.lower()
        if (
            name_lower in EXCLUDED_NAMES
            or name_lower.startswith(".env.")
            or any(name_lower.endswith(suffix) for suffix in EXCLUDED_SUFFIXES)
        ):
            excluded.append((str(rel), "private/runtime file class"))
            continue
        included.append(path)
    return included, excluded

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workshop", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(args.workshop).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Workshop directory not found: {root}")

    paths, excluded = safe_files(root)
    manifest = []
    for path in paths:
        rel = path.relative_to(root).as_posix()
        digest = sha256_file(path)
        size = path.stat().st_size
        manifest.append({"path": rel, "size": size, "sha256": digest})

    tree_sha256 = tree_digest(manifest)

    output = {
        "format": "twis-untethered-workshop-baseline-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(root),
        "included_file_count": len(manifest),
        "excluded_file_count": len(excluded),
        "code_safe_tree_sha256": tree_sha256,
        "files": manifest,
        "excluded": [{"path": p, "reason": reason} for p, reason in excluded],
        "warning": "This is a code-safe manifest, not proof that every excluded file is private and not proof of live functional health.",
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"Included files: {len(manifest)}")
    print(f"Excluded files: {len(excluded)}")
    print(f"Tree SHA-256: {tree_sha256}")

if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


class ImportErrorSafe(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_digest(entries: list[dict]) -> str:
    h = hashlib.sha256()
    for entry in sorted(entries, key=lambda e: e["path"]):
        h.update(
            f'{entry["path"]}\0{entry["size"]}\0{entry["sha256"]}\n'.encode("utf-8")
        )
    return h.hexdigest()


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != "twis-untethered-workshop-baseline-v1":
        raise ImportErrorSafe("unsupported or missing baseline manifest format")
    if not isinstance(data.get("files"), list):
        raise ImportErrorSafe("baseline manifest has no files list")
    return data


def verify_source(manifest: dict, source: Path) -> list[dict]:
    verified = []
    for entry in manifest["files"]:
        rel = Path(entry["path"])
        if rel.is_absolute() or ".." in rel.parts:
            raise ImportErrorSafe(f"unsafe manifest path: {entry['path']}")
        src = source / rel
        if not src.is_file():
            raise ImportErrorSafe(f"source file missing: {rel}")
        size = src.stat().st_size
        digest = sha256_file(src)
        if size != entry["size"] or digest != entry["sha256"]:
            raise ImportErrorSafe(f"source mismatch: {rel}")
        verified.append({"path": rel.as_posix(), "size": size, "sha256": digest})

    digest = tree_digest(verified)
    expected = manifest.get("code_safe_tree_sha256")
    if expected and digest != expected:
        raise ImportErrorSafe(
            f"source tree hash mismatch: expected {expected}, got {digest}"
        )
    return verified


def ensure_clean_destination(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    existing = [p for p in destination.rglob("*") if p.is_file()]
    allowed_placeholder = destination / "README.md"
    unexpected = [p for p in existing if p.resolve() != allowed_placeholder.resolve()]
    if unexpected:
        rels = ", ".join(str(p.relative_to(destination)) for p in unexpected[:10])
        raise ImportErrorSafe(
            "destination is not clean; refusing to overwrite existing baseline files: "
            + rels
        )


def copy_verified(manifest: dict, source: Path, destination: Path) -> list[dict]:
    ensure_clean_destination(destination)
    copied = []

    for entry in manifest["files"]:
        rel = Path(entry["path"])
        src = source / rel
        dst = destination / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

        size = dst.stat().st_size
        digest = sha256_file(dst)
        if size != entry["size"] or digest != entry["sha256"]:
            raise ImportErrorSafe(f"copied file verification failed: {rel}")
        copied.append({"path": rel.as_posix(), "size": size, "sha256": digest})

    digest = tree_digest(copied)
    expected = manifest.get("code_safe_tree_sha256")
    if expected and digest != expected:
        raise ImportErrorSafe(
            f"copied tree hash mismatch: expected {expected}, got {digest}"
        )
    return copied


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy an authenticated code-safe Workshop baseline into this repo."
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--destination", default="workshop")
    parser.add_argument(
        "--source",
        help="Override the source path stored in the manifest.",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest = load_manifest(manifest_path)

    source = Path(args.source or manifest["source"]).expanduser().resolve()
    destination = Path(args.destination).expanduser().resolve()

    if not source.is_dir():
        raise SystemExit(f"Workshop source not found: {source}")
    if source == destination or destination in source.parents:
        raise SystemExit("destination must not be the authoritative Workshop source")

    verify_source(manifest, source)
    copied = copy_verified(manifest, source, destination)

    print(f"Verified source: {source}")
    print(f"Copied files: {len(copied)}")
    print(f"Destination: {destination}")
    print(f"Tree SHA-256: {tree_digest(copied)}")


if __name__ == "__main__":
    main()

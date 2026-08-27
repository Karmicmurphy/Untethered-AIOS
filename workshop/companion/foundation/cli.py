from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from companion.foundation.artifact_compass import ArtifactCompass, ArtifactRecord
from companion.foundation.worker_cards import validate_worker_card


def _load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_records(path: str) -> list[ArtifactRecord]:
    payload = _load_json(path)
    entries = payload.get("artifacts") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        raise ValueError("artifact inventory must be an array or an object with an artifacts array")
    records: list[ArtifactRecord] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("each artifact inventory entry must be an object")
        records.append(
            ArtifactRecord(
                artifact_id=entry["artifact_id"],
                project_id=entry["project_id"],
                source_path=entry["source_path"],
                sha256=entry.get("sha256", ""),
                status=entry["status"],
                provenance=entry.get("provenance", {}),
                content_text=entry.get("content_text", ""),
                size_bytes=entry.get("size_bytes"),
                modified_ns=entry.get("modified_ns"),
            )
        )
    return records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Twis Holo Foundation Release 0.2 utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-worker-card", help="validate one Worker Card v0.1 JSON file")
    validate.add_argument("card")

    for command in ("rebuild-index", "sync-index", "check-index"):
        subparser = subparsers.add_parser(command, help=f"{command.replace('-', ' ')} from an explicit JSON inventory")
        subparser.add_argument("database")
        subparser.add_argument("inventory")

    search = subparsers.add_parser("search-index", help="search an existing Artifact Compass index")
    search.add_argument("database")
    search.add_argument("query", nargs="?", default="")
    search.add_argument("--field", choices=["filename", "path"])
    search.add_argument("--exact-phrase", action="store_true")
    search.add_argument("--project")
    search.add_argument("--status")
    search.add_argument("--provenance")
    search.add_argument("--include-tombstoned", action="store_true")

    duplicates = subparsers.add_parser("duplicate-groups", help="list exact-hash groups with every source path")
    duplicates.add_argument("database")
    duplicates.add_argument("--project")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate-worker-card":
        result = validate_worker_card(_load_json(args.card))
        print(json.dumps({"valid": result.valid, "issues": [issue.__dict__ for issue in result.issues]}, indent=2))
        return 0 if result.valid else 2

    if args.command in {"rebuild-index", "sync-index", "check-index"}:
        records = _load_records(args.inventory)
        with ArtifactCompass(args.database) as compass:
            if args.command == "rebuild-index":
                result = compass.rebuild(records)
                output = result.__dict__
                exit_code = 0
            elif args.command == "sync-index":
                result = compass.sync(records)
                output = result.__dict__
                exit_code = 0
            else:
                stale = compass.detect_stale(records)
                output = {"stale": [entry.__dict__ for entry in stale], "stale_count": len(stale)}
                exit_code = 3 if stale else 0
        print(json.dumps(output, indent=2))
        return exit_code

    with ArtifactCompass(args.database) as compass:
        if args.command == "search-index":
            output = compass.search(
                args.query,
                field=args.field,
                exact_phrase=args.exact_phrase,
                project_id=args.project,
                status=args.status,
                provenance=args.provenance,
                include_tombstoned=args.include_tombstoned,
            )
        elif args.command == "duplicate-groups":
            output = compass.duplicate_groups(project_id=args.project)
        else:
            raise AssertionError(args.command)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

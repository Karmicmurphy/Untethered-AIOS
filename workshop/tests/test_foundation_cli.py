from __future__ import annotations

import json
from pathlib import Path

from companion.foundation.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_cli_validates_worker_card(capsys) -> None:
    card = ROOT / "examples" / "worker_cards" / "valid" / "bounded-file-worker.json"
    assert main(["validate-worker-card", str(card)]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True


def test_cli_rebuild_search_duplicate_and_stale_check(tmp_path: Path, capsys) -> None:
    inventory = tmp_path / "inventory.json"
    entries = [
        {
            "artifact_id": "one", "project_id": "p", "source_path": r"C:\one\same.txt",
            "sha256": "A" * 64, "status": "draft", "provenance": {"kind": "fixture"},
            "content_text": "searchable exact phrase",
        },
        {
            "artifact_id": "two", "project_id": "p", "source_path": r"C:\two\same.txt",
            "sha256": "A" * 64, "status": "reviewed", "provenance": {"kind": "fixture"},
            "content_text": "copy",
        },
    ]
    inventory.write_text(json.dumps({"artifacts": entries}), encoding="utf-8")
    database = tmp_path / "compass.sqlite3"
    assert main(["rebuild-index", str(database), str(inventory)]) == 0
    assert json.loads(capsys.readouterr().out)["inserted"] == 2
    assert main(["search-index", str(database), "exact phrase", "--exact-phrase"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["artifact_id"] == "one"
    assert main(["duplicate-groups", str(database), "--project", "p"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["all_source_paths"] == [r"C:\one\same.txt", r"C:\two\same.txt"]
    assert main(["check-index", str(database), str(inventory)]) == 0
    assert json.loads(capsys.readouterr().out)["stale_count"] == 0

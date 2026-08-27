from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from companion.foundation.artifact_compass import ArtifactCompass, ArtifactRecord

HASH_A = "A" * 64
HASH_B = "B" * 64


def records() -> list[ArtifactRecord]:
    return [
        ArtifactRecord(
            "a-1", "flashriver-source-archive", r"C:\Archive\alpha\Shared Plan.txt", HASH_A, "reviewed",
            {"kind": "imported", "archive": "FLASHRIVER.zip", "member": "alpha/Shared Plan.txt"},
            "Release compass exact phrase lives here", 42, 100,
        ),
        ArtifactRecord(
            "a-2", "flashriver-source-archive", r"C:\Archive\beta\Shared Plan.txt", HASH_A, "pending",
            {"kind": "imported", "archive": "FLASHRIVER.zip", "member": "beta/Shared Plan.txt"},
            "second copy", 42, 101,
        ),
        ArtifactRecord(
            "b-1", "other-project", r"C:\Notes\Unique.txt", HASH_B, "approved",
            {"kind": "human-authored", "owner": "local"}, "unrelated content", 20, 102,
        ),
    ]


def test_rebuild_and_metadata_search_are_deterministic(tmp_path: Path) -> None:
    with ArtifactCompass(tmp_path / "compass.sqlite3") as compass:
        result = compass.rebuild(reversed(records()))
        assert (result.generation, result.inserted, result.changed) == (1, 3, 0)
        assert [item["artifact_id"] for item in compass.search("Shared Plan", field="filename")] == ["a-1", "a-2"]
        assert [item["artifact_id"] for item in compass.search(r"Archive\beta", field="path")] == ["a-2"]
        assert [item["artifact_id"] for item in compass.search(project_id="other-project")] == ["b-1"]
        assert [item["artifact_id"] for item in compass.search(status="reviewed")] == ["a-1"]
        assert [item["artifact_id"] for item in compass.search(provenance="FLASHRIVER.zip")] == ["a-1", "a-2"]


def test_exact_phrase_uses_fts5(tmp_path: Path) -> None:
    with ArtifactCompass(tmp_path / "compass.sqlite3") as compass:
        compass.rebuild(records())
        assert [item["artifact_id"] for item in compass.search("compass exact phrase", exact_phrase=True)] == ["a-1"]
        assert compass.search("phrase exact compass", exact_phrase=True) == []


def test_duplicate_groups_show_every_source_path_and_provenance(tmp_path: Path) -> None:
    with ArtifactCompass(tmp_path / "compass.sqlite3") as compass:
        compass.rebuild(records())
        groups = compass.duplicate_groups(project_id="flashriver-source-archive")
        assert len(groups) == 1
        assert groups[0]["sha256"] == HASH_A
        assert groups[0]["artifact_count"] == 2
        assert groups[0]["all_source_paths"] == [
            r"C:\Archive\alpha\Shared Plan.txt", r"C:\Archive\beta\Shared Plan.txt",
        ]
        assert [artifact["provenance"]["member"] for artifact in groups[0]["artifacts"]] == [
            "alpha/Shared Plan.txt", "beta/Shared Plan.txt",
        ]


def test_changed_records_reindex_and_generation_advances(tmp_path: Path) -> None:
    initial = records()
    with ArtifactCompass(tmp_path / "compass.sqlite3") as compass:
        compass.rebuild(initial)
        changed = [replace(initial[0], content_text="replacement searchable wording"), initial[1], initial[2]]
        result = compass.sync(changed)
        assert (result.generation, result.inserted, result.changed, result.unchanged) == (2, 0, 1, 2)
        assert compass.search("compass exact phrase", exact_phrase=True) == []
        assert [item["artifact_id"] for item in compass.search("replacement searchable", exact_phrase=True)] == ["a-1"]


def test_missing_records_become_visible_tombstones_without_deletion(tmp_path: Path) -> None:
    initial = records()
    with ArtifactCompass(tmp_path / "compass.sqlite3") as compass:
        compass.rebuild(initial)
        result = compass.sync(initial[:2])
        assert result.tombstoned == 1
        assert compass.search("Unique", field="filename") == []
        tombstones = compass.search("Unique", field="filename", include_tombstoned=True)
        assert tombstones[0]["artifact_id"] == "b-1"
        assert tombstones[0]["tombstoned"] is True


def test_stale_detection_reports_changed_missing_returned_and_new(tmp_path: Path) -> None:
    initial = records()
    with ArtifactCompass(tmp_path / "compass.sqlite3") as compass:
        compass.rebuild(initial)
        compass.sync(initial[:2])
        supplied = [
            replace(initial[0], status="approved"), initial[2],
            ArtifactRecord("new-1", "other-project", r"C:\Notes\New.txt", "C" * 64, "pending", {"kind": "imported"}),
        ]
        stale = {(item.artifact_id, item.reason) for item in compass.detect_stale(supplied)}
        assert stale == {
            ("a-1", "source_changed"), ("a-2", "missing_from_source"),
            ("b-1", "source_returned_after_tombstone"), ("new-1", "not_indexed"),
        }


def test_rebuild_removes_old_rows_and_keeps_generation_history(tmp_path: Path) -> None:
    with ArtifactCompass(tmp_path / "compass.sqlite3") as compass:
        compass.rebuild(records())
        result = compass.rebuild(records()[:1])
        assert result.generation == 2
        assert [item["artifact_id"] for item in compass.search()] == ["a-1"]

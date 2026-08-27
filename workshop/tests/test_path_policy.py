from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from companion.foundation.path_policy import WindowsPathPolicy

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows-specific containment policy")


@pytest.fixture
def roots(tmp_path: Path) -> dict[str, Path]:
    read = tmp_path / "read"
    write = tmp_path / "write"
    blocked = read / "private"
    sibling = tmp_path / "read-confused"
    outside = tmp_path / "outside"
    for path in (read, write, blocked, sibling, outside):
        path.mkdir()
    (read / "visible.txt").write_text("visible", encoding="utf-8")
    (write / "existing.txt").write_text("write", encoding="utf-8")
    (blocked / "secret.txt").write_text("secret", encoding="utf-8")
    return {"read": read, "write": write, "blocked": blocked, "sibling": sibling, "outside": outside}


def make_policy(roots: dict[str, Path]) -> WindowsPathPolicy:
    return WindowsPathPolicy(
        read_roots=[roots["read"]],
        write_roots=[roots["write"]],
        blocked_roots=[roots["blocked"]],
    )


def test_canonical_read_and_write_roots_are_separate(roots: dict[str, Path]) -> None:
    policy = make_policy(roots)
    assert policy.decide(roots["read"] / "visible.txt", mode="read").allowed
    assert not policy.decide(roots["read"] / "new.txt", mode="write").allowed
    assert policy.decide(roots["write"] / "new.txt", mode="write").allowed
    assert not policy.decide(roots["write"] / "existing.txt", mode="read").allowed


def test_parent_traversal_is_rejected_before_resolution(roots: dict[str, Path]) -> None:
    decision = make_policy(roots).decide(str(roots["read"] / ".." / "outside" / "escape.txt"), mode="read")
    assert not decision.allowed
    assert decision.code == "parent_traversal"


def test_absolute_escape_and_sibling_prefix_confusion_are_rejected(roots: dict[str, Path]) -> None:
    policy = make_policy(roots)
    assert policy.decide(roots["outside"] / "escape.txt", mode="write").code == "outside_allowed_roots"
    assert policy.decide(roots["sibling"] / "lookalike.txt", mode="read", require_exists=False).code == "outside_allowed_roots"


def test_drive_mismatch_and_unc_are_rejected(roots: dict[str, Path]) -> None:
    policy = make_policy(roots)
    current_drive = roots["read"].drive.upper()
    other_drive = "Z:" if current_drive != "Z:" else "Y:"
    assert policy.decide(other_drive + "\\escape.txt", mode="write").code == "outside_allowed_roots"
    assert policy.decide(r"\\server\share\escape.txt", mode="read").code == "unc_denied"


def test_case_variation_remains_inside_on_windows(roots: dict[str, Path]) -> None:
    path_with_other_case = str(roots["read"] / "visible.txt").swapcase()
    assert make_policy(roots).decide(path_with_other_case, mode="read").allowed


def test_nonexistent_read_is_denied_but_bounded_write_is_allowed(roots: dict[str, Path]) -> None:
    policy = make_policy(roots)
    assert policy.decide(roots["read"] / "missing.txt", mode="read").code == "missing_path"
    assert policy.decide(roots["write"] / "future.txt", mode="write").allowed


def test_ntfs_stream_reserved_and_ambiguous_components_are_rejected(roots: dict[str, Path]) -> None:
    policy = make_policy(roots)
    assert policy.decide(str(roots["write"] / "future.txt") + ":secret", mode="write").code == "unsafe_windows_component"
    assert policy.decide(roots["write"] / "CON", mode="write").code == "unsafe_windows_component"
    assert policy.decide(str(roots["write"] / "ambiguous") + ".", mode="write").code == "unsafe_windows_component"


def test_blocked_root_wins_over_allowed_root(roots: dict[str, Path]) -> None:
    decision = make_policy(roots).decide(roots["blocked"] / "secret.txt", mode="read")
    assert not decision.allowed
    assert decision.code == "blocked_root"


def test_relative_paths_require_an_explicit_base(roots: dict[str, Path]) -> None:
    policy = make_policy(roots)
    assert policy.decide("visible.txt", mode="read").code == "relative_without_base"
    assert policy.decide("visible.txt", mode="read", base=roots["read"]).allowed


def test_symlink_escape_is_rejected_when_windows_allows_symlink_creation(roots: dict[str, Path]) -> None:
    link = roots["read"] / "outside-link"
    try:
        link.symlink_to(roots["outside"], target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    decision = make_policy(roots).decide(link / "escape.txt", mode="read", require_exists=False)
    assert not decision.allowed
    assert decision.code == "outside_allowed_roots"


def test_junction_escape_is_rejected(roots: dict[str, Path]) -> None:
    junction = roots["write"] / "outside-junction"
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(roots["outside"])],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"junction creation unavailable: {result.stderr or result.stdout}")
    try:
        decision = make_policy(roots).decide(junction / "future.txt", mode="write")
        assert not decision.allowed
        assert decision.code == "outside_allowed_roots"
    finally:
        junction.rmdir()

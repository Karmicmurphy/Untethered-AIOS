from __future__ import annotations

import hashlib

import pytest

from companion.visitor_bench import VisitorBench, VisitorBenchError


def test_guest_namespace_is_identity_scoped_and_content_exact(tmp_path):
    bench = VisitorBench(tmp_path / "visitor.sqlite3")
    content = "First line\nSecond line — exact Unicode.\n"
    created = bench.create("guest-a@example.com", {"room":"write","title":"A draft","content":content,"operation":"rewrite"})["submission"]
    assert created["content"] == content
    assert created["content_sha256"] == hashlib.sha256(content.encode()).hexdigest().upper()
    assert created["authority_state"] == "GUEST_SANDBOX_DRAFT"
    assert len(bench.list(identity="guest-a@example.com")) == 1
    assert bench.list(identity="guest-b@example.com") == []
    with pytest.raises(VisitorBenchError):
        bench.get(created["id"], identity="guest-b@example.com")


def test_only_write_and_music_nonempty_drafts_are_accepted(tmp_path):
    bench = VisitorBench(tmp_path / "visitor.sqlite3")
    for value in (
        {"room":"build","title":"No","content":"text"},
        {"room":"music","title":"No","content":"   "},
        {"room":"write","title":"","content":"text"},
    ):
        with pytest.raises(VisitorBenchError):
            bench.create("guest@example.com", value)


def test_promotion_record_is_separate_and_single_use(tmp_path):
    bench = VisitorBench(tmp_path / "visitor.sqlite3")
    submission = bench.create("guest@example.com", {"room":"music","title":"Song","content":"Owner supplied fragment"})["submission"]
    bench.record_promotion(submission["id"], "owner-artifact", "receipt", "owner@example.com")
    after = bench.get(submission["id"], owner=True)
    assert after["content"] == submission["content"]
    assert after["content_sha256"] == submission["content_sha256"]
    assert after["promotion"]["owner_artifact_id"] == "owner-artifact"
    with pytest.raises(VisitorBenchError, match="already promoted"):
        bench.record_promotion(submission["id"], "other", "other", "owner@example.com")

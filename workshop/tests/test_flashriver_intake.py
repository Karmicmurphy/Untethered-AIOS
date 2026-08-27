from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "companion"))

from flashriver_intake import inspect_flashriver_package, sha256_file, stage_flashriver_package


def build_sample_package(path: Path) -> None:
    inner = path.parent / "inner.zip"
    with zipfile.ZipFile(inner, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("nested/README.md", "private nested source")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("FLASHRIVER_SAMPLE/README.md", "# Sample handoff\n")
        z.writestr("FLASHRIVER_SAMPLE/AGENT.md", "# Agent\n")
        z.writestr("FLASHRIVER_SAMPLE/build_plan/BUILD_PLAN.md", "# Plan\n")
        z.write(inner, "FLASHRIVER_SAMPLE/source_artifacts/INNER_SOURCE.zip")
        z.writestr("FLASHRIVER_SAMPLE/visuals/map.png", b"not really a png but binary")


def test_inspect_flashriver_package_verifies_hash_and_classifies(tmp_path: Path) -> None:
    pkg = tmp_path / "FLASHRIVER_SAMPLE.zip"
    build_sample_package(pkg)
    digest = sha256_file(pkg)
    manifest = inspect_flashriver_package(pkg, expected_sha256=digest)
    assert manifest["zipTest"] == "PASS"
    assert manifest["sha256"] == digest
    assert manifest["fileCount"] == 5
    assert manifest["counts"]["core-doc"] >= 2
    assert manifest["counts"]["private-source"] == 1
    assert manifest["counts"]["visual"] == 1
    assert "README.md" in manifest["coreDocsFound"]


def test_stage_flashriver_package_imports_docs_and_keeps_private_sources_local(tmp_path: Path) -> None:
    pkg = tmp_path / "FLASHRIVER_SAMPLE.zip"
    build_sample_package(pkg)
    digest = sha256_file(pkg)
    project_root = tmp_path / "project"
    archive_root = tmp_path / "archives"
    project_root.mkdir()
    result = stage_flashriver_package(zip_path=pkg, project_id="flashriver-test", project_root=project_root, archive_root=archive_root, expected_sha256=digest, now="2026-07-14T00:00:00+00:00")
    assert result["ok"] is True
    manifest = result["manifest"]
    assert manifest["publicSafeDocsImported"] >= 3
    assert len(manifest["privateSourcesCopied"]) == 1
    assert manifest["boundary"]["rawPackageCommittedToGitHub"] is False
    assert manifest["boundary"]["cloudflareAuthority"] is False
    manifest_path = project_root / "sources" / "flashriver" / digest[:16] / "FLASHRIVER_INTAKE_MANIFEST.json"
    assert manifest_path.exists()
    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert saved["sha256"] == digest
    artifact_kinds = {a["kind"] for a in result["artifacts"]}
    assert "flashriver-intake-manifest" in artifact_kinds
    assert "flashriver-core-doc" in artifact_kinds
    assert "flashriver-private-source" in artifact_kinds
    assert "flashriver-visual" in artifact_kinds
    with zipfile.ZipFile(pkg) as archive:
        public_documents = [
            artifact
            for artifact in result["artifacts"]
            if artifact["kind"] in {"flashriver-core-doc", "flashriver-support-doc"}
        ]
        assert public_documents
        for artifact in public_documents:
            target = project_root / artifact["path"]
            member_bytes = archive.read(artifact["payload"]["archiveMember"])
            archive_member_hash = hashlib.sha256(member_bytes).hexdigest()
            materialized_hash = sha256_file(target)
            assert artifact["payload"]["archiveMemberSha256"] == archive_member_hash
            assert artifact["payload"]["materializedSha256"] == materialized_hash
            assert artifact["hash"] == materialized_hash


def test_stage_rejects_sha_mismatch(tmp_path: Path) -> None:
    pkg = tmp_path / "FLASHRIVER_SAMPLE.zip"
    build_sample_package(pkg)
    try:
        stage_flashriver_package(zip_path=pkg, project_id="flashriver-test", project_root=tmp_path / "project", archive_root=tmp_path / "archives", expected_sha256="0" * 64, now="2026-07-14T00:00:00+00:00")
    except ValueError as exc:
        assert "SHA-256 mismatch" in str(exc)
    else:
        raise AssertionError("expected SHA mismatch to fail")

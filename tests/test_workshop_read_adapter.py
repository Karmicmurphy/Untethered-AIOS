from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from untethered_aios import (
    CapabilityGrant,
    CapabilityRequest,
    Kernel,
    ProcessState,
)
from untethered_aios.audit import hash_value
from untethered_aios.kernel import Step
from untethered_aios.workshop_read_adapter import (
    CAPABILITY_NAME,
    WORKSHOP_PRIMITIVE,
    project_scope,
    register_workshop_artifact_read,
)
from workshop.companion import server as workshop_server


class WorkshopReadAdapterTests(unittest.TestCase):
    PROJECT_ID = "public-project"
    ARTIFACT_ID = "public-artifact"

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        root = Path(self._temporary.name)
        self.projects = root / "projects"
        docs = (
            self.projects
            / self.PROJECT_ID
            / "sources"
            / "flashriver"
            / "public-package"
            / "docs"
        )
        docs.mkdir(parents=True)
        self.source = docs / "README.md"
        self.source.write_text("# Public fixture\n", encoding="utf-8")
        self.database = root / "workshop.sqlite3"
        self._create_database()
        self.database_sha256 = self._sha256(self.database)

        projects_patch = patch.object(workshop_server, "PROJECTS", self.projects)
        database_patch = patch.object(workshop_server, "DB", self.database)
        projects_patch.start()
        database_patch.start()
        self.addCleanup(projects_patch.stop)
        self.addCleanup(database_patch.stop)

    def _create_database(self) -> None:
        with closing(sqlite3.connect(self.database)) as connection:
            connection.executescript(
                """
                CREATE TABLE artifacts(
                  id TEXT PRIMARY KEY, project_id TEXT, kind TEXT, title TEXT,
                  path TEXT, payload TEXT, authority_state TEXT, sha256 TEXT,
                  created_at TEXT, updated_at TEXT
                );
                CREATE TABLE artifact_reviews(
                  artifact_id TEXT PRIMARY KEY, project_id TEXT, status TEXT,
                  notes TEXT, reviewed_at TEXT, updated_at TEXT
                );
                """
            )
            connection.execute(
                "INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    self.ARTIFACT_ID,
                    self.PROJECT_ID,
                    "flashriver-core-doc",
                    "README.md",
                    "sources/flashriver/public-package/docs/README.md",
                    json.dumps({"public": True}),
                    "SOURCE",
                    self._sha256(self.source),
                    "2026-08-27T00:00:00Z",
                    "2026-08-27T00:00:00Z",
                ),
            )
            connection.execute(
                "INSERT INTO artifact_reviews VALUES(?,?,?,?,?,?)",
                (
                    self.ARTIFACT_ID,
                    self.PROJECT_ID,
                    "reviewed",
                    "",
                    "2026-08-27T00:00:00Z",
                    "2026-08-27T00:00:00Z",
                ),
            )
            connection.commit()

    @staticmethod
    def _sha256(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest().upper()

    def _run_request(
        self,
        *,
        grants: tuple[CapabilityGrant, ...],
        requested_scope: str | None = None,
        artifact_id: str | None = None,
    ) -> tuple[Kernel, int]:
        kernel = Kernel(clock=lambda: "2026-08-27T00:00:00+00:00")
        register_workshop_artifact_read(kernel.capabilities)

        def worker(ctx):
            return Step.done(
                ctx.invoke(
                    CapabilityRequest(
                        CAPABILITY_NAME,
                        {
                            "project_scope": requested_scope or project_scope(self.PROJECT_ID),
                            "artifact_id": artifact_id or self.ARTIFACT_ID,
                        },
                    )
                )
            )

        pid = kernel.spawn("workshop-reader", worker, grants=grants)
        kernel.run()
        return kernel, pid

    def test_real_workshop_primitive_returns_structured_hashed_read_receipt(self) -> None:
        scope = project_scope(self.PROJECT_ID)
        with patch.object(
            workshop_server,
            "artifact_inspection_options",
            wraps=workshop_server.artifact_inspection_options,
        ) as primitive:
            kernel, pid = self._run_request(
                grants=(CapabilityGrant(CAPABILITY_NAME, (scope,)),)
            )

        primitive.assert_called_once_with(self.PROJECT_ID)
        process = kernel.get_process(pid)
        self.assertEqual(process.state, ProcessState.DONE)
        self.assertEqual(process.grants, (CapabilityGrant(CAPABILITY_NAME, (scope,)),))
        self.assertEqual(
            process.result,
            {
                "schema": "twis-workshop-artifact-read-v0.1",
                "capability": CAPABILITY_NAME,
                "scope": scope,
                "primitive": WORKSHOP_PRIMITIVE,
                "artifact": {
                    "artifact_id": self.ARTIFACT_ID,
                    "project_id": self.PROJECT_ID,
                    "title": "README.md",
                    "kind": "flashriver-core-doc",
                    "path": (
                        "public-project/sources/flashriver/"
                        "public-package/docs/README.md"
                    ),
                    "sha256": self._sha256(self.source),
                    "file_type": "markdown",
                    "byte_count": self.source.stat().st_size,
                    "review_status": "reviewed",
                },
                "trace": [
                    "kernel.capability.invoke",
                    "untethered_aios.workshop_read_adapter.WorkshopArtifactReadAdapter.read",
                    WORKSHOP_PRIMITIVE,
                ],
            },
        )
        [receipt] = [
            receipt
            for receipt in kernel.audit.receipts
            if receipt.kind == "capability.call" and receipt.action == CAPABILITY_NAME
        ]
        self.assertEqual(receipt.pid, pid)
        self.assertEqual(receipt.target, scope)
        self.assertEqual(receipt.detail["output_sha256"], hash_value(process.result))
        self.assertFalse(receipt.detail["mutation"])
        self.assertFalse(any(r.kind == "capability.mutation" for r in kernel.audit.receipts))
        self.assertEqual(self._sha256(self.database), self.database_sha256)
        self.assertEqual(kernel.audit.verify_chain(), (True, ()))

    def test_missing_capability_is_denied_before_adapter(self) -> None:
        with patch.object(
            workshop_server, "artifact_inspection_options"
        ) as primitive:
            kernel, pid = self._run_request(grants=())
        primitive.assert_not_called()
        self.assertEqual(kernel.get_process(pid).state, ProcessState.FAILED)
        self.assertTrue(any(r.kind == "capability.denied" for r in kernel.audit.receipts))

    def test_wrong_project_scope_is_denied_before_adapter(self) -> None:
        with patch.object(
            workshop_server, "artifact_inspection_options"
        ) as primitive:
            kernel, pid = self._run_request(
                grants=(
                    CapabilityGrant(
                        CAPABILITY_NAME,
                        (project_scope(self.PROJECT_ID),),
                    ),
                ),
                requested_scope=project_scope("other-project"),
            )
        primitive.assert_not_called()
        self.assertEqual(kernel.get_process(pid).state, ProcessState.FAILED)
        denied = [r for r in kernel.audit.receipts if r.kind == "capability.denied"]
        self.assertEqual(denied[-1].target, "project:other-project")

    def test_unbounded_wildcard_scope_is_denied_before_adapter(self) -> None:
        with patch.object(
            workshop_server, "artifact_inspection_options"
        ) as primitive:
            kernel, pid = self._run_request(
                grants=(CapabilityGrant(CAPABILITY_NAME, ("*",)),)
            )
        primitive.assert_not_called()
        self.assertEqual(kernel.get_process(pid).state, ProcessState.FAILED)
        self.assertTrue(any(r.kind == "capability.denied" for r in kernel.audit.receipts))

    def test_scope_escape_and_malformed_scope_are_denied(self) -> None:
        grant = CapabilityGrant(CAPABILITY_NAME, (project_scope(self.PROJECT_ID),))
        for unsafe_scope in (
            "project:../other-project",
            "project:public-project/../../other-project",
            "project:C:\\outside",
            "PROJECT:public-project",
            "project:",
        ):
            with self.subTest(scope=unsafe_scope), patch.object(
                workshop_server, "artifact_inspection_options"
            ) as primitive:
                kernel, pid = self._run_request(
                    grants=(grant,), requested_scope=unsafe_scope
                )
                primitive.assert_not_called()
                self.assertEqual(kernel.get_process(pid).state, ProcessState.FAILED)
                self.assertTrue(
                    any(r.kind == "capability.denied" for r in kernel.audit.receipts)
                )

    def test_malformed_artifact_target_fails_with_targeted_evidence(self) -> None:
        scope = project_scope(self.PROJECT_ID)
        kernel, pid = self._run_request(
            grants=(CapabilityGrant(CAPABILITY_NAME, (scope,)),),
            artifact_id="../private",
        )
        self.assertEqual(kernel.get_process(pid).state, ProcessState.FAILED)
        failed = [r for r in kernel.audit.receipts if r.kind == "capability.failed"]
        self.assertEqual(failed[-1].target, scope)
        self.assertIn("artifact_id_invalid", failed[-1].detail["error"])

    def test_missing_workshop_target_has_explicit_failure_receipt(self) -> None:
        scope = project_scope(self.PROJECT_ID)
        kernel, pid = self._run_request(
            grants=(CapabilityGrant(CAPABILITY_NAME, (scope,)),),
            artifact_id="missing-artifact",
        )
        self.assertEqual(kernel.get_process(pid).state, ProcessState.FAILED)
        failed = [r for r in kernel.audit.receipts if r.kind == "capability.failed"]
        self.assertEqual(failed[-1].target, scope)
        self.assertIn("artifact_not_found", failed[-1].detail["error"])

    def test_workshop_primitive_failure_has_targeted_failure_receipt(self) -> None:
        scope = project_scope(self.PROJECT_ID)
        with patch.object(
            workshop_server,
            "artifact_inspection_options",
            side_effect=RuntimeError("fixture failure"),
        ):
            kernel, pid = self._run_request(
                grants=(CapabilityGrant(CAPABILITY_NAME, (scope,)),)
            )
        self.assertEqual(kernel.get_process(pid).state, ProcessState.FAILED)
        failed = [r for r in kernel.audit.receipts if r.kind == "capability.failed"]
        self.assertEqual(failed[-1].target, scope)
        self.assertIn("workshop_primitive_failed", failed[-1].detail["error"])

    def test_worker_cannot_self_grant_workshop_read(self) -> None:
        scope = project_scope(self.PROJECT_ID)
        kernel = Kernel()
        register_workshop_artifact_read(kernel.capabilities)

        def worker(ctx):
            view = ctx.process
            view.grants = (CapabilityGrant(CAPABILITY_NAME, (scope,)),)
            return Step.done(
                ctx.call(
                    CAPABILITY_NAME,
                    project_scope=scope,
                    artifact_id=self.ARTIFACT_ID,
                )
            )

        pid = kernel.spawn("self-grant-reader", worker)
        kernel.run()
        self.assertEqual(kernel.get_process(pid).state, ProcessState.FAILED)
        self.assertEqual(kernel.get_process(pid).grants, ())
        self.assertTrue(any(r.kind == "capability.denied" for r in kernel.audit.receipts))

    def test_child_cannot_receive_broader_workshop_project_scope(self) -> None:
        parent_scope = project_scope(self.PROJECT_ID)
        child_scope = project_scope("other-project")
        kernel = Kernel()
        register_workshop_artifact_read(kernel.capabilities)

        def child(ctx):
            return Step.done()

        def parent(ctx):
            ctx.spawn(
                "broader-reader",
                child,
                grants=(CapabilityGrant(CAPABILITY_NAME, (child_scope,)),),
            )
            return Step.done()

        pid = kernel.spawn(
            "parent-reader",
            parent,
            grants=(CapabilityGrant(CAPABILITY_NAME, (parent_scope,)),),
        )
        kernel.run()
        self.assertEqual(kernel.get_process(pid).state, ProcessState.FAILED)
        self.assertIn("cannot receive capabilities", kernel.get_process(pid).error)

    def test_unbounded_parent_cannot_delegate_exact_workshop_scope(self) -> None:
        scope = project_scope(self.PROJECT_ID)
        kernel = Kernel()
        register_workshop_artifact_read(kernel.capabilities)

        def child(ctx):
            return Step.done()

        def parent(ctx):
            ctx.spawn(
                "exact-reader",
                child,
                grants=(CapabilityGrant(CAPABILITY_NAME, (scope,)),),
            )
            return Step.done()

        pid = kernel.spawn(
            "wildcard-parent",
            parent,
            grants=(CapabilityGrant(CAPABILITY_NAME, ("*",)),),
        )
        kernel.run()
        self.assertEqual(kernel.get_process(pid).state, ProcessState.FAILED)
        self.assertIn("cannot receive capabilities", kernel.get_process(pid).error)

    def test_result_contract_schema_is_bounded_to_read_metadata(self) -> None:
        schema_path = (
            Path(__file__).resolve().parents[1]
            / "contracts"
            / "workshop-artifact-read-v0.1.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(
            schema["properties"]["schema"]["const"],
            "twis-workshop-artifact-read-v0.1",
        )
        self.assertEqual(
            schema["properties"]["capability"]["const"], CAPABILITY_NAME
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(schema["properties"]["artifact"]["additionalProperties"])


if __name__ == "__main__":
    unittest.main()

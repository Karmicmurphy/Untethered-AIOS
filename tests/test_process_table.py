import tempfile
import unittest
from pathlib import Path

from untethered_aios import (
    CapabilityGrant,
    InMemoryProcessTable,
    ProcessRecord,
    ProcessState,
    SQLiteProcessTable,
)


class ProcessTableContract:
    def make_table(self, root: Path):
        raise NotImplementedError

    def test_round_trip_and_monotonic_pid(self):
        with tempfile.TemporaryDirectory() as temp:
            table = self.make_table(Path(temp))
            first = table.allocate_pid()
            record = ProcessRecord(
                pid=first,
                name="worker",
                runner_id="worker.v1",
                grants=(CapabilityGrant("artifact.read", (str(Path(temp)),)),),
                state=ProcessState.READY,
                metadata={"turn": 1},
            )
            table.put(record)

            loaded = table.get(first)
            self.assertEqual(loaded, record)
            loaded.metadata["turn"] = 99
            self.assertEqual(table.get(first).metadata, {"turn": 1})
            self.assertEqual(table.allocate_pid(), first + 1)
            table.close()

    def test_missing_pid_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            table = self.make_table(Path(temp))
            with self.assertRaises(KeyError):
                table.get(404)
            table.close()


class InMemoryProcessTableTests(ProcessTableContract, unittest.TestCase):
    def make_table(self, root: Path):
        return InMemoryProcessTable()


class SQLiteProcessTableTests(ProcessTableContract, unittest.TestCase):
    def make_table(self, root: Path):
        return SQLiteProcessTable(root / "kernel.sqlite3")

    def test_reopen_preserves_rows_receipts_and_pid_sequence(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "kernel.sqlite3"
            table = SQLiteProcessTable(path)
            pid = table.allocate_pid()
            table.put(
                ProcessRecord(
                    pid=pid,
                    name="durable",
                    runner_id="durable.v1",
                    state=ProcessState.WAITING,
                    waiting_for="resume",
                )
            )
            table.append_receipt(
                {
                    "sequence": 1,
                    "kind": "test",
                    "actor": "kernel",
                    "action": "persist",
                    "target": None,
                    "pid": pid,
                    "parent_pid": None,
                    "detail": {},
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "previous_sha256": None,
                    "sha256": "a" * 64,
                }
            )
            table.close()

            reopened = SQLiteProcessTable(path)
            self.assertEqual(reopened.get(pid).waiting_for, "resume")
            self.assertEqual(reopened.allocate_pid(), pid + 1)
            self.assertEqual(reopened.list_receipts()[0]["sha256"], "a" * 64)
            self.assertEqual(reopened.integrity_check(), "ok")
            self.assertEqual(reopened.journal_mode(), "delete")
            reopened.close()


if __name__ == "__main__":
    unittest.main()

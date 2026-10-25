"""Tests for a toy quantum simulation, not IBM hardware or FRIDAY dispatch."""
import importlib.util
import math
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "experiments/friday_quantum_bakeoff.py"
spec = importlib.util.spec_from_file_location("friday_quantum_bakeoff", SOURCE)
q = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(q)


class DeterministicQuantumComparisonTests(unittest.TestCase):
    def test_exact_classical_solution_is_independent(self):
        exact = q.classical_optimum()
        self.assertEqual(exact["best_score"], 2)
        self.assertEqual(exact["candidates_checked"], 8)
        self.assertEqual(len(exact["optimal_solutions"]), 6)
        self.assertNotIn("000", exact["optimal_solutions"])
        self.assertNotIn("111", exact["optimal_solutions"])

    def test_ideal_quantum_distribution_normalized(self):
        probs = q.quantum_probabilities(gamma=0.7, beta=0.9)
        self.assertEqual(len(probs), 8)
        self.assertAlmostEqual(sum(probs), 1, places=10)
        self.assertTrue(all(0 <= p <= 1 for p in probs))
        self.assertTrue(all(abs(p - 0.125) < 1e-12 for p in
                            q.quantum_probabilities(gamma=0, beta=0)))

    def test_grid_is_bounded_and_deterministic(self):
        a, b = q.optimize_fixed_grid(), q.optimize_fixed_grid()
        self.assertEqual(a, b)
        self.assertEqual(a["grid_points"], 289)
        self.assertGreater(a["expected_score"], 1.5)
        self.assertLessEqual(a["expected_score"], 2 + 1e-10)

    def test_reproducible_classical_sampling_is_not_hardware(self):
        probs = q.optimize_fixed_grid()["distribution"]
        first = q.sample_probabilities(probs, shots=256, seed=42)
        self.assertEqual(first, q.sample_probabilities(probs, shots=256, seed=42))
        self.assertNotEqual(first, q.sample_probabilities(probs, shots=256, seed=43))
        self.assertEqual(sum(first.values()), 256)

    def test_bad_input_and_scope_expansion_denied(self):
        for tasks, edges in [
            (("x",), ((0, 1),)), (tuple("abcdef"), ((0, 1),)),
            (("a", "a"), ((0, 1),)), (("a", "b"), ((1, 1),)),
            (("a", "b"), ((0, 4),)), (("a", "b"), ((0, 1), (0, 1))),
            (("a", "b"), ((1, 0),)), (("a", "b"), ()),
            (("a", "!"), ((0, 1),)),
        ]:
            with self.subTest(tasks=tasks, edges=edges):
                with self.assertRaises(ValueError):
                    q.validate_problem(tasks, edges)
        for gamma, beta in ((math.inf, 0), (0, math.nan)):
            with self.assertRaises(ValueError):
                q.quantum_probabilities(gamma=gamma, beta=beta)
        for shots, seed in ((0, 42), (4097, 42), (256, -1), (256, 1.2)):
            with self.assertRaises(ValueError):
                q.sample_probabilities([0.5, 0.5], shots=shots, seed=seed)
        with self.assertRaises(ValueError):
            q.sample_probabilities([0.1, 0.1], shots=20, seed=0)

    def test_candidate_cannot_grant_any_runtime_authority(self):
        self.assertTrue(q.proposal_is_valid("010"))
        for raw in ("", "0010", "007", "hi!", 0, "000000"):
            self.assertFalse(q.proposal_is_valid(raw))
        report = q.run_experiment()
        self.assertEqual(report["qpu_jobs_submitted"], 0)
        self.assertEqual(report["external_requests"], 0)
        self.assertFalse(report["approved_workflows_changed"])
        self.assertEqual(report["admission"], "CLASSICAL_VERIFIER_ONLY_NO_RUNTIME_AUTHORITY")
        self.assertEqual(report["quantum_ideal"]["best_sample_score"], 2)
        self.assertEqual(sum(report["quantum_ideal"]["histogram"].values()), 256)
        self.assertEqual(report["receipt_sha256"], q.run_experiment()["receipt_sha256"])


if __name__ == "__main__":
    unittest.main()

"""Disposable FRIDAY/IBM Quantum experiment: exact classical Max-Cut vs ideal p=1 QAOA.

Uses Python standard library only. This is a local classical *simulation* of a
quantum circuit, NOT a live QPU run, a job scheduler, or permission to execute
any AIOS capability. The verifier remains deterministic and independent.
"""
from __future__ import annotations

import cmath
from collections import Counter
import hashlib
import itertools
import json
import math
import random

TASKS = ("compile", "inspect", "archive")
EDGES = ((0, 1), (1, 2), (0, 2))
MAX_QUBITS = 5


def validate_problem(tasks=TASKS, edges=EDGES):
    if (not isinstance(tasks, tuple) or not 2 <= len(tasks) <= MAX_QUBITS
            or not all(isinstance(x, str) and x.isidentifier() for x in tasks)
            or len(set(tasks)) != len(tasks)):
        raise ValueError("Only 2-5 distinct simulated task identifiers allowed")
    if not isinstance(edges, tuple) or not edges:
        raise ValueError("Immutable nonempty edges required")
    seen = set()
    for edge in edges:
        if (not isinstance(edge, tuple) or len(edge) != 2 or
                not all(type(x) is int and 0 <= x < len(tasks) for x in edge)
                or edge[0] >= edge[1] or edge in seen):
            raise ValueError("Edges must be unique, ordered, valid task pairs")
        seen.add(edge)
    return len(tasks)


def score(bits, edges=EDGES):
    return sum(bits[i] != bits[j] for i, j in edges)


def classical_optimum(tasks=TASKS, edges=EDGES):
    n = validate_problem(tasks, edges)
    candidates = [(score(b, edges), b) for b in itertools.product((0, 1), repeat=n)]
    maximum = max(item[0] for item in candidates)
    return {"best_score": maximum,
            "optimal_solutions": ["".join(map(str, b)) for s, b in candidates if s == maximum],
            "candidates_checked": len(candidates)}


def quantum_probabilities(tasks=TASKS, edges=EDGES, *, gamma: float, beta: float):
    """Ideal circuit H^n -> exp(-i gamma MaxCut) -> tensor exp(-i beta X)."""
    n = validate_problem(tasks, edges)
    if not all(math.isfinite(x) for x in (gamma, beta)):
        raise ValueError("Angles must be finite")
    size = 1 << n
    state = [
        cmath.exp(-1j * gamma * score(tuple((index >> q) & 1 for q in range(n)), edges))
        / math.sqrt(size) for index in range(size)
    ]
    cos_b, sin_b = math.cos(beta), math.sin(beta)
    for target in range(n):
        new_state = state.copy()
        for index in range(size):
            if not index & (1 << target):
                mate = index | (1 << target)
                new_state[index] = cos_b * state[index] - 1j * sin_b * state[mate]
                new_state[mate] = cos_b * state[mate] - 1j * sin_b * state[index]
        state = new_state
    probs = [abs(amp)**2 for amp in state]
    if not math.isclose(sum(probs), 1.0, abs_tol=1e-10):
        raise RuntimeError("Quantum simulation normalization failure")
    return probs


def optimize_fixed_grid(tasks=TASKS, edges=EDGES):
    n = validate_problem(tasks, edges)
    scores = [score(tuple((i >> q) & 1 for q in range(n)), edges) for i in range(1 << n)]
    best = None
    for gi in range(17):
        gamma = math.pi * gi / 16
        for bi in range(17):
            beta = math.pi * bi / 32
            probabilities = quantum_probabilities(tasks, edges, gamma=gamma, beta=beta)
            expected = sum(p * s for p, s in zip(probabilities, scores))
            key = (expected, -gi, -bi)
            if best is None or key > best[0]:
                best = (key, gi, bi, probabilities)
    assert best is not None
    _, gi, bi, probs = best
    return {"gamma": math.pi * gi / 16, "beta": math.pi * bi / 32,
            "grid_index": {"gamma": gi, "beta": bi},
            "expected_score": sum(p * s for p, s in zip(probs, scores)),
            "distribution": probs, "grid_points": 289}


def sample_probabilities(probs, *, shots: int, seed: int):
    """Seeded *classical* sampling for reproducible tests; never QPU evidence."""
    if (type(shots) is not int or not 1 <= shots <= 4096 or
            type(seed) is not int or not 0 <= seed <= 2**32 - 1):
        raise ValueError("Bounded shots and seed required")
    if (not isinstance(probs, list) or not probs or
            any(not isinstance(p, float) or not math.isfinite(p) or p < 0 for p in probs)
            or not math.isclose(sum(probs), 1, abs_tol=1e-10)):
        raise ValueError("Invalid probability distribution")
    return dict(sorted(Counter(random.Random(seed).choices(
        range(len(probs)), weights=probs, k=shots)).items()))


def proposal_is_valid(bits, tasks=TASKS, edges=EDGES):
    n = validate_problem(tasks, edges)
    return isinstance(bits, str) and len(bits) == n and not set(bits).difference("01")


def run_experiment():
    exact = classical_optimum()
    q = optimize_fixed_grid()
    counts = sample_probabilities(q["distribution"], shots=256, seed=42)
    n = len(TASKS)
    report = {
        "schema_version": "1.0.0",
        "mode": "IDEAL_CLASSICAL_QAOA_SIMULATION_ONLY",
        "qpu_jobs_submitted": 0,
        "external_requests": 0,
        "dependencies_added": 0,
        "approved_workflows_changed": False,
        "tasks": list(TASKS), "conflict_edges": [list(edge) for edge in EDGES],
        "classical_exact": exact,
        "quantum_ideal": {
            "depth": 1, "angles_radians": {"gamma": q["gamma"], "beta": q["beta"]},
            "grid_points": q["grid_points"], "expected_score": q["expected_score"],
            "shots": 256, "seed": 42,
            "histogram": {"".join(str((i >> j) & 1) for j in range(n)): count
                          for i, count in counts.items()},
            "best_sample_score": max(
                score(tuple((i >> j) & 1 for j in range(n))) for i in counts),
        },
        "admission": "CLASSICAL_VERIFIER_ONLY_NO_RUNTIME_AUTHORITY",
        "interpretation": "Toy split of three mutually conflicting hypothetical jobs; "
                          "not an actual FRIDAY scheduler and not quantum advantage",
    }
    raw = json.dumps(report, sort_keys=True, separators=(",", ":"))
    return {**report, "receipt_sha256": hashlib.sha256(raw.encode()).hexdigest()}


if __name__ == "__main__":
    print(json.dumps(run_experiment(), indent=2, sort_keys=True))

# FRIDAY Quantum-vs-Deterministic Bench — 2026-10-25

**Status: TESTED LOCALLY / PENDING GITHUB CI / NO REAL QUANTUM HARDWARE USED.** Isolated, reversible research candidate. Neither Harness nor live FRIDAY is modified. No package, IBM credential, network request, quantum hardware job, subscription or spending.

## Why
Owner asked whether IBM Quantum's servers could benefit the deterministic FRIDAY machine. Treat quantum computation as a **probabilistic proposal engine**, never as the governing authority. Keep authorization, input validation, constraints, job identity, independent scoring, receipts and activation deterministic.

## Toy problem and experiment
Three hypothetical tasks (`compile`, `inspect`, `archive`) conflict pairwise. Partition them into two lanes to maximize conflicting pairs separated (Max-Cut). This is a *toy analogy*, **not** an actual machine scheduling contract.

- Independent classical reference enumerates all 2^3=8 allocations. Exact best cut score **2**; six optimal assignments.
- QAOA-inspired ideal depth-one circuit is simulated by **classical Python** complex statevectors, using H on each qubit, diagonal cost phase for Max-Cut and X-mixer rotations. Deterministically search 17 × 17 = **289** angle pairs, then make **256 seeded pseudorandom samples** from the ideal probability distribution.
- First local execution of the isolated fixture: expected cut score approximately **1.9972601386912499**, best sampled score **2**, gamma approximately **2.5525440310**, beta approximately **1.2762720155**. This does not demonstrate a runtime advantage (exhaustive search is trivial here).
- Simulator source: `experiments/friday_quantum_bakeoff.py`. Tests: `tests/test_friday_quantum_bakeoff.py`. The script generates a SHA-256 receipt from the canonical JSON result. All seeded, count-bounded operations are reproducible. No environment or secrets are read.

The critical safety assertion is that *even a successful quantum proposal has no permission to cause a real action*. The current result carries `CLASSICAL_VERIFIER_ONLY_NO_RUNTIME_AUTHORITY`.

## IBM Quantum hardware comparator (not executed)

As of 2026-10-25 IBM Open Plan advertises **10 free QPU minutes per rolling 28 days**: https://quantum.cloud.ibm.com/docs/en/guides/plans-overview

IBM's current QAOA tutorial uses **Premium-only sessions**; Open Plan must use individual **job-mode** submissions: https://quantum.cloud.ibm.com/docs/en/tutorials/quantum-approximate-optimization-algorithm

IBM Quantum Compute client `0.50.0` (Sep 24, 2026) deprecates older server-side `SamplerV2` and `EstimatorV2`; new client-side imports are `qiskit_ibm_runtime.executor_sampler.Sampler` and `...executor_estimator.Estimator`: https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/release-notes

When an **independently approved Open Plan account** is present and after verifying current API syntax and usage estimates, an optional Qiskit circuit can be assembled from the fixture's optimized angles:

1. `QuantumCircuit(3)`, `h(q)` for each qubit.
2. For each edge `(u,v)`, apply `rzz(-gamma,u,v)`. Up to a global phase this represents `exp(-i gamma MaxCut)`.
3. Apply `rx(2*beta,q)` to each qubit; then `measure_all()`.
4. Transpile to actual backend ISA, verify jobs estimate/billing instance (Open Plan only), and run with a **bounded shots count and no session**.
5. Archive backend identity, package versions, exact angles, compiled/transpiled circuit digest, job ID, shot counts, noise and uncertainty, and compare against the independent classical optimum.
6. Stop on authentication, plan or billing ambiguity. No fallback to Pay-As-You-Go.

This is a *specification for a potential IBM run*, **not implemented hardware integration**; device error/noise and drift may make the measured distribution quite different.

## Falsification criteria

- Classic exact answer must be 2 and the normalized ideal state vector must sum to 1.
- Different parameters lead to different distributions; fixed seed/angles reproduce the same local receipt.
- Invalid graph, out-of-bounds shots, bogus bitstrings, nonfinite angles and invalid probabilities are refused.
- A circuit result cannot change Harness pins, FRIDAY policy, compiled job identity, or permitted execution scope.
- The honest expected outcome is **no proven quantum advantage**. A useful result may be only a better way to model uncertainty and validate proposed task partitions.

**Classification: TEST (isolated research candidate), not DEPLOY.** Keep phone/Cloudflare Preview parked and avoid changing the active `FRIDAY_BOUNDED_OPERATOR_LOOP` gate.

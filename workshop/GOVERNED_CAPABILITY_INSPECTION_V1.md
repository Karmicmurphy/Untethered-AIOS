# Governed Capability Inspection V1

Status: deployed and verified on 2026-08-24. Release metadata label: `1.18.0`.

Capability Inspection extends the existing Build + Modules V2 Capability Bay. It does not create another room, registry, worker framework, or installation system.

## Authority and lifecycle

The lifecycle is:

`DISCOVERED → plan pending → explicit plan approval → static/dependency/hardware inspection → optional fixed-adapter functional evidence → VERIFICATION_CANDIDATE / NEEDS_REVIEW / BLOCKED / INCOMPATIBLE / FAILED → explicit owner decision`

`VERIFIED` is never an automated verdict. It requires an owner decision bound to the exact evidence hash, capability version, registry hash, hardware-profile hash, and timestamp. A different version or hardware profile cannot inherit that state.

Inspection jobs and receipts use the existing SQLite `jobs` and `receipts` tables; schema version 13 remains sufficient. The canonical JSON capability registry remains immutable at runtime. Inspection truth appears as a derived exact-version/hardware overlay.

Functional adapters are fixed code registrations, not owner-supplied commands. V1 exposes no arbitrary shell, executable, URL, filesystem, PATH, credential, environment, startup, scheduled-task, or system-install surface. One inspection may be active at a time. Disposable workspaces must remain outside the Workshop root and are removed on success or failure.

## Evidence

Each completed inspection records a canonical hash-addressed `twis-capability-inspection-v1` evidence object in the existing job record. It includes source, license, dependency, permission, hardware, functional, performance, security, network, filesystem, input/output hash, cleanup, limitation, and verdict fields. Receipts bind plan creation, plan decision, evidence, failures, and owner decisions.

## rembg result

Official-source static inspection on 2026-08-24 found rembg 2.0.81 (MIT source code), Python 3.11+, an ONNX Runtime CPU option, and a material scientific-Python dependency set. The current default is the separate BRIA RMBG-2.0 model, reported by the project at roughly 1.02 GB and under a model license that requires a paid agreement for commercial use. Its exact asset byte count and SHA-256 were not downloaded or independently measured. The project still offers `u2net` by explicit model selection, but that path was not downloaded or measured either.

On this AMD A4-6210 / 6.94 GiB Windows 10 computer, the truthful static hardware result is `MAY WORK`, not a fit claim. The package supports CPU and the local Python version, but the default model may be marginal on this machine. Installation footprint, full transitive set, exact model hash, peak RAM, CPU latency, output quality, and cleanup after a real install remain unmeasured.

Therefore V1 records rembg as `NEEDS_REVIEW`, not `VERIFICATION_CANDIDATE` or `VERIFIED`. No rembg package, model, runtime, or image operation was installed, downloaded, or executed. The much smaller `u2netp` path remains unmeasured; its rembg-hosted ONNX release asset also lacks sufficiently explicit model-file license/provenance evidence for selection in the background-removal acquisition candidate. A functional test always requires a separately generated exact authority plan and explicit owner approval.

Primary research evidence:

- PyPI rembg 2.0.81 release metadata and distribution hashes
- Official `danielgatis/rembg` repository `pyproject.toml`, MIT license, README model catalog, and model-license warning
- Official project release history

## Supported V1 depth

- native: metadata and existing health evidence
- Agent Skill: static structure/security metadata; scripts blocked
- local/disposable worker: metadata and already-supported bounded health
- MCP: identity/protocol/tool/resource/schema/health metadata; no tool execution
- A2A: Agent Card validation only
- WASI component: metadata/interface only
- ComfyUI workflow: workflow/schema/requirements only
- local model engine: metadata and existing verified health/performance evidence
- cloud free tier: cost/quota/account/network/provider metadata only
- media runtime: registered binary hash/version/features/health

Deeper inspection remains explicitly unsupported unless a fixed adapter and an approved authority plan exist.

## OpenCV GrabCut synthetic result

The separately approved `opencv-grabcut-synthetic-v1` inspection executed OpenCV 4.14.0 against four deterministic 256x256 synthetic cases. The exact evidence hash `34C09EEFA97856ED4BC9CDF91EC76F4AFE0E4910006185C5348878AE685FACD0` was accepted by the owner on 2026-08-25 and recorded by receipt `73da128c-83c8-4967-9ec9-f1a4b2ed5027`.

That decision verifies the evidence only. It does not install OpenCV, enable an Images operation, or establish production-photo quality. The registry truth is deliberately `VERIFIED` plus `NOT-INSTALLED`; the recommendation layer requires `HEALTHY` runtime state before an approved or verified capability can be offered as usable.

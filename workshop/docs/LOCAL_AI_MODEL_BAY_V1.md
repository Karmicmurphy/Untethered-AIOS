# Local AI Model Bay v1

Release 0.17 adds one optional local inference boundary without making any room own a model.

`room -> governed fixed-worker plan -> deterministic route -> registered model -> registered llama.cpp adapter -> proposed result -> result approval -> inactive draft`

## Fixed Release 0.17 boundary

- Runtime: official llama.cpp Windows CPU server build `b10333` (`08659901c`).
- Binding: `127.0.0.1:8876` only.
- Model: `LiquidAI/LFM2.5-1.2B-Instruct-GGUF`, official `Q4_K_M` file.
- Model resources live beside the Workshop under `TWIS_LOCAL_AI`; the application manifest records exact relative paths, sizes, SHA-256 values, repository revision, runtime build, and license reference.
- Auto-start is off. Workshop startup and all deterministic rooms remain available while the model is stopped.
- The only Release 0.17 room integration is an explicit Write `Local AI Assist` rewrite.

## Governance

The model router accepts only the fixed task categories in the manifest. Runtime start uses a fixed executable and fixed argument list with `shell=False`; no owner command, executable path, model path, URL, or provider endpoint is accepted. The adapter can call only the fixed loopback endpoint. It never falls back to cloud inference.

AI output remains proposed content. The original registered source is hash-verified again before inference, again before result approval, and again before saving. Plan approval, execution, result approval, inactive saving, export, and rollback remain separate actions through the existing Worker Kit.

READY is withheld until the runtime returns exactly `TWIS_LOCAL_MODEL_OK` from a real inference request. A running HTTP server alone is not READY evidence.

## Operational states

- `REGISTERED`: manifest exists, but a resource is missing.
- `INSTALLED`: runtime and model exist and pass exact file/hash verification; process stopped.
- `LOADED_NOT_VERIFIED`: registered process responds but has not passed the real inference assertion in this Workshop session.
- `READY`: real bounded inference passed.
- `DISABLED`: owner disabled local AI.
- `ERROR`: installed resource failed verification or a runtime/inference action failed.

Model weights and runtime binaries are governed external local resources, not application source files. Application rollback does not duplicate or delete them; their separate resource manifests preserve provenance.

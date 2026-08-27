# Future Lightweight Local AI Routing

This is research architecture, not an installation manifest. This consolidation downloads and installs **zero** models and runtimes.

Rooms should request a bounded task capability; they should not own model paths or provider implementations. A future deterministic router may choose only an owner-enabled, installed, configured, hash-verified, healthy model that advertises the requested task.

## Resource tiers for an approximately 8 GB Windows PC

- **Tier 0 — utilities:** embeddings, classification, routing, and deterministic helpers.
- **Tier 1 — small local language model:** tagging, short extraction, metadata, routing, and basic offline assistance.
- **Tier 2 — stronger local model on demand:** loaded only for a bounded task and unloaded afterward.
- **Tier 3 — specialist media engines:** image, video, or audio runtimes activated independently and never kept resident by default.
- **Tier 4 — optional provider adapters:** cloud use only after explicit owner configuration and per-action authority.

Use lazy loading, one heavy runtime at a time, CPU-capable and quantized options, explicit storage/RAM estimates, no silent downloads, and no automatic activation.

## Future registry truth

Each entry should distinguish model name/family, purpose, runtime, local path, quantization, disk size, estimated RAM, hardware compatibility, license, installed state, enabled state, health state, and supported tasks. `known`, `installed`, `configured`, `healthy`, and `suitable` are different states.

## Candidates for owner-machine testing

- Microsoft BitNet family
- Gemma 4 E2B-class models
- current llama.cpp-compatible lightweight models and runtimes
- small embedding models
- quantized specialist models

These are candidates only. No benchmark or suitability claim exists until measured on the owner's PC. Existing Liquid-model notes remain historical/current Model Bay evidence but are not the future search baseline.


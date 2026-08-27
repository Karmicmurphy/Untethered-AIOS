# TWIS Capability Protocol and Candidate Review — 2026-08-23

This review records the standards and candidates used to shape `twis-capability-v1`. It is catalog evidence, not permission to install or execute anything.

## Adopted contract targets

- **Agent Skills:** the open format is a directory centered on `SKILL.md` with optional scripts, references, and assets. TWIS implements metadata discovery, structural validation, hashes, and lazy resource counts only. Scripts remain blocked. Source: <https://github.com/agentskills/agentskills>.
- **MCP 2026-07-28:** the current specification removes the initialize/session handshake, carries client/protocol metadata per request, introduces optional `server/discover`, adds routable headers, and makes list results cache-aware. TWIS implements a loopback-only discovery/catalog proof for `server/discover`, `tools/list`, and `resources/list`; it enables and calls zero tools. Source: <https://blog.modelcontextprotocol.io/posts/2026-07-28/>.
- **A2A 1.0:** Agent Cards advertise ordered `supportedInterfaces`, each with URL, binding, and protocol version. TWIS validates and stores descriptor metadata only; execution is `DEFERRED`. Source: <https://a2a-protocol.org/latest/specification/>.
- **WASI 0.3:** WASI 0.3 is stable and adds native async Component Model interfaces. No suitable runtime was already part of the Workshop, so TWIS adds a contract doorway and does not install Wasmtime or execute a component. Source: <https://wasi.dev/releases>.

## Candidate and provider decisions

- **OpenVINO 2026:** not installed. Current official CPU support focuses on documented Intel and Arm families; the detected AMD A4-6210 is classified `UNSUPPORTED` for this candidate rather than guessed compatible. Source: <https://docs.openvino.ai/2026/about-openvino/release-notes-openvino/system-requirements.html>.
- **rembg 2.0.75:** cataloged as a discovered MIT-licensed CPU/ONNX background-removal candidate. It is not installed, benchmarked, or verified, and normal first use introduces dependencies/model data. Hardware fit remains `MAY WORK`. Source: <https://github.com/danielgatis/rembg>.
- **Cloudflare Workers AI:** cataloged as optional, account/network-dependent, `OFFLINE`, and blocked. The current documented shared free allocation is 10,000 Neurons/day, but model eligibility and pricing may change. There is no credential, provider call, paid fallback, or core dependency. Source: <https://developers.cloudflare.com/workers-ai/platform/pricing/>.
- **ComfyUI:** only the existing workflow-compatibility contract is cataloged. No runtime, custom node, model, workflow execution, or worker is installed. The detected machine is not qualified for the declared GPU-heavy local stack.
- **llama.cpp model bay:** the existing loopback model/runtime registration is retained. The registered files are absent, so status is `OFFLINE` / `NOT-INSTALLED`; no claim of inference availability is made.

## Resource decision

This successor adds static JSON, standard-library validation/discovery logic, and dependency-free UI. It adds no always-on service, model, container, WASI runtime, MCP swarm, ComfyUI environment, OpenVINO package, provider credential, or paid dependency.

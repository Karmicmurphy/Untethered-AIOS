# Worker Card v0.1

Worker Card v0.1 is a validated capability declaration. It is not an operating-system security boundary and does not grant permission. Foundation 0.4 enforces exactly two fixed cards inside the bounded harness: the retained `reference-metadata-worker` proof and `artifact-compass-inspection-worker`. Other cards remain declarations and cannot run or activate.

Schema: `schemas/worker-card-v0.1.schema.json`

Validator: `companion/foundation/worker_cards.py`

## Compatibility

Only `schema_version: "0.1"` is accepted. Unknown fields and incompatible/malformed versions fail closed.

## Enforcement matrix

| Card field | Validator | Fixed Release 0.4 runtime |
|---|---|---|
| Identity/version/status/purpose | Closed formats and enums | Exact fixed worker identity/version rechecked |
| Input/output types | Nonempty unique strings | Worker-specific closed extension/MIME set and one JSON output |
| Read roots | Absolute Windows paths | Exact plan-bound public or fixture roots; parent and child path policy |
| Write roots | Absolute Windows paths | One bounded output root; exact file-effect validation |
| Blocked roots | Absolute paths; contradictions rejected | Database, archives, private roots, visuals, and protected files win |
| Network | Boolean | Must be false; no network client; scrubbed environment; no OS firewall claim |
| Shell | Boolean | Must be false; fixed argv with `shell=False` |
| Destructive actions | Boolean | Must be false |
| Approval required | Boolean/dependencies | Must be true; inspection also binds source/card/plan hashes |
| Timeout | 1–3600 seconds | Fixed at five seconds |
| Tests | Nonempty unique strings | One internal allowlisted deterministic test per fixed worker |
| Failure policy | Closed enum/range | Fail closed; no retries |
| Receipt required | Boolean | Must be true for run/promotion/attachment/rollback |
| Source provenance | Kind/source/optional SHA | Evidence only; not authenticated identity |

Example declarations under `examples/worker_cards/` remain validation examples, not executable workers.

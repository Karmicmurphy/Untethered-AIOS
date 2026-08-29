# Cognitive Substrate V0.1 contracts

Campaign 1 adds a small substrate beside Kernel V0.2. It does not replace the
Kernel, deploy into the Workshop, or implement the later cognitive roadmap.

## Contract map

| Contract | Stack position | Input | Output | Mutation authority | Required capabilities | Determinism and resource expectation | Receipt and failure contract | Central AI |
|---|---|---|---|---|---|---|---|---|
| WorkItem | governor input | ID, task class, urgency, owner priority, novelty, uncertainty, risk, expected benefit, budgets, memory pressure, empirical outcome history, available route estimates, protected flag | immutable validated record and input SHA-256 | none | none | validation is deterministic and O(number of routes) | invalid values fail closed before routing; its hash is bound into the route receipt | never |
| RouteDecision | governor output | one WorkItem plus valued route candidates | exactly one of IGNORE, DEFER, REFLEX, RULE, WORKER, CENTRAL_AI, OWNER_GATE | none | none | same input, estimates, thresholds, and history produce the same decision | includes reason code, benefit, cost, net value, resource assumptions, input hash, and decision receipt hash | only when route is CENTRAL_AI |
| Attention Governor V0.1 | model-governor layer | one WorkItem | one RouteDecision | emits evidence only; cannot execute handlers | AuditLog receipt emission | local Python; no model, network, database, or provider; linear in route count | emits one hash-linked cognitive.route receipt; infeasible work is DEFER, protected/high-risk work is OWNER_GATE | never calls it; it only authorizes the route |
| Computation Memory V0.1 | computation-memory/evidence layer | computation identity, input/dependency hashes, producer, result hash, resource/cost measurements, rule, proof, state | persistent record, reuse decision, or dependent invalidation set | may mutate only its configured candidate SQLite ledger | bounded local SQLite file and AuditLog receipt emission | rollback journal; graph traversal touches only reachable dependents | mutation and reuse-check receipts; invalid digests and unknown dependencies fail closed | never |
| Reflex Handler | future cheap-handler boundary | WorkItem plus fixed handler identity | bounded deterministic result or typed failure | only the explicit capability grants supplied by Kernel | exact Kernel grants; no self-grant | deterministic, low CPU/RAM, no model/network | must return output hash and capability receipts; governor records routing separately | prohibited |
| Blackboard | future coordination boundary | typed facts with owner/process provenance | current typed fact view | append/replace only within an explicit namespace grant | future blackboard namespace capability | ordering and conflict policy must be deterministic | every mutation needs actor, prior/new hash, and failure evidence | not required by contract |
| Memory interface | future general memory boundary | typed key/query, namespace, provenance, retention rule | typed record(s) with proof references | scoped namespace mutation only | explicit read/write memory grant | backend replaceable; no vector database assumed | mutations and invalidations receipted; unavailable backend fails closed | not required |
| Capability Cell | future capability packaging boundary | signed/hashed contract identity, exact scope, resource budget, handler binding | registered bounded capability or denial | registration authority only; cannot widen a process grant | Kernel registration authority | load/validation deterministic; runtime budget declared | registration and invocation evidence; hash mismatch denied | declared per cell, default no |
| Model Gateway | future optional model-adapter boundary | governor-authorized request, prompt/input hashes, model policy, budget | typed result or typed provider failure | no OS authority; cannot override Kernel/governor/owner gates | explicit model grant and, for external providers, destination/credential grant | replaceable backend; cost and latency measured | request/result hashes, model identity, cost, and failure receipt without secret capture | yes, but only after CENTRAL_AI |
| Cognitive Downshift candidate | deferred model-governor optimization | measured central-AI workload and proven cheaper substitute | explicit TEST/DEFER decision or later bounded experiment | none in V0.1 | none in V0.1 | no runtime, model, or dependency is added in Campaign 1 | future experiment requires its own proof and rollback | candidate aims to reduce it |

## Routing value model

For every feasible execution route:

`expected net value = expected benefit * empirical success probability - estimated cost`

Benefit and cost use the same caller-supplied utility unit. Empirical success is
the route estimate multiplied by the observed success rate in failure history;
`true` entries mean failed prior attempts and `false` entries mean successful
prior attempts.
The governor does not blend urgency, novelty, or risk into an opaque score:
those values enforce explicit ignore, owner, handler-familiarity, and resource
boundaries. Positive feasible candidates are compared directly. Exact ties use
stable order REFLEX, RULE, WORKER, CENTRAL_AI.

## Authority boundary

The governor chooses; it does not execute. Kernel V0.2 remains process and
capability authority. Computation Memory owns only its configured candidate
ledger. Models, handlers, workers, blackboards, and future memory backends
cannot self-grant authority or treat a route decision as a capability grant.

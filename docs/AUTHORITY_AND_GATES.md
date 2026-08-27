# Authority and Gates

## Authority

```text
LOCAL WORKSHOP = private authority
UNTETHERED REPO = experimental descendant
GITHUB = code/review history
CLOUD = optional bounded adapter
MODEL = replaceable compute
WORKER = disposable process
ARTIFACT + RECEIPT = durable evidence
OWNER = deployment/destructive authority
```

## Protected-state rule

AIOS development must not mutate:

`C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`

unless the owner issues a separate, explicit production Workshop change/deployment instruction.

## Gates

### Reversible candidate work

Codex may proceed automatically:

- create/edit AIOS code;
- write tests;
- run tests;
- create mock adapters;
- create manifests;
- create evidence;
- fix ordinary candidate bugs;
- benchmark local candidate code;
- simulate deployment/rollback.

### Owner gate required

Stop before:

- modifying the authoritative live Workshop;
- deploying into the authoritative Workshop;
- destructive data deletion;
- publishing externally;
- spending money/enabling paid service;
- widening permanent credentials/permissions;
- making cloud or external provider authoritative.

## Baseline gate

Before copying Workshop code into `workshop/`:

1. inspect local Workshop;
2. run baseline authentication;
3. record exact source path and tree SHA-256;
4. identify excluded private/runtime files;
5. copy code-safe snapshot;
6. hash copied snapshot;
7. verify copied code-safe tree matches the authenticated manifest.

No memory-based reconstruction.

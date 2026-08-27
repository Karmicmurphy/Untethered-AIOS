# Worker Packet 0.8 Contract

## Role

`worker-packet-v1` is the minimum replaceable handoff between a current
Workshop source and one fixed Release 0.8 worker. It prevents a worker from
receiving full project context, unrelated history, private archives, or
authority it does not need.

Release 0.8 does not implement a universal prompt builder, handoff builder,
tool router, or model adapter.

## Required packet fields

Every packet contains:

- `schemaVersion`: exactly `worker-packet-v1`;
- `sourceReferences`: one registered source with artifact identity, owner
  title, kind, current version where applicable, and SHA-256;
- `minimumContent`: selected content only for Note Proposal, otherwise omitted
  from the packet and resolved from the hash-bound registered source;
- `jobPurpose`: one owner-facing bounded purpose;
- `permissions`: only the selected worker's required permissions;
- `prohibitedPermissions`: the contract's explicit deny list;
- `expectedOutput`: exact versioned output schema;
- `limits`: worker input, output, runtime, and archive bounds as applicable;
- `provenance`: source identity/hash/version and Worker Card contract hash;
- `validation`: current source, current selection, valid contract, denied
  network, and denied shell assertions.

The packet has a canonical JSON SHA-256. The enclosing plan binds:

- packet hash;
- source hash and version;
- worker ID and version;
- contract and implementation hashes;
- expected package members/hashes where supplied;
- created and expiry times;
- owner-facing reads, possible creations, and denied access;
- separate approval record and original plan hash.

## Bounded content rule

- one source only;
- no project-wide transcript or artifact history;
- no private archive content unless the explicitly selected registered source
  is itself the package being validated;
- no credentials, settings, unrelated receipts, review notes, permissions,
  source archives, or attachments;
- selected note content at most 256 KiB;
- registered text at most 512 KiB;
- package at most 16 MiB with at most 500 members and 64 MiB expanded size;
- request body at most 256 KiB.

The Package Manifest Validator reads archive members in bounded memory only to
compute hashes. It does not extract them to the filesystem.

## Creation and validation

The host creates the packet from registered SQLite identity and current
content. Owner language cannot introduce a path, permission, worker program,
shell command, network address, or plugin.

Creation fails if:

- project, artifact, worker, or source type is unsupported;
- registered file path is absolute, traversing, outside its canonical project,
  or crosses a reparse point;
- current bytes do not match the registered hash;
- Talk/Write current version is unavailable;
- selected content is blank, too large, or no longer in the source;
- expected package paths are unsafe, repeated, too many, or paired with
  malformed hashes.

Execution revalidates the source, selection, expiry, packet-bound plan,
contract, and implementation. A packet created from older source state never
authorizes current source state.

## Replacement boundary

Future builders may create `worker-packet-v1` values only if they preserve all
current validation and authority rules. A later schema requires an explicit
version bump and migration; consumers must not infer or accept unknown fields.

Optional future model or provider adapters must remain outside Release 0.8 and
may not reinterpret this packet as permission for network, attachment,
activation, module promotion, or arbitrary tools.

## Evidence claim

A valid packet proves only that:

- one current registered source was resolved;
- the selected fixed contract was current;
- the declared bounded content and permissions were validated;
- prohibited capabilities stayed prohibited in the in-process worker design.

It does not prove semantic correctness, owner acceptance, package safety
beyond inspected evidence, or permission to attach or activate the result.

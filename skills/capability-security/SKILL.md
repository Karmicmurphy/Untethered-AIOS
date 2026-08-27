# Skill: Capability Security

Use this skill whenever adding a tool, filesystem action, process execution, network access, artifact mutation, or external adapter.

## Rules

- deny by default;
- capability name alone is insufficient for scoped resources;
- canonicalize filesystem paths before scope comparison;
- reject traversal and scope escape;
- never trust a worker-provided "approved" flag;
- network access must have explicit allowlisted destinations;
- no capability self-elevation;
- mutations produce receipts;
- destructive/permanent/publish/deploy operations require owner gate.

## Tests required

At minimum:

- allowed call succeeds;
- missing capability denied;
- wrong scope denied;
- traversal/scope escape denied when paths are involved;
- receipt emitted for governed mutation.

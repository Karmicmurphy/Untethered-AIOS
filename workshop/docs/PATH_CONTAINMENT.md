# Windows Path Containment

`companion/foundation/path_policy.py` provides canonical, component-aware containment for cooperating callers.

## Policy behavior

- Resolve the requested path before comparing it with roots.
- Keep read and write roots separate.
- Check blocked roots before allowed roots.
- Deny parent (`..`) components before resolution.
- Deny relative paths unless the caller supplies an explicit base.
- Deny UNC paths by default; opt-in must be explicit.
- Deny a read of a nonexistent path by default; permit a nonexistent bounded write target.
- Treat drive mismatch and sibling-prefix lookalikes as outside the allowed root.
- Resolve existing symlinks and junctions so an outward target is denied.
- Deny reserved device names, alternate data streams, and trailing-dot/space components.
- Fail closed on canonicalization errors.

The test suite covers traversal, absolute escape, sibling-prefix confusion, drive mismatch, case variation, UNC, nonexistent paths, symlink escape, a real temporary directory junction, blocked roots, and separate read/write roots.

## Boundary

This class does not intercept arbitrary Python, shell, native, or child-process file access. A caller must request a decision and use `require_allowed()` before I/O. OS ACLs remain the final machine-level boundary.

The decision and later I/O are not atomic; callers handling attacker-controlled directories still need OS permissions that prevent time-of-check/time-of-use path replacement.

# TWIS Holo Workshop Architecture

`CURRENT_STATE.md` is the authoritative current-state description. This file summarizes the stable authority and trust boundaries.

## Runtime

- Windows desktop launcher: health/start gate and dedicated local window.
- Local origin: Python standard-library `ThreadingHTTPServer` on `127.0.0.1:8787`.
- Interface: static, dependency-light HTML/CSS/JavaScript.
- Authority: SQLite plus local project/source folders.
- Governed work: fixed workers and deterministic builders with exact hashes, separate approvals, receipts, recovery, and rollback.

## Authority order

1. Protected live source/data and explicit owner decisions.
2. SQLite artifact/project/receipt state and governed recovery evidence.
3. Derived test, manifest, and rollback evidence.
4. Public GitHub code/documentation/test baseline.
5. Optional Cloudflare transport/authentication metadata.

GitHub and Cloudflare never replace local Workshop authority.

## Remote trust boundary

```text
Cloudflare Access identity
  -> outbound named Tunnel
  -> loopback origin
  -> Access JWT signature/issuer/audience/expiry validation
  -> backend OWNER / GUEST_CREATOR / VISITOR authorization
  -> owner database or isolated Visitor's Bench database
```

Local loopback use remains OWNER. Remote requests without a valid Access token fail closed. Guests cannot reach owner APIs, and guest submissions are stored outside the owner database. Explicit owner promotion creates a new inactive owner artifact and receipt without mutating the guest source.

## Non-goals

No direct public port, router forwarding, public bind, cloud authority, automatic model installation, arbitrary provider execution, automatic guest promotion, or client-side-only authorization.

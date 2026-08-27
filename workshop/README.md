# TWIS Holo Workshop

TWIS is a local-first, artifact-centered creative and project Workshop. The authoritative live installation uses a loopback Python companion, static HTML/CSS/JavaScript rooms, SQLite/project storage, fixed governed workers, explicit approvals, receipts, recovery, and rollback.

Start with [CURRENT_STATE.md](CURRENT_STATE.md). It describes the current Workshop. Historical release files remain evidence, not the current entry point.

## Owner startup

On the installed Windows machine, double-click **TWIS Holo Workshop** on the desktop. The lightweight launcher checks `127.0.0.1:8787`, starts the existing service if needed, waits for health, and opens Sanctuary. The command-line fallback is `START_TWIS.bat`.

## Development

```powershell
python -m pytest tests -q -p no:cacheprovider
node --test tests\*.test.js
python tests\smoke_test.py
```

Use a copied database or isolated temporary data for state-changing tests. Never replace the live tree from GitHub. Stage a bounded candidate, inspect its diff and secret scan, prepare rollback, and deploy only the declared files.

## Public repository boundary

This public repository is a safe code/documentation/test baseline, not Workshop authority or backup of personal content. It intentionally excludes live databases, projects, archives, uploads, guest submissions, exports, logs, credentials, tunnel secrets, model weights, downloaded runtimes, compiled launcher binaries, and rollback packages. See [SECURITY.md](SECURITY.md).

## Remote access

Cloudflare remote access is optional and additive. The supported design is Cloudflare Access + outbound named Tunnel + TWIS origin JWT validation and backend authorization. The origin remains `127.0.0.1:8787`; there is no direct public port. Templates and the mandatory safe deployment order are in [cloudflare/README.md](cloudflare/README.md).

## Honest limits

GitHub cannot reconstruct protected local data or compiled/runtime resources. Cloudflare account resources are not created by source checkout. Visitor's Bench is a bounded Write/Music guest sandbox, not a social platform. Future model routing is documented without installing models.

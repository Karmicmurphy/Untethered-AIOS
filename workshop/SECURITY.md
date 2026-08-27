# Security Policy

## Authority and reporting

The live local Workshop and its protected data are authoritative. GitHub contains public-safe code, documentation, and tests only. Report suspected vulnerabilities privately to the repository owner; do not include secrets, private source content, database rows, tunnel credentials, or personal artifacts in a public issue.

## Never commit

- `.env` values, passwords, cookies, JWTs, API keys, Access tokens, tunnel tokens, service tokens, or Cloudflare credential JSON
- live SQLite databases, WAL/SHM files, project folders, uploads, guest submissions, exported personal content, receipts containing personal data, or source archives
- model weights, runtime downloads, browser profiles, logs, caches, test output, rollback packages, or compiled local launcher binaries

Run a secret/path scan on the staged candidate and inspect the complete diff before every public push. GitHub push protection should remain enabled where available.

## Remote access boundary

TWIS binds only to `127.0.0.1:8787`. Remote access uses an outbound Cloudflare Tunnel protected by Cloudflare Access. The origin validates the Access JWT and derives OWNER, GUEST_CREATOR, or VISITOR from configured application audiences and identity allowlists. Missing, forged, expired, wrong-issuer, wrong-audience, or unmapped tokens fail closed. UI hiding is never authorization.

Do not publish a hostname until its Access application and deny-by-default policy exist. Do not expose port 8787, add router forwarding, bind TWIS to `0.0.0.0`, or store tunnel credentials in this repository.

## GitHub Actions

Workflows use `contents: read` unless a narrowly documented job requires more. Cloudflare deployment is intentionally not automatic from this public repository.


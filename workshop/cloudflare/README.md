# TWIS Cloudflare Remote Access

This directory contains configuration templates and deployment order only. It contains no tunnel credential, token, account ID, domain, or owner identity.

The previous `twis-holo-remote` Worker/Durable Object design is retired in source. It was not the Workshop authority and its missing-token behavior was unsafe. Do not redeploy it.

## Target boundary

```text
Browser -> Cloudflare Access -> Cloudflare Tunnel -> 127.0.0.1:8787 -> TWIS authorization
```

- No router forwarding.
- No public bind. TWIS remains on `127.0.0.1:8787`.
- Access applications and deny-by-default policies must exist before a public hostname is routed.
- Cloudflare authenticates; TWIS validates the Access JWT and authorizes every API.
- Local desktop use remains loopback OWNER access and does not depend on Cloudflare.

## Required deployment order

1. In Cloudflare Zero Trust, create separate Access applications for the owner hostname and Visitor's Bench hostname. Create a preview application only if read-only visitor access is intentionally enabled.
2. Add deny-by-default policies, then narrow allow policies for the verified owner email and explicit guest invitations/domain.
3. Record the application audience tags locally as environment variables described in `config.example.yml`; never commit values.
4. Create a named tunnel and install the official `cloudflared` Windows service using the dashboard-issued command. Keep credentials under the service account/ProgramData, outside this repository.
5. Adapt `config.example.yml` with the real existing domain and tunnel UUID in the protected Cloudflare configuration directory.
6. Verify Access denial and TWIS origin authorization before adding the final public hostname route.
7. Test OWNER, GUEST_CREATOR, and VISITOR abuse cases. Only then classify old resources for retirement.

No authenticated Cloudflare account was available while this source baseline was prepared, so no account resource, DNS record, tunnel, policy, service, or hostname is claimed as deployed.


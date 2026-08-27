# Current Upgrade Pass — 2026-06-18

## Added in this pass

- Local companion `/api/capabilities` endpoint.
- Local companion `/api/security-policy` endpoint.
- Cloudflare `/capabilities` endpoint.
- Optional Cloudflare write-token support via `REMOTE_WRITE_TOKEN` secret.
- Optional Cloudflare `ALLOWED_ORIGIN` CORS restriction.
- Protocol security document for MCP / AG-UI / A2UI / A2A adapters.
- Cloudflare README updated with safer deploy guidance.
- Expanded API end-to-end test to check capabilities and security policy.
- Clean release rebuild.

## Why this pass matters

The previous audited build was functional, but the Cloudflare remote hull accepted writes without an optional token and the protocol adapters did not have a written deny-by-default policy. This pass hardens those pieces before any real external tools are connected.

## Still needs external action

- GitHub manual upload or connector write access.
- Cloudflare login and deploy.
- Installing local model runtimes or downloading model weights.
- Importing the owner's actual folders and media.

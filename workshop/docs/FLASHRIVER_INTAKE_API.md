# FlashRiver Intake API

The local companion exposes:

```text
POST /api/import-flashriver
```

Request body:

```json
{
  "path": "C:\Users\Owner\Downloads\FLASHRIVER_TWIS_WORKSHOP_AGENT_HANDOFF_PACKAGE.zip",
  "expectedSha256": "6ef7317722202769b08d74a434519871736e055d1864fa5eb6c6fb547cb40108",
  "projectId": "flashriver-source-archive",
  "title": "FlashRiver Source Archive"
}
```

The Recover room now has a button named `Import FlashRiver package` that sends this request.

Boundary: the raw ZIP and nested source ZIPs stay local under `data/source_archives` and the active project's `sources/flashriver/...`. GitHub and Cloudflare are not private source authority.

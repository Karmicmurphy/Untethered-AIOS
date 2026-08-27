# Public Repository Inclusion / Exclusion Plan

The live Workshop is authoritative. A public Git branch is assembled from an allowlisted current-state surface; it is never copied back over the live root.

## Include

- application HTML/CSS/JavaScript
- Python companion and fixed worker source
- schemas, examples, public-safe skills, tests, and GitHub workflows
- current and historical release documentation that contains no protected content
- desktop-launcher source, project file, icon, manifest, and documentation
- static model registry metadata only (no weights/runtime)
- Cloudflare architecture documentation and placeholder configuration only
- root startup scripts, package metadata, license, README, CURRENT_STATE, SECURITY, and `.gitignore`

## Exclude

- `data/**` except an empty `.gitkeep`
- all SQLite/DB/WAL/SHM files
- project folders, source archives, FlashRiver packages/receipts, uploads, guest submissions, exports, and user-created artifacts
- `.env`, credentials, keys, certificates, cookies, tokens, tunnel JSON, Cloudflare account values, and machine-auth state
- model weights and downloaded runtimes
- compiled launcher executables/PDBs and other generated binaries
- caches, bytecode, logs, browser/test output, evidence directories, backups, and rollback packages

## Synchronization rule

Create a new branch from remote `main`, overlay only the include surface from the verified live root, remove obsolete remote-only product files, run tests and a path/content secret scan, inspect the complete diff, then push without force. A pull request—not a direct merge—carries the baseline into `main`.

Unexpected personal data, credentials, or unexplained mass deletion blocks publication.

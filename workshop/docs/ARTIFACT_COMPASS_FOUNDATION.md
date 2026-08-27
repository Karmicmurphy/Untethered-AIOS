# Artifact Compass Foundation

Artifact Compass is a deterministic, rebuildable SQLite/FTS5 metadata index. It is deliberately separate from `data/workshop.sqlite3`; the Workshop database and source artifacts remain authoritative.

Implementation: `companion/foundation/artifact_compass.py`

Example inventory: `examples/artifact-compass-inventory.example.json`

## Indexed fields and queries

- artifact ID and project ID
- source path and filename
- exact SHA-256
- review/status value
- structured provenance JSON plus searchable provenance text
- optional content text for exact-phrase/full-text queries
- optional byte size and source modification nanoseconds
- source fingerprint, index generation, and tombstone state

Search supports filename, path, exact phrase, project, status, and provenance filters with deterministic ordering. Exact-hash duplicate groups return every artifact and `all_source_paths`; grouping never deletes, rewrites, or hides a source record.

## Generations, reindex, and tombstones

Every sync advances the generation. New and changed records are indexed; unchanged records are marked seen in the new generation. Records absent from the supplied authoritative inventory become tombstones rather than being deleted. `detect_stale()` reports changed, missing, returned-after-tombstone, and not-yet-indexed entries. `rebuild()` recreates derived rows while preserving the monotonic generation counter.

## Commands

All paths are explicit. No command defaults to the live database or private archives.

```powershell
python -m companion.foundation.cli rebuild-index .\work\compass.sqlite3 .\examples\artifact-compass-inventory.example.json
python -m companion.foundation.cli search-index .\work\compass.sqlite3 "Foundation example phrase" --exact-phrase
python -m companion.foundation.cli duplicate-groups .\work\compass.sqlite3 --project example-project
python -m companion.foundation.cli check-index .\work\compass.sqlite3 .\examples\artifact-compass-inventory.example.json
```

`check-index` exits with code 3 when stale entries are found.

## Limits

Release 0.2 does not automatically index Workshop/private data, parse archives, delete duplicates, provide vector search/embeddings, or make Artifact Compass authoritative. It indexes only the explicit inventory a caller supplies.

# TWIS Background Composition — Images V2

Status: VERIFIED CANDIDATE — NOT DEPLOYED

This bounded successor adds one real Images V2 operation: place a registered foreground over a solid color, a two-color gradient, or a second registered project image.

## Owner workflow

1. Open Images and load a registered image.
2. Open Edit → Compose Background.
3. Choose Solid color, Gradient, or Registered image.
4. Preview the composite locally in Canvas 2D.
5. Compare the protected foreground with the proposed composite.
6. Reject without saving, or explicitly approve and save one new inactive image.
7. Reopen the saved composite through My Work.

## Authority and safety

- Preview is local and unsaved.
- Refresh never resumes a save or silently creates an artifact.
- Approve and Reject are separate owner actions.
- The server verifies the exact foreground hash before every save.
- Registered-image mode verifies the exact background hash too.
- The saved artifact remains `DRAFT` / `inactive-draft`.
- Both source relationships, hashes, composition settings, Canvas engine identity, and approval state are retained in provenance and the approval receipt.
- No source is overwritten, attached, activated, published, or promoted.
- No provider, model, network service, worker, shell, or new runtime is used.

## Scope

The release changes only the existing Images V2 client, media save contract, service-worker cache identifier, bounded tests, and release documentation. It adds no schema migration and no database file to deployment scope.


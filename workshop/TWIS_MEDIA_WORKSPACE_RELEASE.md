# TWIS Media Workspace Correction and Images V2 Release

## Naming correction

The previous implementation prompt accidentally named a new subsystem “HubUI.” That mistake did cause active filenames, classes, routes, schema names, tests, documentation, a cache key, and one claimed worker abstraction to be created.

This release removes that invented abstraction. Useful implementation is rehomed as bounded TWIS media operations:

- projects, artifacts, artifact relationships, and receipts remain authoritative;
- Modules reports capability state;
- the existing local companion provides bounded persistence and routing;
- the existing worker registry remains the only worker authority;
- ComfyUI is represented only as an unregistered compatibility target.

No compatibility alias is retained because the live database contained zero artifacts using the mistaken schemas or name.

## Images V2

Images now provides a real local light-table workstation:

- drag/drop or choose bounded PNG, JPEG, or WebP files into a dominant editable Canvas2D light table;
- draw, place owner text with position/size/alignment controls, grayscale, invert, clear, reset, bounded undo, compare, and export PNG;
- save an inactive, content-addressed visual asset or provenance-linked variation in the current project;
- reopen governed visual assets from My Work;
- create inactive scenes and ordered storyboard frames, reorder them, or remove a frame without deleting its source image;
- see, use, attach, or locally dismiss routed Write context and route selected visuals to Music or Video;
- route exact registered artifact references among Write, Images, Music, and Video;
- inspect truthful capability evidence.

The existing Visual Brief Builder remains available. Image generation, inpainting, upscaling, animation, and video rendering are not claimed.

## ComfyUI audit result

- Real ComfyUI runtime: not found.
- Workflow JSON: no executable workflow found; only an empty WCHO workflow placeholder directory was present.
- Custom nodes: not found.
- Image/video checkpoints, LoRAs, ControlNet models, or VAEs associated with ComfyUI: not found.
- System FFmpeg: not found on PATH; old Playwright-bundled helper executables are not treated as a media engine.
- Node packages named for ComfyUI: found, but they are wrappers and not a working runtime.
- Compatible TWIS media worker: not registered.

On the audited low-spec owner machine, heavyweight local diffusion/video execution is not currently realistic. A future compatible worker may run locally only for a proven bounded workload or on a separately approved disposable worker. TWIS retains project authority, provenance, review, and approval in either case.

## Database and governance

No schema migration or database replacement occurs. SQLite `user_version` remains 13. Source artifacts are not modified. New assets and scenes remain inactive. No provider, external request, model installation, node installation, or silent generation is introduced.

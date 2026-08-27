# TWIS Media Workspace Contract v1

This contract does not create a new product layer. It defines bounded media operations implemented with existing TWIS projects, artifacts, relationships, receipts, Modules registration, and worker authority.

## Authority

- A TWIS project remains the owner context.
- Writing, images, music, video, scenes, routes, and storyboard items remain ordinary TWIS artifacts.
- Cross-room references retain the registered source artifact identity and exact source SHA-256.
- Every new record begins in DRAFT or another explicitly inactive state.
- Routes reference sources; they do not copy, overwrite, approve, activate, or publish them.

## Available local operations

- Browser Canvas2D import, draw, text overlay, grayscale, invert, reset, and PNG export.
- Owner-facing drag/drop or file selection for signature-checked PNG, JPEG, and WebP inputs up to 12 MiB, with a 4096-pixel working-canvas bound.
- A bounded five-change undo history and side-by-side protected-source/working-version comparison.
- Content-addressed PNG, JPEG, or WebP storage after bounded byte, type, dimension, project, and path validation.
- Saved variations record their parent image ID, verified parent SHA-256, and original owner-input SHA-256. A changed or missing parent file blocks the variation.
- Inactive scene creation.
- Reference routing among Write, Images, Music, and Video.
- Inactive ordered storyboard items joining a registered scene and registered image. Reordering or removing a frame never removes its source image.
- Incoming Write references are displayed as project context and retain their registered identity and hash. The owner may dismiss one from the current browser working view without deleting its governed route.

## ComfyUI compatibility

ComfyUI is an optional execution ecosystem, not the TWIS owner interface and not an authority over project state. The capability registry describes compatibility-only workflow contracts for generate, inpaint, upscale, and animate operations.

A compatible worker must be registered before any such operation becomes available. It must advertise its runtime version, workflow IDs, node types, model hashes, hardware class, and output types. It must return the workflow hash, input hashes, model hashes, output hash, and runtime receipt. Workflow JSON, custom nodes, models, and their environment are treated as one versioned compatibility requirement; arbitrary nodes are never copied out and treated as standalone TWIS features.

Current state: no ComfyUI runtime, workflow, custom node, image/video model, or compatible media worker is installed or registered. Generation controls therefore remain unavailable.

## Video composition and render

Video V2 extends the same artifact and relationship authority with two inactive kinds:

- `video-composition` / `twis-video-composition-v1` records ordered references to governed Images V2 assets, optional storyboard items and scene, one governed Music Studio render, bounded owner titles, durations, motion/transition presets, and render presets.
- `video-render` / `twis-video-render-v1` records a content-addressed MP4, its exact source/composition hashes, FFmpeg identity/hash, stream metadata, output hash, render duration, and receipt.

Every referenced image and audio file is rehashed immediately before rendering. A missing or changed source blocks execution. The local adapter invokes only the registered portable FFmpeg executable with a constructed argument list and fixed allowlisted presets; no client may submit executable paths, commands, filters, codecs, filenames, or shell text. Rendering requires an explicit owner action and never changes the source image, storyboard, writing, scene, or Music render.

The browser Preview is approximate and labeled separately from Final Render. Final Render currently supports still-image clips, cut/crossfade, bounded zoom/pan presets, titles, one Music Studio WAV source with volume/start/fades, 480p or 720p H.264 MP4, and AAC when audio is attached. It does not perform text-to-video, image-to-video, diffusion animation, narration generation, arbitrary clip import, or cloud/provider execution.

## Safety boundary

No cloud/provider request, shell execution, model installation, automatic worker registration, silent asset replacement, automatic approval, automatic activation, or database migration is part of this contract.

Imported local files are read into the browser only after validation. They are not registered until the owner explicitly saves the working canvas. Saving never overwrites the imported file or a registered parent asset.

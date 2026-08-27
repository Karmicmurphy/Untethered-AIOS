# TWIS Video V2 Production Workstation

Status: isolated candidate verified; live deployment is pending the exact-scope owner approval gate.

## Before

Video exposed the governed Video Production Brief Builder and could receive project/media routing context, but it could not assemble a timeline, preview a composition, or produce a playable video.

## What this candidate adds

- One owner-facing projection bay with a large browser preview, a visual/audio/text timeline, source bays, and obvious Add Storyboard, Add Image, Add Music, Add Title, Play, Stop, Save, and Render actions.
- Images V2 storyboard and image references, Music Studio WAV references, eligible Write title references, and the existing Project / Scene / Artifact authority.
- One to 24 still-image clips with bounded duration, ordering, cut/crossfade, still, zoom, and directional pan presets.
- One governed Music Studio WAV with start, volume, mute, fade-in, and fade-out composition settings.
- Up to eight title overlays with text, position, size, duration, and optional fade.
- Approximate browser preview clearly separated from final FFmpeg rendering.
- Fixed 480p or 720p local MP4 rendering through the registered portable FFmpeg runtime: H.264 video and AAC audio when music is present.
- Inactive `video-composition` and `video-render` artifacts, content-addressed MP4 storage, source relationships, source/runtime/output hashes, receipts, My Work reopening, and exact artifact rollback.
- Existing Video Production Brief Builder remains accessible.

## Source and authority boundaries

Video stores references and composition settings. It never overwrites Images, Music, Write, storyboard, scene, or project sources. Exact image, audio, and writing-reference hashes are revalidated before completion. A stale, missing, unregistered, mismatched, or unsupported source blocks save/render.

Outputs begin as DRAFT/inactive artifacts. No provider, model, ComfyUI runtime, cloud service, automatic approval, activation, publication, source mutation, or arbitrary command surface is added.

## Real renderer

- FFmpeg: `9.0.1-essentials_build-www.gyan.dev`
- Fixed binaries: `ffmpeg.exe` and `ffprobe.exe`
- No system install and no PATH modification
- Runtime location after approval: `C:\TWIS_FLASHRIVER_REVIEW_READY\runtime\ffmpeg\9.0.1`
- Required features verified: libx264, AAC, xfade, zoompan, drawtext, and afade

The runtime is an adjacent governed resource rather than an ordinary application file so the 100+ MiB binaries are not copied into every application rollback package.

## What Video still cannot do

- No imported video-clip trimming in this bounded release.
- No narration generation or subtitle-file workflow.
- No text-to-video, image-to-video AI, diffusion animation, ComfyUI execution, model download, or cloud rendering.
- No frame-perfect browser/final-preview parity claim.
- No mid-render cancel action; failure and timeout are bounded and do not create a successful artifact.

## Owner workflow

1. Open Sanctuary, enter Crossroads, and choose Video.
2. Choose the active project.
3. Add an Images V2 storyboard or selected governed images.
4. Optionally attach a governed Music Studio render and/or add title text from Write.
5. Set durations, order, motion, transition, audio, title, and the 480p/720p preset.
6. Preview in the browser.
7. Save the inactive composition.
8. Render the real MP4 locally.
9. Reopen the composition or rendered output from My Work.
10. Delete/roll back the unchanged derived artifacts without changing any source.

## ComfyUI truth

No ComfyUI runtime, workflow, custom node, checkpoint, image model, or video model is installed by this release. Existing compatibility-only contracts remain explicitly unavailable.

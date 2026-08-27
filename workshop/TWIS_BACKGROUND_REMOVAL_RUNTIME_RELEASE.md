# TWIS Background Removal Runtime + Images V2

## Release state

`VERIFIED CANDIDATE — NOT DEPLOYED`

This bounded successor adds one real Images V2 operation: owner-guided local background removal. It does not change the database schema, overwrite an image, install a model, add a cloud/provider path, or activate an output automatically.

## Owner workflow

1. Open **Images** and load a registered image.
2. Open **Edit → Remove Background**.
3. Draw one foreground rectangle.
4. Optionally mark pixels with **Keep brush** or **Remove brush**.
5. Select **Preview cutout**. The fixed local OpenCV adapter creates only a proposal.
6. Compare the protected source with the proposed transparent PNG.
7. **Approve & save inactive variation** or **Reject proposal**.
8. Reopen an approved inactive variation through **My Work**; normal artifact rollback remains available.

Refresh recovery restores a still-pending proposal. A changed or missing source hash blocks approval. The selected registered source is never rewritten.

## Runtime

- Engine: OpenCV GrabCut, OpenCV `4.14.0`
- Distribution: `opencv-python-headless 4.14.0.94`
- Numeric runtime: NumPy `2.5.2`
- Location: adjacent governed runtime under `runtime/background-removal/opencv-grabcut/4.14.0.94`
- Runtime tree: 1,033 files, 157,640,551 bytes
- Runtime tree SHA-256: `18668FDD9733C4F9039E55712E5C1022E37E6D1330EFDF7F5083B103D1BBB583`
- Runtime manifest SHA-256: `C9E178F183F662209C682222AA8590FA6C8E8A460F26A946F55F39E32EF102DE`
- Global Python/PATH changes: none
- Persistent process: none
- Network after provisioning: none

The runtime is invoked with `python -I -S` through one fixed adapter, one registered image identity, one exact source SHA-256, and bounded numeric controls. It has no arbitrary command, arbitrary path, model, credential, provider, or network surface.

## Honest limits

GrabCut is assisted foreground extraction, not one-click semantic AI. Hair, fur, transparency, clutter, and low-contrast edges may need owner correction. This release does not add neural matting, generative fill, ComfyUI, Stable Diffusion, automatic background replacement, batch execution, or silent retries.

## Resource impact measured on this machine

- Installed disk: 157,640,551 bytes (about 150.3 MiB), plus small Workshop integration files.
- Synthetic 640×480 run with one keep correction: 3.065 seconds inside the adapter; 4.511 seconds wall time including process startup.
- Observed all-Python working-set increase during that bounded run: about 94.9 MiB over the two already-running Workshop companion processes.
- Idle cost after the operation: zero additional resident process.

The exact candidate manifest, scope digest, rollback package, and verification evidence accompany this release candidate. Live deployment requires the exact owner approval string reported by Codex.

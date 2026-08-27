# TWIS Background Removal Capability Acquisition

Status: exact synthetic capability evidence accepted by the owner; runtime remains not installed and Images integration has not begun.

Decision date: 2026-08-24  
Authoritative live root: `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS` (read-only throughout this candidate)  
Target hardware: AMD A4-6210, 4 logical processors, approximately 6.94 GiB usable RAM, Windows 10, CPython 3.12.

## Artifact Compass scope

The pass widened from the existing rembg record through the underlying capability categories: classical foreground extraction, portrait segmentation, portrait matting, general salient-object removal, small ONNX paths, and multi-network matting. Evidence priority was official documentation, official repositories, and official package metadata. No package, model, runtime, or owner image was downloaded or executed.

Artifact classification:

- canonical: the live Capability Registry, Capability Inspection V1 authority schema, live hardware profile, and existing SQLite evidence tables;
- active supporting: official candidate documentation, package metadata, license text, hashes, and the isolated fixed-adapter source;
- verified narrowly: the accepted four-case synthetic fixed-adapter evidence bound to OpenCV 4.14.0.94, the inspected registry, and the measured hardware profile;
- rejected for this laptop: heavyweight or incompatible runtimes whose operational cost is already disproportionate;
- missing: reliable model-file license/provenance for rembg's small hosted `u2netp` ONNX asset and any local quality evidence.

## Serious shortlist

| Candidate | Package and model license | Provisioning / footprint evidence | CPU / GPU | Offline | Expected fit and limitation | Hardware verdict | Inspection decision |
|---|---|---|---|---|---|---|---|
| OpenCV GrabCut 4.14.0.94 | Python packaging MIT; OpenCV Apache-2.0; bundled notices separate; no model | pinned OpenCV wheel 41.0 MB plus NumPy wheel 12.5 MB; installed footprint unknown until measured | CPU; no GPU | yes after provisioning | General owner-guided cutout; lightweight, but not automatic and weak edges may need touch-up | GOOD FIT | SELECTED for bounded functional inspection |
| MediaPipe Image Segmenter / selfie segmentation 1.0.0 | MediaPipe package Apache-2.0; exact task model license/hash still separate | Windows wheel 16.1 MB; task model and installed footprint unknown | CPU-capable; no required GPU established | expected after provisioning | Useful for people/portraits, not arbitrary objects | MAY WORK | retain as portrait-specific discovered candidate |
| rembg 2.0.81 | wrapper MIT; default BRIA RMBG-2.0 has a separate license requiring paid commercial use; small hosted ONNX provenance/license unresolved | default model reported about 1.02 GB; scientific Python + ONNX Runtime; `u2netp` reported 4.7 MB upstream but distributed ONNX asset unmeasured | CPU backend exists; no GPU required | expected after controlled provisioning | automatic general removal, but default is too costly/restricted for a free-first winner and small model evidence is incomplete | MAY WORK / UNKNOWN quality | NEEDS REVIEW; not selected |
| MODNet official repository | official repository says code, models, and demos Apache-2.0 | model bytes unknown; PyTorch/converted runtime burden expected in gigabyte class | CPU possible; no useful GPU assumed | yes after provisioning | good portrait scope, not general objects; legacy deployment stack | TOO HEAVY | INCOMPATIBLE for this release |
| CarveKit 4.1.0 | framework Apache-2.0; each model/transitive license still needs enumeration | PyTorch plus Tracer/U2Net and FBA; multi-gigabyte installed estimate; exact bytes unmeasured | CPU path exists; no GPU required but resource cost is high | yes after provisioning | broad quality-oriented pipeline, but too many models/dependencies and documented Python only through 3.11 | TOO HEAVY | INCOMPATIBLE for this release |

Unknown values remain `UNKNOWN`; estimates are not measurements.

## Authoritative sources

- OpenCV GrabCut tutorial: https://docs.opencv.org/4.x/d8/d83/tutorial_py_grabcut.html
- OpenCV Python headless 4.14.0.94 package metadata: https://pypi.org/project/opencv-python-headless/4.14.0.94/
- NumPy 2.5.2 package metadata: https://pypi.org/project/numpy/2.5.2/
- Google MediaPipe Image Segmenter documentation: https://ai.google.dev/edge/mediapipe/solutions/vision/image_segmenter/python
- MediaPipe 1.0.0 package metadata: https://pypi.org/project/mediapipe/1.0.0/
- rembg official repository: https://github.com/danielgatis/rembg
- rembg 2.0.81 package metadata: https://pypi.org/project/rembg/2.0.81/
- U-2-Net official repository: https://github.com/xuebinqin/U-2-Net
- rembg model-license provenance question: https://github.com/danielgatis/rembg/issues/837
- MODNet official repository: https://github.com/ZHKKKe/MODNet
- CarveKit official repository: https://github.com/OPHoperHPO/image-background-remove-tool

## Selection

`external.opencv-grabcut-cpu-candidate` wins the first inspection because its complete executable stack is genuinely free, model-free, CPU-only, Windows/Python 3.12 compatible, locally replaceable, and bounded to approximately 53.5 MB of pinned wheel downloads. It also supports a clean offline runtime after provisioning. It beats the automatic neural alternatives on complete-license clarity, RAM/disk risk, reproducibility, and containment.

The limitation is deliberate and owner-visible: this is a FAST / ASSISTED capability, not a QUALITY / AUTOMATIC capability. The first implementation should eventually require the owner to mark the foreground region. A separate automatic capability may be acquired later if its full package/model license and measured laptop cost are acceptable.

## Fixed functional inspection plan

The isolated adapter can only run the command ID `opencv-grabcut-synthetic-v1`. It permits:

- reads: registered capability metadata, measured hardware profile, curated official-source evidence, disposable synthetic inputs;
- writes: inspection job result, receipt, and the inspection-specific disposable workspace;
- network: two pinned HTTPS downloads from `files.pythonhosted.org` only;
- downloads: NumPy 2.5.2 and OpenCV headless 4.14.0.94 Windows wheels, each bound to an exact SHA-256;
- maximum download: 60,000,000 bytes;
- runtime: a disposable CPython 3.12 virtual environment outside the Workshop;
- credentials and inherited owner environment: none;
- timeout: 900 seconds;
- cleanup: delete venv, wheels, synthetic inputs, generated outputs, and scripts; retain only hash-addressed isolated job evidence.

The test set is four deterministic 256x256 synthetic images: high contrast, irregular edge, fur-like edge, and similar tones. Planned evidence includes environment/download footprint, wall and CPU time, peak working set, output RGBA validation, source hashes, output hashes, mask IoU, false foreground/background, edge error, network/filesystem activity, and cleanup.

## Governed result

The exact inspection plan was approved and executed in the isolated acquisition workspace. OpenCV 4.14.0 GrabCut produced four validated 256x256 RGBA outputs while preserving all synthetic sources. The narrow synthetic sanity metrics were mean IoU 1.0 with zero measured false-foreground, false-background, and edge error. Those values are not evidence of quality on photographs, hair, clutter, owner images, or production workloads.

Evidence SHA-256: `34C09EEFA97856ED4BC9CDF91EC76F4AFE0E4910006185C5348878AE685FACD0`  
Owner verification receipt: `73da128c-83c8-4967-9ec9-f1a4b2ed5027`  
Evidence decision time: `2026-08-25T00:47:51.501299+00:00`

The disposable environment was removed completely. No runtime or wheel remains installed in the Workshop. The Capability Registry may therefore show `VERIFIED` evidence and `GOOD FIT`, but must continue to show `NOT-INSTALLED`; Build must not recommend this capability as executable until a separate installation/integration release proves a healthy registered runtime.

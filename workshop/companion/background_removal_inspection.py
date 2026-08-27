from __future__ import annotations

import hashlib
import json
import os
import platform
import struct
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .capability_inspection import InspectionError, InspectionGuard


COMMAND_ID = "opencv-grabcut-synthetic-v1"
CAPABILITY_ID = "external.opencv-grabcut-cpu-candidate"
CAPABILITY_VERSION = "4.14.0.94"
MAX_DOWNLOAD_BYTES = 60_000_000
WHEELS = (
    {
        "name": "numpy",
        "version": "2.5.2",
        "filename": "numpy-2.5.2-cp312-cp312-win_amd64.whl",
        "sha256": "28ac63476ec7651484215ee7fa15a1f78b57c14621f01e392afe17b9a1390ce4",
        "url": "https://files.pythonhosted.org/packages/7f/b9/87fea2769fe1c47c1b5b01d8310772c9d1a85d485de7cf386ef7a3332b02/numpy-2.5.2-cp312-cp312-win_amd64.whl",
    },
    {
        "name": "opencv-python-headless",
        "version": CAPABILITY_VERSION,
        "filename": "opencv_python_headless-4.14.0.94-cp37-abi3-win_amd64.whl",
        "sha256": "cbed65415b8f6a9541c705afe3e64795840524d0ff3bc58f507826284a1dc64b",
        "url": "https://files.pythonhosted.org/packages/ad/8d/db8673846ee53cbb5de4c2b4decc11cf733e203eb7d5146297869f69bd48/opencv_python_headless-4.14.0.94-cp37-abi3-win_amd64.whl",
    },
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def authority_template(temp_root: Path) -> dict[str, Any]:
    return {
        "reads": [
            "registered capability metadata",
            "measured hardware profile",
            "curated official-source evidence",
            "disposable synthetic input",
        ],
        "writes": ["inspection job result", "receipt", "disposable workspace"],
        "network": ["two pinned HTTPS wheel downloads"],
        "allowedDestinations": ["files.pythonhosted.org"],
        "downloads": [
            f"{wheel['filename']} sha256:{wheel['sha256'].upper()}" for wheel in WHEELS
        ],
        "maxDownloadBytes": MAX_DOWNLOAD_BYTES,
        "runtime": "Disposable CPython 3.12 venv; pinned NumPy 2.5.2 and OpenCV headless 4.14.0.94",
        "commands": [COMMAND_ID],
        "temporaryWorkspace": str(temp_root.resolve()),
        "credentials": [],
        "environment": [],
        "hardwareTest": True,
        "timeoutSeconds": 900,
        "cleanup": "delete the inspection-specific venv, wheels, synthetic inputs, outputs, and scripts; retain hash-addressed job evidence only",
        "expectedEvidence": [
            "pinned wheel hashes and actual download bytes",
            "environment creation and installed footprint",
            "four synthetic input and output hashes",
            "per-image timing and process CPU time",
            "peak working set",
            "RGBA dimensions and alpha-channel validation",
            "mask overlap, false foreground, false background, and edge error",
            "source preservation",
            "bounded network and workspace activity",
            "complete cleanup",
        ],
        "functionalTest": True,
    }


def _windows_directory() -> Path:
    if os.name != "nt":
        raise InspectionError("inspection_runtime_incompatible", "The approved functional adapter is Windows-only")
    import ctypes

    buffer = ctypes.create_unicode_buffer(32768)
    length = ctypes.windll.kernel32.GetWindowsDirectoryW(buffer, len(buffer))
    if not length:
        raise InspectionError("inspection_runtime_incompatible", "Windows directory could not be resolved without environment access")
    return Path(buffer.value).resolve()


def _child_environment(workspace: Path, venv_python: Path) -> dict[str, str]:
    windows = _windows_directory()
    return {
        "SYSTEMROOT": str(windows),
        "WINDIR": str(windows),
        "COMSPEC": str(windows / "System32" / "cmd.exe"),
        "PATH": os.pathsep.join((str(venv_python.parent), str(windows / "System32"), str(windows))),
        "TEMP": str(workspace / "temp"),
        "TMP": str(workspace / "temp"),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_CACHE_DIR": "1",
        "PIP_NO_INPUT": "1",
    }


def _run(args: list[str], *, cwd: Path, environment: dict[str, str], timeout: int) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        args,
        cwd=str(cwd),
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        shell=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if completed.returncode:
        tail = (completed.stderr or completed.stdout)[-1500:]
        raise InspectionError("inspection_command_failed", f"Fixed background-removal inspection command failed: {tail}")
    return completed


def _png_rgba_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise InspectionError("inspection_output_invalid", "Functional output is not a valid PNG")
    width, height, bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
    if bit_depth != 8 or color_type != 6:
        raise InspectionError("inspection_output_invalid", "Functional output must be 8-bit RGBA PNG")
    return width, height


SYNTHETIC_SCRIPT = r'''from __future__ import annotations

import ctypes
import hashlib
import json
import math
import os
import time
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "inputs"
OUTPUTS = ROOT / "outputs"
INPUTS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def peak_working_set() -> int | None:
    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    ok = ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
    return int(counters.PeakWorkingSetSize) if ok else None


def make_cases() -> list[tuple[str, np.ndarray, np.ndarray]]:
    size = 256
    yy, xx = np.mgrid[:size, :size]
    cases = []

    image = np.full((size, size, 3), (230, 235, 240), np.uint8)
    truth = (((xx - 128) / 55) ** 2 + ((yy - 128) / 82) ** 2 <= 1).astype(np.uint8)
    image[truth == 1] = (28, 70, 190)
    cases.append(("A_high_contrast", image, truth))

    image = np.full((size, size, 3), (225, 205, 170), np.uint8)
    truth = np.zeros((size, size), np.uint8)
    points = np.array([[128, 38], [151, 91], [213, 99], [165, 139], [181, 204], [128, 166], [75, 204], [91, 139], [43, 99], [105, 91]], np.int32)
    cv2.fillPoly(truth, [points], 1)
    image[truth == 1] = (40, 145, 62)
    cases.append(("B_irregular_edge", image, truth))

    image = np.full((size, size, 3), (215, 228, 238), np.uint8)
    truth = np.zeros((size, size), np.uint8)
    points = []
    for index in range(96):
        angle = index * math.tau / 96
        radius = 78 if index % 2 == 0 else 54
        points.append((int(128 + math.cos(angle) * radius), int(128 + math.sin(angle) * radius)))
    cv2.fillPoly(truth, [np.array(points, np.int32)], 1)
    image[truth == 1] = (75, 45, 160)
    cases.append(("C_fur_like_edge", image, truth))

    image = np.full((size, size, 3), (112, 124, 132), np.int16)
    image += np.clip(((xx + yy) % 13)[:, :, None] - 6, -6, 6)
    image = np.clip(image, 0, 255).astype(np.uint8)
    truth = (((xx - 128) / 62) ** 2 + ((yy - 128) / 76) ** 2 <= 1).astype(np.uint8)
    image[truth == 1] = (92, 112, 126)
    cv2.circle(image, (128, 128), 28, (98, 118, 132), -1)
    cases.append(("D_similar_tones", image, truth))
    return cases


def edge(mask: np.ndarray) -> np.ndarray:
    kernel = np.ones((3, 3), np.uint8)
    return cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_GRADIENT, kernel) > 0


started = time.perf_counter()
cpu_started = time.process_time()
results = []
for name, image, truth in make_cases():
    input_path = INPUTS / f"{name}.png"
    truth_path = INPUTS / f"{name}.truth.png"
    cv2.imwrite(str(input_path), image)
    cv2.imwrite(str(truth_path), truth * 255)
    before = sha256(input_path)
    mask = np.zeros(image.shape[:2], np.uint8)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    case_started = time.perf_counter()
    cv2.grabCut(image, mask, (12, 12, 232, 232), bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
    elapsed = time.perf_counter() - case_started
    predicted = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)
    rgba = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    rgba[:, :, 3] = predicted * 255
    output_path = OUTPUTS / f"{name}.rgba.png"
    cv2.imwrite(str(output_path), rgba)
    intersection = int(np.logical_and(predicted, truth).sum())
    union = int(np.logical_or(predicted, truth).sum())
    false_foreground = int(np.logical_and(predicted == 1, truth == 0).sum())
    false_background = int(np.logical_and(predicted == 0, truth == 1).sum())
    background_pixels = max(1, int((truth == 0).sum()))
    foreground_pixels = max(1, int((truth == 1).sum()))
    edge_error = int(np.logical_xor(edge(predicted), edge(truth)).sum()) / float(predicted.size)
    results.append({
        "case": name, "seconds": round(elapsed, 6), "width": int(image.shape[1]), "height": int(image.shape[0]),
        "inputSha256": before, "inputPreserved": before == sha256(input_path), "truthSha256": sha256(truth_path),
        "outputSha256": sha256(output_path), "alphaValues": sorted(int(value) for value in np.unique(rgba[:, :, 3])),
        "iou": round(intersection / max(1, union), 6),
        "falseForegroundRate": round(false_foreground / background_pixels, 6),
        "falseBackgroundRate": round(false_background / foreground_pixels, 6),
        "edgeErrorRate": round(edge_error, 6),
    })

payload = {
    "schemaVersion": "twis-synthetic-background-removal-result-v1",
    "engine": f"OpenCV {cv2.__version__} GrabCut", "python": os.sys.version.split()[0],
    "wallSeconds": round(time.perf_counter() - started, 6), "cpuSeconds": round(time.process_time() - cpu_started, 6),
    "peakWorkingSetBytes": peak_working_set(), "cases": results,
    "aggregate": {
        "meanIou": round(sum(item["iou"] for item in results) / len(results), 6),
        "meanFalseForegroundRate": round(sum(item["falseForegroundRate"] for item in results) / len(results), 6),
        "meanFalseBackgroundRate": round(sum(item["falseBackgroundRate"] for item in results) / len(results), 6),
        "meanEdgeErrorRate": round(sum(item["edgeErrorRate"] for item in results) / len(results), 6),
    },
}
(ROOT / "metrics.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
'''


def inspect_opencv_grabcut(context: dict[str, Any]) -> dict[str, Any]:
    workspace = Path(context["workspace"]).resolve()
    authority = context["authority"]
    record = context["record"]
    guard: InspectionGuard = context["guard"]
    if record.get("capabilityId") != CAPABILITY_ID or record.get("version") != CAPABILITY_VERSION:
        raise InspectionError("inspection_source_stale", "The fixed adapter only accepts the exact registered OpenCV GrabCut candidate")
    if platform.python_version_tuple()[:2] != ("3", "12") or platform.machine().upper() not in {"AMD64", "X86_64"}:
        raise InspectionError("inspection_runtime_incompatible", "The pinned wheels require CPython 3.12 on Windows x86-64")
    if authority != authority_template(Path(authority["temporaryWorkspace"])):
        raise InspectionError("inspection_authority_invalid", "Functional adapter authority differs from the fixed approved template")

    if not workspace.is_dir() or workspace.parent != Path(authority["temporaryWorkspace"]).resolve():
        raise InspectionError("inspection_path_denied", "Service did not create the exact approved inspection workspace")
    (workspace / "temp").mkdir()
    wheels_dir = workspace / "wheels"
    wheels_dir.mkdir()
    venv_dir = workspace / "venv"
    venv_python = venv_dir / "Scripts" / "python.exe"
    environment = _child_environment(workspace, venv_python)
    guard.write_bytes("synthetic_grabcut_test.py", SYNTHETIC_SCRIPT.encode("utf-8"))

    setup_started = time.perf_counter()
    _run([sys.executable, "-I", "-m", "venv", str(venv_dir)], cwd=workspace, environment=_child_environment(workspace, Path(sys.executable)), timeout=180)
    environment = _child_environment(workspace, venv_python)
    _run(
        [str(venv_python), "-I", "-m", "pip", "download", "--disable-pip-version-check", "--no-deps", "--only-binary=:all:", "--dest", str(wheels_dir), *(str(wheel["url"]) for wheel in WHEELS)],
        cwd=workspace, environment=environment, timeout=authority["timeoutSeconds"],
    )
    actual_download_bytes = 0
    for wheel in WHEELS:
        path = wheels_dir / str(wheel["filename"])
        if not path.is_file() or sha256_file(path).lower() != str(wheel["sha256"]).lower():
            raise InspectionError("inspection_download_hash_mismatch", f"Pinned wheel hash failed for {wheel['filename']}")
        actual_download_bytes += path.stat().st_size
    if actual_download_bytes > authority["maxDownloadBytes"]:
        raise InspectionError("inspection_download_denied", "Pinned wheel bytes exceed the approved allowance")
    guard.record_network("files.pythonhosted.org", actual_download_bytes)
    _run(
        [str(venv_python), "-I", "-m", "pip", "install", "--disable-pip-version-check", "--no-index", "--no-deps", *(str(wheels_dir / str(wheel["filename"])) for wheel in WHEELS)],
        cwd=workspace, environment=environment, timeout=300,
    )
    environment_seconds = round(time.perf_counter() - setup_started, 6)
    run_started = time.perf_counter()
    _run([str(venv_python), "-I", str(workspace / "synthetic_grabcut_test.py")], cwd=workspace, environment=environment, timeout=240)
    execution_seconds = round(time.perf_counter() - run_started, 6)
    metrics_path = workspace / "metrics.json"
    if not metrics_path.is_file():
        raise InspectionError("inspection_output_invalid", "Synthetic inspection did not produce metrics")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    if metrics.get("schemaVersion") != "twis-synthetic-background-removal-result-v1" or len(metrics.get("cases") or []) != 4:
        raise InspectionError("inspection_output_invalid", "Synthetic inspection metrics are malformed")
    input_hashes: list[dict[str, Any]] = []
    output_hashes: list[dict[str, Any]] = []
    for item in metrics["cases"]:
        if not item.get("inputPreserved"):
            raise InspectionError("inspection_source_changed", f"Synthetic source changed for {item.get('case')}")
        output = workspace / "outputs" / f"{item['case']}.rgba.png"
        dimensions = _png_rgba_dimensions(output)
        if dimensions != (256, 256) or sha256_file(output) != item["outputSha256"]:
            raise InspectionError("inspection_output_invalid", f"Output validation failed for {item['case']}")
        input_hashes.extend((
            {"case": item["case"], "kind": "synthetic-input", "sha256": item["inputSha256"]},
            {"case": item["case"], "kind": "ground-truth-mask", "sha256": item["truthSha256"]},
        ))
        output_hashes.append({"case": item["case"], "kind": "rgba-output", "sha256": item["outputSha256"], "width": 256, "height": 256})

    files = [path for path in workspace.rglob("*") if path.is_file()]
    footprint = sum(path.stat().st_size for path in files)
    guard.record_workspace_summary(file_count=len(files), total_bytes=footprint)
    return {
        "functionalEvidence": {
            "state": "COMPLETED",
            "engine": metrics["engine"], "caseCount": 4, "outputsValidated": 4,
            "alphaChannel": "8-bit RGBA validated", "sourcePreserved": True,
            "syntheticSanity": metrics["aggregate"], "cases": metrics["cases"],
        },
        "performanceEvidence": {
            "state": "MEASURED", "elapsedSeconds": execution_seconds,
            "environmentCreationSeconds": environment_seconds,
            "engineWallSeconds": metrics["wallSeconds"], "cpuSeconds": metrics["cpuSeconds"],
            "peakRamBytes": metrics["peakWorkingSetBytes"], "cpuObservation": "Single fixed child process; OpenCV GrabCut at 256x256",
            "downloadedBytes": actual_download_bytes, "disposableFootprintBytes": footprint,
        },
        "networkActivity": guard.network_activity,
        "filesystemActivity": guard.filesystem_activity,
        "inputHashes": input_hashes,
        "outputHashes": output_hashes,
    }

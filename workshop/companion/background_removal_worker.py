from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


MAX_REQUEST_BYTES = 1024 * 1024
MAX_PIXELS = 8_388_608
MAX_STROKES = 2048


class WorkerError(ValueError):
    pass


def _load_runtime(site_packages: Path):
    if not site_packages.is_dir():
        raise WorkerError("The registered OpenCV runtime is missing")
    sys.path.insert(0, str(site_packages))
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except Exception as exc:  # pragma: no cover - converted to bounded process error
        raise WorkerError(f"The registered OpenCV runtime could not load: {type(exc).__name__}") from exc
    cv2.setNumThreads(1)
    return cv2, np


def _read_request(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size < 2 or path.stat().st_size > MAX_REQUEST_BYTES:
        raise WorkerError("The fixed background-removal request is missing or too large")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schemaVersion") != "twis-background-removal-request-v1":
        raise WorkerError("The fixed background-removal request is invalid")
    return value


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WorkerError(f"{name} must be numeric")
    return int(round(value))


def execute(site_packages: Path, request_path: Path, result_path: Path) -> dict[str, Any]:
    cv2, np = _load_runtime(site_packages)
    request = _read_request(request_path)
    source = Path(str(request.get("sourcePath") or ""))
    output = Path(str(request.get("outputPath") or ""))
    if not source.is_file() or output.suffix.lower() != ".png" or output.parent != request_path.parent:
        raise WorkerError("The fixed request paths are invalid")
    image = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if image is None or len(image.shape) != 3 or image.shape[2] != 3:
        raise WorkerError("OpenCV could not decode the registered image")
    height, width = int(image.shape[0]), int(image.shape[1])
    if width < 2 or height < 2 or width * height > MAX_PIXELS:
        raise WorkerError("The image dimensions exceed the bounded GrabCut runtime")

    raw_rectangle = request.get("rectangle")
    if not isinstance(raw_rectangle, dict):
        raise WorkerError("An owner-selected foreground rectangle is required")
    x = max(0, min(width - 2, _integer(raw_rectangle.get("x"), "rectangle.x")))
    y = max(0, min(height - 2, _integer(raw_rectangle.get("y"), "rectangle.y")))
    rect_width = max(2, min(width - x, _integer(raw_rectangle.get("width"), "rectangle.width")))
    rect_height = max(2, min(height - y, _integer(raw_rectangle.get("height"), "rectangle.height")))
    if rect_width < 2 or rect_height < 2:
        raise WorkerError("The foreground rectangle is too small")

    started = time.perf_counter()
    mask = np.zeros((height, width), np.uint8)
    background_model = np.zeros((1, 65), np.float64)
    foreground_model = np.zeros((1, 65), np.float64)
    cv2.grabCut(image, mask, (x, y, rect_width, rect_height), background_model, foreground_model, 3, cv2.GC_INIT_WITH_RECT)

    strokes = request.get("strokes") or []
    if not isinstance(strokes, list) or len(strokes) > MAX_STROKES:
        raise WorkerError("The correction-stroke set is invalid or too large")
    for stroke in strokes:
        if not isinstance(stroke, dict) or stroke.get("mode") not in {"keep", "remove"}:
            raise WorkerError("A correction stroke is invalid")
        sx = max(0, min(width - 1, _integer(stroke.get("x"), "stroke.x")))
        sy = max(0, min(height - 1, _integer(stroke.get("y"), "stroke.y")))
        radius = max(1, min(160, _integer(stroke.get("radius"), "stroke.radius")))
        label = cv2.GC_FGD if stroke["mode"] == "keep" else cv2.GC_BGD
        cv2.circle(mask, (sx, sy), radius, int(label), -1)
    if strokes:
        cv2.grabCut(image, mask, None, background_model, foreground_model, 2, cv2.GC_INIT_WITH_MASK)

    alpha = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype("uint8")
    foreground_pixels = int(np.count_nonzero(alpha))
    if foreground_pixels == 0:
        raise WorkerError("GrabCut found no foreground. Reset and choose a tighter foreground rectangle")
    rgba = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    rgba[:, :, 3] = alpha
    ok, encoded = cv2.imencode(".png", rgba, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    if not ok:
        raise WorkerError("OpenCV could not encode the transparent PNG proposal")
    output.write_bytes(encoded.tobytes())
    result = {
        "schemaVersion": "twis-background-removal-result-v1",
        "engine": "OpenCV GrabCut",
        "opencvVersion": str(cv2.__version__),
        "numpyVersion": str(np.__version__),
        "width": width,
        "height": height,
        "foregroundPixels": foreground_pixels,
        "backgroundPixels": int(width * height - foreground_pixels),
        "foregroundRatio": round(foreground_pixels / (width * height), 6),
        "strokeCount": len(strokes),
        "elapsedSeconds": round(time.perf_counter() - started, 6),
        "outputBytes": output.stat().st_size,
    }
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--site-packages", required=True)
    parser.add_argument("--request")
    parser.add_argument("--result")
    parser.add_argument("--health", action="store_true")
    arguments = parser.parse_args()
    try:
        cv2, np = _load_runtime(Path(arguments.site_packages).resolve())
        if arguments.health:
            print(json.dumps({"ok": True, "opencvVersion": str(cv2.__version__), "numpyVersion": str(np.__version__)}))
            return 0
        if not arguments.request or not arguments.result:
            raise WorkerError("The fixed worker requires request and result paths")
        execute(Path(arguments.site_packages).resolve(), Path(arguments.request).resolve(), Path(arguments.result).resolve())
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc), "errorType": type(exc).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

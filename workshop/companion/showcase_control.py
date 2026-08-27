from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from companion.showcase_server import DEFAULT_PORT, build_server

LOCAL_APP_DATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
STATE_DIR = LOCAL_APP_DATA / "TWIS Holo Workshop" / "showcase"
STATE_FILE = STATE_DIR / "state.json"
URL_FILE = STATE_DIR / "public-url.txt"
STOP_FILE = STATE_DIR / "stop.request"
LOCK_FILE = STATE_DIR / "controller.lock"
LOG_FILE = STATE_DIR / "cloudflared.log"
ERROR_FILE = STATE_DIR / "last-error.txt"
URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def cloudflared_path() -> Path:
    configured = os.environ.get("TWIS_CLOUDFLARED", "").strip()
    candidates = [
        Path(configured) if configured else None,
        LOCAL_APP_DATA / "Programs" / "Cloudflare" / "cloudflared" / "cloudflared.exe",
        Path(shutil.which("cloudflared") or "") if shutil.which("cloudflared") else None,
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate.resolve()
    raise RuntimeError("Official cloudflared executable was not found")


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        process_query_limited_information = 0x1000
        still_active = 259
        handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if not ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == still_active
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_state() -> dict:
    try:
        value = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(value: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, STATE_FILE)


def clear_runtime_files() -> None:
    for path in (STATE_FILE, URL_FILE, STOP_FILE, LOCK_FILE):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def copy_url(url: str) -> None:
    try:
        subprocess.run(["clip.exe"], input=url, text=True, check=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        pass


def wait_for_local(port: int, timeout: float = 10) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/showcase", timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.15)
    raise RuntimeError("Restricted showcase server did not become healthy")


def run_controller(port: int) -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        lock_fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return 2
    os.close(lock_fd)
    server = None
    tunnel = None
    try:
        for path in (STOP_FILE, URL_FILE, ERROR_FILE):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        server = build_server(port)
        server_thread = threading.Thread(target=server.serve_forever, name="twis-showcase-http", daemon=True)
        server_thread.start()
        wait_for_local(port)
        exe = cloudflared_path()
        with LOG_FILE.open("w", encoding="utf-8", errors="replace") as log:
            tunnel = subprocess.Popen(
                [str(exe), "tunnel", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate"],
                cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
            )
        deadline = time.monotonic() + 45
        public_url = ""
        while time.monotonic() < deadline and tunnel.poll() is None and not STOP_FILE.exists():
            try:
                match = URL_PATTERN.search(LOG_FILE.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                match = None
            if match:
                public_url = match.group(0)
                break
            time.sleep(0.2)
        if not public_url:
            raise RuntimeError("Cloudflare Quick Tunnel did not provide a public URL")
        state = {"controllerPid": os.getpid(), "cloudflaredPid": tunnel.pid, "localOrigin": f"http://127.0.0.1:{port}", "publicUrl": public_url, "startedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        write_state(state)
        URL_FILE.write_text(public_url, encoding="utf-8")
        while not STOP_FILE.exists() and tunnel.poll() is None:
            time.sleep(0.4)
        return 0
    except Exception as error:
        ERROR_FILE.write_text(str(error), encoding="utf-8")
        return 1
    finally:
        if tunnel is not None and tunnel.poll() is None:
            tunnel.terminate()
            try:
                tunnel.wait(timeout=8)
            except subprocess.TimeoutExpired:
                tunnel.kill()
                tunnel.wait(timeout=5)
        if server is not None:
            server.shutdown()
            server.server_close()
        clear_runtime_files()


def start_showcase(port: int) -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = read_state()
    if state and process_alive(int(state.get("controllerPid") or 0)) and URL_PATTERN.fullmatch(str(state.get("publicUrl") or "")):
        url = str(state["publicUrl"])
        copy_url(url)
        print(f"TWIS Showcase is already running:\n{url}\n\nThe URL has been copied to the clipboard.")
        return 0
    if LOCK_FILE.exists() and not state:
        try:
            LOCK_FILE.unlink()
        except OSError:
            pass
    for path in (STOP_FILE, URL_FILE, ERROR_FILE):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    creation = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "run", "--port", str(port)], cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True, creationflags=creation)
    deadline = time.monotonic() + 50
    while time.monotonic() < deadline:
        if URL_FILE.is_file():
            url = URL_FILE.read_text(encoding="utf-8").strip()
            if URL_PATTERN.fullmatch(url):
                copy_url(url)
                print(f"TWIS Showcase is running:\n{url}\n\nThe URL has been copied to the clipboard.")
                return 0
        if ERROR_FILE.is_file():
            print(f"TWIS Showcase could not start: {ERROR_FILE.read_text(encoding='utf-8', errors='replace')}", file=sys.stderr)
            return 1
        time.sleep(0.25)
    print("TWIS Showcase startup timed out", file=sys.stderr)
    return 1


def stop_showcase() -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = read_state()
    if not state and not LOCK_FILE.exists():
        print("TWIS Showcase is not running.")
        return 0
    STOP_FILE.write_text("stop", encoding="ascii")
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        state = read_state()
        if not state and not LOCK_FILE.exists():
            print("TWIS Showcase stopped. Public reachability has been removed.")
            return 0
        time.sleep(0.25)
    print("TWIS Showcase stop timed out; check status before assuming it is offline.", file=sys.stderr)
    return 1


def status_showcase() -> int:
    state = read_state()
    alive = bool(state and process_alive(int(state.get("controllerPid") or 0)))
    print(json.dumps({"running": alive, "publicUrl": state.get("publicUrl") if alive else None, "localOrigin": state.get("localOrigin") if alive else None}, indent=2))
    return 0 if alive else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Start or stop the TWIS view-only showcase")
    parser.add_argument("action", choices=("start", "stop", "status", "run"))
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    if args.action == "start":
        return start_showcase(args.port)
    if args.action == "stop":
        return stop_showcase()
    if args.action == "status":
        return status_showcase()
    return run_controller(args.port)


if __name__ == "__main__":
    raise SystemExit(main())

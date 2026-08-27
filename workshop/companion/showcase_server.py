from __future__ import annotations

import argparse
import mimetypes
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOWCASE = ROOT / "showcase"
HOST = "127.0.0.1"
DEFAULT_PORT = 8790

ROUTES = {
    "/showcase": (SHOWCASE / "index.html", "text/html; charset=utf-8"),
    "/showcase/": (SHOWCASE / "index.html", "text/html; charset=utf-8"),
    "/showcase/showcase.css": (SHOWCASE / "showcase.css", "text/css; charset=utf-8"),
    "/showcase/showcase.js": (SHOWCASE / "showcase.js", "text/javascript; charset=utf-8"),
    "/showcase/showcase-icon.svg": (SHOWCASE / "showcase-icon.svg", "image/svg+xml"),
}


class ShowcaseHandler(BaseHTTPRequestHandler):
    server_version = "TwisShowcase/1.0"

    def _headers(self, status: int, content_type: str, length: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'; font-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.end_headers()

    def _deny(self) -> None:
        body = b'{"ok":false,"code":"showcase_view_only","error":"Forbidden"}'
        self._headers(403, "application/json; charset=utf-8", len(body))
        if self.command != "HEAD":
            self.wfile.write(body)

    def _serve(self, head_only: bool = False) -> None:
        raw_path = urllib.parse.urlsplit(self.path).path
        try:
            path = urllib.parse.unquote(raw_path, errors="strict")
        except (UnicodeDecodeError, ValueError):
            self._deny()
            return
        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/showcase")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        item = ROUTES.get(path)
        if item is None:
            self._deny()
            return
        file_path, content_type = item
        try:
            body = file_path.read_bytes()
        except OSError:
            self._deny()
            return
        self._headers(200, content_type or mimetypes.guess_type(file_path.name)[0] or "application/octet-stream", len(body))
        if not head_only:
            self.wfile.write(body)

    def do_GET(self) -> None:
        self._serve()

    def do_HEAD(self) -> None:
        self._serve(head_only=True)

    def do_POST(self) -> None:
        self._deny()

    def do_PUT(self) -> None:
        self._deny()

    def do_PATCH(self) -> None:
        self._deny()

    def do_DELETE(self) -> None:
        self._deny()

    def do_OPTIONS(self) -> None:
        self._deny()

    def log_message(self, _format: str, *_args: object) -> None:
        return


def build_server(port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((HOST, port), ShowcaseHandler)


def main() -> int:
    parser = argparse.ArgumentParser(description="TWIS view-only showcase server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    server = build_server(args.port)
    print(f"TWIS showcase listening on http://{HOST}:{args.port}/showcase", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import urllib.request
from dataclasses import dataclass
from threading import RLock
from typing import Any, Mapping


OWNER = "OWNER"
GUEST_CREATOR = "GUEST_CREATOR"
VISITOR = "VISITOR"
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "[::1]"}
_JWKS_LOCK = RLock()
_JWKS_CACHE: tuple[float, dict[str, Any]] | None = None


class AccessDenied(Exception):
    def __init__(self, code: str, message: str, status: int = 403):
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class Principal:
    role: str
    identity: str
    remote: bool
    auth_type: str


def _csv(name: str) -> set[str]:
    return {item.strip().lower() for item in os.environ.get(name, "").split(",") if item.strip()}


def _host(headers: Mapping[str, str]) -> str:
    return headers.get("Host", "").split(":", 1)[0].strip().lower()


def _b64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _team_origin() -> str:
    configured = os.environ.get("TWIS_CF_ACCESS_TEAM_DOMAIN", "").strip().lower()
    if not configured:
        raise AccessDenied("access_not_configured", "Remote Access identity validation is not configured", 503)
    configured = configured.removeprefix("https://").removeprefix("http://").rstrip("/")
    if not configured.endswith(".cloudflareaccess.com"):
        raise AccessDenied("access_team_invalid", "Remote Access team domain is invalid", 503)
    return f"https://{configured}"


def _load_jwks() -> dict[str, Any]:
    global _JWKS_CACHE
    now = time.time()
    with _JWKS_LOCK:
        if _JWKS_CACHE and now - _JWKS_CACHE[0] < 3600:
            return _JWKS_CACHE[1]
        url = f"{_team_origin()}/cdn-cgi/access/certs"
        request = urllib.request.Request(url, headers={"User-Agent": "TWIS-Access-Verifier/1"})
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                data = json.loads(response.read(256 * 1024).decode("utf-8"))
        except Exception as exc:
            raise AccessDenied("access_keys_unavailable", "Remote Access signing keys are unavailable", 503) from exc
        if not isinstance(data, dict) or not isinstance(data.get("keys"), list):
            raise AccessDenied("access_keys_invalid", "Remote Access signing keys are malformed", 503)
        _JWKS_CACHE = (now, data)
        return data


def _verify_rs256(signing_input: bytes, signature: bytes, key: Mapping[str, Any]) -> bool:
    try:
        modulus = int.from_bytes(_b64url(str(key["n"])), "big")
        exponent = int.from_bytes(_b64url(str(key["e"])), "big")
        encoded = pow(int.from_bytes(signature, "big"), exponent, modulus).to_bytes((modulus.bit_length() + 7) // 8, "big")
    except (KeyError, TypeError, ValueError):
        return False
    digest_info = bytes.fromhex("3031300d060960864801650304020105000420") + hashlib.sha256(signing_input).digest()
    padding_length = len(encoded) - len(digest_info) - 3
    return padding_length >= 8 and encoded == b"\x00\x01" + (b"\xff" * padding_length) + b"\x00" + digest_info


def _role_for(payload: Mapping[str, Any]) -> str:
    audience = payload.get("aud", [])
    audiences = {str(audience)} if isinstance(audience, str) else {str(item) for item in audience}
    email = str(payload.get("email", "")).strip().lower()
    if not email:
        raise AccessDenied("access_identity_missing", "Remote Access identity is missing")
    owner_aud = os.environ.get("TWIS_CF_ACCESS_OWNER_AUD", "").strip()
    bench_aud = os.environ.get("TWIS_CF_ACCESS_BENCH_AUD", "").strip()
    preview_aud = os.environ.get("TWIS_CF_ACCESS_PREVIEW_AUD", "").strip()
    if owner_aud and owner_aud in audiences and email in _csv("TWIS_CF_ACCESS_OWNER_EMAILS"):
        return OWNER
    guest_emails = _csv("TWIS_CF_ACCESS_GUEST_EMAILS")
    guest_domains = _csv("TWIS_CF_ACCESS_GUEST_DOMAINS")
    email_domain = email.rsplit("@", 1)[-1] if "@" in email else ""
    if bench_aud and bench_aud in audiences and (email in guest_emails or email_domain in guest_domains):
        return GUEST_CREATOR
    if preview_aud and preview_aud in audiences:
        return VISITOR
    raise AccessDenied("access_role_denied", "This authenticated identity has no TWIS role")


def _validate_token(token: str) -> Principal:
    parts = token.split(".")
    if len(parts) != 3:
        raise AccessDenied("access_token_malformed", "Remote Access token is malformed", 401)
    try:
        header = json.loads(_b64url(parts[0]))
        payload = json.loads(_b64url(parts[1]))
        signature = _b64url(parts[2])
    except Exception as exc:
        raise AccessDenied("access_token_malformed", "Remote Access token is malformed", 401) from exc
    if not isinstance(header, dict) or not isinstance(payload, dict) or header.get("alg") != "RS256":
        raise AccessDenied("access_token_algorithm", "Remote Access token algorithm is not allowed", 401)
    key = next((item for item in _load_jwks().get("keys", []) if item.get("kid") == header.get("kid")), None)
    if not key or not _verify_rs256(f"{parts[0]}.{parts[1]}".encode("ascii"), signature, key):
        raise AccessDenied("access_token_signature", "Remote Access token signature is invalid", 401)
    now = int(time.time())
    try:
        expires = int(payload.get("exp", 0))
        not_before = int(payload.get("nbf", 0))
    except (TypeError, ValueError) as exc:
        raise AccessDenied("access_token_time", "Remote Access token time claims are invalid", 401) from exc
    if expires <= now or not_before > now + 30:
        raise AccessDenied("access_token_expired", "Remote Access token is expired or not yet valid", 401)
    if str(payload.get("iss", "")).rstrip("/") != _team_origin():
        raise AccessDenied("access_token_issuer", "Remote Access token issuer is invalid", 401)
    identity = str(payload.get("email", "")).strip().lower()
    return Principal(_role_for(payload), identity, True, "cloudflare-access-jwt")


def authenticate(headers: Mapping[str, str], client_ip: str) -> Principal:
    host = _host(headers)
    has_cloudflare_headers = any(str(name).lower().startswith("cf-") for name in headers.keys())
    if client_ip in {"127.0.0.1", "::1"} and host in _LOOPBACK_HOSTS and not has_cloudflare_headers:
        return Principal(OWNER, "local-owner", False, "loopback-local-owner")
    token = headers.get("Cf-Access-Jwt-Assertion", "").strip()
    if not token:
        raise AccessDenied("access_token_missing", "A valid Cloudflare Access identity is required", 401)
    return _validate_token(token)


def authorize_path(principal: Principal, method: str, path: str) -> None:
    if principal.role == OWNER:
        return
    if path == "/api/session":
        return
    if path.startswith("/api/visitor-bench"):
        if principal.role == VISITOR and method.upper() != "GET":
            raise AccessDenied("visitor_read_only", "Visitor access is read-only")
        return
    if path.startswith("/api/"):
        raise AccessDenied("owner_api_required", "This Workshop operation requires OWNER authority")


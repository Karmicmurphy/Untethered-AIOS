from __future__ import annotations

import base64
import hashlib
import json
import time

import pytest

from companion import remote_access
from companion.remote_access import AccessDenied, GUEST_CREATOR, OWNER, Principal, VISITOR, authenticate, authorize_path


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _prime(start: int) -> int:
    def probable(value: int) -> bool:
        if value % 2 == 0:
            return False
        d, s = value - 1, 0
        while d % 2 == 0:
            d //= 2
            s += 1
        for base in (2, 3, 5, 7, 11, 13, 17, 19, 23):
            x = pow(base, d, value)
            if x in (1, value - 1):
                continue
            for _ in range(s - 1):
                x = pow(x, 2, value)
                if x == value - 1:
                    break
            else:
                return False
        return True
    value = start | 1
    while not probable(value):
        value += 2
    return value


def _signed_token(payload: dict) -> tuple[str, dict]:
    # Deterministic 768-bit test key. This is test material, never a credential.
    p = _prime((1 << 383) + 0x25F)
    q = _prime((1 << 382) + 0x38B)
    n, e = p * q, 65537
    d = pow(e, -1, (p - 1) * (q - 1))
    header = _b64(json.dumps({"alg": "RS256", "kid": "test"}, separators=(",", ":")).encode())
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signing = f"{header}.{body}".encode("ascii")
    digest_info = bytes.fromhex("3031300d060960864801650304020105000420") + hashlib.sha256(signing).digest()
    size = (n.bit_length() + 7) // 8
    encoded = b"\x00\x01" + b"\xff" * (size - len(digest_info) - 3) + b"\x00" + digest_info
    signature = pow(int.from_bytes(encoded, "big"), d, n).to_bytes(size, "big")
    key = {"kid": "test", "kty": "RSA", "n": _b64(n.to_bytes(size, "big")), "e": _b64(e.to_bytes(3, "big"))}
    return f"{header}.{body}.{_b64(signature)}", key


def _environment(monkeypatch):
    monkeypatch.setenv("TWIS_CF_ACCESS_TEAM_DOMAIN", "team.cloudflareaccess.com")
    monkeypatch.setenv("TWIS_CF_ACCESS_OWNER_AUD", "owner-aud")
    monkeypatch.setenv("TWIS_CF_ACCESS_BENCH_AUD", "bench-aud")
    monkeypatch.setenv("TWIS_CF_ACCESS_PREVIEW_AUD", "preview-aud")
    monkeypatch.setenv("TWIS_CF_ACCESS_OWNER_EMAILS", "owner@example.com")
    monkeypatch.setenv("TWIS_CF_ACCESS_GUEST_EMAILS", "guest@example.com")


def test_loopback_is_local_owner_only_without_cloudflare_headers():
    principal = authenticate({"Host": "127.0.0.1:8787"}, "127.0.0.1")
    assert principal == Principal(OWNER, "local-owner", False, "loopback-local-owner")
    with pytest.raises(AccessDenied, match="valid Cloudflare Access"):
        authenticate({"Host": "workshop.example.com"}, "127.0.0.1")
    with pytest.raises(AccessDenied):
        authenticate({"Host": "127.0.0.1:8787", "Cf-Connecting-Ip": "203.0.113.1"}, "127.0.0.1")


def test_valid_signed_owner_and_guest_tokens(monkeypatch):
    _environment(monkeypatch)
    now = int(time.time())
    owner_token, key = _signed_token({"iss":"https://team.cloudflareaccess.com","aud":["owner-aud"],"email":"owner@example.com","nbf":now-2,"exp":now+60})
    monkeypatch.setattr(remote_access, "_load_jwks", lambda: {"keys": [key]})
    owner = authenticate({"Host":"workshop.example.com","Cf-Access-Jwt-Assertion":owner_token}, "127.0.0.1")
    assert owner.role == OWNER
    guest_token, key = _signed_token({"iss":"https://team.cloudflareaccess.com","aud":["bench-aud"],"email":"guest@example.com","nbf":now-2,"exp":now+60})
    monkeypatch.setattr(remote_access, "_load_jwks", lambda: {"keys": [key]})
    assert authenticate({"Host":"bench.example.com","Cf-Access-Jwt-Assertion":guest_token}, "127.0.0.1").role == GUEST_CREATOR


def test_missing_forged_expired_and_wrong_audience_fail_closed(monkeypatch):
    _environment(monkeypatch)
    now = int(time.time())
    with pytest.raises(AccessDenied):
        authenticate({"Host":"bench.example.com","Cf-Access-Authenticated-User-Email":"guest@example.com"}, "127.0.0.1")
    expired, key = _signed_token({"iss":"https://team.cloudflareaccess.com","aud":["bench-aud"],"email":"guest@example.com","exp":now-1})
    monkeypatch.setattr(remote_access, "_load_jwks", lambda: {"keys": [key]})
    with pytest.raises(AccessDenied, match="expired"):
        authenticate({"Host":"bench.example.com","Cf-Access-Jwt-Assertion":expired}, "127.0.0.1")
    wrong, key = _signed_token({"iss":"https://team.cloudflareaccess.com","aud":["other"],"email":"guest@example.com","exp":now+60})
    monkeypatch.setattr(remote_access, "_load_jwks", lambda: {"keys": [key]})
    with pytest.raises(AccessDenied, match="no TWIS role"):
        authenticate({"Host":"bench.example.com","Cf-Access-Jwt-Assertion":wrong}, "127.0.0.1")


def test_backend_authorization_is_not_ui_dependent():
    guest = Principal(GUEST_CREATOR, "guest@example.com", True, "test")
    visitor = Principal(VISITOR, "visitor@example.com", True, "test")
    authorize_path(guest, "POST", "/api/visitor-bench/submissions")
    authorize_path(visitor, "GET", "/api/visitor-bench/presentation")
    for path in (
        "/api/projects",
        "/api/jobs",
        "/api/local-ai/runtime/start",
        "/api/artifacts/owner-id",
        "/api/write-projects/x/recovery",
        "/api/background-removal/health",
        "/api/background-removal/projects/x/proposals",
    ):
        with pytest.raises(AccessDenied):
            authorize_path(guest, "GET", path)
    with pytest.raises(AccessDenied, match="read-only"):
        authorize_path(visitor, "POST", "/api/visitor-bench/submissions")

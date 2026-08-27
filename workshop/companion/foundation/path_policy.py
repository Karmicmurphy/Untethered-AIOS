from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Iterable, Literal

AccessMode = Literal["read", "write"]


@dataclass(frozen=True)
class PathDecision:
    allowed: bool
    mode: AccessMode
    requested_path: str
    resolved_path: str | None
    matched_root: str | None
    code: str
    reason: str

    def require_allowed(self) -> Path:
        if not self.allowed or self.resolved_path is None:
            raise PermissionError(f"path policy denied {self.mode}: {self.code}: {self.reason}")
        return Path(self.resolved_path)


def _contains_parent_reference(value: str) -> bool:
    return ".." in PureWindowsPath(value).parts


def _looks_unc(value: str) -> bool:
    return value.startswith("\\\\") or value.startswith("//")


def _has_unsafe_component(value: str) -> bool:
    pure = PureWindowsPath(value)
    for component in pure.parts[1:] if pure.anchor else pure.parts:
        if ":" in component or component.endswith((".", " ")) or PureWindowsPath(component).is_reserved():
            return True
    return False


def _canonical(value: str | os.PathLike[str]) -> Path:
    return Path(value).expanduser().resolve(strict=False)


def _is_within(candidate: Path, root: Path) -> bool:
    candidate_text = os.path.normcase(str(candidate))
    root_text = os.path.normcase(str(root))
    try:
        return os.path.commonpath((candidate_text, root_text)) == root_text
    except ValueError:
        return False


class WindowsPathPolicy:
    """Canonical Windows containment checks for cooperating callers.

    This library is an application-level enforcement component. It does not
    sandbox arbitrary processes and does not replace operating-system ACLs.
    """

    def __init__(
        self,
        *,
        read_roots: Iterable[str | os.PathLike[str]],
        write_roots: Iterable[str | os.PathLike[str]],
        blocked_roots: Iterable[str | os.PathLike[str]] = (),
        allow_unc: bool = False,
    ) -> None:
        if os.name != "nt":
            raise OSError("WindowsPathPolicy is only supported on Windows")
        self.allow_unc = allow_unc
        self.read_roots = self._prepare_roots(read_roots, "read")
        self.write_roots = self._prepare_roots(write_roots, "write")
        self.blocked_roots = self._prepare_roots(blocked_roots, "blocked")

    def _prepare_roots(
        self,
        roots: Iterable[str | os.PathLike[str]],
        label: str,
    ) -> tuple[Path, ...]:
        prepared: list[Path] = []
        for root in roots:
            text = os.fspath(root)
            pure = PureWindowsPath(text)
            if not pure.is_absolute() or not pure.anchor:
                raise ValueError(f"{label} root is not an absolute Windows path: {text}")
            if _looks_unc(text) and not self.allow_unc:
                raise ValueError(f"{label} UNC root requires allow_unc=True: {text}")
            prepared.append(_canonical(text))
        return tuple(prepared)

    def decide(
        self,
        requested_path: str | os.PathLike[str],
        *,
        mode: AccessMode,
        base: str | os.PathLike[str] | None = None,
        require_exists: bool | None = None,
    ) -> PathDecision:
        requested = os.fspath(requested_path)
        if mode not in {"read", "write"}:
            raise ValueError(f"unsupported access mode: {mode}")
        if not requested.strip():
            return self._deny(mode, requested, None, "empty_path", "path is empty")
        if _looks_unc(requested) and not self.allow_unc:
            return self._deny(mode, requested, None, "unc_denied", "UNC paths are not enabled")
        if _contains_parent_reference(requested):
            return self._deny(mode, requested, None, "parent_traversal", "parent path components are denied")
        if _has_unsafe_component(requested):
            return self._deny(
                mode,
                requested,
                None,
                "unsafe_windows_component",
                "reserved names, alternate data streams, and trailing dot/space components are denied",
            )

        pure = PureWindowsPath(requested)
        if pure.is_absolute():
            combined = Path(requested)
        elif base is not None:
            base_text = os.fspath(base)
            if _looks_unc(base_text) and not self.allow_unc:
                return self._deny(mode, requested, None, "unc_denied", "UNC base paths are not enabled")
            combined = Path(base_text) / requested
        else:
            return self._deny(mode, requested, None, "relative_without_base", "relative paths require an explicit base")

        try:
            resolved = _canonical(combined)
        except (OSError, RuntimeError, ValueError) as exc:
            return self._deny(mode, requested, None, "canonicalization_failed", str(exc))

        for root in self.blocked_roots:
            if _is_within(resolved, root):
                return self._deny(mode, requested, resolved, "blocked_root", f"path is inside blocked root {root}")

        allowed_roots = self.read_roots if mode == "read" else self.write_roots
        matched = next((root for root in allowed_roots if _is_within(resolved, root)), None)
        if matched is None:
            return self._deny(mode, requested, resolved, "outside_allowed_roots", f"path is outside configured {mode} roots")

        must_exist = mode == "read" if require_exists is None else require_exists
        if must_exist and not resolved.exists():
            return self._deny(mode, requested, resolved, "missing_path", "path does not exist")

        return PathDecision(
            True,
            mode,
            requested,
            str(resolved),
            str(matched),
            "allowed",
            f"canonical path is inside configured {mode} root",
        )

    @staticmethod
    def _deny(
        mode: AccessMode,
        requested: str,
        resolved: Path | None,
        code: str,
        reason: str,
    ) -> PathDecision:
        return PathDecision(False, mode, requested, str(resolved) if resolved else None, None, code, reason)

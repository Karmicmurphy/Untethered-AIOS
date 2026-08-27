from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path, PureWindowsPath
from typing import Any, Callable


class PermissionDenied(RuntimeError):
    def __init__(self, message: str, *, target: str | None = None) -> None:
        super().__init__(message)
        self.target = target


@dataclass(frozen=True)
class CapabilityGrant:
    name: str
    scopes: tuple[str, ...]


@dataclass(frozen=True)
class CapabilityRequest:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class CapabilityOutcome:
    value: Any
    target: str | None
    mutation: bool


@dataclass
class Capability:
    name: str
    handler: Callable[..., Any]
    scope_arg: str | None = None
    mutation: bool = False


def _looks_unc(value: str) -> bool:
    return value.startswith("\\\\") or value.startswith("//")


def _contains_parent_reference(value: str) -> bool:
    if os.name == "nt":
        return ".." in PureWindowsPath(value).parts
    return ".." in Path(value).parts


def _has_unsafe_windows_component(value: str) -> bool:
    if os.name != "nt":
        return False
    pure = PureWindowsPath(value)
    components = pure.parts[1:] if pure.anchor else pure.parts
    return any(
        ":" in component
        or component.endswith((".", " "))
        or PureWindowsPath(component).is_reserved()
        for component in components
    )


def canonical_path(value: str) -> str:
    if not value.strip():
        raise PermissionDenied("path is empty")
    if os.name == "nt" and _looks_unc(value):
        raise PermissionDenied("UNC paths are not enabled", target=value)
    if _contains_parent_reference(value):
        raise PermissionDenied("parent traversal is denied", target=value)
    if _has_unsafe_windows_component(value):
        raise PermissionDenied("unsafe Windows path component", target=value)
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise PermissionDenied("scoped paths must be absolute", target=value)
    try:
        return str(path.resolve(strict=False))
    except (OSError, RuntimeError, ValueError) as exc:
        raise PermissionDenied(f"path canonicalization failed: {exc}", target=value) from exc


def _path_within(candidate: str, scope: str) -> bool:
    if scope == "*":
        return True
    try:
        candidate_path = canonical_path(candidate)
        scope_path = canonical_path(scope)
        candidate_text = os.path.normcase(candidate_path)
        scope_text = os.path.normcase(scope_path)
        return os.path.commonpath((candidate_text, scope_text)) == scope_text
    except (PermissionDenied, ValueError):
        return False


def scope_within(candidate: str, parent: str) -> bool:
    if parent == "*" or candidate == parent:
        return True
    candidate_path = Path(candidate).expanduser()
    parent_path = Path(parent).expanduser()
    if candidate_path.is_absolute() and parent_path.is_absolute():
        return _path_within(candidate, parent)
    return False


def grants_are_subset(
    requested: tuple[CapabilityGrant, ...],
    parent: tuple[CapabilityGrant, ...],
) -> bool:
    for child_grant in requested:
        matching = [grant for grant in parent if grant.name == child_grant.name]
        if not matching:
            return False
        for child_scope in child_grant.scopes:
            if not any(
                scope_within(child_scope, parent_scope)
                for grant in matching
                for parent_scope in grant.scopes
            ):
                return False
    return True


class CapabilityRegistry:
    def __init__(self) -> None:
        self._caps: dict[str, Capability] = {}

    def register(
        self,
        name: str,
        handler: Callable[..., Any],
        scope_arg: str | None = None,
        *,
        mutation: bool = False,
    ) -> None:
        if name in self._caps:
            raise ValueError(f"capability already registered: {name}")
        self._caps[name] = Capability(
            name=name,
            handler=handler,
            scope_arg=scope_arg,
            mutation=mutation,
        )

    def invoke_request(
        self,
        request: CapabilityRequest,
        grants: tuple[CapabilityGrant, ...],
    ) -> CapabilityOutcome:
        cap = self._caps.get(request.name)
        if cap is None:
            raise PermissionDenied(f"unknown capability: {request.name}")

        matching = [grant for grant in grants if grant.name == request.name]
        if not matching:
            raise PermissionDenied(f"capability denied: {request.name}")

        target = None
        if cap.scope_arg is not None:
            if cap.scope_arg not in request.arguments:
                raise PermissionDenied(f"missing scoped argument: {cap.scope_arg}")
            requested_target = str(request.arguments[cap.scope_arg])
            try:
                target = canonical_path(requested_target)
            except PermissionDenied as exc:
                raise PermissionDenied(str(exc), target=requested_target) from exc
            allowed = any(
                _path_within(target, scope)
                for grant in matching
                for scope in grant.scopes
            )
            if not allowed:
                raise PermissionDenied(
                    f"scope denied for {request.name}: {requested_target}",
                    target=target,
                )

        handler_arguments = dict(request.arguments)
        if cap.scope_arg is not None:
            # The authorization decision and the operation must use the same
            # canonical path. Passing the caller's raw spelling after checking
            # a resolved path would weaken the scope boundary.
            handler_arguments[cap.scope_arg] = target

        value = cap.handler(**handler_arguments)
        return CapabilityOutcome(value=value, target=target, mutation=cap.mutation)

    def invoke(
        self,
        name: str,
        kwargs: dict[str, Any],
        grants: tuple[CapabilityGrant, ...],
    ) -> Any:
        return self.invoke_request(CapabilityRequest(name, kwargs), grants).value

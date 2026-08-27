from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

class PermissionDenied(RuntimeError):
    pass

@dataclass(frozen=True)
class CapabilityGrant:
    name: str
    scopes: tuple[str, ...]

@dataclass
class Capability:
    name: str
    handler: Callable[..., Any]
    scope_arg: str | None = None

def _path_within(candidate: str, scope: str) -> bool:
    c = Path(candidate).expanduser().resolve(strict=False)
    s = Path(scope).expanduser().resolve(strict=False)
    try:
        c.relative_to(s)
        return True
    except ValueError:
        return False

class CapabilityRegistry:
    def __init__(self) -> None:
        self._caps: dict[str, Capability] = {}

    def register(self, name: str, handler: Callable[..., Any], scope_arg: str | None = None) -> None:
        if name in self._caps:
            raise ValueError(f"capability already registered: {name}")
        self._caps[name] = Capability(name=name, handler=handler, scope_arg=scope_arg)

    def invoke(
        self,
        name: str,
        kwargs: dict[str, Any],
        grants: tuple[CapabilityGrant, ...],
    ) -> Any:
        cap = self._caps.get(name)
        if cap is None:
            raise PermissionDenied(f"unknown capability: {name}")

        matching = [g for g in grants if g.name == name]
        if not matching:
            raise PermissionDenied(f"capability denied: {name}")

        if cap.scope_arg is not None:
            if cap.scope_arg not in kwargs:
                raise PermissionDenied(f"missing scoped argument: {cap.scope_arg}")
            target = str(kwargs[cap.scope_arg])
            allowed = any(_path_within(target, scope) for g in matching for scope in g.scopes)
            if not allowed:
                raise PermissionDenied(f"scope denied for {name}: {target}")

        return cap.handler(**kwargs)

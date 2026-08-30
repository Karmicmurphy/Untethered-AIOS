from __future__ import annotations
from dataclasses import dataclass
from typing import Any,Callable
@dataclass(frozen=True)
class CellBudget:
    max_steps:int;max_children:int;max_output_bytes:int
    def __post_init__(self)->None:
        if min(self.max_steps,self.max_children,self.max_output_bytes)<0:raise ValueError("cell budgets cannot be negative")
@dataclass(frozen=True)
class CapabilityCellSpec:
    cell_id:str;exact_capabilities:tuple[str,...];expected_inputs:tuple[str,...];expected_outputs:tuple[str,...];budget:CellBudget
@dataclass(frozen=True)
class CellResult:
    outputs:dict[str,Any];steps_used:int;child_count:int
class CapabilityCell:
    """Pure bounded-worker prep contract; no hostile-code isolation claim."""
    def __init__(self,spec:CapabilityCellSpec)->None:self.spec=spec
    def run(self,fn:Callable[[dict[str,Any],Callable[[str],None]],dict[str,Any]],inputs:dict[str,Any],*,granted_capabilities:set[str])->CellResult:
        if set(inputs)!=set(self.spec.expected_inputs):raise ValueError("cell inputs do not match contract")
        if not set(self.spec.exact_capabilities).issubset(granted_capabilities):raise PermissionError("cell capability denied")
        steps=0
        def checkpoint(capability:str)->None:
            nonlocal steps
            if capability not in self.spec.exact_capabilities:raise PermissionError(f"capability not declared by cell: {capability}")
            steps+=1
            if steps>self.spec.budget.max_steps:raise RuntimeError("cell step budget exceeded")
        outputs=fn(dict(inputs),checkpoint)
        if set(outputs)!=set(self.spec.expected_outputs):raise ValueError("cell outputs do not match contract")
        if len(repr(outputs).encode("utf-8"))>self.spec.budget.max_output_bytes:raise RuntimeError("cell output budget exceeded")
        return CellResult(outputs,steps,0)

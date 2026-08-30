from __future__ import annotations
from dataclasses import dataclass,replace
from enum import Enum
from typing import Any
class EvolutionStage(str,Enum):
    WEAKNESS_DETECTED="WEAKNESS_DETECTED";QUERY_PROPOSED="QUERY_PROPOSED";SOURCE_CANDIDATE="SOURCE_CANDIDATE";LEGAL_GATE_PASSED="LEGAL_GATE_PASSED";PROTOTYPE_READY="PROTOTYPE_READY";PROOF_PASSED="PROOF_PASSED";CAPABILITY_REGISTERED="CAPABILITY_REGISTERED";MEASURED="MEASURED";REJECTED="REJECTED"
_ALLOWED={
EvolutionStage.WEAKNESS_DETECTED:{EvolutionStage.QUERY_PROPOSED,EvolutionStage.REJECTED},EvolutionStage.QUERY_PROPOSED:{EvolutionStage.SOURCE_CANDIDATE,EvolutionStage.REJECTED},EvolutionStage.SOURCE_CANDIDATE:{EvolutionStage.LEGAL_GATE_PASSED,EvolutionStage.REJECTED},EvolutionStage.LEGAL_GATE_PASSED:{EvolutionStage.PROTOTYPE_READY,EvolutionStage.REJECTED},EvolutionStage.PROTOTYPE_READY:{EvolutionStage.PROOF_PASSED,EvolutionStage.REJECTED},EvolutionStage.PROOF_PASSED:{EvolutionStage.CAPABILITY_REGISTERED,EvolutionStage.REJECTED},EvolutionStage.CAPABILITY_REGISTERED:{EvolutionStage.MEASURED},EvolutionStage.MEASURED:set(),EvolutionStage.REJECTED:set()}
@dataclass(frozen=True)
class EvolutionRecord:
    evolution_id:str;weakness:str;stage:EvolutionStage;source_ref:str|None=None;license_basis:str|None=None;prototype_ref:str|None=None;proof_ref:str|None=None;capability_id:str|None=None;notes:tuple[str,...]=();authority_expanded:bool=False
class EvolutionLedger:
    """Reversible self-growth state machine; protected authority expansion is denied."""
    def __init__(self)->None:self._records={}
    def start(self,evolution_id:str,weakness:str)->EvolutionRecord:
        if evolution_id in self._records:raise ValueError("evolution_id already exists")
        r=EvolutionRecord(evolution_id,weakness,EvolutionStage.WEAKNESS_DETECTED);self._records[evolution_id]=r;return r
    def advance(self,evolution_id:str,stage:EvolutionStage,**changes:Any)->EvolutionRecord:
        current=self._records[evolution_id]
        if stage not in _ALLOWED[current.stage]:raise RuntimeError(f"invalid evolution transition {current.stage.value} -> {stage.value}")
        if changes.get("authority_expanded"):raise PermissionError("prep evolution cannot expand protected authority")
        updated=replace(current,stage=stage,**changes)
        if stage is EvolutionStage.LEGAL_GATE_PASSED and not(updated.source_ref and updated.license_basis):raise RuntimeError("legal gate requires source_ref and license_basis")
        if stage is EvolutionStage.PROOF_PASSED and not updated.proof_ref:raise RuntimeError("proof stage requires proof_ref")
        if stage is EvolutionStage.CAPABILITY_REGISTERED and not updated.capability_id:raise RuntimeError("registration requires capability_id")
        self._records[evolution_id]=updated;return updated
    def get(self,evolution_id:str)->EvolutionRecord:return self._records[evolution_id]

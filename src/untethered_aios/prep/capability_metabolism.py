from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
class MetabolismState(str,Enum):
    KEEP="KEEP";REFINE="REFINE";MERGE="MERGE";SHRINK="SHRINK";ARCHIVE="ARCHIVE";REBUILD="REBUILD";DISCARD="DISCARD"
@dataclass(frozen=True)
class CapabilityHealth:
    capability_id:str;uses:int;successes:int;failures:int;avg_cpu_ms:float;avg_memory_bytes:int;dependency_count:int;duplicate_coverage:float;replacement_health:float;owner_value:float;days_since_use:int;dependency_health:float=1.0
    def __post_init__(self)->None:
        if not self.capability_id:raise ValueError("capability_id required")
        if min(self.uses,self.successes,self.failures,self.avg_memory_bytes,self.dependency_count,self.days_since_use)<0:raise ValueError("counts cannot be negative")
        if self.successes+self.failures>self.uses:raise ValueError("successes + failures cannot exceed uses")
        for name in("duplicate_coverage","replacement_health","owner_value","dependency_health"):
            if not 0.0<=getattr(self,name)<=1.0:raise ValueError(f"{name} must be between 0 and 1")
    @property
    def success_rate(self)->float:return 1.0 if self.uses==0 else self.successes/self.uses
@dataclass(frozen=True)
class MetabolismRecommendation:
    capability_id:str;state:MetabolismState;reason:str;destructive_action_allowed:bool=False
class MetabolismAdvisor:
    """Advisory-only. It can recommend pruning but never destroys assets."""
    @staticmethod
    def _r(h:CapabilityHealth,s:MetabolismState,reason:str)->MetabolismRecommendation:return MetabolismRecommendation(h.capability_id,s,reason,False)
    def recommend(self,h:CapabilityHealth)->MetabolismRecommendation:
        if h.uses==0 and h.days_since_use>=90:return self._r(h,MetabolismState.ARCHIVE,"never used and stale")
        if h.days_since_use>=180 and h.owner_value<=0.1 and h.replacement_health>=0.9:return self._r(h,MetabolismState.DISCARD,"long-unused, low-value, healthy replacement exists")
        if h.duplicate_coverage>=0.85 and h.replacement_health>=0.8:return self._r(h,MetabolismState.MERGE,"high duplicate coverage with healthy replacement")
        if h.dependency_health<0.4 or h.success_rate<0.6:return self._r(h,MetabolismState.REBUILD,"poor dependency or reliability health")
        if h.dependency_count>=12 and h.owner_value<0.7:return self._r(h,MetabolismState.SHRINK,"dependency burden high for delivered value")
        if h.success_rate<0.9 or h.avg_cpu_ms>500:return self._r(h,MetabolismState.REFINE,"works but reliability or cost can improve")
        return self._r(h,MetabolismState.KEEP,"healthy, useful, and sufficiently efficient")

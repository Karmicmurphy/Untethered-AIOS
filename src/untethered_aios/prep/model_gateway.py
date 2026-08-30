from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
class CognitiveBackend(Protocol):
    backend_id:str
    def infer(self,prompt:str)->str:...
@dataclass(frozen=True)
class BackendInfo:
    backend_id:str;local:bool;paid:bool;requires_network:bool;notes:str=""
@dataclass(frozen=True)
class ModelCall:
    backend_id:str;prompt:str;result:str;call_index:int
class FakeBackend:
    backend_id="fake-deterministic"
    def __init__(self,prefix:str="fake")->None:self.prefix=prefix;self.calls=0
    def infer(self,prompt:str)->str:self.calls+=1;return f"{self.prefix}:{prompt}"
class ModelGateway:
    """Replaceable compute only. Registration conveys no operating authority."""
    def __init__(self)->None:self._backends={};self._history=[]
    def register(self,info:BackendInfo,backend:CognitiveBackend)->None:
        if info.backend_id!=backend.backend_id:raise ValueError("backend metadata ID mismatch")
        if info.backend_id in self._backends:raise ValueError(f"backend already registered: {info.backend_id}")
        self._backends[info.backend_id]=(info,backend)
    def call(self,backend_id:str,prompt:str,*,allow_paid:bool=False,allow_network:bool=False)->str:
        if backend_id not in self._backends:raise KeyError(f"unknown backend: {backend_id}")
        info,backend=self._backends[backend_id]
        if info.paid and not allow_paid:raise PermissionError("paid backend requires explicit allowance")
        if info.requires_network and not allow_network:raise PermissionError("network backend requires explicit allowance")
        result=backend.infer(prompt);self._history.append(ModelCall(backend_id,prompt,result,len(self._history)+1));return result
    def infos(self)->tuple[BackendInfo,...]:return tuple(sorted((x[0] for x in self._backends.values()),key=lambda x:x.backend_id))
    @property
    def call_count(self)->int:return len(self._history)
    @property
    def history(self)->tuple[ModelCall,...]:return tuple(self._history)

from __future__ import annotations
from dataclasses import dataclass
import hashlib,json
from collections import Counter
from typing import Any,Iterable

def stable_hash(value:Any)->str:return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
@dataclass(frozen=True)
class TraceEvent:
    kind:str; action:str; args:dict[str,Any]; protected:bool=False
    @property
    def signature(self)->tuple[str,str]:return(self.kind,self.action)
@dataclass(frozen=True)
class SkillCandidate:
    candidate_id:str; sequence:tuple[tuple[str,str],...]; occurrences:int; stable_arguments:tuple[dict[str,Any],...]; variable_keys:tuple[tuple[str,...],...]; source_trace_count:int; protected_event_seen:bool; status:str="CANDIDATE"
class PatternDetector:
    """Small repeated-trace detector for prep work; no automatic promotion."""
    def __init__(self,*,min_occurrences:int=2,max_pattern_len:int=6)->None:
        if min_occurrences<2 or max_pattern_len<2:raise ValueError("invalid detector bounds")
        self.min_occurrences=min_occurrences;self.max_pattern_len=max_pattern_len
    def detect(self,traces:Iterable[Iterable[TraceEvent]])->SkillCandidate|None:
        trace_list=[tuple(t) for t in traces];counts=Counter();occ={}
        for trace in trace_list:
            sig=[e.signature for e in trace]
            for length in range(2,min(self.max_pattern_len,len(trace))+1):
                for start in range(len(trace)-length+1):
                    key=tuple(sig[start:start+length]);counts[key]+=1;occ.setdefault(key,[]).append(trace[start:start+length])
        eligible=[k for k,c in counts.items() if c>=self.min_occurrences]
        if not eligible:return None
        eligible.sort(key=lambda k:(-len(k),-counts[k],k));sequence=eligible[0];windows=occ[sequence];stable=[];variable=[];protected=False
        for pos in range(len(sequence)):
            events=[w[pos] for w in windows];protected=protected or any(e.protected for e in events);keys=sorted(set().union(*(e.args.keys() for e in events)));s={};v=[]
            for key in keys:
                vals=[e.args.get(key,object()) for e in events];first=vals[0]
                if all(x==first for x in vals[1:]):s[key]=first
                else:v.append(key)
            stable.append(s);variable.append(tuple(v))
        cid=stable_hash({"sequence":sequence,"stable":stable,"variables":variable})[:16]
        return SkillCandidate(f"skill-candidate-{cid}",sequence,counts[sequence],tuple(stable),tuple(variable),len(trace_list),protected)
    def verify(self,candidate:SkillCandidate,traces:Iterable[Iterable[TraceEvent]])->dict[str,Any]:
        detected=self.detect(traces)
        if detected is None:return{"verified":False,"reason":"pattern no longer repeats"}
        if detected.sequence!=candidate.sequence:return{"verified":False,"reason":"dominant repeated sequence changed"}
        if candidate.protected_event_seen or detected.protected_event_seen:return{"verified":False,"reason":"protected events prohibit automatic downshift promotion"}
        return{"verified":True,"reason":"repeated non-protected sequence remains stable","occurrences":detected.occurrences,"candidate_id":candidate.candidate_id}

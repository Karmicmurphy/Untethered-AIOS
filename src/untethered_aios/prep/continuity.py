from __future__ import annotations
from dataclasses import dataclass
import json,sqlite3,time
from pathlib import Path
from typing import Any
@dataclass(frozen=True)
class ContinuityCheckpoint:
    session_id:str;active_project:str|None;thread_summary:str;context_refs:tuple[str,...];owner_context:dict[str,Any];ai_identity:dict[str,Any];interrupted_at_ns:int
    def __post_init__(self)->None:
        if not self.session_id:raise ValueError("session_id required")
        if self.owner_context is self.ai_identity:raise ValueError("owner_context and ai_identity must be distinct objects")
        if self.owner_context==self.ai_identity and self.owner_context:raise ValueError("OWNER CONTEXT must not be serialized as AI IDENTITY")
class ContinuityStore:
    """Resumable conversation/project checkpoint store with identity separation."""
    def __init__(self,path:str|Path=":memory:")->None:
        self.db=sqlite3.connect(str(path));self.db.row_factory=sqlite3.Row;self.db.execute("PRAGMA journal_mode=DELETE")
        self.db.execute("CREATE TABLE IF NOT EXISTS continuity_checkpoints(session_id TEXT PRIMARY KEY,active_project TEXT NULL,thread_summary TEXT NOT NULL,context_refs_json TEXT NOT NULL,owner_context_json TEXT NOT NULL,ai_identity_json TEXT NOT NULL,interrupted_at_ns INTEGER NOT NULL,saved_at_ns INTEGER NOT NULL)");self.db.commit()
    @staticmethod
    def _dump(v:Any)->str:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    def save(self,c:ContinuityCheckpoint)->None:
        self.db.execute("INSERT INTO continuity_checkpoints(session_id,active_project,thread_summary,context_refs_json,owner_context_json,ai_identity_json,interrupted_at_ns,saved_at_ns) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(session_id) DO UPDATE SET active_project=excluded.active_project,thread_summary=excluded.thread_summary,context_refs_json=excluded.context_refs_json,owner_context_json=excluded.owner_context_json,ai_identity_json=excluded.ai_identity_json,interrupted_at_ns=excluded.interrupted_at_ns,saved_at_ns=excluded.saved_at_ns",(c.session_id,c.active_project,c.thread_summary,self._dump(c.context_refs),self._dump(c.owner_context),self._dump(c.ai_identity),c.interrupted_at_ns,time.time_ns()));self.db.commit()
    def resume(self,session_id:str)->ContinuityCheckpoint|None:
        r=self.db.execute("SELECT * FROM continuity_checkpoints WHERE session_id=?",(session_id,)).fetchone()
        if r is None:return None
        return ContinuityCheckpoint(r['session_id'],r['active_project'],r['thread_summary'],tuple(json.loads(r['context_refs_json'])),json.loads(r['owner_context_json']),json.loads(r['ai_identity_json']),r['interrupted_at_ns'])
    def close(self)->None:self.db.close()

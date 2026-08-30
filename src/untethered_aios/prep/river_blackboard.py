from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json, sqlite3, time
from pathlib import Path
from typing import Any

class BlackboardStatus(str,Enum):
    NEED="NEED"; CLAIM="CLAIM"; RESULT="RESULT"; BLOCKED="BLOCKED"; FAILED="FAILED"; PROVEN="PROVEN"; EXPIRED="EXPIRED"

@dataclass(frozen=True)
class BlackboardItem:
    item_id:int; kind:str; status:BlackboardStatus; payload:dict[str,Any]; claimed_by:str|None; result:dict[str,Any]|None; created_ns:int; updated_ns:int; expires_ns:int|None; version:int
@dataclass(frozen=True)
class BlackboardEvent:
    seq:int; item_id:int; event:str; actor:str; detail:dict[str,Any]; created_ns:int

class RiverBlackboard:
    """SQLite shared work state: workers coordinate through state/traces, not conversation."""
    def __init__(self,path:str|Path=":memory:")->None:
        self.db=sqlite3.connect(str(path),isolation_level=None); self.db.row_factory=sqlite3.Row
        self.db.execute("PRAGMA journal_mode=DELETE"); self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS blackboard_items(item_id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,status TEXT NOT NULL,payload_json TEXT NOT NULL,claimed_by TEXT NULL,result_json TEXT NULL,created_ns INTEGER NOT NULL,updated_ns INTEGER NOT NULL,expires_ns INTEGER NULL,version INTEGER NOT NULL DEFAULT 0);
        CREATE INDEX IF NOT EXISTS idx_blackboard_status ON blackboard_items(status,kind,item_id);
        CREATE TABLE IF NOT EXISTS blackboard_events(seq INTEGER PRIMARY KEY AUTOINCREMENT,item_id INTEGER NOT NULL REFERENCES blackboard_items(item_id),event TEXT NOT NULL,actor TEXT NOT NULL,detail_json TEXT NOT NULL,created_ns INTEGER NOT NULL);
        """)
    @staticmethod
    def _dump(v:Any)->str:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    def _event(self,item_id:int,event:str,actor:str,detail:dict[str,Any])->None:self.db.execute("INSERT INTO blackboard_events(item_id,event,actor,detail_json,created_ns) VALUES(?,?,?,?,?)",(item_id,event,actor,self._dump(detail),time.time_ns()))
    def post_need(self,kind:str,payload:dict[str,Any],*,actor:str="system",ttl_ns:int|None=None)->BlackboardItem:
        now=time.time_ns(); exp=now+ttl_ns if ttl_ns is not None else None
        cur=self.db.execute("INSERT INTO blackboard_items(kind,status,payload_json,claimed_by,result_json,created_ns,updated_ns,expires_ns,version) VALUES(?,?,?,?,?,?,?,?,0)",(kind,BlackboardStatus.NEED.value,self._dump(payload),None,None,now,now,exp)); item_id=int(cur.lastrowid); self._event(item_id,"need.posted",actor,{"kind":kind}); return self.get(item_id)
    def claim(self,kind:str,worker_id:str)->BlackboardItem|None:
        self.expire_due(); self.db.execute("BEGIN IMMEDIATE")
        try:
            r=self.db.execute("SELECT item_id,version FROM blackboard_items WHERE kind=? AND status=? ORDER BY item_id LIMIT 1",(kind,BlackboardStatus.NEED.value)).fetchone()
            if r is None:self.db.execute("COMMIT"); return None
            cur=self.db.execute("UPDATE blackboard_items SET status=?,claimed_by=?,updated_ns=?,version=version+1 WHERE item_id=? AND status=? AND version=?",(BlackboardStatus.CLAIM.value,worker_id,time.time_ns(),r['item_id'],BlackboardStatus.NEED.value,r['version']))
            if cur.rowcount!=1:self.db.execute("ROLLBACK"); return None
            self.db.execute("COMMIT")
        except Exception:self.db.execute("ROLLBACK"); raise
        self._event(int(r['item_id']),"work.claimed",worker_id,{"kind":kind}); return self.get(int(r['item_id']))
    def _finish(self,item_id:int,worker_id:str,status:BlackboardStatus,result:dict[str,Any],event:str)->BlackboardItem:
        r=self.db.execute("SELECT status,claimed_by,version FROM blackboard_items WHERE item_id=?",(item_id,)).fetchone()
        if r is None:raise KeyError(item_id)
        if r['status']!=BlackboardStatus.CLAIM.value or r['claimed_by']!=worker_id:raise RuntimeError("only current claimant may finish")
        cur=self.db.execute("UPDATE blackboard_items SET status=?,result_json=?,updated_ns=?,version=version+1 WHERE item_id=? AND status=? AND claimed_by=? AND version=?",(status.value,self._dump(result),time.time_ns(),item_id,BlackboardStatus.CLAIM.value,worker_id,r['version']))
        if cur.rowcount!=1:raise RuntimeError("blackboard item changed while completing")
        self._event(item_id,event,worker_id,result); return self.get(item_id)
    def complete(self,item_id:int,worker_id:str,result:dict[str,Any],*,proven:bool=False)->BlackboardItem:return self._finish(item_id,worker_id,BlackboardStatus.PROVEN if proven else BlackboardStatus.RESULT,result,"work.proven" if proven else "work.result")
    def fail(self,item_id:int,worker_id:str,detail:dict[str,Any])->BlackboardItem:return self._finish(item_id,worker_id,BlackboardStatus.FAILED,detail,"work.failed")
    def block(self,item_id:int,worker_id:str,detail:dict[str,Any])->BlackboardItem:return self._finish(item_id,worker_id,BlackboardStatus.BLOCKED,detail,"work.blocked")
    def expire_due(self)->int:
        now=time.time_ns(); rows=self.db.execute("SELECT item_id FROM blackboard_items WHERE expires_ns IS NOT NULL AND expires_ns<=? AND status IN (?,?)",(now,BlackboardStatus.NEED.value,BlackboardStatus.CLAIM.value)).fetchall()
        for r in rows:self.db.execute("UPDATE blackboard_items SET status=?,updated_ns=?,version=version+1 WHERE item_id=?",(BlackboardStatus.EXPIRED.value,now,r['item_id'])); self._event(int(r['item_id']),"work.expired","blackboard",{})
        return len(rows)
    def get(self,item_id:int)->BlackboardItem:
        r=self.db.execute("SELECT * FROM blackboard_items WHERE item_id=?",(item_id,)).fetchone()
        if r is None:raise KeyError(item_id)
        return BlackboardItem(r['item_id'],r['kind'],BlackboardStatus(r['status']),json.loads(r['payload_json']),r['claimed_by'],json.loads(r['result_json']) if r['result_json'] else None,r['created_ns'],r['updated_ns'],r['expires_ns'],r['version'])
    def scan(self,*,status:BlackboardStatus|None=None,kind:str|None=None)->tuple[BlackboardItem,...]:
        where=[];args=[]
        if status is not None:where.append("status=?");args.append(status.value)
        if kind is not None:where.append("kind=?");args.append(kind)
        sql="SELECT item_id FROM blackboard_items"+(" WHERE "+" AND ".join(where) if where else "")+" ORDER BY item_id"
        return tuple(self.get(int(r['item_id'])) for r in self.db.execute(sql,args))
    def events_since(self,seq:int=0)->tuple[BlackboardEvent,...]:
        rows=self.db.execute("SELECT * FROM blackboard_events WHERE seq>? ORDER BY seq",(seq,)).fetchall(); return tuple(BlackboardEvent(r['seq'],r['item_id'],r['event'],r['actor'],json.loads(r['detail_json']),r['created_ns']) for r in rows)
    def close(self)->None:self.db.close()

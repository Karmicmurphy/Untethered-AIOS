from __future__ import annotations

from dataclasses import dataclass
import hashlib, json, math, re, sqlite3, time
from pathlib import Path
from typing import Any, Iterable

_TOKEN = re.compile(r"[A-Za-z0-9_'-]+")

def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _tokens(text: str) -> list[str]:
    return [m.group(0).lower() for m in _TOKEN.finditer(text)]

def _vector(text: str, dimensions: int = 256) -> dict[int, int]:
    vec: dict[int, int] = {}
    for token in _tokens(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        for offset in range(0, 12, 4):
            raw = int.from_bytes(digest[offset:offset+4], "big")
            index = raw % dimensions
            sign = 1 if (digest[12 + (offset // 4)] & 1) == 0 else -1
            vec[index] = vec.get(index, 0) + sign
    return vec

def _cosine(a: dict[int, int], b: dict[int, int]) -> float:
    if not a or not b: return 0.0
    dot = sum(value * b.get(index, 0) for index, value in a.items())
    na = math.sqrt(sum(value * value for value in a.values()))
    nb = math.sqrt(sum(value * value for value in b.values()))
    return 0.0 if not na or not nb else dot / (na * nb)

@dataclass(frozen=True)
class TruthFact:
    fact_id: int; namespace: str; key: str; value: Any; source_ref: str; observed_at_ns: int; supersedes_fact_id: int | None
@dataclass(frozen=True)
class Association:
    ref: str; text: str; score: float; metadata: dict[str, Any]
@dataclass(frozen=True)
class Prediction:
    event: str; confidence: float; observations: int; context: tuple[str, ...]

class TriMemory:
    """Truth, associative recollection, and temporal prediction stay physically distinct."""
    def __init__(self, path: str | Path = ":memory:", *, temporal_order: int = 2) -> None:
        if temporal_order < 1 or temporal_order > 4: raise ValueError("temporal_order must be between 1 and 4")
        self.path = str(path); self.temporal_order = temporal_order
        self.db = sqlite3.connect(self.path); self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=DELETE"); self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS truth_facts(fact_id INTEGER PRIMARY KEY AUTOINCREMENT,namespace TEXT NOT NULL,key TEXT NOT NULL,value_json TEXT NOT NULL,source_ref TEXT NOT NULL,observed_at_ns INTEGER NOT NULL,supersedes_fact_id INTEGER NULL REFERENCES truth_facts(fact_id));
        CREATE INDEX IF NOT EXISTS idx_truth_current ON truth_facts(namespace,key,fact_id DESC);
        CREATE TABLE IF NOT EXISTS associative_items(ref TEXT PRIMARY KEY,text TEXT NOT NULL,vector_json TEXT NOT NULL,metadata_json TEXT NOT NULL,remembered_at_ns INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS temporal_transitions(context_json TEXT NOT NULL,next_event TEXT NOT NULL,count INTEGER NOT NULL,PRIMARY KEY(context_json,next_event));
        """); self.db.commit()

    def assert_truth(self, namespace: str, key: str, value: Any, *, source_ref: str, observed_at_ns: int | None = None) -> TruthFact:
        if not namespace or not key or not source_ref: raise ValueError("namespace, key, and source_ref are required")
        current = self.get_truth(namespace,key); ts = observed_at_ns if observed_at_ns is not None else time.time_ns()
        cur = self.db.execute("INSERT INTO truth_facts(namespace,key,value_json,source_ref,observed_at_ns,supersedes_fact_id) VALUES(?,?,?,?,?,?)",(namespace,key,_json(value),source_ref,ts,current.fact_id if current else None)); self.db.commit()
        return TruthFact(int(cur.lastrowid),namespace,key,value,source_ref,ts,current.fact_id if current else None)

    def get_truth(self, namespace: str, key: str) -> TruthFact | None:
        r=self.db.execute("SELECT * FROM truth_facts WHERE namespace=? AND key=? ORDER BY fact_id DESC LIMIT 1",(namespace,key)).fetchone()
        if r is None: return None
        return TruthFact(r['fact_id'],r['namespace'],r['key'],json.loads(r['value_json']),r['source_ref'],r['observed_at_ns'],r['supersedes_fact_id'])

    def truth_history(self, namespace: str, key: str) -> tuple[TruthFact,...]:
        rows=self.db.execute("SELECT * FROM truth_facts WHERE namespace=? AND key=? ORDER BY fact_id",(namespace,key)).fetchall()
        return tuple(TruthFact(r['fact_id'],r['namespace'],r['key'],json.loads(r['value_json']),r['source_ref'],r['observed_at_ns'],r['supersedes_fact_id']) for r in rows)

    def remember_association(self, ref: str, text: str, *, metadata: dict[str,Any] | None=None) -> None:
        vec=_vector(text)
        self.db.execute("INSERT INTO associative_items(ref,text,vector_json,metadata_json,remembered_at_ns) VALUES(?,?,?,?,?) ON CONFLICT(ref) DO UPDATE SET text=excluded.text,vector_json=excluded.vector_json,metadata_json=excluded.metadata_json,remembered_at_ns=excluded.remembered_at_ns",(ref,text,_json(vec),_json(metadata or {}),time.time_ns())); self.db.commit()

    def recall(self, query: str, *, limit: int=5, min_score: float=0.0) -> tuple[Association,...]:
        qv=_vector(query); out=[]
        for r in self.db.execute("SELECT * FROM associative_items"):
            sv={int(k):int(v) for k,v in json.loads(r['vector_json']).items()}; score=_cosine(qv,sv)
            if score>=min_score: out.append(Association(r['ref'],r['text'],score,json.loads(r['metadata_json'])))
        out.sort(key=lambda x:(-x.score,x.ref)); return tuple(out[:limit])

    def observe_sequence(self, events: Iterable[str]) -> None:
        seq=[str(e) for e in events]
        if len(seq)<2:return
        with self.db:
            for i in range(1,len(seq)):
                context=tuple(seq[max(0,i-self.temporal_order):i]); nxt=seq[i]; cj=_json(context)
                self.db.execute("INSERT INTO temporal_transitions(context_json,next_event,count) VALUES(?,?,1) ON CONFLICT(context_json,next_event) DO UPDATE SET count=count+1",(cj,nxt))

    def predict_next(self, context: Iterable[str]) -> tuple[Prediction,...]:
        ctx=tuple(str(x) for x in context)[-self.temporal_order:]
        if not ctx:return ()
        rows=self.db.execute("SELECT next_event,count FROM temporal_transitions WHERE context_json=? ORDER BY count DESC,next_event ASC",(_json(ctx),)).fetchall(); total=sum(int(r['count']) for r in rows)
        if not total:return ()
        return tuple(Prediction(r['next_event'],int(r['count'])/total,int(r['count']),ctx) for r in rows)

    def close(self) -> None: self.db.close()

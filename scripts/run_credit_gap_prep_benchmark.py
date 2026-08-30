from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# This runner intentionally exercises prep modules only. It does not touch Workshop.
from untethered_aios.prep.rule_lane import build_default_rule_registry, DEFAULT_RULE_TASK_CLASS
from untethered_aios.prep.tri_memory import TriMemory
from untethered_aios.prep.river_blackboard import RiverBlackboard
from untethered_aios.prep.microforge import MicroForge, build_default_primitive_registry, blueprint_overlay_recipe
from untethered_aios.prep.downshift import PatternDetector, TraceEvent

if __name__ == "__main__":
    rule = build_default_rule_registry().execute(DEFAULT_RULE_TASK_CLASS,{"operation":"read","mutating":False,"publishing":False,"spending":False,"credential_change":False,"authority_change":False})
    memory=TriMemory(); memory.assert_truth("prep","ok",True,source_ref="runner"); memory.remember_association("a","cheap rule memory"); memory.observe_sequence(["need","claim","proven"])
    board=RiverBlackboard(); item=board.post_need("prep",{}); claim=board.claim("prep","runner"); board.complete(claim.item_id,"runner",{"ok":True},proven=True)
    forge=MicroForge(build_default_primitive_registry()).execute(blueprint_overlay_recipe(),{"width":24,"height":16,"title":"24x16"},granted_capabilities={"geometry.draw","artifact.compose"})
    candidate=PatternDetector().detect([[TraceEvent("x","a",{}),TraceEvent("x","b",{})],[TraceEvent("x","a",{}),TraceEvent("x","b",{})]])
    checks=[rule.result["policy_class"]=="READ_ONLY_SAFE",memory.get_truth("prep","ok").value is True,bool(memory.recall("rule")),memory.predict_next(["need","claim"])[0].event=="proven",board.get(item.item_id).status.value=="PROVEN",len(forge["trace"])==4,candidate is not None]
    memory.close();board.close();print("PASS" if all(checks) else "FAIL");raise SystemExit(0 if all(checks) else 1)

import tempfile
import time
import unittest
from pathlib import Path

from untethered_aios.prep.rule_lane import build_default_rule_registry, DEFAULT_RULE_TASK_CLASS, RuleRegistry, RuleSpec, RuleConflict, NoRuleMatch, stable_hash
from untethered_aios.prep.tri_memory import TriMemory
from untethered_aios.prep.river_blackboard import RiverBlackboard, BlackboardStatus
from untethered_aios.prep.microforge import MicroForge, build_default_primitive_registry, blueprint_overlay_recipe, ForgeError
from untethered_aios.prep.downshift import PatternDetector, TraceEvent
from untethered_aios.prep.capability_metabolism import CapabilityHealth, MetabolismAdvisor, MetabolismState
from untethered_aios.prep.continuity import ContinuityCheckpoint, ContinuityStore
from untethered_aios.prep.model_gateway import BackendInfo, FakeBackend, ModelGateway
from untethered_aios.prep.capability_cell import CapabilityCell, CapabilityCellSpec, CellBudget
from untethered_aios.prep.evolution import EvolutionLedger, EvolutionStage

class CreditGapPrepTests(unittest.TestCase):
    def test_rule_read_only(self):
        r=build_default_rule_registry();p={"operation":"read","mutating":False,"publishing":False,"spending":False,"credential_change":False,"authority_change":False}
        self.assertEqual(r.execute(DEFAULT_RULE_TASK_CLASS,p).result["policy_class"],"READ_ONLY_SAFE")
    def test_rule_protected_like_no_match(self):
        r=build_default_rule_registry();p={"operation":"read","mutating":True,"publishing":False,"spending":False,"credential_change":False,"authority_change":False}
        with self.assertRaises(NoRuleMatch):r.execute(DEFAULT_RULE_TASK_CLASS,p)
    def test_rule_conflict_fails_closed(self):
        r=RuleRegistry();base=dict(version="1",task_class="x",predicate_name="p",action_name="a",required_capabilities=(),input_contract={},output_contract={},dependency_identity="x",dependency_sha256=stable_hash("x"),priority=1)
        r.register(RuleSpec(rule_id="rule-a",**base),lambda _:True,lambda _:{"x":1});r.register(RuleSpec(rule_id="rule-b",**base),lambda _:True,lambda _:{"x":2})
        with self.assertRaises(RuleConflict):r.execute("x",{})
    def test_tri_memory_separates_truth_recall_prediction(self):
        m=TriMemory();m.assert_truth("p","status","verified",source_ref="proof");m.remember_association("a","verified workshop artifact");m.observe_sequence(["need","claim","proven"])
        self.assertEqual(m.get_truth("p","status").value,"verified");self.assertEqual(m.recall("artifact")[0].ref,"a");self.assertEqual(m.predict_next(["need","claim"])[0].event,"proven");self.assertIsNone(m.get_truth("prediction","proven"))
    def test_tri_memory_reopen(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"m.sqlite3";m=TriMemory(p);m.assert_truth("x","y",7,source_ref="s");m.close();m=TriMemory(p);self.assertEqual(m.get_truth("x","y").value,7);m.close()
    def test_blackboard_three_workers(self):
        b=RiverBlackboard();[b.post_need("job",{"n":n}) for n in range(3)]
        for w in("w1","w2","w3"):
            i=b.claim("job",w);self.assertIsNotNone(i);b.complete(i.item_id,w,{"ok":True},proven=True)
        self.assertEqual(len(b.scan(status=BlackboardStatus.PROVEN)),3);self.assertIsNone(b.claim("job","w4"))
    def test_microforge_recipe_and_capability_denial(self):
        f=MicroForge(build_default_primitive_registry());recipe=blueprint_overlay_recipe();result=f.execute(recipe,{"width":24,"height":16,"title":"24x16"},granted_capabilities={"geometry.draw","artifact.compose"});self.assertEqual(len(result["trace"]),4)
        with self.assertRaises(ForgeError):f.execute(recipe,{"width":24,"height":16,"title":"x"},granted_capabilities={"geometry.draw"})
    def test_downshift_candidate_and_protected_denial(self):
        d=PatternDetector();traces=[[TraceEvent("c","read",{"p":"a"}),TraceEvent("c","norm",{"m":"x"})],[TraceEvent("c","read",{"p":"b"}),TraceEvent("c","norm",{"m":"x"})]];c=d.detect(traces);self.assertTrue(d.verify(c,traces)["verified"])
        protected=[[TraceEvent("c","read",{},True),TraceEvent("c","norm",{})],[TraceEvent("c","read",{},True),TraceEvent("c","norm",{})]];pc=d.detect(protected);self.assertFalse(d.verify(pc,protected)["verified"])
    def test_metabolism_advisory_only(self):
        h=CapabilityHealth("x",20,20,0,20,1024,2,0.9,0.9,0.6,5);r=MetabolismAdvisor().recommend(h);self.assertEqual(r.state,MetabolismState.MERGE);self.assertFalse(r.destructive_action_allowed)
    def test_continuity_identity_separation(self):
        with tempfile.TemporaryDirectory() as td:
            s=ContinuityStore(Path(td)/"c.sqlite3");c=ContinuityCheckpoint("s","p","summary",("r",),{"owner":"context"},{"ai":"identity"},time.time_ns());s.save(c);x=s.resume("s");self.assertNotEqual(x.owner_context,x.ai_identity);s.close()
    def test_model_gateway_paid_network_fail_closed(self):
        g=ModelGateway();b=FakeBackend();g.register(BackendInfo(b.backend_id,True,False,False),b);self.assertEqual(g.call(b.backend_id,"hi"),"fake:hi")
        p=FakeBackend("paid");p.backend_id="paid";g.register(BackendInfo("paid",False,True,True),p)
        with self.assertRaises(PermissionError):g.call("paid","x")
    def test_capability_cell_exact_boundary(self):
        cell=CapabilityCell(CapabilityCellSpec("c",("read",),("x",),("y",),CellBudget(2,0,100)));r=cell.run(lambda inp,check:(check("read") or {"y":inp["x"]+1}),{"x":1},granted_capabilities={"read"});self.assertEqual(r.outputs["y"],2)
    def test_evolution_denies_authority_expansion(self):
        l=EvolutionLedger();l.start("e","weakness")
        with self.assertRaises(PermissionError):l.advance("e",EvolutionStage.QUERY_PROPOSED,authority_expanded=True)

if __name__ == "__main__":unittest.main()

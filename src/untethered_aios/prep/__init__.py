"""Credit-gap prep modules for Untethered AIOS.

These modules are intentionally additive and authority-free. They are designed to be
reviewed and integrated against the latest verified local successor by Codex later.
"""

from .rule_lane import RuleRegistry, RuleSpec, RuleConflict, NoRuleMatch
from .tri_memory import TriMemory
from .river_blackboard import RiverBlackboard, BlackboardStatus
from .microforge import MicroForge, ToolRecipe, RecipeStep
from .downshift import PatternDetector, SkillCandidate
from .capability_metabolism import CapabilityHealth, MetabolismAdvisor
from .continuity import ContinuityStore, ContinuityCheckpoint
from .model_gateway import ModelGateway, FakeBackend
from .capability_cell import CapabilityCell, CapabilityCellSpec, CellBudget
from .evolution import EvolutionLedger, EvolutionStage

__all__ = [
    "RuleRegistry", "RuleSpec", "RuleConflict", "NoRuleMatch", "TriMemory",
    "RiverBlackboard", "BlackboardStatus", "MicroForge", "ToolRecipe", "RecipeStep",
    "PatternDetector", "SkillCandidate", "CapabilityHealth", "MetabolismAdvisor",
    "ContinuityStore", "ContinuityCheckpoint", "ModelGateway", "FakeBackend",
    "CapabilityCell", "CapabilityCellSpec", "CellBudget", "EvolutionLedger", "EvolutionStage",
]

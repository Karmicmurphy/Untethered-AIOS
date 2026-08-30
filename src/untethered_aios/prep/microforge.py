from __future__ import annotations
from dataclasses import dataclass
import hashlib,json
from typing import Any,Callable

class ForgeError(RuntimeError): pass

def stable_hash(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

@dataclass(frozen=True)
class PrimitiveSpec:
    name:str; version:str; required_capabilities:tuple[str,...]; deterministic:bool=True
@dataclass(frozen=True)
class RecipeStep:
    step_id:str; primitive:str; args:dict[str,Any]; save_as:str
@dataclass(frozen=True)
class ToolRecipe:
    recipe_id:str; version:str; inputs:tuple[str,...]; steps:tuple[RecipeStep,...]; required_capabilities:tuple[str,...]; max_steps:int=32
    @property
    def recipe_sha256(self)->str:
        return stable_hash({"recipe_id":self.recipe_id,"version":self.version,"inputs":self.inputs,"steps":[{"step_id":s.step_id,"primitive":s.primitive,"args":s.args,"save_as":s.save_as} for s in self.steps],"required_capabilities":self.required_capabilities,"max_steps":self.max_steps})
Primitive=Callable[...,Any]

class PrimitiveRegistry:
    def __init__(self)->None:self._items:dict[str,tuple[PrimitiveSpec,Primitive]]={}
    def register(self,spec:PrimitiveSpec,fn:Primitive)->None:
        if spec.name in self._items:raise ValueError(f"primitive already registered: {spec.name}")
        self._items[spec.name]=(spec,fn)
    def resolve(self,name:str)->tuple[PrimitiveSpec,Primitive]:
        if name not in self._items:raise ForgeError(f"unknown primitive: {name}")
        return self._items[name]

class MicroForge:
    """Declarative capability-checked recipe executor. No arbitrary code eval."""
    def __init__(self,registry:PrimitiveRegistry)->None:self.registry=registry
    def validate(self,recipe:ToolRecipe)->None:
        if not recipe.recipe_id or not recipe.version:raise ForgeError("recipe_id and version required")
        if len(recipe.steps)>recipe.max_steps:raise ForgeError("recipe exceeds step budget")
        if len({s.step_id for s in recipe.steps})!=len(recipe.steps):raise ForgeError("step IDs must be unique")
        produced=set(recipe.inputs); required=set()
        for step in recipe.steps:
            spec,_=self.registry.resolve(step.primitive)
            if not spec.deterministic:raise ForgeError("V0.1 prep allows deterministic primitives only")
            required.update(spec.required_capabilities)
            for value in step.args.values():
                if isinstance(value,str) and value.startswith("$"):
                    ref=value[1:].split(".",1)[0]
                    if ref not in produced:raise ForgeError(f"unknown reference: {value}")
            produced.add(step.save_as)
        if not required.issubset(set(recipe.required_capabilities)):raise ForgeError(f"recipe omitted capabilities: {sorted(required-set(recipe.required_capabilities))}")
    @staticmethod
    def _resolve(value:Any,values:dict[str,Any])->Any:
        if not(isinstance(value,str) and value.startswith("$")):return value
        parts=value[1:].split("."); current=values[parts[0]]
        for part in parts[1:]:current=current[part] if isinstance(current,dict) else getattr(current,part)
        return current
    def execute(self,recipe:ToolRecipe,inputs:dict[str,Any],*,granted_capabilities:set[str])->dict[str,Any]:
        self.validate(recipe)
        if set(inputs)!=set(recipe.inputs):raise ForgeError("inputs do not match contract")
        if not set(recipe.required_capabilities).issubset(granted_capabilities):raise ForgeError("caller lacks recipe capabilities")
        values=dict(inputs);trace=[]
        for index,step in enumerate(recipe.steps,1):
            if index>recipe.max_steps:raise ForgeError("step budget exceeded")
            spec,fn=self.registry.resolve(step.primitive)
            if not set(spec.required_capabilities).issubset(granted_capabilities):raise ForgeError(f"primitive capability denied: {step.primitive}")
            result=fn(**{k:self._resolve(v,values) for k,v in step.args.items()});values[step.save_as]=result
            trace.append({"step_id":step.step_id,"primitive":step.primitive,"primitive_version":spec.version,"result_sha256":stable_hash(result)})
        return {"recipe_id":recipe.recipe_id,"recipe_version":recipe.version,"recipe_sha256":recipe.recipe_sha256,"outputs":{s.save_as:values[s.save_as] for s in recipe.steps},"trace":trace}

def build_default_primitive_registry()->PrimitiveRegistry:
    r=PrimitiveRegistry()
    r.register(PrimitiveSpec("geometry.line","1.0.0",("geometry.draw",)),lambda x1,y1,x2,y2:{"kind":"line","x1":x1,"y1":y1,"x2":x2,"y2":y2})
    r.register(PrimitiveSpec("geometry.label","1.0.0",("geometry.draw",)),lambda text,x,y:{"kind":"label","text":str(text),"x":x,"y":y})
    r.register(PrimitiveSpec("artifact.bundle","1.0.0",("artifact.compose",)),lambda name,line_a,line_b,label_a:{"name":name,"commands":[line_a,line_b,label_a]})
    return r

def blueprint_overlay_recipe()->ToolRecipe:
    return ToolRecipe("blueprint-overlay-plan-v1","1.0.0",("width","height","title"),(
        RecipeStep("top","geometry.line",{"x1":0,"y1":0,"x2":"$width","y2":0},"top_line"),
        RecipeStep("side","geometry.line",{"x1":0,"y1":0,"x2":0,"y2":"$height"},"side_line"),
        RecipeStep("title","geometry.label",{"text":"$title","x":0,"y":0},"title_label"),
        RecipeStep("bundle","artifact.bundle",{"name":"$title","line_a":"$top_line","line_b":"$side_line","label_a":"$title_label"},"overlay_plan"),
    ),("geometry.draw","artifact.compose"),8)

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const html = fs.readFileSync(new URL("../app/index.html", import.meta.url), "utf8");
const js = fs.readFileSync(new URL("../app/assets/capability-bay.js", import.meta.url), "utf8");
const css = fs.readFileSync(new URL("../app/assets/capability-bay.css", import.meta.url), "utf8");
const builder = fs.readFileSync(new URL("../app/assets/builder-workspace.js", import.meta.url), "utf8");
const worker = fs.readFileSync(new URL("../companion/local_worker_kit.py", import.meta.url), "utf8");
const serviceWorker = fs.readFileSync(new URL("../app/service-worker.js", import.meta.url), "utf8");

test("Modules exposes one truthful Capability Bay with measured hardware and concise detail", () => {
  for (const id of ["capabilityBay", "capabilityBayState", "capabilityHardware", "capabilitySearch", "capabilityList", "capabilityDetail", "capabilityProtocols", "capabilityCompassHandoff"]) {
    assert.match(html, new RegExp(`id="${id}"`));
  }
  for (const label of ["Verified", "Discovered", "Installed", "Free", "Local", "Offline", "Workers", "Skills", "MCP", "Creative", "AI", "Media", "Development", "Experimental", "Degraded", "Retired"]) {
    assert.match(html, new RegExp(`>${label}<`));
  }
  assert.match(js, /\/api\/capability-registry/);
  assert.match(js, /\/api\/hardware-profile/);
  assert.match(js, /Registry compatibility remains|hardwareFit/);
  assert.match(js, /What it does/);
  assert.match(js, /Known limit/);
  assert.match(js, /Artifact Compass finding → Capability candidate/);
});

test("Build advisor is free-first and only prepares governed builder inputs", () => {
  for (const id of ["buildCapabilityRequest", "capabilityRecommend", "capabilityRecommendation", "capabilityPrepareBuild", "capabilityPrepareModule"]) {
    assert.match(html, new RegExp(`id="${id}"`));
  }
  assert.match(js, /\/api\/capability-registry\/recommend/);
  assert.match(js, /window\.twisOpenBuilder\?\.\("build"\)/);
  assert.match(js, /window\.twisOpenBuilder\?\.\("module"\)/);
  assert.doesNotMatch(js, /child_process|exec\(|spawn\(|npm install|pip install|provider\s*(?:call|request|fallback)|0\.0\.0\.0/i);
});

test("Capability Inspection is a real staged owner-controlled lifecycle, not a self-verifying scan", () => {
  for (const id of ["capabilityInspection", "capabilityInspect", "capabilityPlanApprove", "capabilityPlanReject", "capabilityRunInspection", "capabilityOwnerVerify", "capabilityOwnerBlock", "capabilityOwnerIncompatible", "capabilityInspectionEvidence"]) assert.match(html, new RegExp(`id="${id}"`));
  for (const stage of ["source", "dependencies", "hardware", "permissions", "test", "evidence", "decision"]) assert.match(html, new RegExp(`data-inspection-stage="${stage}"`));
  assert.match(js, /\/api\/capability-inspections\/authority-template/);
  assert.match(js, /\/plan-decision/);
  assert.match(js, /\/owner-decision/);
  assert.match(js, /evidenceHash:\s*state\.inspection\.evidenceHash/);
  assert.match(html, /Discovery grants no execution authority/);
  assert.doesNotMatch(js, /setTimeout\([^)]*(?:VERIFIED|verification_candidate)|fake|scanning animation/i);
});

test("Build and Module proposal builders bind registry requests and scaffold type without execution", () => {
  assert.match(builder, /id="build-capabilityRequest"/);
  assert.match(builder, /id="module-scaffoldType"/);
  for (const profile of ["TWIS native capability", "Agent Skill", "Local Python worker", "Local JavaScript worker", "Disposable worker", "MCP server wrapper", "MCP client adapter", "WASI component proposal", "Comfy workflow adapter", "Cloudflare free-tier worker"]) {
    assert.match(builder, new RegExp(profile));
  }
  assert.match(worker, /capabilityRegistryContext/);
  assert.match(worker, /stale_capability_registry/);
});

test("switching between governed builder types cannot reuse the previous job identity", () => {
  assert.match(builder, /state\.job\.worker\?\.workerId !== requestedWorkerId/);
  assert.match(builder, /sessionStorage\.removeItem\("twis\.builder\.job"\)/);
  assert.match(builder, /localStorage\.removeItem\(recoveryKey\(projectId\)\)/);
  assert.match(builder, /\$\("#builderPlan"\)\.hidden = true/);
  assert.match(builder, /\$\("#builderResult"\)\.hidden = true/);
});

test("Capability Bay is mobile-safe, reduced-motion-safe, and service-worker cached", () => {
  assert.match(css, /@media \(max-width: 410px\)/);
  assert.match(css, /min-height: 44px/);
  assert.match(css, /prefers-reduced-motion/);
  assert.match(serviceWorker, /capability-bay\.css/);
  assert.match(serviceWorker, /capability-bay\.js/);
  assert.match(serviceWorker, /v27-music-loop-deck-v1/);
});

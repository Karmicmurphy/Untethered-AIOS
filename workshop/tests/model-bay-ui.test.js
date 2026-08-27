import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const html = fs.readFileSync(new URL("../app/index.html", import.meta.url), "utf8");
const ui = fs.readFileSync(new URL("../app/assets/model-bay.js", import.meta.url), "utf8");
const builder = fs.readFileSync(new URL("../app/assets/builder-workspace.js", import.meta.url), "utf8");
const server = fs.readFileSync(new URL("../companion/server.py", import.meta.url), "utf8");

test("Model Bay renders only measured model and runtime truth", () => {
  for (const id of ["modelBayState", "modelBayVerify", "modelBayStart", "modelBayHealth", "modelBayStop", "modelBayTruth", "controlModelBayState"]) assert.match(html, new RegExp(`id="${id}"`));
  assert.match(ui, /model\.state/);
  assert.match(ui, /lastReadyVerification/);
  assert.doesNotMatch(ui, /GPU utilization|tokens per second|fake/i);
});

test("Write AI Assist is explicit and reuses separate builder approvals", () => {
  assert.match(html, /id="openWriteAiStudio"[^>]*>Open Write Studio AI/);
  assert.match(html, /id="writeAiApprovePlan"/);
  assert.match(html, /id="writeAiApproveResult"/);
  assert.match(builder, /ai: "local-ai-rewrite"/);
  assert.match(builder, /inferencePreset/);
  assert.match(html, /builderApprovePlan/);
  assert.match(html, /builderApproveResult/);
  assert.match(html, /Save inactive draft/);
});

test("arbitrary remote AI endpoint is retired", () => {
  assert.doesNotMatch(html, /id="aiEndpoint"|id="aiKey"|id="aiModel"/);
  assert.match(server, /arbitrary_ai_endpoint_retired/);
  assert.match(server, /registered localhost Model Bay route/);
});

test("local AI remains optional and auto-start is visibly off", () => {
  assert.match(html, /Auto-start local model \(OFF in Release 0\.17\)/);
  assert.match(html, /Workshop startup never depends on it/);
  assert.match(html, /127\.0\.0\.1:8876/);
});

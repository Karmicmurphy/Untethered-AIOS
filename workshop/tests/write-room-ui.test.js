import test from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";

const index = await readFile(new URL("../app/index.html", import.meta.url), "utf8");
const writeRoom = await readFile(new URL("../app/assets/write-room.js", import.meta.url), "utf8");
const app = await readFile(new URL("../app/assets/app.js", import.meta.url), "utf8");
const style = await readFile(new URL("../app/assets/style.css", import.meta.url), "utf8");
const serviceWorker = await readFile(new URL("../app/service-worker.js", import.meta.url), "utf8");

test("Write Room exposes durable daily-use and recovery controls in owner-facing terms", () => {
  for (const id of [
    "writeSaveStatus",
    "writeRecoveryBanner",
    "snapshotDialog",
    "restoreWriteDialog",
    "compareWriteDialog",
    "writeProposalPanel",
    "exportWriteProject",
  ]) {
    assert.match(index, new RegExp(`id="${id}"`));
  }
  assert.match(index, /role="status" aria-live="polite"/);
  assert.match(index, /Keep current writing/);
  assert.match(index, /They never change your writing until you approve it/);
});

test("Write Room client uses immediate browser recovery plus durable recovery and autosave", () => {
  assert.match(writeRoom, /localStorage\.setItem\(localKey/);
  assert.match(writeRoom, /\/recovery/);
  assert.match(writeRoom, /saveNow\("autosave"\)/);
  assert.match(writeRoom, /visibilitychange/);
  assert.match(writeRoom, /write_version_conflict/);
  assert.match(writeRoom, /requiresExplicitDecision|source-preserving proposal/i);
  assert.match(writeRoom, /if \(cause !== "autosave"\) throw error;\s+return null;/);
  const apiSource = writeRoom.match(
    /async function api[\s\S]*?\n}\n\nfunction setStatus/,
  )?.[0] || "";
  assert.doesNotMatch(apiSource, /\bcause\b/);
  assert.match(writeRoom, /localStorage\.setItem[\s\S]*?return true;[\s\S]*?catch[\s\S]*?return false;/);
  assert.match(writeRoom, /const localRecoveryReady = saveLocalRecovery\(\);/);
  assert.match(writeRoom, /if \(localRecoveryReady\) \{\s+setStatus\("Unsaved changes/);
});

test("imported text, findings, paths, and diffs render as text rather than HTML", () => {
  assert.doesNotMatch(writeRoom, /\.innerHTML\s*=/);
  assert.match(writeRoom, /row\.textContent = finding\.message/);
  assert.match(writeRoom, /exportResult\.textContent/);
  assert.match(writeRoom, /content\.textContent = lines\.length/);
  assert.match(writeRoom, /write-change-grid/);
});

test("My Work opens stable writing identity and projects durable metadata", () => {
  assert.match(app, /twisWriteRoom\?\.openProject\(i\.id\)/);
  assert.match(app, /versionCount/);
  assert.match(app, /Recovery draft/);
  assert.match(app, /data-write-history/);
  assert.match(app, /data-write-export/);
  assert.match(app, /twis:write-summaries/);
});

test("service worker cache is bumped and includes the Write Room client", () => {
  assert.match(serviceWorker, /twis-holo-full-v27-music-loop-deck-v1/);
  assert.match(serviceWorker, /\.\/assets\/write-room\.js/);
  assert.match(index, /<script src="assets\/write-room\.js"><\/script>/);
});

test("Write Studio exposes real governed local AI actions without mutating on generation", () => {
  for (const id of [
    "writeAiStudio", "writeAiAction", "writeAiContextSources", "writeAiCreatePlan",
    "writeAiApprovePlan", "writeAiRun", "writeAiApproveResult", "writeAiRejectResult",
    "writeAiOriginal", "writeAiProposal", "writeAiApply", "writeAiSaveVersion",
    "writeAiSaveDraft", "writeAiRollbackVersion", "writeAiReadDraft", "writeAiStopSpeaking",
  ]) assert.match(index, new RegExp(`id="${id}"`));
  for (const action of ["Brainstorm story ideas", "Continue passage", "Rewrite selection", "Make darker", "Make funnier", "Make more emotional", "Make more direct", "Make stranger or surreal", "Improve dialogue", "Suggest dialogue", "Suggest next scene", "Develop character", "Generate alternate version", "Suggest structure", "Summarize direction", "Suggest creative possibilities"]) assert.match(writeRoom, new RegExp(action));
  assert.match(writeRoom, /local-ai-rewrite/);
  assert.match(writeRoom, /plan-decision/);
  assert.match(writeRoom, /result-decision/);
  assert.match(writeRoom, /Approve the result before applying it/);
  assert.match(writeRoom, /speechSynthesis/);
  assert.doesNotMatch(writeRoom, /0\.0\.0\.0|https:\/\/api\.|provider/i);
});

test("mobile layout permits the single app column and sidebar to shrink", () => {
  assert.match(
    style,
    /@media\(max-width:900px\)\{\.app\{grid-template-columns:minmax\(0,1fr\)\}\.sidebar\{min-width:0\}\}/,
  );
});

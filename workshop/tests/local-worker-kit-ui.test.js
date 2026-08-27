import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";

const index = readFileSync(new URL("../app/index.html", import.meta.url), "utf8");
const script = readFileSync(
  new URL("../app/assets/local-worker-kit.js", import.meta.url),
  "utf8",
);
const style = readFileSync(
  new URL("../app/assets/local-worker-kit.css", import.meta.url),
  "utf8",
);
const serviceWorker = readFileSync(
  new URL("../app/service-worker.js", import.meta.url),
  "utf8",
);
const talk = readFileSync(new URL("../app/assets/talk-room.js", import.meta.url), "utf8");
const write = readFileSync(new URL("../app/assets/write-room.js", import.meta.url), "utf8");

test("My Work presents four supported local workers in owner language", () => {
  assert.match(index, /id="localWorkerKitTitle">Supported local workers/);
  assert.match(index, /Prepare worker plan/);
  assert.match(index, /Review before anything runs/);
  assert.match(index, /Validated output is evidence, not approval/);
  assert.match(index, /Worker job history/);
  assert.match(script, /approved-text-reader/);
  assert.match(script, /code-structure-inspector/);
  assert.match(script, /note-proposal-worker/);
  assert.match(script, /package-manifest-validator/);
  assert.match(script, /Inspect this approved file/);
  assert.match(script, /Show me the structure of this code/);
  assert.match(script, /Make a note from this content/);
  assert.match(script, /Validate this approved package/);
});

test("Talk and Write expose current saved sources without asking for IDs", () => {
  assert.match(index, /id="talkWorkerRead"/);
  assert.match(index, /id="talkWorkerStructure"/);
  assert.match(index, /id="talkWorkerNote"/);
  assert.match(index, /id="writeWorkerRead"/);
  assert.match(index, /id="writeWorkerStructure"/);
  assert.match(index, /id="writeWorkerNote"/);
  assert.match(talk, /getState: \(\) =>/);
  assert.match(write, /getState: \(\) =>/);
  assert.match(script, /selectedTalkText/);
  assert.match(script, /selectedWriteText/);
  assert.match(script, /source\.title/);
});

test("UI uses the fixed API and keeps approval separate from execution and result", () => {
  assert.match(script, /\/api\/local-workers/);
  assert.match(script, /\/api\/local-worker-sources/);
  assert.match(script, /\/api\/local-worker-jobs\/plan/);
  assert.match(script, /plan-decision/);
  assert.match(script, /"execute"/);
  assert.match(script, /result-decision/);
  assert.match(script, /"rollback"/);
  assert.match(script, /"cancel"/);
  assert.match(script, /"recover"/);
  assert.match(script, /\/delete/);
  assert.match(script, /Plan approved; the worker has not run yet/);
  assert.match(script, /result awaits a separate decision/);
  assert.match(script, /remains unattached and inactive/);
  assert.match(script, /receipts preserved/i);
});

test("owner and worker output is inserted as text, not executable markup", () => {
  assert.match(script, /addCard\(root, "Approved source", job\.source\.title\)/);
  assert.match(script, /area\.value = String/);
  assert.match(script, /pre\.textContent = JSON\.stringify/);
  assert.doesNotMatch(script, /\.innerHTML\s*=/);
  assert.doesNotMatch(script, /insertAdjacentHTML/);
  assert.doesNotMatch(script, /\beval\s*\(/);
  assert.doesNotMatch(script, /new Function/);
  assert.doesNotMatch(script, /new Worker/);
  assert.doesNotMatch(script, /WebSocket/);
});

test("Release 0.8 worker UI is cached and usable at 390 pixel width", () => {
  assert.match(serviceWorker, /twis-holo-full-v27-music-loop-deck-v1/);
  assert.match(serviceWorker, /local-worker-kit\.css/);
  assert.match(serviceWorker, /local-worker-kit\.js/);
  assert.match(style, /@media \(max-width: 700px\)/);
  assert.match(style, /\.local-worker-kit \[hidden\]\s*{\s*display: none/);
  assert.match(style, /\.local-worker-cards,\s*\n\s*\.local-worker-builder/);
  assert.match(style, /grid-template-columns: 1fr/);
  assert.match(index, /assets\/local-worker-kit\.css/);
  assert.match(index, /assets\/local-worker-kit\.js/);
});

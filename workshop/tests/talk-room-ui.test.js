import test from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";

const index = await readFile(new URL("../app/index.html", import.meta.url), "utf8");
const talkRoom = await readFile(new URL("../app/assets/talk-room.js", import.meta.url), "utf8");
const app = await readFile(new URL("../app/assets/app.js", import.meta.url), "utf8");
const style = await readFile(new URL("../app/assets/style.css", import.meta.url), "utf8");
const serviceWorker = await readFile(new URL("../app/service-worker.js", import.meta.url), "utf8");

test("Talk Room exposes durable daily-use, recovery, history, transfer, inspection, export, and voice controls", () => {
  for (const id of [
    "talkSessionPicker",
    "talkSaveStatus",
    "saveTalkTitle",
    "talkRecoveryBanner",
    "talkTranscript",
    "talkDraft",
    "talkSnapshotDialog",
    "restoreTalkDialog",
    "compareTalkDialog",
    "talkTransferPanel",
    "talkInspectionPanel",
    "openApprovedArtifactInspection",
    "talkPassages",
    "talkExportFormat",
    "startTalkListening",
    "stopTalkListening",
    "talkVoiceDraft",
    "readTalkAloud",
    "pauseTalkReading",
    "stopTalkReading",
  ]) {
    assert.match(index, new RegExp(`id="${id}"`));
  }
  assert.match(index, /original Talk remains unchanged/i);
  assert.match(index, /approval note/i);
  assert.match(index, /recovery version first/i);
});

test("Talk client uses immediate browser recovery and durable SQLite recovery with conflict gating", () => {
  assert.match(talkRoom, /localStorage\.setItem\(recoveryKey/);
  assert.match(talkRoom, /\/recovery/);
  assert.match(talkRoom, /scheduleRecovery/);
  assert.match(talkRoom, /talk_version_conflict/);
  assert.match(talkRoom, /baseVersion: current\.currentVersion/);
  assert.match(talkRoom, /\/title/);
  assert.match(talkRoom, /visibilitychange/);
  assert.match(talkRoom, /voice-draft-approved/);
});

test("transcript, imported text, inspection findings, passages, and diffs are rendered as text", () => {
  assert.doesNotMatch(talkRoom, /\.innerHTML\s*=/);
  assert.doesNotMatch(talkRoom, /insertAdjacentHTML|outerHTML|document\.write|eval\(|new Function/);
  assert.match(talkRoom, /content\.textContent = entry\.content/);
  assert.match(talkRoom, /quote\.textContent = passage\.quote/);
  assert.match(talkRoom, /before\.textContent =/);
  assert.match(talkRoom, /after\.textContent =/);
  assert.match(talkRoom, /summary\.textContent =/);
  assert.match(talkRoom, /item\.textContent = text\(value\)/);
});

test("voice requires explicit local proof, never installs a pack, and exposes stop/failure state", () => {
  assert.match(talkRoom, /"processLocally" in SR\.prototype/);
  assert.match(talkRoom, /typeof SR\.available === "function"/);
  assert.match(talkRoom, /processLocally: true/);
  assert.match(talkRoom, /status === "available"/);
  assert.match(talkRoom, /recognition\.processLocally = true/);
  assert.match(talkRoom, /voice\.localService === true/);
  assert.match(talkRoom, /recognition\.abort\(\)/);
  assert.match(talkRoom, /utterance\.onerror/);
  assert.doesNotMatch(talkRoom, /\.install\(|SpeechRecognition\.install/);
  assert.doesNotMatch(talkRoom, /getUserMedia|MediaRecorder|Blob\(/);
});

test("legacy network-capable Talk bridge is removed and the Talk client calls local routes only", () => {
  assert.doesNotMatch(app, /aiReply|\/api\/ai\/chat|chatForm|chatInput|webkitSpeechRecognition/);
  assert.doesNotMatch(index, /Legacy Talk bridge|id="chatForm"|id="chatInput"/);
  const fetchArguments = [...talkRoom.matchAll(/fetch\(([^,\n]+)/g)].map((match) => match[1]);
  assert.deepEqual(fetchArguments, ["path"]);
  assert.doesNotMatch(talkRoom, /https?:\/\/|WebSocket|XMLHttpRequest/);
});

test("My Work opens stable Talk identity and exposes useful Talk actions", () => {
  assert.match(app, /twisTalkRoom\?\.openSession\(i\.id\)/);
  assert.match(app, /data-talk-history/);
  assert.match(app, /data-talk-export/);
  assert.match(app, /data-talk-transfer/);
  assert.match(app, /talk-session-summary-v1/);
  assert.match(talkRoom, /twis:talk-summaries/);
  assert.match(app, /projectTitle=active\(\)\?\.title/);
});

test("approved artifact inspection reuses the governed existing room instead of bypassing it", () => {
  assert.match(talkRoom, /function openApprovedArtifactInspection/);
  assert.match(talkRoom, /twisOpenRoom\?\.\("flashriver-review"\)/);
  assert.match(talkRoom, /selection, plan, approval, and receipt gates remain in force/);
  assert.match(talkRoom, /inspect: openApprovedArtifactInspection/);
  assert.match(talkRoom, /document\.createRange\(\)/);
  assert.doesNotMatch(talkRoom, /textContent\.indexOf\(quote\)/);
});

test("blank Talk-to-Write approval is blocked before an API request", () => {
  assert.match(talkRoom, /decision === "approve" && !note\.trim\(\)/);
  assert.match(talkRoom, /Add a short approval note before creating the Write document/);
  assert.match(talkRoom, /\$\("#talkTransferNote"\)\.focus\(\)/);
});

test("durable Talk-to-Write decisions are rebound after a browser restart", () => {
  assert.match(talkRoom, /function renderTransfer\(\)/);
  assert.match(talkRoom, /Number\(transfer\.sourceVersion\) === current\.currentVersion/);
  assert.match(talkRoom, /current\?\.transfers \|\| \[\]/);
  assert.match(talkRoom, /\$\("#rollbackTalkTransfer"\)\.hidden = !approved/);
  assert.match(talkRoom, /Stale — Talk changed; prepare a new proposal/);
  assert.match(talkRoom, /renderTransfer\(\);\s+chooseRecovery\(\);/);
});

test("service worker cache is Release 0.8 and includes the Talk client", () => {
  assert.match(serviceWorker, /twis-holo-full-v27-music-loop-deck-v1/);
  assert.match(serviceWorker, /\.\/assets\/talk-room\.js/);
  assert.match(index, /<script src="assets\/talk-room\.js"><\/script>/);
  assert.match(
    serviceWorker,
    /if\(request\.method!=="GET"\|\|url\.origin!==self\.location\.origin\|\|url\.pathname\.startsWith\("\/api\/"\)\)return;/,
  );
});

test("Talk layout collapses to one column and supports narrow-screen text wrapping", () => {
  assert.match(style, /@media\(max-width:1050px\)\{\.talk-daily-grid\{grid-template-columns:1fr\}/);
  assert.match(style, /\.talk-entry-content\{[^}]*overflow-wrap:anywhere/);
  assert.match(style, /@media\(max-width:700px\)/);
});

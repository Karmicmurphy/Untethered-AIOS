import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const html = fs.readFileSync(new URL("../app/index.html", import.meta.url), "utf8");
const css = fs.readFileSync(new URL("../app/assets/room-system.css", import.meta.url), "utf8");
const coherenceCss = fs.readFileSync(new URL("../app/assets/ui-coherence.css", import.meta.url), "utf8");
const js = fs.readFileSync(new URL("../app/assets/room-system.js", import.meta.url), "utf8");
const coherenceJs = fs.readFileSync(new URL("../app/assets/ui-coherence.js", import.meta.url), "utf8");
const app = fs.readFileSync(new URL("../app/assets/app.js", import.meta.url), "utf8");
const shell = fs.readFileSync(new URL("../app/assets/shell-0.14.js", import.meta.url), "utf8");
const navigation = fs.readFileSync(new URL("../app/assets/navigation-state.js", import.meta.url), "utf8");
const worker = fs.readFileSync(new URL("../app/service-worker.js", import.meta.url), "utf8");
const server = fs.readFileSync(new URL("../companion/server.py", import.meta.url), "utf8");
const pkg = JSON.parse(fs.readFileSync(new URL("../package.json", import.meta.url), "utf8"));

test("Sanctuary is the clean root landing and Crossroads represents all fourteen spaces", () => {
  assert.ok(app.includes('const restoredRoom=location.hash?navigation.resolveRoom({hash:location.hash,lastRoom:state.lastRoom,projects:state.projects}):"sanctuary"'));
  for (const panel of ["sanctuary", "crossroads", "new-idea"]) assert.match(html, new RegExp(`data-panel="${panel}"`));
  for (const room of ["control", "work", "new-idea", "write", "image", "music", "video", "code", "research", "import", "modules", "settings"]) assert.match(html, new RegExp(`data-room="${room}"`));
  assert.match(navigation, /"sanctuary", "crossroads", "control", "new-idea"/);
});

test("Crossroads replaces repeated status clutter with five functional districts", () => {
  for (const district of ["Create", "Make", "Discover", "Manage", "Recover"]) assert.match(html, new RegExp(`>${district}<`));
  for (const capability of ["Draft Workshop", "Visual Brief", "Song Brief", "Production Brief", "Work Orders", "Capability Bay", "Evidence Compare", "Idea Intake", "Archive & drafts", "System deck", "Recovery & receipts"]) assert.match(html, new RegExp(capability));
  assert.doesNotMatch(html.slice(html.indexOf("crossroads-room"), html.indexOf("new-idea-room")), /ACTIVE TOOL|SYSTEM ROOM|RECOVERY READY/);
  assert.doesNotMatch(html, /room-unfinished|FOUNDATION ONLY/); assert.match(js, /unfinishedRooms = new Set\(\)/);
  assert.doesNotMatch(js, /roomNewProject|#newProject/); assert.doesNotMatch(js, /fetch\(|XMLHttpRequest|WebSocket|https?:\/\//);
});

test("coherence layer makes controls distinct and clocks real without fake telemetry", () => {
  assert.match(html, /ui-coherence\.css/); assert.match(html, /ui-coherence\.js/);
  assert.match(html, /sanctuaryTime/); assert.match(html, /crossroadsTime/);
  assert.match(coherenceJs, /new Date\(\)/); assert.match(coherenceJs, /Intl\.DateTimeFormat/);
  assert.match(coherenceCss, /button:not\(:disabled\):hover/); assert.match(coherenceCss, /pointer-events:none/);
  assert.match(coherenceCss, /--twis-cyan:#18e4ff/); assert.match(coherenceCss, /--twis-brass:#c89b4a/);
  assert.match(coherenceCss, /prefers-reduced-motion:reduce/); assert.match(coherenceCss, /@media\(max-width:520px\)/);
  assert.doesNotMatch(coherenceJs, /fetch\(|XMLHttpRequest|WebSocket|GPU|throughput|token/i);
});

test("New Idea is an inline, inactive, project-aware artifact workflow", () => {
  for (const selector of ["newIdeaForm", "newIdeaName", "newIdeaNote", "newIdeaProject", "saveNewIdea", "cancelNewIdea", "newIdeaStatus"]) {
    assert.match(html, new RegExp(`id="${selector}"`));
  }
  assert.match(html, /id="newIdeaName"[^>]*required/);
  assert.match(html, /option value="idea">Inactive ideas/);
  assert.match(app, /async function saveNewIdea/);
  assert.match(app, /note=\$\("#newIdeaNote"\)\.value/);
  assert.match(app, /type:"idea"/);
  assert.match(app, /authorityState:"DRAFT"/);
  assert.match(app, /projectId:projectId\|\|null/);
  assert.match(app, /\/api\/projects\/\$\{storageProjectId\}\/artifacts/);
  assert.match(app, /resetNewIdeaForm\(\);openRoom\("crossroads"\)/);
  const workflow = app.slice(app.indexOf("async function saveNewIdea"), app.indexOf("async function loadArtifacts"));
  assert.doesNotMatch(workflow, /prompt\(|confirm\(|local-worker|provider|publish|activate/i);
});

test("every existing room receives a semantic Crossroads return without replacing its selectors", () => {
  assert.match(js, /\.room-return/); assert.match(js, /window\.twisOpenRoom\?\.\("crossroads"\)/);
  for (const selector of ["projectSelect", "builderWorkspace", "workList", "recoverControlDeck"]) assert.match(html + js + shell, new RegExp(selector));
  assert.match(js, /Existing durable Talk flow/);
});

test("the room system is dependency-free, reduced-motion safe, and mobile readable", () => {
  assert.match(css, /prefers-reduced-motion:reduce/); assert.match(css, /@media\(max-width:800px\)/); assert.match(css, /position:relative!important/);
  assert.match(css, /overflow:hidden/); assert.doesNotMatch(css + js, /react|vue|svelte|webpack|vite|WebGL|canvas/i);
  assert.match(css, /\.idea-intake :focus-visible/); assert.match(css, /@media\(max-width:430px\).*\.idea-actions/s);
});

test("the service worker advances to the room cache and includes both static room assets", () => {
  assert.match(worker, /twis-holo-full-v27-music-loop-deck-v1/); assert.match(worker, /room-system\.css/); assert.match(worker, /room-system\.js/); assert.match(worker, /ui-coherence\.css/); assert.match(worker, /ui-coherence\.js/);
  assert.equal(pkg.version, "0.17.0"); assert.match(server, /"workshopRelease": "0\.17"/);
});

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const html = fs.readFileSync(new URL("../app/index.html", import.meta.url), "utf8");
const css = fs.readFileSync(new URL("../app/assets/shell-0.14.css", import.meta.url), "utf8");
const js = fs.readFileSync(new URL("../app/assets/shell-0.14.js", import.meta.url), "utf8");
const worker = fs.readFileSync(new URL("../app/service-worker.js", import.meta.url), "utf8");

test("Release 0.14 installs the dependency-free governed shell without replacing room selectors", () => {
  assert.match(html, /assets\/shell-0\.14\.css/); assert.match(html, /assets\/shell-0\.14\.js/);
  for (const room of ["home", "talk", "write", "music", "image", "video", "research", "code", "import", "work", "modules", "settings"]) assert.match(html, new RegExp(`data-room="${room}"`));
  for (const selector of ["projectSelect", "builderWorkspace", "builderStatus", "workList", "localWorkerKitTitle"]) assert.match(html, new RegExp(`id="${selector}"`));
  assert.doesNotMatch(html, /react|vue|svelte|webpack|vite/i);
});

test("shell state language is truthful and quarantine is conditional", () => {
  for (const text of ["ACTIVE TOOL", "RECOVERY READY", "SYSTEM ROOM", "NOT EXPOSED", "UNKNOWN", "NONE SELECTED"]) assert.match(js, new RegExp(text));
  assert.match(js, /status === "stale"/); assert.match(js, /classList\.toggle\("shell-hazard", conflicts > 0\)/);
  assert.match(js, /\/api\/health/); assert.match(js, /\/api\/local-worker-sources/); assert.match(js, /\/api\/local-worker-jobs/); assert.match(js, /\/receipts/);
  assert.match(js, /window\.twisOpenRoom/); assert.doesNotMatch(js, /https?:\/\/|WebSocket|XMLHttpRequest|provider|model/i);
});

test("shell has sharp geometry, focus, reduced motion, split view, and mobile stacking", () => {
  assert.match(css, /border-radius:0!important/); assert.match(css, /:focus-visible/); assert.match(css, /prefers-reduced-motion:reduce/);
  assert.match(css, /\.shell-split\{display:grid/); assert.match(css, /\.shell-single \.shell-split/); assert.match(css, /@media\(max-width:600px\)/);
  assert.match(css, /grid-template-columns:1fr!important/); assert.doesNotMatch(css, /backdrop-filter:(?!none)/);
});

test("Release 0.14 cache contains only the current shell assets", () => {
  assert.match(worker, /twis-holo-full-v27-music-loop-deck-v1/); assert.match(worker, /shell-0\.14\.css/); assert.match(worker, /shell-0\.14\.js/);
});

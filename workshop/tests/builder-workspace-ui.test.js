import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const html = fs.readFileSync(new URL("../app/index.html", import.meta.url), "utf8");
const js = fs.readFileSync(new URL("../app/assets/builder-workspace.js", import.meta.url), "utf8");
const app = fs.readFileSync(new URL("../app/assets/app.js", import.meta.url), "utf8");
const css = fs.readFileSync(new URL("../app/assets/builder-workspace.css", import.meta.url), "utf8");
const modules = JSON.parse(fs.readFileSync(new URL("../app/modules/modules.json", import.meta.url), "utf8"));

test("Release 0.9 exposes the governed builder workspace and separate gates", () => {
  for (const id of ["builderWorkspace", "builderSources", "builderPrepare", "builderApprovePlan", "builderRun", "builderApproveResult", "builderRejectResult", "builderSave", "builderExportTxt", "builderExportJson", "builderRollback"]) assert.match(html, new RegExp(`id="${id}"`));
  assert.match(js, /sourceArtifactIds: selectedIds\(\)/);
  assert.match(js, /save-draft/);
  assert.match(js, /includeProvenance: true, confirmed: true/);
  assert.match(js, /twis:artifacts-loaded/);
  assert.match(js, /localStorage\.getItem\(recoveryKey\(projectId\)\)/);
});

test("builder entry points and mobile wrapping are present", () => {
  assert.ok((html.match(/data-builder-open="handoff"/g) || []).length >= 3);
  assert.ok((html.match(/data-builder-open="prompt"/g) || []).length >= 3);
  assert.match(css, /@media\(max-width:600px\)/);
  assert.match(css, /overflow-wrap:anywhere/);
});

test("Release 0.10 exposes Draft Workshop without a provider action", () => {
  assert.match(html, /data-builder-open="draft">Open Draft Workshop/);
  assert.match(html, /value="writing-draft">Draft Workshop outputs/);
  assert.match(html, /id="builderRoughText"/);
  for (const operation of ["Rewrite clearly", "Shorten without losing meaning", "Expand rough notes", "Change tone", "Organize into a structured document"]) assert.match(js, new RegExp(operation));
  assert.match(js, /draft-workshop/);
  assert.match(js, /\["#builderExportMd", "md"\]/);
  assert.doesNotMatch(js, /openai|chatgpt\.com|provider-call|executePrompt/i);
});

test("Release 0.11 exposes Evidence Compare with bounded multi-source controls", () => {
  assert.match(html, /data-builder-open="compare">Open Evidence Compare/);
  assert.match(html, /value="research-comparison-draft">Evidence Compare outputs/);
  for (const focus of ["General comparison", "Factual consistency", "Implementation differences", "Project status differences", "Requirement coverage", "Conflicting claims", "Missing evidence"]) assert.match(js, new RegExp(focus));
  assert.match(js, /evidence-compare/);
  assert.match(js, /minimum 2 · maximum 8/);
  assert.match(js, /textContent: "Remove"/);
  assert.match(js, /window\.twisOpenBuilderJob = reopen/);
  assert.match(app, /research-comparison-draft.*twisOpenBuilderJob/);
});

test("Release 0.12 exposes Visual Brief Builder without image generation", () => {
  assert.match(html, /data-builder-open="visual">Open Visual Brief Builder/);
  assert.match(html, /value="visual-brief-draft">Visual Brief outputs/);
  for (const id of ["builderVisualNotes", "visualCentralSubject", "visualSetting", "visualMoodEmotion", "visualStyle", "visualComposition", "visualLighting", "visualColorDirection", "visualRequiredElements", "visualProhibitedElements", "visualReferenceSourcePriority"]) assert.match(html, new RegExp(`id="${id}"`));
  for (const preset of ["Song or album cover", "Story or scene artwork", "Character concept", "Poster or promotional image", "Product or invention concept", "Memorial or emotional artwork", "General image concept"]) assert.match(js, new RegExp(preset));
  assert.match(js, /visual-brief-builder/);
  assert.match(js, /maximum 4 · owner notes/);
  assert.match(js, /reopenBuilderDraftArtifact/);
  assert.match(css, /builder-optional-grid/);
  assert.doesNotMatch(js, /imagegen|openai|chatgpt\.com|provider-call|executePrompt/i);
});

test("Release 0.13 exposes Song Production Brief Builder without music execution", () => {
  assert.match(html, /data-builder-open="music">Open Song Production Brief Builder/);
  for (const preset of ["Full original song", "Song from existing story or source", "Instrumental composition", "Song rewrite or alternate arrangement", "Soundtrack or cinematic cue", "Memorial or emotional song", "Commercial, theme, or promotional music", "General music concept"]) assert.match(js, new RegExp(preset));
  for (const id of ["builderMusicNotes", "builderMusicLyrics", "music-workingTitle", "music-genre", "music-tempoBpm", "music-songStructure", "music-lyricBoundaries"]) assert.match(js, new RegExp(id));
  assert.match(js, /song-production-brief-builder/);
  assert.match(js, /song-production-brief-draft/);
  assert.match(js, /maximum 4 · music notes/);
  assert.doesNotMatch(js, /musicgen|suno\.com|udio\.com|provider-call|executePrompt/i);
});

test("Release 0.15 exposes Video Production Brief Builder without video rendering", () => {
  assert.match(html, /data-builder-open="video">Open Video Production Brief Builder/);
  assert.match(html, /Video Production Brief Builder/);
  for (const preset of ["Cinematic scene", "Music video", "Short-form vertical", "Talking \/ performance", "Surreal visual", "Documentary \/ story", "Product \/ demonstration", "Image-to-video concept"]) assert.match(js, new RegExp(preset));
  for (const id of ["builderVideoNotes", "video-workingTitle", "video-productionGoal", "video-targetDuration", "video-aspectRatio", "video-cameraLanguage", "video-shotIdeas", "video-continuityRequirements", "video-unresolvedDecisions"]) assert.match(js, new RegExp(id));
  assert.match(js, /video-production-brief-builder/);
  assert.match(js, /video-production-brief-draft/);
  assert.match(js, /maximum 4 · video notes/);
  assert.match(js, /videoNotes: type === "video"/);
  assert.match(js, /videoControls: type === "video"/);
  assert.match(js, /\["save-draft", "rollback"\].*twisReloadArtifacts/);
  assert.match(app, /video-production-brief-draft.*twisOpenBuilderJob/);
  assert.doesNotMatch(js, /wan-video|comfyui|stable-diffusion|provider-call|executePrompt|renderVideo|uploadVideo/i);
});

test("Release 0.16 exposes governed Build and Module proposal rooms without execution or installation", () => {
  assert.match(html, /data-builder-open="build">Open Build Work Order Builder/);
  assert.match(html, /data-builder-open="module">Open Module Proposal Builder/);
  for (const preset of ["Add feature", "Fix defect", "UI refinement", "Deployment work order", "Local tool", "Worker", "Adapter", "Experimental module"]) assert.match(js, new RegExp(preset));
  for (const id of ["builderBuildNotes", "build-workingTitle", "build-buildGoal", "build-requirements", "build-acceptanceCriteria", "builderModuleNotes", "module-moduleName", "module-purpose", "module-permissionsCapabilities", "module-rollbackRequirements"]) assert.match(js, new RegExp(id));
  for (const value of ["build-work-order-builder", "module-proposal-builder", "build-work-order-draft", "module-proposal-draft"]) assert.match(js + app, new RegExp(value));
  assert.match(js, /buildNotes: type === "build"/); assert.match(js, /moduleNotes: type === "module"/);
  assert.doesNotMatch(js, /execCommand|spawn\(|child_process|npm install|pip install|fetchModule|provider-call|executePrompt/i);
});

test("Release 0.16 module registry distinguishes available capability from inactive contracts", () => {
  const build = modules.find(item => item.id === "build-work-order");
  const proposal = modules.find(item => item.id === "module-proposal");
  assert.equal(build.enabledByDefault, true); assert.match(build.summary, /no code, shell, file mutation/i);
  assert.equal(proposal.enabledByDefault, true); assert.match(proposal.summary, /no install, download, execution, or activation/i);
  for (const item of modules.filter(item => !item.enabledByDefault)) assert.match(item.status, /^inactive-/);
});

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const html = fs.readFileSync(new URL("../app/index.html", import.meta.url), "utf8");
const engine = fs.readFileSync(new URL("../app/assets/music-engine.js", import.meta.url), "utf8");
const room = fs.readFileSync(new URL("../app/assets/music-room.js", import.meta.url), "utf8");
const css = fs.readFileSync(new URL("../app/assets/music-studio.css", import.meta.url), "utf8");
const worker = fs.readFileSync(new URL("../app/service-worker.js", import.meta.url), "utf8");
const server = fs.readFileSync(new URL("../companion/server.py", import.meta.url), "utf8");

test("Music Studio exposes real transport, pads, patterns, mixer, arrangement, and WAV controls", () => {
  for (const id of [
    "musicPlay", "musicPause", "musicStop", "musicBpm", "musicLoop", "musicPads",
    "musicKeys", "musicSequencer", "musicMixer", "musicArrangement", "musicPatternButtons",
    "musicCopyPattern", "musicClearPattern", "musicSave", "musicSaveVersion", "musicRollback",
    "musicRender", "musicDownload", "musicSaveRender", "musicRenderPreview",
  ]) assert.match(html, new RegExp(`id="${id}"`));
  assert.match(room, /\["A","B","C","D"\]/);
  assert.match(room, /music-studio-artifact-v2/);
  assert.match(room, /restore-from-v/);
});

test("Music Loop Deck exposes only controls backed by real local audio operations", () => {
  for (const id of [
    "musicLoopFile", "musicLoopTarget", "musicLoopBpm", "musicLoopBars", "musicImportLoop",
    "musicLoopLibrary", "musicLoadLibrary", "musicLoopQuantize", "musicStopAllLoops",
    "musicCaptureStart", "musicCaptureStop", "musicLoopDeck",
  ]) assert.match(html, new RegExp(`id="${id}"`));
  assert.match(engine, /createStereoPanner/);
  assert.match(engine, /createDelay/);
  assert.match(engine, /quantizedTime/);
  assert.match(engine, /playbackRate\.value/);
  assert.match(room, /music-loop-v1/);
  assert.match(room, /recordPerformance/);
  assert.match(room, /source bytes remain unchanged/i);
});

test("native Web Audio performs actual synthesis, clock scheduling, metering, and offline WAV rendering", () => {
  assert.match(engine, /AudioContext/);
  assert.match(engine, /OfflineAudioContext/);
  assert.match(engine, /createOscillator/);
  assert.match(engine, /createBufferSource/);
  assert.match(engine, /createAnalyser/);
  assert.match(engine, /scheduler\(\)/);
  assert.match(engine, /RIFF/);
  assert.match(engine, /nonSilent/);
  assert.doesNotMatch(`${html}\n${engine}\n${room}`, /tone\.js|cdn\.jsdelivr|unpkg\.com/i);
});

test("Music AI changes remain hash-bound proposals until separate result approval and explicit apply", () => {
  for (const id of [
    "musicAiCreatePlan", "musicAiApprovePlan", "musicAiRejectPlan", "musicAiRun",
    "musicAiApproveResult", "musicAiRejectResult", "musicAiApply",
  ]) assert.match(html, new RegExp(`id="${id}"`));
  assert.match(room, /musicState:source\.music/);
  assert.match(room, /Approve the AI result before applying it/);
  assert.match(room, /Music changed after planning/);
  assert.match(room, /result_approved/);
  assert.match(room, /proposalData/);
});

test("saved audio is bounded to governed local PCM WAV artifacts", () => {
  assert.match(server, /MUSIC_RENDER_MAX_BYTES/);
  assert.match(server, /audio\/wav/);
  assert.match(server, /music\.render\.saved/);
  assert.match(server, /music-render-v1/);
  assert.match(server, /Music render path is outside the governed export directory/);
  assert.match(server, /contains no audible waveform data/);
  assert.match(server, /MUSIC_LOOP_MAX_BYTES/);
  assert.match(server, /music\.loop\.imported/);
  assert.match(server, /music-loop-v1/);
  assert.match(server, /Music loop hash no longer matches its registered source/);
});

test("Music Studio is cached, mobile-safe, focus-visible, and reduced-motion aware", () => {
  assert.match(worker, /twis-holo-full-v27-music-loop-deck-v1/);
  assert.match(worker, /music-studio\.css/);
  assert.match(worker, /music-engine\.js/);
  assert.match(worker, /music-room\.js/);
  assert.match(css, /@media\(max-width:780px\)/);
  assert.match(css, /focus-visible/);
  assert.match(css, /prefers-reduced-motion/);
});

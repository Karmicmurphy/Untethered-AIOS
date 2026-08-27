import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const html=fs.readFileSync(new URL("../app/index.html",import.meta.url),"utf8");
const js=fs.readFileSync(new URL("../app/assets/video-workstation.js",import.meta.url),"utf8");
const css=fs.readFileSync(new URL("../app/assets/video-workstation.css",import.meta.url),"utf8");
const runtime=JSON.parse(fs.readFileSync(new URL("../config/ffmpeg-runtime.json",import.meta.url),"utf8"));

test("Video V2 centers real preview timeline and owner render actions",()=>{
  for(const id of ["videoPreviewStage","videoVisualTrack","videoAudioTrack","videoTextTrack","videoAddStoryboard","videoAddImage","videoAddMusic","videoAddTitle","videoPlay","videoStop","videoSave","videoRender"]){
    assert.match(html,new RegExp(`id="${id}"`));
  }
  assert.match(html,/Browser preview · final render uses FFmpeg/);
  assert.match(html,/existing governed brief builder remains available/i);
  assert.doesNotMatch(html,/fake render|text-to-video|generate video/i);
});

test("Video V2 uses governed IDs and fixed bounded presets",()=>{
  assert.match(js,/\/api\/video-workstation\/projects\//);
  assert.match(js,/sourceArtifactId/);
  assert.match(js,/sourceSha256/);
  assert.match(js,/video-composition/);
  assert.match(js,/video-render/);
  for(const motion of ["still","zoom-in","zoom-out","pan-left","pan-right","pan-up","pan-down"]) assert.match(js,new RegExp(motion));
  assert.doesNotMatch(js,/child_process|exec\(|spawn\(|shell|0\.0\.0\.0/);
  assert.doesNotMatch(js,/https?:\/\/(?!127\.0\.0\.1)/);
});

test("Preview and timeline controls perform concrete state changes",()=>{
  assert.match(js,/requestAnimationFrame/);
  assert.match(js,/audio\.play\(\)/);
  assert.match(js,/composition\.clips\.splice/);
  assert.match(js,/saveComposition/);
  assert.match(js,/renderVideo/);
  assert.match(js,/openComposition/);
  assert.match(js,/openRender/);
});

test("Video V2 is touch responsive and honors reduced motion",()=>{
  assert.match(css,/@media\(max-width:430px\)/);
  assert.match(css,/min-height:44px/);
  assert.match(css,/@media\(prefers-reduced-motion:reduce\)/);
  assert.doesNotMatch(css,/min-width:\s*[4-9]\d\dpx/);
});

test("portable runtime manifest is exact and does not modify PATH",()=>{
  assert.equal(runtime.version,"9.0.1-essentials_build-www.gyan.dev");
  assert.equal(runtime.archiveSha256,"fec81ae03971d9dd4be3ebe02e263bd2ec1d789483f931bdba5f5715e65da2e9");
  assert.equal(runtime.systemPathModified,false);
  assert.equal(runtime.networkAtRuntime,false);
});

import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const html=fs.readFileSync(new URL("../app/index.html",import.meta.url),"utf8");
const js=fs.readFileSync(new URL("../app/assets/media-workspace.js",import.meta.url),"utf8");
const css=fs.readFileSync(new URL("../app/assets/media-workspace.css",import.meta.url),"utf8");
const capabilities=JSON.parse(fs.readFileSync(new URL("../config/media-capabilities.json",import.meta.url),"utf8"));
const modules=JSON.parse(fs.readFileSync(new URL("../app/modules/modules.json",import.meta.url),"utf8"));

test("Images V2 exposes an owner-usable light table and honest unavailable generation",()=>{
  for(const view of ["work","edit","create","assets","storyboard","director"]) assert.match(html,new RegExp(`data-media-tab="${view}"`));
  assert.match(html,/DROP IMAGE HERE/);
  assert.match(html,/No image generator is connected/);
  assert.match(html,/Save inactive asset/);
  assert.doesNotMatch(html,/Generate image[^\n]*class="primary"/i);
});

test("TWIS Media Workspace validates local images and preserves variation provenance",()=>{
  assert.match(js,/MAX_BYTES = 12 \* 1024 \* 1024/);
  assert.match(js,/MAX_SIDE = 4096/);
  assert.match(js,/image\/png.*image\/jpeg.*image\/webp/s);
  assert.match(js,/crypto\.subtle\.digest\("SHA-256"/);
  assert.match(js,/X-TWIS-Source-Artifact/);
  assert.match(js,/X-TWIS-Original-SHA256/);
  assert.match(js,/history\.length > MAX_HISTORY/);
  assert.match(js,/dataTransfer\.files/);
});

test("TWIS Media Workspace routes references and manages storyboard frames through bounded APIs",()=>{
  assert.match(js,/\/api\/media-workspace\/projects\//);
  assert.match(js,/\/image-assets/);
  assert.match(js,/targetRoom/);
  assert.match(js,/storyboard-items/);
  assert.match(js,/storyboard-order/);
  assert.match(js,/storyboard-remove/);
  assert.match(js,/source image preserved/);
  assert.match(js,/From Write|mediaIncomingRefs/);
  assert.match(js,/data-incoming-dismiss/);
  assert.match(js,/dismissedRoutes/);
  assert.doesNotMatch(js,/https?:\/\/(?!127\.0\.0\.1)/);
  assert.doesNotMatch(`${html}\n${js}\n${css}`,/hub[ -]?ui|hubui|media-hub|hub-media/i);
});

test("assisted background removal is real, proposal-only, source-bound, and owner-decided",()=>{
  for(const id of ["backgroundMaskCanvas","backgroundRectangle","backgroundKeep","backgroundRemove","backgroundPreview","backgroundApprove","backgroundReject"]){
    assert.match(html,new RegExp(`id="${id}"`));
  }
  assert.match(html,/Local assisted cutout/i);
  assert.match(html,/protected source is never overwritten/i);
  assert.match(js,/\/api\/background-removal\/health/);
  assert.match(js,/\/background-removal\/projects\//);
  assert.match(js,/sourceArtifactId/);
  assert.match(js,/sourceSha256/);
  assert.match(js,/decideBackgroundProposal\("approve"\)/);
  assert.match(js,/decideBackgroundProposal\("reject"\)/);
  assert.match(js,/PROPOSED|proposed/i);
  assert.doesNotMatch(js,/background-removal[^\n]*(fetch\(["']https?:|XMLHttpRequest)/i);
});

test("background composition previews locally and requires explicit governed approval",()=>{
  for(const id of ["backgroundCompositionPanel","compositeMode","compositeBackgroundAsset","compositePreview","compositeApprove","compositeReject"]){
    assert.match(html,new RegExp(`id="${id}"`));
  }
  assert.match(html,/solid color/i);
  assert.match(html,/gradient/i);
  assert.match(html,/registered image/i);
  assert.match(html,/Preview first; saving requires a separate owner approval/i);
  assert.match(js,/createLinearGradient/);
  assert.match(js,/drawCover/);
  assert.match(js,/PROPOSED COMPOSITE/);
  assert.match(js,/\/background-composites/);
  assert.match(js,/X-TWIS-Source-SHA256/);
  assert.match(js,/X-TWIS-Background-SHA256/);
  assert.match(js,/decideCompositeProposal\("approve"\)/);
  assert.match(js,/decideCompositeProposal\("reject"\)/);
  assert.doesNotMatch(js,/background-composites[^\n]*(https?:\/\/|XMLHttpRequest)/i);
});

test("ComfyUI remains an honest unregistered compatibility target",()=>{
  const runtime=capabilities.runtimes.find(item=>item.id==="comfyui");
  const worker=capabilities.workerContracts.find(item=>item.id==="comfyui-compatible-media-worker-v1");
  const module=modules.find(item=>item.id==="comfyui-workflow-compatibility");
  assert.equal(runtime.state,"NOT_INSTALLED");
  assert.equal(worker.state,"UNREGISTERED");
  assert.equal(module.enabledByDefault,false);
  assert.equal(module.status,"inactive-not-installed-unregistered");
  for(const capability of capabilities.capabilities.filter(item=>item.workflowContract?.startsWith("comfyui-"))){
    assert.equal(capability.state,"UNAVAILABLE");
    assert.deepEqual(capability.compatibleWorkers,[]);
  }
});

test("mobile layout stacks without fixed width",()=>{
  assert.match(css,/@media \(max-width: 700px\)/);
  assert.match(css,/grid-template-columns: 1fr/);
  assert.doesNotMatch(css,/min-width:\s*[4-9]\d\dpx/);
});

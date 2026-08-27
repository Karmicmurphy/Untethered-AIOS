(() => {
  "use strict";
  const $ = selector => document.querySelector(selector);
  const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[char]);
  const clone = value => JSON.parse(JSON.stringify(value));
  let summary = { items: [], runtime: {} };
  let composition = blank();
  let selected = null;
  let playing = false;
  let playStarted = 0;
  let playOffset = 0;
  let animationFrame = 0;

  function blank() {
    return { id: "", title: "Untitled video composition", sceneId: "", clips: [], audio: null, titles: [], render: { size: "720p", quality: "standard" } };
  }
  function projectId() { return window.twisGetActiveProject?.() || ""; }
  async function json(url, options = {}) {
    const response = await fetch(url, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `Video request failed (${response.status})`);
    return data;
  }
  function setStatus(message, state = "idle") {
    const element = $("#videoStatus");
    if (!element) return;
    element.textContent = message;
    element.dataset.state = state;
  }
  function items(kind) { return summary.items.filter(item => item.kind === kind); }
  function item(id) { return summary.items.find(value => value.id === id); }
  function imageUrl(id) { return `/api/media-assets/${encodeURIComponent(id)}`; }
  function audioUrl(id) { return `/api/music-renders/${encodeURIComponent(id)}`; }
  function videoUrl(id) { return `/api/video-renders/${encodeURIComponent(id)}`; }
  function shortHash(value) { return (value || "unknown").slice(0, 12); }
  function totalDuration() {
    return Math.max(0, composition.clips.reduce((total, clip, index) => total + Number(clip.durationSeconds || 0) - (index && clip.transition === "crossfade" ? .5 : 0), 0));
  }
  function clipAt(time) {
    let cursor = 0;
    for (let index = 0; index < composition.clips.length; index += 1) {
      const clip = composition.clips[index];
      const start = cursor;
      const end = start + Number(clip.durationSeconds || 0);
      if (time < end || index === composition.clips.length - 1) return { clip, index, local: Math.max(0, time - start) };
      cursor = end - (composition.clips[index + 1]?.transition === "crossfade" ? .5 : 0);
    }
    return null;
  }
  function titleAt(time) {
    return composition.titles.find(title => time >= Number(title.startSeconds || 0) && time < Number(title.startSeconds || 0) + Number(title.durationSeconds || 0));
  }
  function formatTime(seconds) {
    const safe = Math.max(0, Number(seconds) || 0);
    return `${String(Math.floor(safe / 60)).padStart(2, "0")}:${(safe % 60).toFixed(1).padStart(4, "0")}`;
  }
  function currentPayload() {
    return {
      title: $("#videoCompositionTitle").value,
      sceneId: $("#videoSceneSelect").value,
      clips: clone(composition.clips),
      audio: composition.audio ? {
        ...clone(composition.audio),
        volume: Number($("#videoAudioVolume").value),
        startSeconds: Number($("#videoAudioStart").value),
        fadeInSeconds: Number($("#videoAudioFadeIn").value),
        fadeOutSeconds: Number($("#videoAudioFadeOut").value),
        muted: $("#videoAudioMuted").checked,
      } : null,
      titles: clone(composition.titles),
      size: $("#videoRenderSize").value,
      quality: $("#videoRenderQuality").value,
    };
  }

  function setPreview(time) {
    const stage = $("#videoPreviewStage");
    const image = $("#videoPreviewImage");
    const active = clipAt(time);
    stage.className = "video-preview-stage";
    if (active) {
      stage.classList.add("has-media", `preview-${active.clip.motion || "still"}`);
      if (active.clip.transition === "crossfade" && active.local < .5) stage.classList.add("preview-crossfade");
      stage.style.setProperty("--clip-duration", `${active.clip.durationSeconds}s`);
      if (image.dataset.artifactId !== active.clip.sourceArtifactId) {
        image.dataset.artifactId = active.clip.sourceArtifactId;
        image.src = imageUrl(active.clip.sourceArtifactId);
      }
    } else {
      image.removeAttribute("src");
      image.dataset.artifactId = "";
    }
    const title = titleAt(time);
    const titleElement = $("#videoPreviewTitle");
    titleElement.textContent = title?.text || "";
    titleElement.dataset.position = title?.position || "center";
    titleElement.style.fontSize = title ? `${Math.max(24, Math.min(96, Number(title.size || 52)))}px` : "";
    titleElement.style.opacity = title ? "1" : "0";
    titleElement.classList.toggle("video-title-on", Boolean(title));
    $("#videoTimeReadout").textContent = `${formatTime(time)} / ${formatTime(totalDuration())}`;
    const width = $("#videoVisualTrack").clientWidth || 1;
    $("#videoPlayhead").style.translate = `${Math.min(width, width * (time / Math.max(totalDuration(), .001)))}px 0`;
  }

  function stopPreview(reset = true) {
    playing = false;
    cancelAnimationFrame(animationFrame);
    const audio = $("#videoPreviewAudio");
    audio.pause();
    if (reset) playOffset = 0;
    setPreview(playOffset);
  }
  async function playPreview() {
    if (!composition.clips.length) return setStatus("Add at least one visual before previewing.", "failed");
    stopPreview(false);
    const duration = totalDuration();
    if (playOffset >= duration) playOffset = 0;
    playing = true;
    playStarted = performance.now() - playOffset * 1000;
    const audio = $("#videoPreviewAudio");
    if (composition.audio && !$("#videoAudioMuted").checked) {
      audio.src = audioUrl(composition.audio.sourceArtifactId);
      audio.volume = Math.min(1, Number($("#videoAudioVolume").value));
      const requested = Math.max(0, playOffset - Number($("#videoAudioStart").value || 0) + Number(composition.audio.trimStartSeconds || 0));
      try { audio.currentTime = requested; await audio.play(); } catch { setStatus("Visual preview is running; the browser held audio until another owner gesture."); }
    }
    setStatus("Preview playing. Final render may differ slightly from this browser preview.", "rendering");
    const tick = now => {
      if (!playing) return;
      playOffset = (now - playStarted) / 1000;
      if (playOffset >= duration) { stopPreview(); setStatus("Preview complete.", "complete"); return; }
      setPreview(playOffset);
      animationFrame = requestAnimationFrame(tick);
    };
    animationFrame = requestAnimationFrame(tick);
  }

  function sourceCard(source, buttonText, action, image = false) {
    return `<article class="video-source-card">${image ? `<img loading="lazy" src="${imageUrl(source.id)}" alt="">` : "<span aria-hidden='true'>◇</span>"}<div><b>${esc(source.title)}</b><small>${esc(source.kind)} · ${esc(shortHash(source.sha256))}</small></div><button class="quiet" data-video-source-action="${esc(action)}" data-video-source-id="${esc(source.id)}">${esc(buttonText)}</button></article>`;
  }
  function renderSources() {
    const images = items("image");
    const boards = [...items("storyboard-item")].sort((a, b) => Number(a.payload?.order || 999) - Number(b.payload?.order || 999));
    const music = items("music-render");
    const writing = summary.items.filter(value => ["document", "writing-draft"].includes(value.kind) || (value.kind === "media-route" && value.payload?.targetRoom === "video"));
    $("#videoStoryboardSources").innerHTML = boards.length ? boards.map(board => {
      const source = item(board.payload?.primaryImageId);
      return source ? sourceCard({...source, title: board.title}, "Add frame", `board:${board.id}`, true) : "";
    }).join("") : "<p class='muted'>No Images V2 storyboard frames in this project.</p>";
    $("#videoImageSources").innerHTML = images.length ? images.map(source => sourceCard(source, "Add visual", "image", true)).join("") : "<p class='muted'>No governed Images V2 assets.</p>";
    $("#videoMusicSources").innerHTML = music.length ? music.map(source => sourceCard(source, "Use music", "music")).join("") : "<p class='muted'>No governed Music Studio WAV renders.</p>";
    $("#videoWritingSources").innerHTML = writing.length ? writing.map(source => sourceCard(source, "Use as title", "writing")).join("") : "<p class='muted'>No eligible writing or routed context.</p>";
    document.querySelectorAll("[data-video-source-action]").forEach(button => button.onclick = () => addSource(button.dataset.videoSourceId, button.dataset.videoSourceAction));
  }
  function addSource(id, action) {
    if (action.startsWith("board:")) {
      const board = item(action.split(":")[1]);
      const source = item(board?.payload?.primaryImageId);
      if (source) addClip(source, board);
    } else if (action === "image") addClip(item(id));
    else if (action === "music") setMusic(item(id));
    else if (action === "writing") addWritingTitle(item(id));
  }
  function addClip(source, board = null) {
    if (!source || composition.clips.length >= 24) return setStatus("The bounded timeline accepts at most 24 visuals.", "failed");
    composition.clips.push({
      sourceArtifactId: source.id,
      sourceSha256: source.sha256,
      storyboardItemId: board?.id || null,
      title: source.title,
      durationSeconds: Number(board?.payload?.durationSeconds || 4),
      motion: "still",
      transition: /dissolve|crossfade/.test(String(board?.payload?.transitionNotes || "").toLowerCase()) ? "crossfade" : "cut",
    });
    selected = { type: "clip", index: composition.clips.length - 1 };
    render();
    setStatus(`${source.title} added by reference. The source was not copied or changed.`);
  }
  function setMusic(source) {
    if (!source) return;
    composition.audio = { sourceArtifactId: source.id, sourceSha256: source.sha256, title: source.title, startSeconds: 0, trimStartSeconds: 0, volume: 1, fadeInSeconds: 0, fadeOutSeconds: 0, muted: false };
    $("#videoPreviewAudio").src = audioUrl(source.id);
    render();
    setStatus(`${source.title} attached by reference. The Music render remains unchanged.`);
  }
  function writingText(source) {
    if (source.kind === "media-route") {
      const routed = item(source.payload?.sourceArtifactId);
      return routed ? writingText(routed) : source.title;
    }
    const payload = source.payload || {};
    return String(payload.text || payload.body || payload.content || payload.plainText || source.title).slice(0, 500);
  }
  function addWritingTitle(source) {
    const actual = source.kind === "media-route" ? item(source.payload?.sourceArtifactId) || source : source;
    composition.titles.push({ text: writingText(source), startSeconds: 0, durationSeconds: 3, position: "center", size: 52, fade: true, sourceArtifactId: actual.id, sourceSha256: actual.sha256 || source.payload?.sourceSha256 || null });
    selected = { type: "title", index: composition.titles.length - 1 };
    render();
    setStatus("Writing was referenced as editable Video title text. The writing source remains unchanged.");
  }

  function renderInspector() {
    const target = $("#videoClipInspector");
    if (!selected) { target.innerHTML = "<h3>Selected item</h3><p class='muted'>Select a visual or title in the timeline.</p>"; return; }
    if (selected.type === "clip") {
      const clip = composition.clips[selected.index];
      if (!clip) { selected = null; return renderInspector(); }
      target.innerHTML = `<h3>${esc(clip.title)}</h3><label>Duration seconds<input id="videoClipDuration" type="number" min="0.5" max="60" step="0.5" value="${esc(clip.durationSeconds)}"></label><label>Motion<select id="videoClipMotion">${["still","zoom-in","zoom-out","pan-left","pan-right","pan-up","pan-down"].map(value => `<option value="${value}" ${clip.motion === value ? "selected" : ""}>${value.replaceAll("-", " ")}</option>`).join("")}</select></label><label>Transition into clip<select id="videoClipTransition"><option value="cut" ${clip.transition === "cut" ? "selected" : ""}>Cut</option><option value="crossfade" ${clip.transition === "crossfade" ? "selected" : ""}>Crossfade</option></select></label><div class="video-inspector-actions"><button data-clip-action="earlier">Earlier</button><button data-clip-action="later">Later</button><button data-clip-action="duplicate">Duplicate</button><button class="danger" data-clip-action="remove">Remove</button></div><small>Removing this clip never deletes its source image.</small>`;
      $("#videoClipDuration").onchange = event => { clip.durationSeconds = Math.max(.5, Math.min(60, Number(event.target.value) || 4)); render(); };
      $("#videoClipMotion").onchange = event => { clip.motion = event.target.value; render(); };
      $("#videoClipTransition").onchange = event => { clip.transition = event.target.value; render(); };
      target.querySelectorAll("[data-clip-action]").forEach(button => button.onclick = () => clipAction(button.dataset.clipAction));
    } else {
      const title = composition.titles[selected.index];
      if (!title) { selected = null; return renderInspector(); }
      target.innerHTML = `<h3>Title overlay</h3><label>Text<textarea id="videoTitleText" rows="4" maxlength="500">${esc(title.text)}</textarea></label><label>Start seconds<input id="videoTitleStart" type="number" min="0" max="300" step="0.1" value="${esc(title.startSeconds)}"></label><label>Duration seconds<input id="videoTitleDuration" type="number" min="0.25" max="300" step="0.25" value="${esc(title.durationSeconds)}"></label><label>Position<select id="videoTitlePosition"><option value="top" ${title.position === "top" ? "selected" : ""}>Top</option><option value="center" ${title.position === "center" ? "selected" : ""}>Center</option><option value="bottom" ${title.position === "bottom" ? "selected" : ""}>Bottom</option></select></label><label>Size<input id="videoTitleSize" type="number" min="24" max="96" value="${esc(title.size)}"></label><label class="check"><input id="videoTitleFade" type="checkbox" ${title.fade ? "checked" : ""}> Fade title</label><button id="videoRemoveTitle" class="danger">Remove title</button>`;
      const update = () => { Object.assign(title, { text: $("#videoTitleText").value, startSeconds: Number($("#videoTitleStart").value), durationSeconds: Number($("#videoTitleDuration").value), position: $("#videoTitlePosition").value, size: Number($("#videoTitleSize").value), fade: $("#videoTitleFade").checked }); render(false); };
      ["#videoTitleText", "#videoTitleStart", "#videoTitleDuration", "#videoTitlePosition", "#videoTitleSize", "#videoTitleFade"].forEach(selector => $(selector).oninput = update);
      $("#videoRemoveTitle").onclick = () => { composition.titles.splice(selected.index, 1); selected = null; render(); };
    }
  }
  function clipAction(action) {
    const index = selected.index;
    if (action === "remove") { composition.clips.splice(index, 1); selected = null; }
    if (action === "duplicate" && composition.clips.length < 24) { composition.clips.splice(index + 1, 0, clone(composition.clips[index])); selected.index += 1; }
    if (action === "earlier" && index > 0) { [composition.clips[index - 1], composition.clips[index]] = [composition.clips[index], composition.clips[index - 1]]; selected.index -= 1; }
    if (action === "later" && index < composition.clips.length - 1) { [composition.clips[index + 1], composition.clips[index]] = [composition.clips[index], composition.clips[index + 1]]; selected.index += 1; }
    render();
  }

  function renderTimeline() {
    $("#videoVisualTrack").innerHTML = composition.clips.length ? composition.clips.map((clip, index) => `<button class="video-clip" data-video-clip="${index}" aria-selected="${selected?.type === "clip" && selected.index === index}"><img loading="lazy" src="${imageUrl(clip.sourceArtifactId)}" alt=""><span><b>${esc(clip.title)}</b><small>${esc(clip.durationSeconds)}s · ${esc(clip.motion)} · ${esc(clip.transition)}</small></span></button>`).join("") : "<p class='muted'>No visual clips.</p>";
    $("#videoAudioTrack").innerHTML = composition.audio ? `<button class="video-audio-chip" data-video-open-music><b>${esc(composition.audio.title)}</b><small>${esc(shortHash(composition.audio.sourceSha256))}</small></button>` : "<p class='muted'>No music selected.</p>";
    $("#videoTextTrack").innerHTML = composition.titles.length ? composition.titles.map((title, index) => `<button class="video-title-chip" data-video-title="${index}" aria-selected="${selected?.type === "title" && selected.index === index}"><b>${esc(title.text || "Untitled")}</b><small>${esc(title.startSeconds)}s for ${esc(title.durationSeconds)}s</small></button>`).join("") : "<p class='muted'>No titles.</p>";
    $("#videoClipCount").textContent = `${composition.clips.length} VISUAL${composition.clips.length === 1 ? "" : "S"}`;
    $("#videoDuration").textContent = `${totalDuration().toFixed(1)} SECONDS`;
    document.querySelectorAll("[data-video-clip]").forEach(button => button.onclick = () => { selected = { type: "clip", index: Number(button.dataset.videoClip) }; render(); });
    document.querySelectorAll("[data-video-title]").forEach(button => button.onclick = () => { selected = { type: "title", index: Number(button.dataset.videoTitle) }; render(); });
    const music = $("[data-video-open-music]");
    if (music) music.onclick = () => $("#videoAudioPanel").open = true;
  }
  function renderSaved() {
    const compositions = items("video-composition");
    const outputs = items("video-render");
    $("#videoSavedWork").innerHTML = [
      ...compositions.map(value => `<article class="video-source-card"><span>◆</span><div><b>${esc(value.title)}</b><small>Inactive composition · ${esc(shortHash(value.sha256))}</small></div><button data-video-open-composition="${esc(value.id)}">Open composition</button></article>`),
      ...outputs.map(value => `<article class="video-source-card"><span>▶</span><div><b>${esc(value.title)}</b><small>Inactive MP4 · ${esc(shortHash(value.sha256))}</small></div><button data-video-open-render="${esc(value.id)}">Play rendered output</button></article>`),
    ].join("") || "<p class='muted'>No saved Video compositions or renders.</p>";
    document.querySelectorAll("[data-video-open-composition]").forEach(button => button.onclick = () => openComposition(item(button.dataset.videoOpenComposition)));
    document.querySelectorAll("[data-video-open-render]").forEach(button => button.onclick = () => openRender(item(button.dataset.videoOpenRender)));
  }
  function render(refreshInspector = true) {
    $("#videoCompositionTitle").value = composition.title || "Untitled video composition";
    $("#videoSceneSelect").value = composition.sceneId || "";
    $("#videoRenderSize").value = composition.render?.size || "720p";
    $("#videoRenderQuality").value = composition.render?.quality || "standard";
    if (composition.audio) {
      $("#videoAudioVolume").value = composition.audio.volume ?? 1;
      $("#videoAudioStart").value = composition.audio.startSeconds ?? 0;
      $("#videoAudioFadeIn").value = composition.audio.fadeInSeconds ?? 0;
      $("#videoAudioFadeOut").value = composition.audio.fadeOutSeconds ?? 0;
      $("#videoAudioMuted").checked = Boolean(composition.audio.muted);
    }
    renderTimeline();
    if (refreshInspector) renderInspector();
    renderSaved();
    setPreview(Math.min(playOffset, totalDuration()));
  }
  function openComposition(source) {
    if (!source?.payload) return;
    stopPreview();
    composition = { id: source.id, title: source.title, sceneId: source.payload.sceneId || "", clips: clone(source.payload.clips || []), audio: clone(source.payload.audio || null), titles: clone(source.payload.titles || []), render: clone(source.payload.render || { size: "720p", quality: "standard" }) };
    selected = composition.clips.length ? { type: "clip", index: 0 } : null;
    $("#videoRenderedOutput").hidden = true;
    render();
    setStatus("Inactive composition reopened. Source hashes will be revalidated before save or render.");
  }
  function openRender(source) {
    if (!source) return;
    stopPreview();
    const output = $("#videoRenderedOutput");
    output.src = videoUrl(source.id);
    output.hidden = false;
    output.load();
    setStatus(`Opened governed rendered output ${shortHash(source.sha256)}.`, "complete");
  }

  async function saveComposition() {
    if (!composition.clips.length) throw new Error("Add at least one visual before saving.");
    composition.title = $("#videoCompositionTitle").value;
    composition.sceneId = $("#videoSceneSelect").value;
    composition.render = { size: $("#videoRenderSize").value, quality: $("#videoRenderQuality").value };
    const result = await json(`/api/video-workstation/projects/${encodeURIComponent(projectId())}/compositions`, { method: "POST", body: JSON.stringify(currentPayload()) });
    composition.id = result.artifact.id;
    await window.twisReloadArtifacts?.();
    await refresh();
    setStatus(`Inactive composition saved · ${shortHash(result.artifact.sha256)}.`, "complete");
    return result.artifact;
  }
  async function renderVideo() {
    const button = $("#videoRender");
    try {
      button.disabled = true;
      stopPreview(false);
      setStatus("Preparing and rendering locally. TWIS remains responsive in other tabs.", "rendering");
      const saved = await saveComposition();
      setStatus("Rendering locally with the fixed FFmpeg plan…", "rendering");
      const result = await json(`/api/video-workstation/projects/${encodeURIComponent(projectId())}/renders`, { method: "POST", body: JSON.stringify({ compositionId: saved.id }) });
      await window.twisReloadArtifacts?.();
      await refresh();
      openRender(result.artifact);
      setStatus(`Render complete in ${result.renderSeconds}s · ${result.artifact.payload.width}×${result.artifact.payload.height} · ${shortHash(result.artifact.sha256)}.`, "complete");
    } catch (error) { setStatus(error.message, "failed"); }
    finally { button.disabled = false; }
  }

  async function refresh() {
    if (!$("#videoWorkstation") || !projectId()) return;
    try {
      summary = await json(`/api/video-workstation/projects/${encodeURIComponent(projectId())}`);
      const runtime = summary.runtime || {};
      $("#videoRuntimeState").textContent = runtime.available ? "LOCAL RENDERER AVAILABLE" : "RENDERER UNAVAILABLE";
      $("#videoRuntimeState").dataset.state = runtime.available ? "ready" : "error";
      $("#videoRuntimeDetail").textContent = runtime.available ? "FFmpeg registered locally · no provider" : (runtime.reason || "No registered renderer");
      const sceneValue = composition.sceneId || $("#videoSceneSelect").value;
      $("#videoSceneSelect").innerHTML = `<option value="">No scene reference</option>${items("scene").map(scene => `<option value="${esc(scene.id)}">${esc(scene.title)}</option>`).join("")}`;
      $("#videoSceneSelect").value = items("scene").some(scene => scene.id === sceneValue) ? sceneValue : "";
      renderSources();
      render();
    } catch (error) { setStatus(error.message, "failed"); }
  }

  function bind() {
    $("#videoAddStoryboard").onclick = () => {
      const boards = [...items("storyboard-item")].sort((a, b) => Number(a.payload?.order || 999) - Number(b.payload?.order || 999));
      if (!boards.length) { $("#videoStoryboardBay").open = true; return setStatus("No storyboard frames are available in this project.", "failed"); }
      for (const board of boards) {
        const source = item(board.payload?.primaryImageId);
        if (source && composition.clips.length < 24 && !composition.clips.some(clip => clip.storyboardItemId === board.id)) addClip(source, board);
      }
      setStatus("Storyboard frames added by reference. The Images storyboard remains unchanged.");
    };
    $("#videoAddImage").onclick = () => { $("#videoImageBay").open = true; $("#videoImageBay").scrollIntoView({block:"nearest"}); };
    $("#videoAddMusic").onclick = () => { $("#videoMusicBay").open = true; $("#videoMusicBay").scrollIntoView({block:"nearest"}); };
    $("#videoAddTitle").onclick = () => { composition.titles.push({text:"Title",startSeconds:0,durationSeconds:3,position:"center",size:52,fade:true,sourceArtifactId:null,sourceSha256:null}); selected={type:"title",index:composition.titles.length-1}; render(); };
    $("#videoPlay").onclick = playPreview;
    $("#videoStop").onclick = () => { stopPreview(); setStatus("Preview stopped."); };
    $("#videoSave").onclick = () => saveComposition().catch(error => setStatus(error.message, "failed"));
    $("#videoRender").onclick = renderVideo;
    $("#videoCompositionTitle").oninput = event => { composition.title = event.target.value; };
    $("#videoSceneSelect").onchange = event => { composition.sceneId = event.target.value; };
    ["#videoAudioVolume", "#videoAudioStart", "#videoAudioFadeIn", "#videoAudioFadeOut", "#videoAudioMuted"].forEach(selector => $(selector).oninput = () => { if (composition.audio) composition.audio = currentPayload().audio; renderTimeline(); });
    ["#videoRenderSize", "#videoRenderQuality"].forEach(selector => $(selector).onchange = () => { composition.render = {size:$("#videoRenderSize").value,quality:$("#videoRenderQuality").value}; });
    window.addEventListener("twis:artifacts-loaded", () => refresh());
    document.addEventListener("click", event => {
      const room = event.target.closest?.("[data-room]")?.dataset.room;
      if (room === "video") setTimeout(refresh, 0);
    }, true);
  }
  window.twisVideoWorkstation = { onRoomOpen: refresh, openArtifact(source) { if (source?.type === "video-composition") openComposition({ ...source, kind: source.type, payload: source.data, sha256: source.sha256 }); else if (source?.type === "video-render") openRender({ ...source, kind: source.type, payload: source.data, sha256: source.sha256 }); }, refresh };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => { bind(); refresh(); });
  else { bind(); refresh(); }
})();

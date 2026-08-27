(() => {
  "use strict";

  const MAX_BYTES = 12 * 1024 * 1024;
  const MAX_SIDE = 4096;
  const MAX_HISTORY = 5;
  const ACCEPTED = new Set(["image/png", "image/jpeg", "image/webp"]);
  const $ = selector => document.querySelector(selector);
  const $$ = selector => [...document.querySelectorAll(selector)];
  const host = () => window.twisMediaHost || window.twisMusicHost;

  let summary = { items: [] };
  let currentImageId = "";
  let currentSourceHash = "";
  let originalInputHash = "";
  let sourceUrl = "";
  let importedUrl = "";
  let drawing = false;
  let drawMode = false;
  let lastPoint = null;
  let history = [];
  let backgroundRuntime = null;
  let backgroundMode = "";
  let backgroundRectangle = null;
  let backgroundStrokes = [];
  let backgroundPointerStart = null;
  let pendingBackgroundProposal = null;
  let pendingCompositeProposal = null;
  let pendingCompositeUrl = "";
  const dismissedRoutes = new Set();

  function escapeHtml(value) {
    const node = document.createElement("span");
    node.textContent = String(value || "");
    return node.innerHTML;
  }

  function itemList(kinds) {
    return summary.items.filter(item => kinds.includes(item.kind));
  }

  function imageUrl(item) {
    return item?.payload?.schemaVersion === "twis-media-asset-v1"
      ? `/api/media-assets/${encodeURIComponent(item.id)}`
      : item?.payload?.png || "";
  }

  async function json(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
    return data;
  }

  function status(message, isError = false) {
    const element = $("#mediaCanvasStatus");
    if (element) {
      element.textContent = message;
      element.classList.toggle("media-error", isError);
    }
  }

  function toast(message) {
    host()?.toast?.(message);
  }

  function option(item) {
    return `<option value="${escapeHtml(item.id)}">${escapeHtml(item.title)} · ${escapeHtml((item.sha256 || item.id).slice(0, 10))}</option>`;
  }

  function canvas() {
    return $("#imageCanvas");
  }

  function setImageControls(enabled) {
    ["#saveImage", "#exportPng", "#compareImage"].forEach(selector => {
      const button = $(selector);
      if (button) button.disabled = !enabled;
    });
    $("#undoImage").disabled = !enabled || history.length === 0;
    $("#mediaEmptyState").hidden = enabled;
  }

  function backgroundCanvas() {
    return $("#backgroundMaskCanvas");
  }

  function syncBackgroundOverlay() {
    const overlay = backgroundCanvas();
    const work = canvas();
    if (!overlay || !work) return;
    overlay.width = work.width;
    overlay.height = work.height;
    const stageRect = $("#mediaStage").getBoundingClientRect();
    const workRect = work.getBoundingClientRect();
    overlay.style.left = (workRect.left - stageRect.left) + "px";
    overlay.style.top = (workRect.top - stageRect.top) + "px";
    overlay.style.width = workRect.width + "px";
    overlay.style.height = workRect.height + "px";
    redrawBackgroundOverlay();
  }

  function redrawBackgroundOverlay(transientRectangle = null) {
    const overlay = backgroundCanvas();
    if (!overlay) return;
    const context = overlay.getContext("2d");
    context.clearRect(0, 0, overlay.width, overlay.height);
    const rectangle = transientRectangle || backgroundRectangle;
    if (rectangle) {
      context.save();
      context.strokeStyle = "#38e8ff";
      context.lineWidth = Math.max(2, overlay.width / 500);
      context.setLineDash([10, 7]);
      context.fillStyle = "rgba(20, 227, 255, .09)";
      context.fillRect(rectangle.x * overlay.width, rectangle.y * overlay.height, rectangle.width * overlay.width, rectangle.height * overlay.height);
      context.strokeRect(rectangle.x * overlay.width, rectangle.y * overlay.height, rectangle.width * overlay.width, rectangle.height * overlay.height);
      context.restore();
    }
    for (const stroke of backgroundStrokes) {
      context.beginPath();
      context.fillStyle = stroke.mode === "keep" ? "rgba(73, 255, 153, .82)" : "rgba(255, 78, 91, .82)";
      context.arc(stroke.x * overlay.width, stroke.y * overlay.height, stroke.radius * Math.max(overlay.width, overlay.height), 0, Math.PI * 2);
      context.fill();
    }
  }

  function setBackgroundMode(mode) {
    backgroundMode = mode;
    drawMode = false;
    $("#drawToggle").textContent = "Draw off";
    $("#drawToggle").setAttribute("aria-pressed", "false");
    $("#mediaStage").classList.toggle("is-masking", Boolean(mode));
    const overlay = backgroundCanvas();
    overlay.hidden = !mode;
    overlay.style.pointerEvents = mode ? "auto" : "none";
    for (const [selector, value] of [["#backgroundRectangle", "rectangle"], ["#backgroundKeep", "keep"], ["#backgroundRemove", "remove"]]) {
      $(selector).setAttribute("aria-pressed", String(mode === value));
    }
    redrawBackgroundOverlay();
  }

  function resetBackgroundState(restoreSource = true) {
    backgroundRectangle = null;
    backgroundStrokes = [];
    backgroundPointerStart = null;
    pendingBackgroundProposal = null;
    setBackgroundMode("");
    $("#backgroundProposalActions").hidden = true;
    $("#mediaCompare").hidden = true;
    if (restoreSource && sourceUrl) loadImage(sourceUrl, { id: currentImageId, sha256: currentSourceHash, originalInputHash });
    updateBackgroundControls();
  }

  function updateBackgroundControls() {
    const ready = backgroundRuntime?.state === "HEALTHY";
    const registered = Boolean(currentImageId && currentSourceHash);
    const proposal = Boolean(pendingBackgroundProposal);
    const locked = proposal || Boolean(pendingCompositeProposal);
    $("#backgroundRectangle").disabled = !ready || !registered || locked;
    $("#backgroundKeep").disabled = !ready || !registered || !backgroundRectangle || locked;
    $("#backgroundRemove").disabled = !ready || !registered || !backgroundRectangle || locked;
    $("#backgroundReset").disabled = !registered || locked || (!backgroundRectangle && !backgroundStrokes.length);
    $("#backgroundPreview").disabled = !ready || !registered || !backgroundRectangle || locked;
    $("#backgroundProposalActions").hidden = !proposal;
    for (const selector of ["#saveImage", "#exportPng", "#undoImage", "#drawToggle", "#gray", "#invert", "#clearImage", "#resetImage", "#addText"]) {
      const control = $(selector);
      if (control) control.disabled = locked || (!sourceUrl && selector !== "#drawToggle");
    }
    if (!registered && sourceUrl) $("#backgroundRemovalStatus").textContent = "Save this local image as an inactive asset before background removal.";
    if ($("#compositePreview")) updateCompositeControls();
  }

  async function checkBackgroundRuntime() {
    try {
      backgroundRuntime = await json("/api/background-removal/health");
      $("#backgroundRuntimeState").textContent = "LOCAL RUNTIME READY";
      $("#backgroundRuntimeState").dataset.state = "healthy";
    } catch (error) {
      backgroundRuntime = null;
      $("#backgroundRuntimeState").textContent = "RUNTIME UNAVAILABLE";
      $("#backgroundRuntimeState").dataset.state = "error";
      $("#backgroundRemovalStatus").textContent = error.message;
    }
    updateBackgroundControls();
  }

  function backgroundPoint(event) {
    const rect = backgroundCanvas().getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(1, (event.clientX - rect.left) / Math.max(1, rect.width))),
      y: Math.max(0, Math.min(1, (event.clientY - rect.top) / Math.max(1, rect.height))),
    };
  }

  function bindBackgroundMask() {
    const overlay = backgroundCanvas();
    overlay.addEventListener("pointerdown", event => {
      if (!backgroundMode || pendingBackgroundProposal) return;
      event.preventDefault();
      overlay.setPointerCapture(event.pointerId);
      const point = backgroundPoint(event);
      if (backgroundMode === "rectangle") {
        backgroundPointerStart = point;
      } else {
        const radius = Number($("#backgroundBrushSize").value) / Math.max(overlay.width, overlay.height);
        backgroundStrokes.push({ mode: backgroundMode, x: point.x, y: point.y, radius });
        redrawBackgroundOverlay();
      }
    });
    overlay.addEventListener("pointermove", event => {
      if (!overlay.hasPointerCapture(event.pointerId) || !backgroundMode) return;
      const point = backgroundPoint(event);
      if (backgroundMode === "rectangle" && backgroundPointerStart) {
        redrawBackgroundOverlay({
          x: Math.min(backgroundPointerStart.x, point.x),
          y: Math.min(backgroundPointerStart.y, point.y),
          width: Math.abs(point.x - backgroundPointerStart.x),
          height: Math.abs(point.y - backgroundPointerStart.y),
        });
      } else if (backgroundMode === "keep" || backgroundMode === "remove") {
        const radius = Number($("#backgroundBrushSize").value) / Math.max(overlay.width, overlay.height);
        const last = backgroundStrokes[backgroundStrokes.length - 1];
        if (!last || Math.hypot(last.x - point.x, last.y - point.y) > radius * .45) {
          backgroundStrokes.push({ mode: backgroundMode, x: point.x, y: point.y, radius });
          redrawBackgroundOverlay();
        }
      }
    });
    overlay.addEventListener("pointerup", event => {
      if (backgroundMode === "rectangle" && backgroundPointerStart) {
        const point = backgroundPoint(event);
        const rectangle = {
          x: Math.min(backgroundPointerStart.x, point.x),
          y: Math.min(backgroundPointerStart.y, point.y),
          width: Math.abs(point.x - backgroundPointerStart.x),
          height: Math.abs(point.y - backgroundPointerStart.y),
        };
        if (rectangle.width < .02 || rectangle.height < .02) {
          $("#backgroundRemovalStatus").textContent = "Choose a larger foreground rectangle.";
        } else {
          backgroundRectangle = rectangle;
          backgroundStrokes = [];
          $("#backgroundRemovalStatus").textContent = "Foreground rectangle ready. Add Keep or Remove corrections, or preview now.";
        }
        backgroundPointerStart = null;
        setBackgroundMode("");
        updateBackgroundControls();
      }
    });
    new ResizeObserver(syncBackgroundOverlay).observe(canvas());
    window.addEventListener("resize", syncBackgroundOverlay);
  }

  async function loadBackgroundPreview(previewUrl) {
    const image = new Image();
    return new Promise(resolve => {
      image.onload = () => {
        const work = canvas();
        work.getContext("2d").clearRect(0, 0, work.width, work.height);
        work.getContext("2d").drawImage(image, 0, 0, work.width, work.height);
        $("#mediaCompareSource").src = sourceUrl;
        $("#mediaCompareSource").nextElementSibling.textContent = "PROTECTED SOURCE";
        $("#mediaCompareCurrent").src = previewUrl;
        $("#mediaCompareCurrent").nextElementSibling.textContent = "PROPOSED CUTOUT";
        $("#mediaCompare").hidden = false;
        $("#backgroundProposalActions").hidden = false;
        updateBackgroundControls();
        resolve(true);
      };
      image.onerror = () => { $("#backgroundRemovalStatus").textContent = "The proposal preview could not be reopened."; resolve(false); };
      image.src = previewUrl + (previewUrl.includes("?") ? "&" : "?") + "t=" + Date.now();
    });
  }

  async function previewBackgroundRemoval() {
    if (!currentImageId || !currentSourceHash || !backgroundRectangle) return;
    $("#backgroundRemovalStatus").textContent = "Running fixed local OpenCV GrabCut…";
    $("#backgroundPreview").disabled = true;
    try {
      const projectId = host().getProjectId();
      const result = await json("/api/background-removal/projects/" + encodeURIComponent(projectId) + "/proposals", {
        method: "POST",
        body: JSON.stringify({ sourceArtifactId: currentImageId, sourceSha256: currentSourceHash, rectangle: backgroundRectangle, strokes: backgroundStrokes }),
      });
      pendingBackgroundProposal = result.proposal;
      $("#backgroundResultTitle").value = ($("#imageTitle").value || pendingBackgroundProposal.sourceTitle || "Image") + " cutout";
      setBackgroundMode("");
      await loadBackgroundPreview(result.previewUrl);
      $("#backgroundRemovalStatus").textContent = "Proposed cutout ready. Compare it, then approve or reject. Nothing has been saved.";
    } catch (error) {
      $("#backgroundRemovalStatus").textContent = error.message;
      updateBackgroundControls();
    }
  }

  async function decideBackgroundProposal(decision) {
    if (!pendingBackgroundProposal) return;
    const projectId = host().getProjectId();
    try {
      const result = await json("/api/background-removal/projects/" + encodeURIComponent(projectId) + "/proposals/" + encodeURIComponent(pendingBackgroundProposal.proposalId) + "/decision", {
        method: "POST",
        body: JSON.stringify({ decision, title: $("#backgroundResultTitle").value }),
      });
      const wasApproved = decision === "approve";
      const sourceId = currentImageId;
      const sourceHash = currentSourceHash;
      pendingBackgroundProposal = null;
      $("#backgroundProposalActions").hidden = true;
      $("#mediaCompare").hidden = true;
      backgroundRectangle = null;
      backgroundStrokes = [];
      if (wasApproved) {
        await host().reloadArtifacts();
        await refresh();
        await loadImage(imageUrl(result.artifact), { id: result.artifact.id, sha256: result.artifact.sha256 });
        $("#backgroundRemovalStatus").textContent = "Approved cutout saved as a new inactive image. The protected source remains unchanged.";
        toast("Inactive transparent image saved with OpenCV provenance");
      } else {
        await loadImage(sourceUrl, { id: sourceId, sha256: sourceHash, originalInputHash });
        $("#backgroundRemovalStatus").textContent = "Proposal rejected and removed. The protected source remains unchanged.";
      }
      updateBackgroundControls();
    } catch (error) {
      $("#backgroundRemovalStatus").textContent = error.message;
    }
  }

  async function recoverBackgroundProposal() {
    const projectId = host()?.getProjectId?.();
    if (!projectId || !host()?.hasCompanion?.()) return;
    try {
      const result = await json("/api/background-removal/projects/" + encodeURIComponent(projectId) + "/proposals");
      const proposal = result.proposals?.[0];
      if (!proposal || pendingBackgroundProposal) return;
      const source = summary.items.find(item => item.id === proposal.sourceArtifactId);
      if (!source) return;
      await loadImage(imageUrl(source), { id: source.id, sha256: source.sha256 });
      pendingBackgroundProposal = proposal;
      $("#backgroundResultTitle").value = (source.title || "Image") + " cutout";
      await loadBackgroundPreview(proposal.previewUrl);
      $("#backgroundRemovalStatus").textContent = "Recovered a proposed cutout after refresh. Approve or reject; no save was resumed.";
    } catch (_) {}
  }

  function resetCompositeProposal(message = "") {
    if (pendingCompositeUrl) URL.revokeObjectURL(pendingCompositeUrl);
    pendingCompositeUrl = "";
    pendingCompositeProposal = null;
    $("#compositeProposalActions").hidden = true;
    $("#mediaCompare").hidden = true;
    if (message) $("#compositeStatus").textContent = message;
    updateCompositeControls();
    updateBackgroundControls();
  }

  function updateCompositeControls() {
    const mode = $("#compositeMode")?.value || "solid";
    const registered = Boolean(currentImageId && currentSourceHash);
    const proposal = Boolean(pendingCompositeProposal);
    const blocked = Boolean(pendingBackgroundProposal);
    $("#compositeColorALabel").hidden = mode === "image";
    $("#compositeColorBLabel").hidden = mode !== "gradient";
    $("#compositeDirectionLabel").hidden = mode !== "gradient";
    $("#compositeImageLabel").hidden = mode !== "image";
    const chosenBackground = mode !== "image" || Boolean($("#compositeBackgroundAsset").value);
    $("#compositePreview").disabled = !registered || !chosenBackground || proposal || blocked;
    $("#compositeReset").disabled = !proposal;
    $("#compositeProposalActions").hidden = !proposal;
    if (!registered && sourceUrl) $("#compositeStatus").textContent = "Save this local image as an inactive asset before composing a background.";
  }

  function renderCompositeSources(images) {
    const select = $("#compositeBackgroundAsset");
    const previous = select.value;
    const eligible = images.filter(item => item.id !== currentImageId);
    select.innerHTML = `<option value="">Choose registered image</option>${eligible.map(option).join("")}`;
    if (eligible.some(item => item.id === previous)) select.value = previous;
    updateCompositeControls();
  }

  function imageElement(src) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error("The selected background image could not be decoded."));
      image.src = src;
    });
  }

  function drawCover(context, image, width, height) {
    const scale = Math.max(width / image.naturalWidth, height / image.naturalHeight);
    const drawWidth = image.naturalWidth * scale;
    const drawHeight = image.naturalHeight * scale;
    context.drawImage(image, (width - drawWidth) / 2, (height - drawHeight) / 2, drawWidth, drawHeight);
  }

  async function previewComposite() {
    if (!currentImageId || !currentSourceHash || pendingBackgroundProposal) return;
    resetCompositeProposal();
    const mode = $("#compositeMode").value;
    const background = mode === "image" ? summary.items.find(item => item.id === $("#compositeBackgroundAsset").value && item.kind === "image") : null;
    if (mode === "image" && !background) {
      $("#compositeStatus").textContent = "Choose a registered project image for the background.";
      updateCompositeControls();
      return;
    }
    $("#compositeStatus").textContent = "Preparing local composite preview…";
    try {
      const foreground = canvas();
      const output = document.createElement("canvas");
      output.width = foreground.width;
      output.height = foreground.height;
      const context = output.getContext("2d");
      if (mode === "image") {
        drawCover(context, await imageElement(imageUrl(background)), output.width, output.height);
      } else if (mode === "gradient") {
        const directions = {
          vertical: [0, 0, 0, output.height],
          horizontal: [0, 0, output.width, 0],
          "diagonal-down": [0, 0, output.width, output.height],
          "diagonal-up": [0, output.height, output.width, 0],
        };
        const gradient = context.createLinearGradient(...directions[$("#compositeDirection").value]);
        gradient.addColorStop(0, $("#compositeColorA").value);
        gradient.addColorStop(1, $("#compositeColorB").value);
        context.fillStyle = gradient;
        context.fillRect(0, 0, output.width, output.height);
      } else {
        context.fillStyle = $("#compositeColorA").value;
        context.fillRect(0, 0, output.width, output.height);
      }
      context.drawImage(foreground, 0, 0);
      const blob = await new Promise(resolve => output.toBlob(resolve, "image/png"));
      if (!blob) throw new Error("The browser could not encode the composite preview.");
      pendingCompositeUrl = URL.createObjectURL(blob);
      pendingCompositeProposal = {
        blob,
        sourceArtifactId: currentImageId,
        sourceSha256: currentSourceHash,
        mode,
        colorA: mode === "image" ? "" : $("#compositeColorA").value,
        colorB: mode === "gradient" ? $("#compositeColorB").value : "",
        direction: $("#compositeDirection").value,
        backgroundArtifactId: background?.id || "",
        backgroundSha256: background?.sha256 || "",
        width: output.width,
        height: output.height,
      };
      $("#compositeResultTitle").value = `${$("#imageTitle").value || "Image"} composite`;
      $("#mediaCompareSource").src = sourceUrl;
      $("#mediaCompareSource").nextElementSibling.textContent = "PROTECTED FOREGROUND";
      $("#mediaCompareCurrent").src = pendingCompositeUrl;
      $("#mediaCompareCurrent").nextElementSibling.textContent = "PROPOSED COMPOSITE";
      $("#mediaCompare").hidden = false;
      $("#compositeStatus").textContent = "Composite proposal ready. Compare it, then approve or reject. Nothing has been saved.";
      updateCompositeControls();
      updateBackgroundControls();
    } catch (error) {
      $("#compositeStatus").textContent = error.message;
      resetCompositeProposal();
    }
  }

  async function decideCompositeProposal(decision) {
    if (!pendingCompositeProposal) return;
    if (decision === "reject") {
      resetCompositeProposal("Composite proposal rejected. No artifact was saved and both sources remain unchanged.");
      return;
    }
    const proposal = pendingCompositeProposal;
    $("#compositeStatus").textContent = "Verifying source hashes and saving approved inactive composite…";
    try {
      const response = await fetch(`/api/media-workspace/projects/${encodeURIComponent(host().getProjectId())}/background-composites`, {
        method: "POST",
        headers: {
          "Content-Type": "image/png",
          "X-TWIS-Title": $("#compositeResultTitle").value,
          "X-TWIS-Width": String(proposal.width),
          "X-TWIS-Height": String(proposal.height),
          "X-TWIS-Source-Artifact": proposal.sourceArtifactId,
          "X-TWIS-Source-SHA256": proposal.sourceSha256,
          "X-TWIS-Background-Mode": proposal.mode,
          "X-TWIS-Background-Color-A": proposal.colorA,
          "X-TWIS-Background-Color-B": proposal.colorB,
          "X-TWIS-Background-Direction": proposal.direction,
          "X-TWIS-Background-Artifact": proposal.backgroundArtifactId,
          "X-TWIS-Background-SHA256": proposal.backgroundSha256,
        },
        body: proposal.blob,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || "Composite save failed");
      resetCompositeProposal();
      await host().reloadArtifacts();
      await refresh();
      await loadImage(imageUrl(data.artifact), { id: data.artifact.id, sha256: data.artifact.sha256 });
      $("#compositeStatus").textContent = "Approved composite saved as a new inactive image. Every selected source remains unchanged.";
      toast("Inactive background composite saved with source provenance");
    } catch (error) {
      $("#compositeStatus").textContent = error.message;
      updateCompositeControls();
    }
  }

  function revokeWorkingUrls() {
    if (importedUrl) URL.revokeObjectURL(importedUrl);
    importedUrl = "";
    history.forEach(value => URL.revokeObjectURL(value));
    history = [];
  }

  function snapshot() {
    if (!sourceUrl) return;
    canvas().toBlob(blob => {
      if (!blob) return;
      history.push(URL.createObjectURL(blob));
      while (history.length > MAX_HISTORY) URL.revokeObjectURL(history.shift());
      $("#undoImage").disabled = false;
    }, "image/png");
  }

  function loadImage(src, metadata = {}) {
    resetCompositeProposal();
    resetBackgroundState(false);
    const image = new Image();
    const loaded = new Promise(resolve => {
    image.onload = () => {
      const scale = Math.min(1, MAX_SIDE / Math.max(image.naturalWidth, image.naturalHeight));
      const work = canvas();
      work.width = Math.max(1, Math.round(image.naturalWidth * scale));
      work.height = Math.max(1, Math.round(image.naturalHeight * scale));
      work.getContext("2d").drawImage(image, 0, 0, work.width, work.height);
      sourceUrl = src;
      currentImageId = metadata.id || "";
      currentSourceHash = metadata.sha256 || "";
      originalInputHash = metadata.originalInputHash || metadata.sha256 || "";
      renderCompositeSources(itemList(["image"]));
      history.forEach(value => URL.revokeObjectURL(value));
      history = [];
      setImageControls(true);
      $("#mediaSourceState").textContent = currentImageId ? "Registered source loaded" : "Local source loaded";
      $("#mediaAssetTruth").textContent = currentImageId
        ? `Protected source ${(currentSourceHash || currentImageId).slice(0, 16)} · saving creates a new variation.`
        : `Local input ${originalInputHash.slice(0, 16)} · the original file is not modified or registered.`;
      $("#saveImage").textContent = currentImageId ? "Save new variation" : "Save inactive asset";
      status(`Loaded ${image.naturalWidth} × ${image.naturalHeight}${scale < 1 ? ` · working canvas limited to ${work.width} × ${work.height}` : ""}`);
      $("#mediaStage").focus({ preventScroll: true });
      syncBackgroundOverlay();
      updateBackgroundControls();
      resolve(true);
    };
    image.onerror = () => { status("That image could not be decoded safely.", true); resolve(false); };
    });
    image.src = src;
    return loaded;
  }

  async function hashFile(file) {
    const value = await crypto.subtle.digest("SHA-256", await file.arrayBuffer());
    return [...new Uint8Array(value)].map(byte => byte.toString(16).padStart(2, "0")).join("");
  }

  async function openFile(file) {
    if (!file) return;
    if (!ACCEPTED.has(file.type)) throw new Error("Choose a PNG, JPEG, or WebP image.");
    if (file.size < 1 || file.size > MAX_BYTES) throw new Error("Image must be between 1 byte and 12 MiB.");
    const bytes = new Uint8Array(await file.slice(0, 12).arrayBuffer());
    const png = bytes.length >= 8 && bytes.slice(0, 8).every((value, index) => value === [137, 80, 78, 71, 13, 10, 26, 10][index]);
    const jpeg = bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255;
    const webp = String.fromCharCode(...bytes.slice(0, 4)) === "RIFF" && String.fromCharCode(...bytes.slice(8, 12)) === "WEBP";
    if (!(png || jpeg || webp)) throw new Error("The file signature does not match a supported image.");
    revokeWorkingUrls();
    importedUrl = URL.createObjectURL(file);
    const digest = await hashFile(file);
    $("#imageTitle").value = file.name.replace(/\.[^.]+$/, "").slice(0, 180) || "Untitled visual asset";
    loadImage(importedUrl, { originalInputHash: digest });
  }

  function showTab(name) {
    $$('[data-media-tab]').forEach(button => button.classList.toggle("active", button.dataset.mediaTab === name));
    $$('[data-media-view]').forEach(view => { view.hidden = view.dataset.mediaView !== name; });
  }

  async function refresh() {
    const api = host();
    const projectId = api?.getProjectId?.();
    $("#mediaProjectLabel").textContent = api?.getProjectTitle?.() || projectId || "No project";
    if (!api?.hasCompanion?.() || !projectId) return;
    try {
      summary = await json(`/api/media-workspace/projects/${encodeURIComponent(projectId)}`);
      render();
    } catch (error) {
      status(`Media context unavailable: ${error.message}`, true);
    }
  }

  function renderIncoming() {
    const routes = itemList(["media-route"]).filter(item => item.payload?.targetRoom === "image" && !dismissedRoutes.has(item.id));
    const container = $("#mediaIncomingRefs");
    if (!container) return;
    container.innerHTML = routes.length ? routes.map(route => {
      const source = summary.items.find(item => item.id === route.payload?.sourceArtifactId);
      return `<article class="media-incoming"><strong>${escapeHtml(source?.title || "Unavailable writing source")}</strong><small>${escapeHtml((route.payload?.sourceSha256 || source?.sha256 || "unknown").slice(0, 16))}</small><p>${escapeHtml(source?.body || source?.content || source?.payload?.text || "Registered writing context")}</p><div class="row"><button class="quiet" data-incoming-use="${escapeHtml(source?.id || "")}">Use as inspiration</button><button class="quiet" data-incoming-scene="${escapeHtml(source?.id || "")}">Attach to scene</button><button class="quiet" data-incoming-dismiss="${escapeHtml(route.id)}">Dismiss</button></div></article>`;
    }).join("") : "<p class='muted'>No writing references routed to Images.</p>";
  }

  function renderAssets(images) {
    const shelf = $("#mediaAssetShelf");
    shelf.innerHTML = images.length ? images.map(item => `<article class="media-asset"><button class="media-asset-open" data-media-open="${escapeHtml(item.id)}"><img loading="lazy" src="${escapeHtml(imageUrl(item))}" alt=""><span>Open on light table</span></button><h4>${escapeHtml(item.title)}</h4><dl><div><dt>State</dt><dd>Inactive asset</dd></div><div><dt>Size</dt><dd>${escapeHtml(item.payload?.width || "?")} × ${escapeHtml(item.payload?.height || "?")}</dd></div><div><dt>Hash</dt><dd>${escapeHtml((item.sha256 || "unknown").slice(0, 16))}</dd></div></dl><div class="row"><button class="quiet" data-media-storyboard="${escapeHtml(item.id)}">Storyboard</button><button class="quiet" data-media-route="${escapeHtml(item.id)}" data-target="music">To Music</button><button class="quiet" data-media-route="${escapeHtml(item.id)}" data-target="video">To Video</button></div></article>`).join("") : "<p class='muted'>No project visual assets yet.</p>";
  }

  function renderStoryboard(boards, images, scenes) {
    const ordered = [...boards].sort((a, b) => (a.payload?.order ?? 9999) - (b.payload?.order ?? 9999));
    $("#mediaStoryboardList").innerHTML = ordered.length ? ordered.map((item, index) => {
      const image = images.find(value => value.id === item.payload?.primaryImageId);
      const scene = scenes.find(value => value.id === item.payload?.sceneId);
      return `<article class="media-frame"><span class="media-frame-number">${String(index + 1).padStart(2, "0")}</span><img loading="lazy" src="${escapeHtml(imageUrl(image))}" alt=""><div><h4>${escapeHtml(scene?.title || item.title)}</h4><p>${escapeHtml(item.payload?.durationSeconds)} seconds · ${escapeHtml(item.payload?.transitionNotes || "cut")}</p><small>Source ${(image?.sha256 || item.payload?.imageSha256 || "unknown").slice(0, 16)}</small></div><div class="media-frame-actions"><button class="quiet" data-board-order="${escapeHtml(item.id)}" data-direction="earlier" ${index === 0 ? "disabled" : ""}>Earlier</button><button class="quiet" data-board-order="${escapeHtml(item.id)}" data-direction="later" ${index === ordered.length - 1 ? "disabled" : ""}>Later</button><button class="quiet" data-media-open="${escapeHtml(image?.id || "")}">Open</button><button class="quiet" data-media-route="${escapeHtml(item.id)}" data-target="video">To Video</button><button class="danger" data-board-remove="${escapeHtml(item.id)}">Remove frame</button></div></article>`;
    }).join("") : "<p class='muted'>No storyboard frames. Choose a scene and visual asset above.</p>";
  }

  function render() {
    const scenes = itemList(["scene"]);
    const images = itemList(["image"]);
    const boards = itemList(["storyboard-item"]);
    const sceneValue = $("#mediaSceneSelect").value;
    $("#mediaSceneSelect").innerHTML = `<option value="">No active scene</option>${scenes.map(option).join("")}`;
    if (scenes.some(item => item.id === sceneValue)) $("#mediaSceneSelect").value = sceneValue;
    $("#mediaImageSelect").innerHTML = images.length ? images.map(option).join("") : "<option value=''>Save an image first</option>";
    renderIncoming();
    renderAssets(images);
    renderCompositeSources(images);
    renderStoryboard(boards, images, scenes);
    bindDynamic();
    renderStrips();
  }

  async function route(id, target, sceneId = "", notes = "") {
    if (!id) throw new Error("Choose a registered source first.");
    await json(`/api/media-workspace/projects/${encodeURIComponent(host().getProjectId())}/routes`, {
      method: "POST",
      body: JSON.stringify({ sourceArtifactId: id, targetRoom: target, sceneId, notes }),
    });
    await host().reloadArtifacts();
    await refresh();
    toast(`Reference sent to ${target}`);
  }

  function bindDynamic() {
    $$('[data-media-open]').forEach(button => {
      button.onclick = () => {
        const item = summary.items.find(value => value.id === button.dataset.mediaOpen);
        if (!item) return;
        revokeWorkingUrls();
        loadImage(imageUrl(item), { id: item.id, sha256: item.sha256 });
        showTab("work");
      };
    });
    $$('[data-media-route]').forEach(button => {
      button.onclick = () => route(button.dataset.mediaRoute, button.dataset.target, $("#mediaSceneSelect")?.value || "").catch(error => toast(error.message));
    });
    $$('[data-media-storyboard]').forEach(button => {
      button.onclick = () => { $("#mediaImageSelect").value = button.dataset.mediaStoryboard; showTab("storyboard"); };
    });
    $$('[data-board-order]').forEach(button => {
      button.onclick = async () => {
        await json(`/api/media-workspace/projects/${encodeURIComponent(host().getProjectId())}/storyboard-order`, { method: "POST", body: JSON.stringify({ itemId: button.dataset.boardOrder, direction: button.dataset.direction }) });
        await refresh();
      };
    });
    $$('[data-board-remove]').forEach(button => {
      button.onclick = async () => {
        await json(`/api/media-workspace/projects/${encodeURIComponent(host().getProjectId())}/storyboard-remove`, { method: "POST", body: JSON.stringify({ itemId: button.dataset.boardRemove }) });
        await host().reloadArtifacts();
        await refresh();
        toast("Storyboard frame removed; source image preserved");
      };
    });
    $$('[data-incoming-use]').forEach(button => {
      button.onclick = () => {
        const source = summary.items.find(item => item.id === button.dataset.incomingUse);
        $("#mediaAssetTruth").textContent = source ? `Writing inspiration: ${source.title} · source remains unchanged.` : "Writing source is unavailable.";
      };
    });
    $$('[data-incoming-scene]').forEach(button => {
      button.onclick = () => route(button.dataset.incomingScene, "image", $("#mediaSceneSelect").value, "Attached as scene inspiration").catch(error => toast(error.message));
    });
    $$('[data-incoming-dismiss]').forEach(button => {
      button.onclick = () => {
        dismissedRoutes.add(button.dataset.incomingDismiss);
        renderIncoming();
        bindDynamic();
        status("Writing reference dismissed from this working view; its governed route remains intact.");
      };
    });
  }

  function bindCanvas() {
    const work = canvas();
    const context = work.getContext("2d", { willReadFrequently: true });
    context.fillStyle = "#05080d";
    context.fillRect(0, 0, work.width, work.height);
    const point = event => {
      const rect = work.getBoundingClientRect();
      return { x: (event.clientX - rect.left) * work.width / rect.width, y: (event.clientY - rect.top) * work.height / rect.height };
    };
    work.onpointerdown = event => {
      if (!drawMode || !sourceUrl) return;
      snapshot();
      drawing = true;
      lastPoint = point(event);
      work.setPointerCapture(event.pointerId);
    };
    work.onpointermove = event => {
      if (!drawing) return;
      const next = point(event);
      context.strokeStyle = $("#brushColor").value;
      context.lineWidth = Number($("#brushSize").value);
      context.lineCap = "round";
      context.beginPath();
      context.moveTo(lastPoint.x, lastPoint.y);
      context.lineTo(next.x, next.y);
      context.stroke();
      lastPoint = next;
    };
    work.onpointerup = () => { drawing = false; };

    $("#drawToggle").onclick = () => {
      drawMode = !drawMode;
      $("#drawToggle").textContent = drawMode ? "Draw on" : "Draw off";
      $("#drawToggle").setAttribute("aria-pressed", String(drawMode));
      $("#mediaStage").classList.toggle("is-drawing", drawMode);
    };
    const filter = transform => {
      if (!sourceUrl) return;
      snapshot();
      const pixels = context.getImageData(0, 0, work.width, work.height);
      for (let index = 0; index < pixels.data.length; index += 4) transform(pixels.data, index);
      context.putImageData(pixels, 0, 0);
    };
    $("#gray").onclick = () => filter((data, index) => { const gray = (data[index] + data[index + 1] + data[index + 2]) / 3; data[index] = data[index + 1] = data[index + 2] = gray; });
    $("#invert").onclick = () => filter((data, index) => { data[index] = 255 - data[index]; data[index + 1] = 255 - data[index + 1]; data[index + 2] = 255 - data[index + 2]; });
    $("#clearImage").onclick = () => { if (!sourceUrl) return; snapshot(); context.fillStyle = "#05080d"; context.fillRect(0, 0, work.width, work.height); };
    $("#resetImage").onclick = () => { if (sourceUrl) { snapshot(); loadImage(sourceUrl, { id: currentImageId, sha256: currentSourceHash, originalInputHash }); } };
    $("#addText").onclick = () => {
      const text = $("#imageText").value;
      if (!sourceUrl || !text) return;
      snapshot();
      context.fillStyle = $("#brushColor").value;
      context.font = `${Math.max(12, Number($("#textSize").value))}px sans-serif`;
      context.textAlign = $("#textAlign").value;
      context.textBaseline = "middle";
      context.fillText(text, work.width * Number($("#textX").value) / 100, work.height * Number($("#textY").value) / 100, work.width * 0.9);
    };
    $("#undoImage").onclick = () => {
      const previous = history.pop();
      if (!previous) return;
      const keepHistory = [...history];
      const image = new Image();
      image.onload = () => { context.clearRect(0, 0, work.width, work.height); context.drawImage(image, 0, 0, work.width, work.height); URL.revokeObjectURL(previous); history = keepHistory; $("#undoImage").disabled = history.length === 0; };
      image.src = previous;
    };
    $("#compareImage").onclick = () => {
      const compare = $("#mediaCompare");
      if (!compare.hidden) { compare.hidden = true; return; }
      $("#mediaCompareSource").src = sourceUrl;
      $("#mediaCompareSource").nextElementSibling.textContent = "PROTECTED SOURCE";
      $("#mediaCompareCurrent").src = work.toDataURL("image/png");
      $("#mediaCompareCurrent").nextElementSibling.textContent = "CURRENT WORKING VERSION";
      compare.hidden = false;
    };
    $("#exportPng").onclick = () => work.toBlob(blob => {
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `${($("#imageTitle").value || "twis-visual-asset").replace(/[^a-z0-9_-]+/gi, "-").replace(/^-|-$/g, "") || "twis-visual-asset"}.png`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    }, "image/png");
    $("#saveImage").onclick = () => work.toBlob(async blob => {
      try {
        const response = await fetch(`/api/media-workspace/projects/${encodeURIComponent(host().getProjectId())}/image-assets`, {
          method: "POST",
          headers: {
            "Content-Type": "image/png",
            "X-TWIS-Title": $("#imageTitle").value,
            "X-TWIS-Width": String(work.width),
            "X-TWIS-Height": String(work.height),
            "X-TWIS-Source-Artifact": currentImageId,
            "X-TWIS-Original-SHA256": originalInputHash,
          },
          body: blob,
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Save failed");
        currentImageId = data.artifact.id;
        currentSourceHash = data.artifact.sha256;
        sourceUrl = imageUrl(data.artifact);
        $("#saveImage").textContent = "Save new variation";
        await host().reloadArtifacts();
        await refresh();
        toast("Inactive visual asset saved with provenance");
      } catch (error) { toast(error.message); }
    }, "image/png");
  }

  function bindDrop() {
    const stage = $("#mediaStage");
    let depth = 0;
    stage.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); $("#imageInput").click(); } });
    stage.addEventListener("dragenter", event => { event.preventDefault(); depth += 1; $("#mediaDropOverlay").hidden = false; });
    stage.addEventListener("dragover", event => { event.preventDefault(); event.dataTransfer.dropEffect = "copy"; });
    stage.addEventListener("dragleave", () => { depth -= 1; if (depth <= 0) { depth = 0; $("#mediaDropOverlay").hidden = true; } });
    stage.addEventListener("drop", event => {
      event.preventDefault(); depth = 0; $("#mediaDropOverlay").hidden = true;
      openFile(event.dataTransfer.files?.[0]).catch(error => status(error.message, true));
    });
    $("#imageInput").onchange = event => openFile(event.target.files?.[0]).catch(error => status(error.message, true));
  }

  function installStrips() {
    for (const room of ["write", "music", "video"]) {
      const panel = document.querySelector(`.room[data-panel="${room}"]`);
      if (!panel || panel.querySelector(".project-media-strip")) continue;
      const element = document.createElement("section");
      element.className = "project-media-strip";
      element.dataset.mediaStrip = room;
      panel.prepend(element);
    }
  }

  function renderStrips() {
    for (const element of $$('[data-media-strip]')) {
      const room = element.dataset.mediaStrip;
      const eligible = summary.items.filter(item => room === "write" ? ["document", "writing-draft"].includes(item.kind) : room === "music" ? ["image", "music", "music-render"].includes(item.kind) : ["image", "music", "music-render", "storyboard-item"].includes(item.kind));
      element.innerHTML = `<div class="row"><div><strong>Project media context</strong><div class="media-route-state">${itemList(["scene"]).length} scenes · ${itemList(["image"]).length} images · ${itemList(["storyboard-item"]).length} frames</div></div><select aria-label="Project reference">${eligible.length ? eligible.map(option).join("") : "<option value=''>No compatible asset</option>"}</select><select aria-label="Scene"><option value=''>No scene</option>${itemList(["scene"]).map(option).join("")}</select>${room === "write" ? "<button data-strip-target='image'>Send to Images</button>" : room === "music" ? "<button data-strip-target='video'>Send to Video</button>" : ""}</div>`;
      const button = element.querySelector("[data-strip-target]");
      if (button) button.onclick = () => { const selects = element.querySelectorAll("select"); if (selects[0].value) route(selects[0].value, button.dataset.stripTarget, selects[1].value).catch(error => toast(error.message)); };
    }
  }

  async function init() {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "assets/media-workspace.css";
    document.head.append(link);
    installStrips();
    bindCanvas();
    bindDrop();
    bindBackgroundMask();
    $$('[data-media-tab]').forEach(button => { button.onclick = () => showTab(button.dataset.mediaTab); });
    $$('[data-media-open-tab]').forEach(button => { button.onclick = () => showTab(button.dataset.mediaOpenTab); });
    $("#mediaRefreshAssets").onclick = refresh;
    $("#mediaQuickScene").onclick = () => showTab("storyboard");
    $("#backgroundRectangle").onclick = () => { setBackgroundMode("rectangle"); $("#backgroundRemovalStatus").textContent = "Drag a rectangle around the foreground subject."; };
    $("#backgroundKeep").onclick = () => { setBackgroundMode("keep"); $("#backgroundRemovalStatus").textContent = "Paint green over foreground that must stay."; };
    $("#backgroundRemove").onclick = () => { setBackgroundMode("remove"); $("#backgroundRemovalStatus").textContent = "Paint red over background that must be removed."; };
    $("#backgroundReset").onclick = () => { backgroundRectangle = null; backgroundStrokes = []; setBackgroundMode(""); updateBackgroundControls(); $("#backgroundRemovalStatus").textContent = "Mask reset. Draw a new foreground rectangle."; };
    $("#backgroundPreview").onclick = previewBackgroundRemoval;
    $("#backgroundApprove").onclick = () => decideBackgroundProposal("approve");
    $("#backgroundReject").onclick = () => decideBackgroundProposal("reject");
    $("#compositeMode").onchange = updateCompositeControls;
    $("#compositeBackgroundAsset").onchange = updateCompositeControls;
    $("#compositePreview").onclick = previewComposite;
    $("#compositeReset").onclick = () => resetCompositeProposal("Composite proposal cleared. No artifact was saved.");
    $("#compositeApprove").onclick = () => decideCompositeProposal("approve");
    $("#compositeReject").onclick = () => decideCompositeProposal("reject");
    $("#mediaCreateScene").onclick = async () => {
      try {
        await json(`/api/media-workspace/projects/${encodeURIComponent(host().getProjectId())}/scenes`, { method: "POST", body: JSON.stringify({ title: $("#mediaSceneTitle").value, description: $("#mediaSceneDescription").value }) });
        await host().reloadArtifacts(); await refresh(); toast("Inactive scene created");
      } catch (error) { toast(error.message); }
    };
    $("#mediaCreateStoryboard").onclick = async () => {
      try {
        await json(`/api/media-workspace/projects/${encodeURIComponent(host().getProjectId())}/storyboard-items`, { method: "POST", body: JSON.stringify({ sceneId: $("#mediaSceneSelect").value, imageId: $("#mediaImageSelect").value, durationSeconds: Number($("#mediaDuration").value), transitionNotes: $("#mediaTransition").value }) });
        await host().reloadArtifacts(); await refresh(); toast("Storyboard frame added");
      } catch (error) { toast(error.message); }
    };
    try {
      const capabilities = await json("/api/media-capabilities");
      $("#mediaImageCapability").textContent = "LOCAL CANVAS READY · GENERATION UNAVAILABLE";
      $("#mediaImageCapability").classList.add("media-unavailable");
      $("#mediaCapabilityEvidence").textContent = JSON.stringify(capabilities, null, 2);
    } catch (_) { $("#mediaImageCapability").textContent = "MEDIA CONTRACT OFFLINE"; }
    setImageControls(false);
    await refresh();
    await checkBackgroundRuntime();
    await recoverBackgroundProposal();
  }

  window.twisMediaHost = window.twisMediaHost || window.twisMusicHost;
  document.addEventListener("click", event => {
    const open = event.target.closest?.("[data-open]");
    if (open) {
      const item = host()?.getItems().find(value => value.id === open.dataset.open);
      if (item?.type === "image" && item.data?.schemaVersion === "twis-media-asset-v1") {
        event.preventDefault(); event.stopImmediatePropagation(); window.twisMediaWorkspace.openImage(item); return;
      }
    }
    const nav = event.target.closest?.("[data-room]");
    if (nav && ["write", "music", "image", "video"].includes(nav.dataset.room)) setTimeout(refresh, 0);
  }, true);
  window.addEventListener("twis:artifacts-loaded", () => refresh().catch(() => {}));
  window.twisMediaWorkspace = {
    onRoomOpen: refresh,
    openImage: item => { revokeWorkingUrls(); loadImage(item.data?.schemaVersion === "twis-media-asset-v1" ? `/api/media-assets/${encodeURIComponent(item.id)}` : item.data?.png || "", { id: item.id, sha256: item.sha256 || item.data?.sha256 }); window.twisOpenRoom("image"); },
  };
  window.addEventListener("beforeunload", revokeWorkingUrls);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();

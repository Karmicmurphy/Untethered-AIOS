(() => {
  const PROJECT_ID = "flashriver-source-archive";
  const $ = (selector) => document.querySelector(selector);
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[char]);
  let data = null;
  const selected = new Set();
  const groups = [
    ["Core handover documents", (artifact) => artifact.kind === "flashriver-core-doc" && /README|HANDOFF|CONTEXT|ENGINEERING|PRODUCT_SPEC|PLATFORM_MATRIX/i.test(artifact.title)],
    ["Agent, harness, and skills", (artifact) => /AGENT|HARNESS|SKILL/i.test(artifact.title)],
    ["Security and governance", (artifact) => /SECURITY|PROTOCOL|POLICY|RECEIPT|LIMIT/i.test(artifact.title)],
    ["API and MCP plans", (artifact) => /API|MCP|TOOL_REGISTRY/i.test(artifact.title)],
    ["Artifact Compass research", (artifact) => /ARTIFACT_COMPASS/i.test(artifact.title)],
    ["Build plans and roadmaps", (artifact) => /BUILD|ROADMAP|NEXT_PROMPT|DEBUG/i.test(artifact.title)],
    ["Receipts and manifests", (artifact) => artifact.kind === "flashriver-intake-manifest" || /RECEIPT|MANIFEST/i.test(artifact.title)],
    ["Visual references", (artifact) => artifact.kind === "flashriver-visual"],
    ["Private source archives", (artifact) => artifact.kind === "flashriver-private-source"],
    ["Planning and architecture", (artifact) => artifact.kind.includes("doc")],
    ["Other or unclassified", () => true]
  ];

  async function api(path, opts = {}) {
    const response = await fetch(path, { headers: { "Content-Type": "application/json", ...(opts.headers || {}) }, ...opts });
    const text = await response.text();
    let body = {};
    try { body = text ? JSON.parse(text) : {}; } catch { body = { raw: text }; }
    if (!response.ok) throw Error(body.error || text || `HTTP ${response.status}`);
    return body;
  }

  function payload(artifact) { return artifact.payload || {}; }
  function statusLabel(status) {
    return ({
      unreviewed: "Unreviewed",
      reviewed: "Reviewed",
      current_candidate: "Current candidate",
      superseded: "Superseded",
      conflicted: "Conflicted",
      private_source: "Private source",
      do_not_use: "Do not use"
    })[status] || status;
  }
  function sourcePath(artifact) {
    const details = payload(artifact);
    return details.archiveMember || details.relativeName || artifact.path || details.localPath || "Path unavailable";
  }
  function find(id) { return data.artifacts.find((artifact) => artifact.id === id); }

  function duplicateGroups() {
    if (Array.isArray(data.duplicateGroups)) return data.duplicateGroups;
    const buckets = new Map();
    for (const artifact of data.artifacts) {
      const digest = String(artifact.sha256 || "").trim().toLowerCase();
      if (!digest) continue;
      if (!buckets.has(digest)) buckets.set(digest, []);
      buckets.get(digest).push(artifact);
    }
    return [...buckets.entries()].filter(([, artifacts]) => artifacts.length > 1).map(([sha256, artifacts]) => ({
      sha256,
      count: artifacts.length,
      members: artifacts.map((artifact) => ({ artifactId: artifact.id, title: artifact.title, sourcePath: sourcePath(artifact) }))
    })).sort((left, right) => right.count - left.count || left.sha256.localeCompare(right.sha256));
  }

  function categoryArtifacts(artifacts) {
    const remain = [...artifacts];
    const output = [];
    for (const [name, test] of groups) {
      const items = [];
      for (let index = remain.length - 1; index >= 0; index -= 1) {
        if (test(remain[index])) items.unshift(...remain.splice(index, 1));
      }
      if (items.length) output.push([name, items]);
    }
    return output;
  }

  function summary(duplicates) {
    const manifest = payload(data.manifest || {});
    const duplicateRecords = duplicates.reduce((total, group) => total + group.count, 0);
    $("#frReviewSummary").innerHTML = `
      <div><b>${esc(data.project?.title || "FlashRiver Source Archive")}</b><small>Dedicated local project</small></div>
      <div><b>${esc(manifest.zipTest || "Unknown")}</b><small>ZIP integrity</small></div>
      <div><b>${esc(manifest.fileCount || data.artifacts.length)}</b><small>Files inspected</small></div>
      <div><b>${esc(manifest.publicSafeDocsImported || 0)}</b><small>Documents</small></div>
      <div><b>${esc((manifest.privateSourcesCopied || []).length)}</b><small>Private sources</small></div>
      <div><b>${esc((manifest.visualsCopied || []).length)}</b><small>Visuals</small></div>
      <div><b>${esc(duplicates.length)}</b><small>Exact duplicate groups</small></div>
      <div><b>${esc(duplicateRecords)}</b><small>Records grouped, none removed</small></div>
      <div class="wide"><b class="mono">${esc(manifest.sha256 || "")}</b><small>Package SHA-256</small></div>`;
  }

  function filtered(artifact) {
    const query = $("#frReviewSearch").value.trim().toLowerCase();
    const status = $("#frReviewStatus").value;
    if (status !== "all" && artifact.review_status !== status) return false;
    return !query || `${artifact.title} ${artifact.kind} ${sourcePath(artifact)} ${JSON.stringify(artifact.payload)}`.toLowerCase().includes(query);
  }

  function card(artifact) {
    const details = payload(artifact);
    const previewText = details.contentPreview || "";
    return `<article class="review-card" data-id="${artifact.id}">
      <div class="review-card-top"><label class="select-artifact"><input type="checkbox" data-select="${artifact.id}" ${selected.has(artifact.id) ? "checked" : ""}> compare</label><span class="review-status status-${esc(artifact.review_status)}">${esc(statusLabel(artifact.review_status))}</span></div>
      <h4>${esc(artifact.title)}</h4>
      <p class="artifact-meta">${esc(artifact.kind)} · ${esc(sourcePath(artifact))}</p>
      <p>${esc(previewText.slice(0, 260))}${previewText.length > 260 ? "…" : ""}</p>
      <div class="hash-line">${artifact.sha256 ? `SHA ${esc(artifact.sha256.slice(0, 16))}…` : "No file hash"}</div>
      <div class="review-actions"><button data-preview="${artifact.id}">Preview</button><select data-status="${artifact.id}">${["unreviewed", "reviewed", "current_candidate", "superseded", "conflicted", "private_source", "do_not_use"].map((status) => `<option value="${status}" ${artifact.review_status === status ? "selected" : ""}>${statusLabel(status)}</option>`).join("")}</select><button data-source="${artifact.id}">Source</button></div>
      <textarea data-notes="${artifact.id}" rows="2" placeholder="Review notes">${esc(artifact.review_notes || "")}</textarea>
      <button class="save-review" data-save="${artifact.id}">Save review</button>
    </article>`;
  }

  function duplicateSections(duplicates) {
    if (!duplicates.length) return "";
    const sections = duplicates.map((group) => {
      const artifacts = group.members.map((member) => find(member.artifactId)).filter(Boolean);
      const shown = artifacts.filter(filtered);
      if (!shown.length) return "";
      const paths = group.members.map((member) => `<li><span>${esc(member.title)}</span><code>${esc(member.sourcePath || "Path unavailable")}</code></li>`).join("");
      return `<section class="review-group duplicate-group" data-sha="${esc(group.sha256)}">
        <div class="section-head"><div><h3>Exact duplicate group</h3><p class="duplicate-hash mono">SHA-256 ${esc(group.sha256)}</p></div><span class="badge">${esc(group.count)} records</span></div>
        <ul class="duplicate-paths" aria-label="All source paths for duplicate hash">${paths}</ul>
        <div class="review-grid">${shown.map(card).join("")}</div>
      </section>`;
    }).join("");
    return sections ? `<section class="duplicate-overview"><h3>Exact-hash duplicates</h3><p class="muted">Identical files are grouped by SHA-256. Every source record and every source path remains visible and separately reviewable.</p>${sections}</section>` : "";
  }

  function categorySections(artifacts) {
    return categoryArtifacts(artifacts).map(([name, items]) => {
      const shown = items.filter(filtered);
      return shown.length ? `<section class="review-group"><div class="section-head"><h3>${esc(name)}</h3><span class="badge">${shown.length}</span></div><div class="review-grid">${shown.map(card).join("")}</div></section>` : "";
    }).join("");
  }

  function render() {
    const duplicates = duplicateGroups();
    summary(duplicates);
    const duplicateIds = new Set(duplicates.flatMap((group) => group.members.map((member) => member.artifactId)));
    const singletonArtifacts = data.artifacts.filter((artifact) => !duplicateIds.has(artifact.id));
    const html = duplicateSections(duplicates) + categorySections(singletonArtifacts);
    $("#frReviewGroups").innerHTML = html || '<p class="muted">No matching FlashRiver artifacts.</p>';
    bind();
  }

  function show(title, html) {
    $("#frDialogTitle").textContent = title;
    $("#frDialogBody").innerHTML = html;
    const dialog = $("#frReviewDialog");
    if (dialog.showModal) dialog.showModal(); else dialog.setAttribute("open", "");
  }

  async function preview(artifact) {
    if (artifact.kind === "flashriver-private-source" || artifact.kind === "flashriver-visual") return source(artifact);
    if (!artifact.path) return show(artifact.title, "<p>No local file path is recorded.</p>");
    try {
      const file = await api(`/api/files?path=${encodeURIComponent(`${PROJECT_ID}/${artifact.path}`)}`);
      show(artifact.title, `<pre class="artifact-preview">${esc(file.content)}</pre>`);
    } catch (error) {
      show(artifact.title, `<p class="warning">This source is unavailable or not readable as text.</p><pre>${esc(error.message)}</pre>`);
    }
  }

  function source(artifact) {
    const details = payload(artifact);
    show(artifact.title, `<dl class="source-grid"><dt>Type</dt><dd>${esc(artifact.kind)}</dd><dt>Review status</dt><dd>${esc(statusLabel(artifact.review_status))}</dd><dt>Authority</dt><dd>${esc(artifact.authority_state)}</dd><dt>Project path</dt><dd>${esc(artifact.path || details.localPath || "")}</dd><dt>Archive member</dt><dd>${esc(details.archiveMember || "")}</dd><dt>Source package</dt><dd>${esc(details.sourcePackage || "")}</dd><dt>SHA-256</dt><dd class="mono">${esc(artifact.sha256 || details.sha256 || "")}</dd><dt>Size</dt><dd>${esc(details.size || "")}</dd></dl>`);
  }

  async function saveReview(id) {
    const artifact = find(id);
    const artifactCard = document.querySelector(`.review-card[data-id="${id}"]`);
    const status = artifactCard.querySelector(`[data-status="${id}"]`).value;
    const notes = artifactCard.querySelector(`[data-notes="${id}"]`).value;
    const saved = await api(`/api/artifacts/${id}/review`, { method: "POST", body: JSON.stringify({ status, notes }) });
    artifact.review_status = saved.status;
    artifact.review_notes = saved.notes;
    artifact.reviewed_at = saved.reviewedAt;
    render();
  }

  function compare() {
    const artifacts = [...selected].map(find).filter(Boolean);
    if (artifacts.length !== 2) return show("Compare artifacts", "<p>Select exactly two artifacts.</p>");
    show("Compare artifacts", `<div class="compare-grid">${artifacts.map((artifact) => `<section><h3>${esc(artifact.title)}</h3><p>${esc(artifact.kind)} · ${esc(statusLabel(artifact.review_status))}</p><pre class="artifact-preview">${esc((payload(artifact).contentPreview || JSON.stringify(payload(artifact), null, 2)).slice(0, 12000))}</pre></section>`).join("")}</div>`);
  }

  function bind() {
    document.querySelectorAll("[data-select]").forEach((input) => { input.onchange = () => input.checked ? selected.add(input.dataset.select) : selected.delete(input.dataset.select); });
    document.querySelectorAll("[data-preview]").forEach((button) => { button.onclick = () => preview(find(button.dataset.preview)); });
    document.querySelectorAll("[data-source]").forEach((button) => { button.onclick = () => source(find(button.dataset.source)); });
    document.querySelectorAll("[data-save]").forEach((button) => { button.onclick = () => saveReview(button.dataset.save).catch((error) => show("Review save failed", `<pre>${esc(error.message)}</pre>`)); });
  }

  async function load() {
    try {
      data = await api(`/api/projects/${PROJECT_ID}/flashriver-review`);
      render();
    } catch (error) {
      $("#frReviewGroups").innerHTML = `<p class="warning">Could not load FlashRiver Review: ${esc(error.message)}</p>`;
    }
  }

  function boot() {
    if (!$("#frReviewSearch")) return;
    $("#frReviewSearch").oninput = render;
    $("#frReviewStatus").onchange = render;
    $("#frCompare").onclick = compare;
    $("#frDialogClose").onclick = () => $("#frReviewDialog").close();
    window.addEventListener("twis:flashriver-review-open", load);
    window.addEventListener("twis:select-project", (event) => { if (event.detail?.openReview) setTimeout(load, 50); });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();

(() => {
  "use strict";
  const $ = selector => document.querySelector(selector);
  const statusForRoom = {
    home: "SYSTEM ROOM", talk: "ACTIVE ROOM", write: "ACTIVE TOOL", music: "ACTIVE TOOL",
    image: "ACTIVE TOOL", video: "ACTIVE TOOL", research: "ACTIVE TOOL", code: "ACTIVE TOOL",
    import: "RECOVERY READY", work: "SYSTEM ROOM", modules: "ACTIVE TOOL", settings: "SYSTEM ROOM",
  };
  const draftKinds = new Set(["handoff-draft", "prompt-draft", "writing-draft", "research-comparison-draft", "visual-brief-draft", "song-production-brief-draft", "video-production-brief-draft", "build-work-order-draft", "module-proposal-draft"]);
  const api = async path => {
    const response = await fetch(path, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`Local state unavailable (${response.status})`);
    return response.json();
  };
  const setText = (selector, value, state = "") => {
    const node = $(selector); if (!node) return;
    if (node.textContent !== value) node.textContent = value;
    if (node.dataset.truth !== state) node.dataset.truth = state;
  };
  function installFrame() {
    document.body.classList.add("shell014");
    const brand = $(".brand");
    if (brand) {
      brand.querySelector(".cube").textContent = "TWIS";
      brand.querySelector("strong").textContent = "HOLO WORKSHOP";
      brand.querySelector("small").textContent = "SOVEREIGN-HUD / LATTICE-OS";
    }
    for (const button of document.querySelectorAll("#nav .nav")) {
      button.dataset.roomStatus = statusForRoom[button.dataset.room] || "NOT EXPOSED";
      button.setAttribute("aria-label", `${button.textContent.trim()} — ${button.dataset.roomStatus}`);
    }
    const topbar = $(".topbar");
    topbar?.insertAdjacentHTML("afterend", `<section id="shellStatusBand" class="shell-status-band" aria-label="Workshop status">
      <div><small>ACTIVE PROJECT</small><b id="shellProject">UNKNOWN</b></div><div><small>SELECTED ROOM</small><b id="shellRoom">HOME</b></div>
      <div><small>LOCAL COMPANION</small><b id="shellCompanion">CHECKING</b></div><div><small>DATABASE / LEDGER</small><b id="shellLedger">NOT EXPOSED</b></div>
      <div><small>CURRENT SOURCE</small><b id="shellSource">NONE SELECTED</b></div><div><small>PENDING APPROVALS</small><b id="shellApprovals">UNKNOWN</b></div>
      <div><small>RECOVERY</small><b id="shellRecovery">CHECKING</b></div><button id="shellSplitToggle" type="button" aria-pressed="true">SPLIT: ON</button>
    </section>`);
    const home = $('.room[data-panel="home"]');
    home?.insertAdjacentHTML("afterbegin", `<section id="homeControlDeck" class="shell-control-deck" aria-labelledby="homeDeckTitle">
      <div class="shell-screen-head"><div><small>ROOM 03 / CONTROL ROOM</small><h2 id="homeDeckTitle">OWNER CONTROL DECK</h2></div><span>FOUNDATION 0.16</span></div>
      <div class="shell-metrics"><article><small>REGISTERED SOURCES</small><b id="homeSources">UNKNOWN</b><span id="homeSourcesState">NOT EXPOSED</span></article><article><small>ARTIFACTS</small><b id="homeArtifacts">UNKNOWN</b><span>ACTIVE PROJECT</span></article><article class="shell-ghost"><small>INACTIVE DRAFTS</small><b id="homeDrafts">UNKNOWN</b><span>PROPOSED / INACTIVE</span></article><article><small>PENDING APPROVALS</small><b id="homePending">UNKNOWN</b><span>OWNER AUTHORITY</span></article></div>
      <div class="shell-split"><section class="shell-panel"><header><h3>ROOM CAPABILITY GRID</h3><span>DEPLOYED STATE</span></header><div class="shell-capabilities">
        <button data-room="write"><b>WRITE</b><i>ACTIVE TOOL</i><small>Draft Workshop</small></button><button data-room="research"><b>EXPLORE</b><i>ACTIVE TOOL</i><small>Evidence Compare</small></button><button data-room="image"><b>IMAGES</b><i>ACTIVE TOOL</i><small>Visual Brief Builder</small></button><button data-room="music"><b>MUSIC</b><i>ACTIVE TOOL</i><small>Song Production Brief</small></button><button data-room="video"><b>VIDEO</b><i>ACTIVE TOOL</i><small>Video Production Brief</small></button><button data-room="code"><b>BUILD</b><i>ACTIVE TOOL</i><small>Build Work Order</small></button><button data-room="modules"><b>MODULES</b><i>ACTIVE TOOL</i><small>Registry + proposals</small></button><button data-room="import"><b>RECOVER</b><i>RECOVERY READY</i><small>Existing recovery paths</small></button>
      </div></section><aside class="shell-panel shell-context"><header><h3>CONTEXT INSPECTOR</h3><span>REAL STATE</span></header><dl><div><dt>PROJECT</dt><dd id="homeProject">UNKNOWN</dd></div><div><dt>SOURCE CONTEXT</dt><dd id="homeSource">NONE SELECTED</dd></div><div><dt>LOCAL-ONLY</dt><dd>YES</dd></div><div><dt>EXTERNAL NETWORK</dt><dd>NOT EXPOSED</dd></div><div><dt>RELEASE</dt><dd id="homeRelease">UNKNOWN</dd></div><div><dt>RECENT RECEIPT</dt><dd id="homeReceipt">NONE EXPOSED</dd></div></dl></aside></div>
    </section>`);
    const recover = $('.room[data-panel="import"]');
    recover?.insertAdjacentHTML("afterbegin", `<section id="recoverControlDeck" class="shell-control-deck" aria-labelledby="recoverDeckTitle"><div class="shell-screen-head"><div><small>ROOM 12 / RECOVER</small><h2 id="recoverDeckTitle">RECOVER / MACHINE ROOM</h2></div><span id="recoverOverall">CHECKING</span></div><div class="shell-metrics shell-recovery-metrics"><article><small>DATABASE</small><b id="recoverDatabase">UNKNOWN</b><span>LOCAL HEALTH ENDPOINT</span></article><article><small>INTERRUPTED JOBS</small><b id="recoverInterrupted">UNKNOWN</b><span>GOVERNED JOB STATE</span></article><article><small>ROLLBACK ELIGIBLE</small><b id="recoverRollback">UNKNOWN</b><span>EXISTING ACTIONS</span></article><article id="recoverConflictCell"><small>SOURCE-HASH CONFLICTS</small><b id="recoverConflicts">UNKNOWN</b><span>STALE JOB STATE</span></article></div><div class="shell-split"><section class="shell-panel"><header><h3>RECENT RECOVERY RECEIPTS</h3><span>REAL LEDGER</span></header><div id="recoverReceipts" class="shell-receipts"><p>NOT EXPOSED</p></div></section><aside class="shell-panel shell-context"><header><h3>PROTECTED STATE</h3><span>READ ONLY</span></header><dl><div><dt>PROTECTED HASH MANIFEST</dt><dd>NOT EXPOSED BY UI API</dd></div><div><dt>DATABASE INTEGRITY CHECK</dt><dd>NOT EXPOSED BY UI API</dd></div><div><dt>AUTOMATIC RESUME</dt><dd>DISABLED BY CONTRACT</dd></div></dl></aside></div></section>`);
    document.body.insertAdjacentHTML("beforeend", `<footer class="shell-ledger-strip"><span>LOCAL AUTHORITY · OWNER APPROVAL REQUIRED</span><span id="shellReceiptStrip">RECEIPTS: UNKNOWN</span><span>EXTERNAL NETWORK: NOT EXPOSED</span></footer>`);
    $("#shellSplitToggle")?.addEventListener("click", event => {
      const enabled = !document.body.classList.toggle("shell-single");
      event.currentTarget.setAttribute("aria-pressed", String(enabled));
      event.currentTarget.textContent = `SPLIT: ${enabled ? "ON" : "OFF"}`;
    });
    for (const button of document.querySelectorAll("#homeControlDeck [data-room]")) button.addEventListener("click", () => window.twisOpenRoom?.(button.dataset.room));
  }
  function updateRoomTruth() {
    const active = $("#nav .nav.active");
    setText("#shellRoom", active?.textContent.trim().toUpperCase() || "UNKNOWN", active?.dataset.roomStatus === "ACTIVE TOOL" ? "compute" : "");
  }
  function updateSourceTruth() {
    const checked = $("#builderSources input:checked");
    const source = checked?.closest(".builder-source");
    const title = source?.querySelector("b")?.textContent.trim();
    const metadata = source?.querySelector("small")?.textContent || "";
    const hash = metadata.match(/SHA-256\s+([^·]+)/)?.[1]?.trim();
    const value = title ? `${title} · ${hash || "HASH NOT EXPOSED"}` : "NONE SELECTED";
    setText("#shellSource", value, title ? "read" : ""); setText("#homeSource", value, title ? "read" : "");
  }
  function classifyWorkflow() {
    const status = $("#builderStatus"); if (!status) return;
    const value = status.textContent.toLowerCase();
    const workspace = $("#builderWorkspace");
    workspace.classList.toggle("shell-hazard", /stale|hash mismatch|failed|invalid|conflict/.test(value));
    workspace.classList.toggle("shell-approved", /approved|inactive draft|rolled back|validated/.test(value) && !/awaiting/.test(value));
    workspace.classList.toggle("shell-active-operation", /running|generating|processing/.test(value));
  }
  function classifyWorkItems() {
    for (const item of document.querySelectorAll("#workList .item")) {
      const kind = item.querySelector("small")?.textContent.toLowerCase() || "";
      item.classList.toggle("shell-ghost", [...draftKinds].some(value => kind.includes(value)));
      item.classList.toggle("shell-read", /source|flashriver-core-doc|flashriver-support-doc/.test(kind));
    }
  }
  async function refreshTruth() {
    const projectId = window.twisGetActiveProject?.() || $("#projectSelect")?.value || "";
    const projectTitle = $("#projectSelect option:checked")?.textContent.trim() || (projectId ? projectId : "UNKNOWN");
    setText("#shellProject", projectTitle); setText("#homeProject", projectTitle);
    updateRoomTruth(); updateSourceTruth(); classifyWorkflow(); classifyWorkItems();
    if (!projectId || !window.twisHasCompanion?.()) {
      setText("#shellCompanion", "UNAVAILABLE"); setText("#shellLedger", "NOT EXPOSED"); setText("#shellRecovery", "NOT EXPOSED"); return;
    }
    try {
      const [health, artifacts, sources, jobs, receipts] = await Promise.all([
        api("/api/health"), api(`/api/projects/${encodeURIComponent(projectId)}/artifacts`),
        api(`/api/local-worker-sources?projectId=${encodeURIComponent(projectId)}`),
        api(`/api/local-worker-jobs?projectId=${encodeURIComponent(projectId)}`),
        api(`/api/projects/${encodeURIComponent(projectId)}/receipts`),
      ]);
      const inactiveDrafts = artifacts.filter(item => draftKinds.has(item.kind) && item.authority_state === "DRAFT").length;
      const pending = jobs.filter(job => ["planned", "plan_approved", "running", "awaiting_result_approval", "result_approved"].includes(job.status)).length;
      const interrupted = jobs.filter(job => job.status === "interrupted").length;
      const rollback = jobs.filter(job => job.actions?.rollbackDraft || job.actions?.rollback).length;
      const conflicts = jobs.filter(job => job.status === "stale").length;
      setText("#shellCompanion", health.ok ? "LOCAL / READY" : "UNAVAILABLE", health.ok ? "read" : "");
      setText("#shellLedger", health.sqlite ? "OPEN" : "NOT EXPOSED", health.sqlite ? "read" : "");
      setText("#shellApprovals", String(pending).padStart(2, "0"), pending ? "compute" : "read");
      setText("#shellRecovery", interrupted ? "ACTION REQUIRED" : "READY", interrupted ? "hazard" : "read");
      setText("#homeSources", String(sources.length).padStart(2, "0")); setText("#homeSourcesState", sources.length ? "REGISTERED / HASH-BOUND" : "NONE REGISTERED", sources.length ? "read" : "");
      setText("#homeArtifacts", String(artifacts.length).padStart(2, "0")); setText("#homeDrafts", String(inactiveDrafts).padStart(2, "0")); setText("#homePending", String(pending).padStart(2, "0"));
      setText("#homeRelease", health.workshopRelease || "UNKNOWN"); setText("#homeReceipt", receipts[0]?.action || "NONE"); setText("#shellReceiptStrip", `RECEIPTS: ${receipts.length} EXPOSED FOR PROJECT`);
      setText("#recoverDatabase", health.ok && health.sqlite ? "OPEN" : "UNAVAILABLE", health.ok && health.sqlite ? "read" : "hazard");
      setText("#recoverInterrupted", String(interrupted).padStart(2, "0"), interrupted ? "hazard" : "read"); setText("#recoverRollback", String(rollback).padStart(2, "0"), rollback ? "compute" : "read"); setText("#recoverConflicts", String(conflicts).padStart(2, "0"), conflicts ? "hazard" : "read");
      $("#recoverConflictCell")?.classList.toggle("shell-hazard", conflicts > 0); setText("#recoverOverall", interrupted || conflicts ? "ATTENTION" : "RECOVERY READY", interrupted || conflicts ? "hazard" : "read");
      const recoveryReceipts = receipts.filter(receipt => /recover|rollback|stale|interrupt/.test(receipt.action)).slice(0, 6);
      const root = $("#recoverReceipts"); root.replaceChildren();
      if (!recoveryReceipts.length) root.append(Object.assign(document.createElement("p"), { textContent: "NO RECOVERY RECEIPTS EXPOSED FOR THIS PROJECT" }));
      for (const receipt of recoveryReceipts) {
        const row = document.createElement("div"); const action = document.createElement("b"); const time = document.createElement("small");
        action.textContent = receipt.action; time.textContent = receipt.created_at; row.append(action, time); root.append(row);
      }
    } catch {
      setText("#shellCompanion", "UNAVAILABLE"); setText("#shellLedger", "NOT EXPOSED"); setText("#shellRecovery", "UNKNOWN"); setText("#recoverOverall", "UNKNOWN");
    }
  }
  function bindTruthObservers() {
    const observer = new MutationObserver(() => { updateRoomTruth(); updateSourceTruth(); classifyWorkflow(); classifyWorkItems(); });
    observer.observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true, attributeFilter: ["class", "hidden", "checked", "data-state"] });
    $("#projectSelect")?.addEventListener("change", () => setTimeout(refreshTruth, 50));
    window.addEventListener("hashchange", () => setTimeout(refreshTruth, 50)); window.addEventListener("twis:artifacts-loaded", () => setTimeout(refreshTruth, 50));
  }
  function boot() { installFrame(); bindTruthObservers(); for (const delay of [0, 500, 1500, 3000]) setTimeout(refreshTruth, delay); }
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", boot) : boot();
})();

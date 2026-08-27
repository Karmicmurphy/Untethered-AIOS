(() => {
  "use strict";

  const $ = selector => document.querySelector(selector);
  const state = { registry: null, hardware: null, skills: null, mcp: null, selected: null, filters: new Set(), recommendation: null, inspection: null, authorityTemplate: null };
  const freeClasses = new Set(["local-free", "open-source-free", "free-tier", "free-with-account"]);

  async function getJson(path) {
    const response = await fetch(path, { headers: { "Accept": "application/json" } });
    const value = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(value.error || `Capability request failed (${response.status})`);
    return value;
  }
  async function postJson(path, body) {
    const response = await fetch(path, { method: "POST", headers: { "Accept": "application/json", "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
    const value = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(value.error || `Capability action failed (${response.status})`);
    return value;
  }

  function text(node, value) { if (node) node.textContent = value == null || value === "" ? "Not exposed" : String(value); }
  function shortHash(value) { return value ? `${value.slice(0, 12)}…${value.slice(-8)}` : "Not verified"; }
  function gib(bytes) { return Number.isFinite(bytes) ? `${(bytes / 1073741824).toFixed(2)} GiB` : "Not exposed"; }
  function setStatus(message, failed = false) {
    const node = $("#capabilityBayState");
    if (!node) return;
    node.textContent = message;
    node.dataset.state = failed ? "failed" : "";
  }

  function visibleCapabilities() {
    if (!state.registry) return [];
    const query = ($("#capabilitySearch")?.value || "").trim().toLowerCase();
    return state.registry.capabilities.filter(item => {
      const haystack = [item.name, item.description, item.capabilityType, item.status, item.costClass, item.replacementGroup, ...(item.tags || [])].join(" ").toLowerCase();
      if (query && !query.split(/\s+/).every(token => haystack.includes(token))) return false;
      if (state.filters.has("verified") && !["VERIFIED", "APPROVED"].includes(item.status)) return false;
      if (state.filters.has("discovered") && !["DISCOVERED", "INSPECTING", "TESTING"].includes(item.status)) return false;
      if (state.filters.has("installed") && item.healthState === "NOT-INSTALLED") return false;
      if (state.filters.has("free") && !freeClasses.has(item.costClass)) return false;
      if (state.filters.has("local") && item.networkRequirement !== "none") return false;
      if (state.filters.has("offline") && item.networkRequirement !== "none") return false;
      if (state.filters.has("workers") && !item.capabilityType.includes("worker")) return false;
      if (state.filters.has("skills") && item.capabilityType !== "agent-skill") return false;
      if (state.filters.has("mcp") && item.capabilityType !== "mcp") return false;
      for (const tag of ["creative", "ai", "media", "development", "experimental"]) {
        if (state.filters.has(tag) && !(item.tags || []).includes(tag)) return false;
      }
      if (state.filters.has("degraded") && !["DEGRADED", "OFFLINE", "BLOCKED"].includes(item.status)) return false;
      if (state.filters.has("retired") && item.status !== "RETIRED") return false;
      return true;
    });
  }

  function renderHardware() {
    const root = $("#capabilityHardware");
    if (!root || !state.hardware) return;
    root.replaceChildren();
    const entries = [
      ["Processor", state.hardware.cpu?.name],
      ["Memory", gib(state.hardware.memory?.totalBytes)],
      ["Logical processors", state.hardware.cpu?.logicalProcessors],
      ["Profile hash", shortHash(state.hardware.profileHash)],
    ];
    for (const [label, value] of entries) {
      const cell = document.createElement("div");
      cell.append(Object.assign(document.createElement("small"), { textContent: label }), Object.assign(document.createElement("b"), { textContent: value == null ? "Not exposed" : String(value) }));
      root.append(cell);
    }
  }

  function renderDetail() {
    const root = $("#capabilityDetail");
    if (!root) return;
    const item = state.selected;
    root.hidden = !item;
    root.replaceChildren();
    if (!item) return;
    root.append(Object.assign(document.createElement("h4"), { textContent: item.name }));
    const dl = document.createElement("dl");
    const entries = [
      ["What it does", item.description],
      ["State", `${item.status} · ${item.healthState}`],
      ["Hardware", `${item.hardwareFit?.state || item.compatibilityState} · ${(item.hardwareFit?.reasons || []).join(" ")}`],
      ["Runtime", item.runtime],
      ["Protocol", item.protocol],
      ["Cost", item.costClass],
      ["Free tier / quota", [item.freeTierNotes, item.quota, item.quotaReset].filter(Boolean).join(" · ") || "Not applicable"],
      ["Provider availability", item.currentAvailability || "Not applicable"],
      ["Network", item.networkRequirement],
      ["Authority", item.authorityLevel],
      ["Input / output", `${(item.inputTypes || []).join(", ")} → ${(item.outputTypes || []).join(", ")}`],
      ["Last verified", item.lastVerifiedAt || "Never verified"],
      ["Verification age", item.verificationAge],
      ["Permissions", `read ${item.permissions.reads.length}; write ${item.permissions.writes.length}; network ${item.permissions.network.length}; shell ${item.permissions.shell.length}`],
      ["Provenance", item.provenanceSupport ? "Supported" : "Not provided"],
      ["Known limit", item.knownLimitations],
      ["Replacement group", item.replacementGroup || "No declared alternative group"],
      ["Evidence", (item.evidence || []).join(" · ") || "Not exposed"],
    ];
    for (const [label, value] of entries) {
      const box = document.createElement("div");
      box.append(Object.assign(document.createElement("dt"), { textContent: label }), Object.assign(document.createElement("dd"), { textContent: value || "Not exposed" }));
      dl.append(box);
    }
    root.append(dl);
    const action = Object.assign(document.createElement("button"), { type: "button", className: "primary", textContent: "Inspect Capability" });
    action.addEventListener("click", () => { $("#capabilityInspection")?.scrollIntoView({ block: "start" }); $("#capabilityInspect")?.focus(); });
    root.append(action);
  }

  function renderInspection() {
    const root = $("#capabilityInspection");
    if (!root) return;
    root.hidden = !state.selected;
    if (!state.selected) return;
    const inspection = state.inspection;
    const status = inspection?.status || "no_inspection";
    text($("#capabilityInspectionTitle"), `Inspect ${state.selected.name}`);
    text($("#capabilityInspectionState"), status.replaceAll("_", " ").toUpperCase());
    text($("#capabilityInspectionSummary"), inspection ? `Inspection ${inspection.inspectionId}. Every decision remains bound to the exact plan and evidence hashes.` : "Create a static inspection plan. Nothing will be installed, downloaded, or executed.");
    const stageOrder = ["source", "dependencies", "hardware", "permissions", "test", "evidence", "decision"];
    let current = inspection ? (status === "inspection_plan_pending" ? 3 : status === "inspection_plan_approved" ? 4 : ["verification_candidate", "needs_review", "blocked", "incompatible", "failed", "verified"].includes(status) ? 6 : 0) : 0;
    document.querySelectorAll("[data-inspection-stage]").forEach(node => {
      const index = stageOrder.indexOf(node.dataset.inspectionStage);
      node.dataset.state = index < current ? "complete" : index === current ? "current" : "";
    });
    $("#capabilityInspect").disabled = Boolean(inspection && !["cancelled", "plan_rejected", "verified", "blocked", "incompatible", "failed"].includes(status));
    $("#capabilityPlanApprove").disabled = status !== "inspection_plan_pending";
    $("#capabilityPlanReject").disabled = status !== "inspection_plan_pending";
    $("#capabilityRunInspection").disabled = status !== "inspection_plan_approved";
    $("#capabilityOwnerVerify").disabled = status !== "verification_candidate";
    $("#capabilityOwnerBlock").disabled = !inspection?.evidenceHash || !["verification_candidate", "needs_review", "blocked", "incompatible", "failed"].includes(status);
    $("#capabilityOwnerIncompatible").disabled = !inspection?.evidenceHash || !["verification_candidate", "needs_review", "blocked", "incompatible", "failed"].includes(status);
    const truth = $("#capabilityInspectionTruth"); truth.replaceChildren();
    const evidence = inspection?.evidence || {};
    const rows = [
      ["Registry state", state.selected.status], ["Exact version", inspection?.plan?.capabilityVersion || state.selected.version],
      ["Plan", inspection?.plan?.planHash ? shortHash(inspection.plan.planHash) : "Not created"],
      ["Hardware", evidence.hardwareEvidence?.qualification?.state || state.selected.hardwareFit?.state || "Unknown"],
      ["Functional test", evidence.functionalEvidence?.state || "Not requested"], ["Verdict", evidence.finalInspectionVerdict || "No evidence"],
    ];
    for (const [label, value] of rows) { const card = document.createElement("article"); card.append(Object.assign(document.createElement("small"), { textContent: label }), Object.assign(document.createElement("b"), { textContent: value })); truth.append(card); }
    text($("#capabilityInspectionEvidence"), inspection ? JSON.stringify({ plan: inspection.plan, planApproval: inspection.planApproval, evidence: inspection.evidence, evidenceHash: inspection.evidenceHash, ownerDecision: inspection.ownerDecision, receipts: inspection.receipts }, null, 2) : "No inspection evidence.");
  }

  async function loadInspection() {
    state.inspection = null;
    if (!state.selected) { renderInspection(); return; }
    try {
      const value = await getJson(`/api/capability-inspections?capabilityId=${encodeURIComponent(state.selected.capabilityId)}`);
      state.inspection = value.inspections?.[0] || null;
    } catch (error) { text($("#capabilityInspectionSummary"), error.message); }
    renderInspection();
  }

  async function createInspectionPlan() {
    if (!state.selected) return;
    try {
      if (!state.authorityTemplate) state.authorityTemplate = (await getJson("/api/capability-inspections/authority-template")).authority;
      state.inspection = await postJson("/api/capability-inspections/plan", { projectId: window.twisGetActiveProject?.() || "", capabilityId: state.selected.capabilityId, authority: state.authorityTemplate, note: $("#capabilityInspectionNote")?.value || "" });
      renderInspection();
    } catch (error) { text($("#capabilityInspectionSummary"), error.message); }
  }
  async function planDecision(decision) {
    if (!state.inspection) return;
    try { state.inspection = await postJson(`/api/capability-inspections/${state.inspection.inspectionId}/plan-decision`, { decision, note: $("#capabilityInspectionNote")?.value || "" }); renderInspection(); }
    catch (error) { text($("#capabilityInspectionSummary"), error.message); }
  }
  async function runInspection() {
    if (!state.inspection) return;
    try { state.inspection = await postJson(`/api/capability-inspections/${state.inspection.inspectionId}/execute`, {}); renderInspection(); await load(); }
    catch (error) { text($("#capabilityInspectionSummary"), error.message); }
  }
  async function ownerDecision(decision) {
    if (!state.inspection) return;
    try { state.inspection = await postJson(`/api/capability-inspections/${state.inspection.inspectionId}/owner-decision`, { decision, note: $("#capabilityInspectionNote")?.value || "", evidenceHash: state.inspection.evidenceHash }); renderInspection(); await load(); }
    catch (error) { text($("#capabilityInspectionSummary"), error.message); }
  }

  function renderCapabilities() {
    const root = $("#capabilityList");
    if (!root) return;
    root.replaceChildren();
    const rows = visibleCapabilities();
    text($("#capabilityCount"), `${rows.length} shown · ${state.registry?.count || 0} registered`);
    if (!rows.length) {
      root.append(Object.assign(document.createElement("p"), { className: "muted", textContent: "No capability matches these filters." }));
      return;
    }
    for (const item of rows) {
      const card = Object.assign(document.createElement("button"), { type: "button", className: "capability-card" });
      card.dataset.status = item.status;
      card.dataset.fit = item.hardwareFit?.state || item.compatibilityState;
      card.dataset.selected = String(state.selected?.capabilityId === item.capabilityId);
      card.append(
        Object.assign(document.createElement("strong"), { textContent: item.name }),
        Object.assign(document.createElement("span"), { className: "capability-state", textContent: item.status }),
        Object.assign(document.createElement("small"), { textContent: `${item.capabilityType} · ${item.costClass} · ${item.hardwareFit?.state || item.compatibilityState}` }),
        Object.assign(document.createElement("p"), { textContent: item.description })
      );
      card.addEventListener("click", () => { state.selected = item; renderCapabilities(); renderDetail(); void loadInspection(); });
      root.append(card);
    }
  }

  function renderProtocols() {
    const root = $("#capabilityProtocols");
    if (!root) return;
    root.replaceChildren();
    const skills = state.skills || {};
    const mcp = state.mcp || {};
    const cards = [
      ["Agent Skills", `${skills.count || 0} discovered`, "Metadata and resource counts only; scripts are never executed during discovery."],
      ["MCP catalog", `${mcp.count || 0} registered`, "2026-07-28 discovery metadata only; no tool or resource is invoked automatically."],
      ["A2A + WASI", "Contract only", "Descriptor validation is available; execution stays deferred until a separately approved runtime exists."],
    ];
    for (const [title, stateLabel, detail] of cards) {
      const card = document.createElement("article");
      card.append(Object.assign(document.createElement("h4"), { textContent: title }), Object.assign(document.createElement("b"), { textContent: stateLabel }), Object.assign(document.createElement("p"), { textContent: detail }));
      root.append(card);
    }
  }

  function renderRecommendation(value) {
    state.recommendation = value;
    const root = $("#capabilityRecommendation");
    if (!root) return;
    root.replaceChildren();
    const chosen = value.recommended;
    const candidate = value.discoveredCandidates?.[0] || value.matched?.[0];
    root.dataset.state = chosen ? "verified" : "proposal";
    root.append(Object.assign(document.createElement("h4"), { textContent: chosen ? `Use ${chosen.name}` : candidate ? `Inspect ${candidate.name}` : "Create our own governed capability proposal" }));
    root.append(Object.assign(document.createElement("p"), { textContent: value.decision }));
    root.append(Object.assign(document.createElement("p"), { className: "muted", textContent: `Registry ${shortHash(value.registryHash)} · group ${value.replacementGroup || "unclassified"}` }));
    $("#capabilityPrepareBuild").hidden = false;
    $("#capabilityPrepareModule").hidden = !value.createOurOwn;
  }

  async function recommend() {
    const request = ($("#buildCapabilityRequest")?.value || "").trim();
    if (!request) { text($("#capabilityRecommendation"), "Describe the capability you need first."); return; }
    try {
      const value = await getJson(`/api/capability-registry/recommend?request=${encodeURIComponent(request)}`);
      renderRecommendation(value);
    } catch (error) { text($("#capabilityRecommendation"), error.message); }
  }

  function setInput(selector, value) { const node = $(selector); if (node) { node.value = value || ""; node.dispatchEvent(new Event("input", { bubbles: true })); } }
  function prepareBuild() {
    const request = ($("#buildCapabilityRequest")?.value || "").trim();
    window.twisOpenBuilder?.("build");
    setInput("#build-capabilityRequest", request);
    setInput("#build-buildGoal", `Create a bounded work order for: ${request}`);
    setInput("#build-existingContext", state.recommendation ? `Capability registry ${state.recommendation.registryHash}; deterministic decision: ${state.recommendation.decision}` : "Use the current verified Capability Bay decision.");
    setInput("#builderGoal", "Bind this work order to current capability, hardware, permission, cost, provenance, receipt, and rollback evidence.");
  }

  function prepareModule() {
    const request = ($("#buildCapabilityRequest")?.value || "").trim();
    window.twisOpenBuilder?.("module");
    const profile = $("#builderProfile");
    if (profile && [...profile.options].some(option => option.value === "Local JavaScript worker")) profile.value = "Local JavaScript worker";
    setInput("#module-moduleName", request ? `${request} capability` : "New Workshop capability");
    setInput("#module-scaffoldType", "Capability proposal only");
    setInput("#module-purpose", `Create a governed free-first proposal for: ${request}`);
    setInput("#module-problemSolved", state.recommendation?.decision || "No verified free capability currently satisfies this request.");
    setInput("#builderGoal", "Produce a proposal scaffold only. Do not install, execute, download, activate, or submit anything.");
  }

  function prepareCompassFinding() {
    window.twisOpenBuilder?.("module");
    const profile = $("#builderProfile");
    if (profile && [...profile.options].some(option => option.value === "TWIS native capability")) profile.value = "TWIS native capability";
    setInput("#module-scaffoldType", "Capability proposal only");
    setInput("#module-purpose", "Inspect and catalog one explicit Artifact Compass finding as a DISCOVERED capability candidate.");
    setInput("#module-integrationPoints", "Artifact Compass finding → Capability candidate → Modules inspection → testing → approval. Select the finding as a registered source in this builder.");
    setInput("#builderGoal", "Retain source identity and relocation evidence. Discovery is not verification, installation, activation, or execution.");
  }

  async function load() {
    if (!$("#capabilityBay")) return;
    try {
      setStatus("INSPECTING");
      [state.registry, state.hardware, state.skills, state.mcp] = await Promise.all([
        getJson("/api/capability-registry"), getJson("/api/hardware-profile"), getJson("/api/agent-skills"), getJson("/api/mcp-catalog"),
      ]);
      renderHardware(); renderCapabilities(); renderProtocols();
      if (state.selected) {
        state.selected = state.registry.capabilities.find(item => item.capabilityId === state.selected.capabilityId) || null;
        renderDetail(); renderInspection();
      }
      text($("#capabilityRegistryHash"), `Registry ${shortHash(state.registry.registryHash)} · hardware ${shortHash(state.registry.hardwareProfileHash)}`);
      setStatus("VALID REGISTRY");
    } catch (error) { setStatus("UNAVAILABLE", true); text($("#capabilityCount"), error.message); }
  }

  function bind() {
    if (!$("#capabilityBay")) return;
    $("#capabilitySearch")?.addEventListener("input", renderCapabilities);
    $("#capabilityRefresh")?.addEventListener("click", () => void load());
    $("#capabilityRecommend")?.addEventListener("click", () => void recommend());
    $("#capabilityPrepareBuild")?.addEventListener("click", prepareBuild);
    $("#capabilityPrepareModule")?.addEventListener("click", prepareModule);
    $("#capabilityCompassHandoff")?.addEventListener("click", prepareCompassFinding);
    $("#capabilityInspect")?.addEventListener("click", () => void createInspectionPlan());
    $("#capabilityPlanApprove")?.addEventListener("click", () => void planDecision("approve"));
    $("#capabilityPlanReject")?.addEventListener("click", () => void planDecision("reject"));
    $("#capabilityRunInspection")?.addEventListener("click", () => void runInspection());
    $("#capabilityOwnerVerify")?.addEventListener("click", () => void ownerDecision("verify"));
    $("#capabilityOwnerBlock")?.addEventListener("click", () => void ownerDecision("block"));
    $("#capabilityOwnerIncompatible")?.addEventListener("click", () => void ownerDecision("incompatible"));
    document.querySelectorAll("[data-capability-filter]").forEach(button => button.addEventListener("click", () => {
      const key = button.dataset.capabilityFilter;
      state.filters.has(key) ? state.filters.delete(key) : state.filters.add(key);
      button.setAttribute("aria-pressed", String(state.filters.has(key)));
      renderCapabilities();
    }));
    window.addEventListener("twis:project-changed", () => void load());
    void load();
  }

  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", bind) : bind();
  window.twisCapabilityBay = { reload: load, getState: () => ({ registryHash: state.registry?.registryHash || null, hardwareProfileHash: state.hardware?.profileHash || null }) };
})();

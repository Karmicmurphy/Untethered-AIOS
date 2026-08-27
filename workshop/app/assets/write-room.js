(() => {
"use strict";

const $ = selector => document.querySelector(selector);
const LOCAL_PREFIX = "twisHolo.write.recovery.v1.";
const RECOVERY_DELAY = 450;
const AUTOSAVE_DELAY = 1800;
const state = {
  document: null,
  dirty: false,
  editGeneration: 0,
  recoveryTimer: null,
  autosaveTimer: null,
  saving: null,
  pendingRecovery: null,
  activeProposal: null,
  restoreTarget: null,
  restoreOperationId: null,
  summariesProject: "",
  retryCount: 0,
  aiJob: null,
  aiSelection: null,
  aiSources: [],
  aiAppliedBaseVersion: null,
};

const elements = {
  projectPicker: $("#writeProjectPicker"),
  title: $("#docTitle"),
  body: $("#docBody"),
  status: $("#writeSaveStatus"),
  versionBadge: $("#writeVersionBadge"),
  words: $("#wordCount"),
  newButton: $("#newDoc"),
  snapshotButton: $("#snapshotDoc"),
  saveButton: $("#saveDoc"),
  rollbackRestoreButton: $("#rollbackWriteRestore"),
  recoveryBanner: $("#writeRecoveryBanner"),
  recoveryMessage: $("#writeRecoveryMessage"),
  loadRecovery: $("#loadWriteRecovery"),
  discardRecovery: $("#discardWriteRecovery"),
  versions: $("#versions"),
  compareLeft: $("#compareLeft"),
  compareRight: $("#compareRight"),
  compareButton: $("#compareWriteVersions"),
  refreshHistory: $("#refreshWriteHistory"),
  action: $("#writeAction"),
  command: $("#writeCommand"),
  propose: $("#proposeWriteAction"),
  proposalPanel: $("#writeProposalPanel"),
  proposalTitle: $("#writeProposalTitle"),
  proposalStatus: $("#writeProposalStatus"),
  proposalFindings: $("#writeProposalFindings"),
  proposalDiff: $("#writeProposalDiff"),
  proposalNote: $("#writeProposalNote"),
  approveProposal: $("#approveWriteProposal"),
  rejectProposal: $("#rejectWriteProposal"),
  rollbackProposal: $("#rollbackWriteProposal"),
  exportFormat: $("#writeExportFormat"),
  exportProvenance: $("#writeExportProvenance"),
  exportButton: $("#exportWriteProject"),
  exportResult: $("#writeExportResult"),
  snapshotDialog: $("#snapshotDialog"),
  snapshotLabel: $("#snapshotLabel"),
  confirmSnapshot: $("#confirmSnapshot"),
  newDialog: $("#newWriteDialog"),
  newTitle: $("#newWriteTitle"),
  newContent: $("#newWriteContent"),
  confirmNew: $("#confirmNewWrite"),
  restoreDialog: $("#restoreWriteDialog"),
  restoreMessage: $("#restoreWriteMessage"),
  confirmRestore: $("#confirmWriteRestore"),
  compareDialog: $("#compareWriteDialog"),
  closeCompare: $("#closeWriteCompare"),
  compareSummary: $("#writeCompareSummary"),
  compareDiff: $("#writeCompareDiff"),
  aiStudio: $("#writeAiStudio"), aiOpen: $("#openWriteAiStudio"), aiAction: $("#writeAiAction"),
  aiPreset: $("#writeAiPreset"), aiInstruction: $("#writeAiInstruction"), aiScope: $("#writeAiScope"),
  aiScopeDetail: $("#writeAiScopeDetail"), aiContextCount: $("#writeAiContextCount"), aiContextSources: $("#writeAiContextSources"),
  aiCreatePlan: $("#writeAiCreatePlan"), aiCancel: $("#writeAiCancel"), aiStatus: $("#writeAiStatus"),
  aiPlan: $("#writeAiPlan"), aiPlanState: $("#writeAiPlanState"), aiPlanSummary: $("#writeAiPlanSummary"),
  aiPlanNote: $("#writeAiPlanNote"), aiApprovePlan: $("#writeAiApprovePlan"), aiRejectPlan: $("#writeAiRejectPlan"), aiRun: $("#writeAiRun"),
  aiResult: $("#writeAiResult"), aiResultState: $("#writeAiResultState"), aiOriginal: $("#writeAiOriginal"), aiProposal: $("#writeAiProposal"),
  aiResultNote: $("#writeAiResultNote"), aiApproveResult: $("#writeAiApproveResult"), aiRejectResult: $("#writeAiRejectResult"),
  aiApprovedActions: $("#writeAiApprovedActions"), aiApplyMode: $("#writeAiApplyMode"), aiCopy: $("#writeAiCopy"), aiApply: $("#writeAiApply"),
  aiSaveVersion: $("#writeAiSaveVersion"), aiSaveDraft: $("#writeAiSaveDraft"), aiRollbackVersion: $("#writeAiRollbackVersion"),
  aiReadDraft: $("#writeAiReadDraft"), aiReadProposal: $("#writeAiReadProposal"), aiStopSpeaking: $("#writeAiStopSpeaking"),
  aiEngineState: $("#writeAiEngineState"), aiStartModel: $("#writeAiStartModel"),
};

const WRITE_AI_ACTIONS = [
  "Brainstorm story ideas", "Continue passage", "Rewrite selection", "Make darker", "Make funnier",
  "Make more emotional", "Make more direct", "Make stranger or surreal", "Improve dialogue",
  "Suggest dialogue", "Suggest next scene", "Develop character", "Generate alternate version",
  "Suggest structure", "Summarize direction", "Suggest creative possibilities",
];

function activeProject() {
  return window.twisGetActiveProject?.() || $("#projectSelect")?.value || "";
}

function localKey(artifactId) {
  return `${LOCAL_PREFIX}${artifactId}`;
}

function localRecovery(artifactId) {
  try {
    const value = JSON.parse(localStorage.getItem(localKey(artifactId)) || "null");
    return value && value.artifactId === artifactId ? value : null;
  } catch {
    return null;
  }
}

function saveLocalRecovery() {
  if (!state.document || !state.dirty) return false;
  const value = {
    artifactId: state.document.id,
    projectId: state.document.projectId,
    baseVersion: state.document.currentVersion,
    title: elements.title.value,
    content: elements.body.value,
    updatedAt: new Date().toISOString(),
  };
  try {
    localStorage.setItem(localKey(state.document.id), JSON.stringify(value));
    return true;
  } catch {
    setStatus("Browser recovery storage is full. Use Save now.", "error");
    return false;
  }
}

function clearLocalRecovery(artifactId) {
  try {
    localStorage.removeItem(localKey(artifactId));
  } catch {
    // The server-side recovery record remains authoritative when browser storage is unavailable.
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {"Content-Type": "application/json", ...(options.headers || {})},
    ...options,
  });
  const text = await response.text();
  let value = null;
  if (text) {
    try {
      value = JSON.parse(text);
    } catch {
      value = {error: text};
    }
  }
  if (!response.ok) {
    const error = new Error(value?.error || `Request failed (${response.status})`);
    error.code = value?.code || "request_failed";
    error.details = value?.details || {};
    throw error;
  }
  return value;
}

function setStatus(message, kind = "normal") {
  elements.status.textContent = message;
  elements.status.dataset.state = kind;
}

function formatDate(value) {
  if (!value) return "unknown time";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "unknown time" : date.toLocaleString();
}

function countWords() {
  const count = (elements.body.value.trim().match(/\S+/g) || []).length;
  elements.words.textContent = `${count} word${count === 1 ? "" : "s"}`;
}

function setEnabled(enabled) {
  elements.title.disabled = !enabled;
  elements.body.disabled = !enabled;
  elements.snapshotButton.disabled = !enabled;
  elements.saveButton.disabled = !enabled;
  elements.refreshHistory.disabled = !enabled;
  elements.action.disabled = !enabled;
  elements.command.disabled = !enabled;
  elements.propose.disabled = !enabled;
  elements.exportFormat.disabled = !enabled;
  elements.exportButton.disabled = !enabled;
  elements.aiOpen.disabled = !enabled;
  elements.aiCreatePlan.disabled = !enabled;
  ["#writeWorkerRead", "#writeWorkerStructure", "#writeWorkerNote"].forEach(selector => {
    const button = $(selector);
    if (button) button.disabled = !enabled;
  });
}

function clearTimers() {
  clearTimeout(state.recoveryTimer);
  clearTimeout(state.autosaveTimer);
  state.recoveryTimer = null;
  state.autosaveTimer = null;
}

function schedulePersistence() {
  clearTimers();
  state.recoveryTimer = setTimeout(() => void persistServerRecovery(), RECOVERY_DELAY);
  state.autosaveTimer = setTimeout(() => void saveNow("autosave"), AUTOSAVE_DELAY);
}

function onInput() {
  if (!state.document) return;
  state.dirty = true;
  state.editGeneration += 1;
  const localRecoveryReady = saveLocalRecovery();
  countWords();
  if (localRecoveryReady) {
    setStatus("Unsaved changes — local recovery ready", "dirty");
  }
  schedulePersistence();
}

async function persistServerRecovery() {
  if (!state.document || !state.dirty) return;
  const documentAtStart = state.document;
  try {
    const result = await api(`/api/write-projects/${encodeURIComponent(documentAtStart.id)}/recovery`, {
      method: "POST",
      body: JSON.stringify({
        title: elements.title.value,
        content: elements.body.value,
        baseVersion: documentAtStart.currentVersion,
      }),
    });
    if (state.document?.id === documentAtStart.id && state.dirty) {
      setStatus(`Unsaved changes — recovery stored ${formatDate(result.updatedAt)}`, "recovery");
    }
    await refreshProject(documentAtStart.projectId);
  } catch (error) {
    if (state.document?.id === documentAtStart.id) {
      setStatus(`Recovery save failed: ${error.message}`, "error");
    }
  }
}

async function saveNow(cause = "manual") {
  if (!state.document) return null;
  if (state.saving) {
    await state.saving;
    if (state.dirty && cause === "manual") return saveNow(cause);
    return state.document;
  }
  if (!state.dirty && cause === "autosave") return state.document;
  clearTimers();
  const artifactId = state.document.id;
  const generation = state.editGeneration;
  const title = elements.title.value;
  const content = elements.body.value;
  const baseVersion = state.document.currentVersion;
  setStatus(cause === "autosave" ? "Autosaving…" : "Saving…", "saving");
  state.saving = api(`/api/write-projects/${encodeURIComponent(artifactId)}/save`, {
    method: "POST",
    body: JSON.stringify({
      title,
      content,
      baseVersion,
      cause,
      actor: "local-owner",
    }),
  });
  try {
    const result = await state.saving;
    if (state.document?.id !== artifactId) return result;
    state.document = result;
    if (state.editGeneration === generation) {
      state.dirty = false;
      clearLocalRecovery(artifactId);
      state.pendingRecovery = null;
      elements.recoveryBanner.hidden = true;
      setStatus(
        result.unchanged
          ? `Already saved — version ${result.currentVersion}`
          : `${cause === "autosave" ? "Autosaved" : "Saved"} ${formatDate(result.lastSavedAt)}`,
        "saved",
      );
    } else {
      state.dirty = true;
      saveLocalRecovery();
      setStatus("New edits remain — local recovery ready", "dirty");
      schedulePersistence();
    }
    renderDocumentState();
    await refreshProject(result.projectId);
    window.twisReloadArtifacts?.();
    return result;
  } catch (error) {
    state.dirty = true;
    saveLocalRecovery();
    if (error.code === "write_version_conflict") {
      setStatus("Save stopped: a newer saved version exists. Reopen this writing project.", "error");
    } else {
      if (cause === "autosave" && state.retryCount < 2) {
        state.retryCount += 1;
        setStatus(`Autosave failed: ${error.message}. Retrying locally…`, "error");
        state.autosaveTimer = setTimeout(() => void saveNow("autosave"), 5000);
      } else {
        setStatus(`Save failed: ${error.message}. Use Save now to retry.`, "error");
      }
    }
    if (cause !== "autosave") throw error;
    return null;
  } finally {
    if (!state.dirty) state.retryCount = 0;
    state.saving = null;
  }
}

function chooseRecovery(documentValue) {
  const local = localRecovery(documentValue.id);
  const server = documentValue.recovery
    ? {
        artifactId: documentValue.id,
        projectId: documentValue.projectId,
        baseVersion: documentValue.recovery.baseVersion,
        title: documentValue.recovery.title,
        content: documentValue.recovery.content,
        updatedAt: documentValue.recovery.updatedAt,
        source: "durable local database",
      }
    : null;
  const candidates = [local && {...local, source: "browser recovery"}, server].filter(Boolean);
  candidates.sort((left, right) => String(right.updatedAt).localeCompare(String(left.updatedAt)));
  const chosen = candidates[0] || null;
  if (
    chosen
    && chosen.title === documentValue.title
    && chosen.content === documentValue.content
  ) {
    return null;
  }
  return chosen;
}

function showRecovery() {
  const recovery = state.pendingRecovery;
  elements.recoveryBanner.hidden = !recovery;
  if (!recovery) return;
  elements.recoveryMessage.textContent =
    `Saved ${formatDate(recovery.updatedAt)} in ${recovery.source}. ` +
    `It is based on version ${recovery.baseVersion}.`;
}

function renderComparison(target, comparison) {
  target.replaceChildren();
  const operations = comparison?.operations || [];
  if (!operations.length) {
    const unchanged = document.createElement("p");
    unchanged.className = "muted";
    unchanged.textContent = "No text differences.";
    target.append(unchanged);
    return;
  }
  const labels = {insert: "Added", delete: "Removed", replace: "Replaced"};
  for (const operation of operations) {
    const change = document.createElement("section");
    change.className = "write-change";
    const header = document.createElement("header");
    header.textContent =
      `${labels[operation.kind] || "Changed"} · before lines ${operation.leftStart}–${operation.leftEnd || operation.leftStart}, ` +
      `after lines ${operation.rightStart}–${operation.rightEnd || operation.rightStart}`;
    const grid = document.createElement("div");
    grid.className = "write-change-grid";
    for (const [label, lines] of [
      ["Before", operation.leftLines || []],
      ["After", operation.rightLines || []],
    ]) {
      const side = document.createElement("div");
      side.className = "write-change-side";
      const sideLabel = document.createElement("b");
      sideLabel.textContent = label;
      const content = document.createElement("pre");
      content.textContent = lines.length ? lines.join("\n") : "(nothing)";
      side.append(sideLabel, content);
      grid.append(side);
    }
    change.append(header, grid);
    target.append(change);
  }
}

function viewVersion(version) {
  elements.compareSummary.replaceChildren();
  for (const message of [
    `Version ${version.number}`,
    version.label || version.cause,
    formatDate(version.createdAt),
  ]) {
    const badge = document.createElement("span");
    badge.textContent = message;
    elements.compareSummary.append(badge);
  }
  elements.compareDiff.replaceChildren();
  const content = document.createElement("pre");
  content.textContent = version.content || "(empty writing project)";
  elements.compareDiff.append(content);
  elements.compareDialog.showModal();
}

function renderHistory() {
  const versions = state.document?.versions || [];
  elements.versions.replaceChildren();
  if (!versions.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No durable versions yet.";
    elements.versions.append(empty);
  }
  for (const version of versions) {
    const row = document.createElement("div");
    row.className = "write-version";
    const text = document.createElement("div");
    const title = document.createElement("b");
    title.textContent = `v${version.number} — ${version.label || version.cause}`;
    const meta = document.createElement("small");
    meta.textContent = `${formatDate(version.createdAt)} · ${version.cause}`;
    text.append(title, meta);
    const actions = document.createElement("div");
    actions.className = "write-version-actions";
    const view = document.createElement("button");
    view.className = "link";
    view.textContent = "View";
    view.addEventListener("click", () => viewVersion(version));
    const restore = document.createElement("button");
    restore.className = "link";
    restore.textContent = "Restore";
    restore.disabled = version.number === state.document.currentVersion;
    restore.addEventListener("click", () => prepareRestore(version));
    actions.append(view, restore);
    row.append(text, actions);
    elements.versions.append(row);
  }
  const options = versions.map(version => {
    const option = document.createElement("option");
    option.value = String(version.number);
    option.textContent = `v${version.number} — ${version.label || version.cause}`;
    return option;
  });
  elements.compareLeft.replaceChildren(...options.map(option => option.cloneNode(true)));
  elements.compareRight.replaceChildren(...options.map(option => option.cloneNode(true)));
  if (versions.length > 1) {
    elements.compareLeft.value = String(versions[1].number);
    elements.compareRight.value = String(versions[0].number);
  }
  const canCompare = versions.length > 1;
  elements.compareLeft.disabled = !canCompare;
  elements.compareRight.disabled = !canCompare;
  elements.compareButton.disabled = !canCompare;
}

function renderProposal(proposal) {
  state.activeProposal = proposal || null;
  elements.proposalPanel.hidden = !proposal;
  if (!proposal) return;
  elements.proposalTitle.textContent =
    `${proposal.action.replaceAll("_", " ")} proposal`;
  elements.proposalStatus.textContent = proposal.status.replaceAll("_", " ");
  elements.proposalFindings.replaceChildren();
  const findings = document.createElement("div");
  findings.className = "write-findings";
  for (const finding of proposal.findings || []) {
    const row = document.createElement("div");
    row.className = "write-finding";
    row.textContent = finding.message || "No finding text.";
    findings.append(row);
  }
  elements.proposalFindings.append(findings);
  if (proposal.comparison?.changed) {
    renderComparison(elements.proposalDiff, proposal.comparison);
  } else {
    elements.proposalDiff.replaceChildren();
    const unchanged = document.createElement("p");
    unchanged.className = "muted";
    unchanged.textContent = "This proposal reports findings only. It does not change the writing.";
    elements.proposalDiff.append(unchanged);
  }
  const awaiting = proposal.status === "awaiting_approval";
  elements.approveProposal.hidden = !awaiting;
  elements.rejectProposal.hidden = !awaiting;
  elements.proposalNote.disabled = !awaiting;
  elements.proposalNote.value = proposal.decisionNote || "";
  elements.rollbackProposal.hidden = !(
    proposal.status === "approved"
    && proposal.modifiesContent
    && proposal.appliedVersionId
  );
}

function renderDocumentState() {
  const documentValue = state.document;
  setEnabled(Boolean(documentValue));
  if (!documentValue) {
    elements.title.value = "Untitled";
    elements.body.value = "";
    elements.body.placeholder = "Create a writing project to begin.";
    elements.versionBadge.textContent = "No saved version";
    elements.rollbackRestoreButton.hidden = true;
    renderHistory();
    renderProposal(null);
    countWords();
    return;
  }
  if (!state.dirty) {
    elements.title.value = documentValue.title;
    elements.body.value = documentValue.content || "";
  }
  elements.body.placeholder = "Start writing.";
  if ([...elements.projectPicker.options].some(option => option.value === documentValue.id)) {
    elements.projectPicker.value = documentValue.id;
  }
  elements.versionBadge.textContent =
    `Version ${documentValue.currentVersion} · ${documentValue.versionCount} saved`;
  renderHistory();
  renderProposal(
    state.activeProposal
    || (documentValue.proposals || []).find(proposal => proposal.status === "awaiting_approval")
    || null,
  );
  elements.rollbackRestoreButton.hidden = !state.restoreOperationId;
  countWords();
}

async function openProject(artifactId) {
  if (!artifactId) return;
  if (state.document && state.document.id !== artifactId && state.dirty) {
    try {
      await saveNow("manual");
    } catch {
      return;
    }
  }
  clearTimers();
  setStatus("Opening writing project…", "loading");
  try {
    const documentValue = await api(`/api/write-projects/${encodeURIComponent(artifactId)}`);
    state.document = documentValue;
    state.dirty = false;
    state.editGeneration += 1;
    state.activeProposal = null;
    state.restoreOperationId = null;
    state.pendingRecovery = chooseRecovery(documentValue);
    renderDocumentState();
    showRecovery();
    setStatus(`Saved ${formatDate(documentValue.lastSavedAt)}`, "saved");
    await loadAiSources();
  } catch (error) {
    setStatus(`Could not open writing project: ${error.message}`, "error");
  }
}

async function createFromText(title = "Untitled", content = "") {
  if (!window.twisHasCompanion?.()) {
    setStatus("The local companion is required for durable writing projects.", "error");
    return;
  }
  if (state.document && state.dirty) {
    try {
      await saveNow("manual");
    } catch {
      return;
    }
  }
  const projectId = activeProject();
  if (!projectId) {
    setStatus("Choose a Workshop project first.", "error");
    return;
  }
  setStatus("Creating writing project…", "saving");
  try {
    const documentValue = await api("/api/write-projects", {
      method: "POST",
      body: JSON.stringify({
        projectId,
        title,
        content,
        actor: "local-owner",
      }),
    });
    state.document = documentValue;
    state.dirty = false;
    state.editGeneration += 1;
    state.pendingRecovery = null;
    state.activeProposal = null;
    state.restoreOperationId = null;
    showRecovery();
    renderDocumentState();
    setStatus("Writing project created and saved.", "saved");
    await refreshProject(projectId);
    await window.twisReloadArtifacts?.();
  } catch (error) {
    setStatus(`Create failed: ${error.message}`, "error");
  }
}

async function refreshProject(projectId = activeProject()) {
  if (!projectId || !window.twisHasCompanion?.()) return [];
  try {
    const summaries = await api(`/api/write-projects?projectId=${encodeURIComponent(projectId)}`);
    window.twisWriteSummaries = new Map(summaries.map(summary => [summary.id, summary]));
    state.summariesProject = projectId;
    elements.projectPicker.replaceChildren();
    if (!summaries.length) {
      const empty = document.createElement("option");
      empty.value = "";
      empty.textContent = "No writing projects yet";
      elements.projectPicker.append(empty);
    } else {
      for (const summary of summaries) {
        const option = document.createElement("option");
        option.value = summary.id;
        option.textContent = `${summary.title}${summary.hasRecovery ? " — recovery available" : ""}`;
        elements.projectPicker.append(option);
      }
      if (state.document && summaries.some(summary => summary.id === state.document.id)) {
        elements.projectPicker.value = state.document.id;
      }
    }
    window.dispatchEvent(new CustomEvent("twis:write-summaries", {detail: {projectId}}));
    return summaries;
  } catch {
    return [];
  }
}

async function onRoomOpen() {
  const projectId = activeProject();
  const summaries = await refreshProject(projectId);
  if (state.document?.projectId === projectId) {
    await refreshAiModelStatus(); await loadAiSources(); await recoverAiJob(); return;
  }
  if (summaries[0]) {
    await openProject(summaries[0].id);
  } else {
    state.document = null;
    state.dirty = false;
    state.pendingRecovery = null;
    state.activeProposal = null;
    showRecovery();
    renderDocumentState();
    setStatus("Create your first writing project.", "normal");
  }
  await refreshAiModelStatus();
  await loadAiSources();
  await recoverAiJob();
}

function aiRecoveryKey() { return `twis.write.ai.job.${activeProject()}`; }

function setAiStatus(message, failed = false) {
  elements.aiStatus.textContent = message;
  elements.aiStatus.dataset.state = failed ? "failed" : "";
}

function captureAiSelection() {
  const start = elements.body.selectionStart;
  const end = elements.body.selectionEnd;
  const raw = start !== end ? elements.body.value.slice(start, end) : "";
  const trimmed = raw.trim();
  const offset = trimmed ? raw.indexOf(trimmed) : 0;
  const selection = trimmed ? {start: start + offset, end: start + offset + trimmed.length, text: trimmed} : null;
  elements.aiScope.textContent = selection ? "Selected passage" : "Whole draft";
  elements.aiScopeDetail.textContent = selection ? `${selection.text.length} characters bound to this plan.` : "No selected passage; the saved whole draft is bound to this plan.";
  return selection;
}

async function refreshAiModelStatus() {
  try {
    const value = await api("/api/local-ai/status");
    const model = value.models?.[0];
    elements.aiEngineState.textContent = model ? `${model.state} · ${model.displayName}` : "MODEL UNAVAILABLE";
    elements.aiStartModel.hidden = model?.state === "READY";
  } catch (error) {
    elements.aiEngineState.textContent = `ERROR · ${error.message}`;
  }
}

async function startAiModel() {
  elements.aiStartModel.disabled = true;
  setAiStatus("Starting the registered local CPU model and running its real health inference…");
  try {
    await api("/api/local-ai/runtime/start", {method: "POST", body: "{}"});
    await refreshAiModelStatus();
    setAiStatus("Local model READY.");
  } catch (error) {
    setAiStatus(`Model start failed safely: ${error.message}`, true);
  } finally {
    elements.aiStartModel.disabled = false;
  }
}

function selectedAiContextIds() {
  return [...elements.aiContextSources.querySelectorAll("input:checked")].map(input => input.value);
}

async function loadAiSources() {
  const projectId = activeProject();
  if (!projectId || !state.document) return;
  try {
    state.aiSources = await api(`/api/local-worker-sources?projectId=${encodeURIComponent(projectId)}`);
    elements.aiContextSources.replaceChildren();
    for (const source of state.aiSources.filter(item => item.artifactId !== state.document.id && item.allowedWorkers?.includes("local-ai-rewrite"))) {
      const label = document.createElement("label"); label.className = "write-ai-context-source";
      const input = Object.assign(document.createElement("input"), {type: "checkbox", value: source.artifactId});
      const text = document.createElement("span");
      text.textContent = `${source.title} · ${source.kind} · ${source.sha256.slice(0, 12)}…`;
      input.addEventListener("change", () => {
        if (selectedAiContextIds().length > 3) { input.checked = false; setAiStatus("Choose no more than three context sources.", true); }
        elements.aiContextCount.textContent = `${selectedAiContextIds().length} selected`;
      });
      label.append(input, text); elements.aiContextSources.append(label);
    }
    if (!elements.aiContextSources.children.length) elements.aiContextSources.textContent = "No additional registered text sources are available in this project.";
  } catch (error) { setAiStatus(`Context list unavailable: ${error.message}`, true); }
}

function renderAiJob(job) {
  state.aiJob = job;
  if (job.plan.selection && !state.aiSelection) {
    const start = elements.body.value.indexOf(job.plan.selection);
    if (start >= 0) state.aiSelection = {start, end: start + job.plan.selection.length, text: job.plan.selection};
  }
  localStorage.setItem(aiRecoveryKey(), job.jobId);
  elements.aiPlan.hidden = false;
  elements.aiPlanState.textContent = job.statusLabel;
  elements.aiPlanSummary.textContent = [
    `Action: ${job.plan.destinationProfile}`,
    `Scope: ${job.plan.selection ? "selected passage" : "whole draft"}`,
    `Model: ${job.plan.inference?.modelId || "unavailable"}`,
    `Preset: ${job.plan.inference?.parameterPreset || "unavailable"}`,
    `Sources:\n${job.sources.map(source => `  ${source.title} · ${source.sha256}`).join("\n")}`,
    `Instruction: ${job.plan.ownerGoal || "No additional instruction"}`,
  ].join("\n\n");
  elements.aiApprovePlan.hidden = !job.actions.approvePlan;
  elements.aiRejectPlan.hidden = !job.actions.rejectPlan;
  elements.aiRun.hidden = !job.actions.execute;
  elements.aiCancel.disabled = !job.actions.cancel;
  const output = job.result?.output;
  elements.aiResult.hidden = !output?.proposedText;
  if (output?.proposedText) {
    elements.aiResultState.textContent = job.statusLabel;
    elements.aiOriginal.textContent = state.aiSelection?.text || elements.body.value;
    elements.aiProposal.textContent = output.proposedText;
    elements.aiApproveResult.hidden = !job.actions.approveResult;
    elements.aiRejectResult.hidden = !job.actions.rejectResult;
    elements.aiApprovedActions.hidden = !["result_approved", "draft_saved"].includes(job.status);
    elements.aiSaveDraft.hidden = !job.actions.saveDraft;
  }
  setAiStatus(job.statusLabel);
}

async function aiJobAction(action, body = {}) {
  if (!state.aiJob) return;
  try {
    const value = await api(`/api/local-worker-jobs/${encodeURIComponent(state.aiJob.jobId)}/${action}`, {
      method: "POST", body: JSON.stringify({actor: "local-owner", ...body}),
    });
    renderAiJob(value);
    if (["save-draft", "rollback"].includes(action)) await window.twisReloadArtifacts?.();
  } catch (error) { setAiStatus(`${action.replaceAll("-", " ")} failed safely: ${error.message}`, true); }
}

async function createAiPlan() {
  if (!state.document) return;
  const selection = captureAiSelection();
  if (state.dirty) { try { await saveNow("manual"); } catch { return; } }
  state.aiSelection = selection;
  state.aiAppliedBaseVersion = null;
  try {
    const sourceArtifactIds = [state.document.id, ...selectedAiContextIds()];
    const job = await api("/api/local-worker-jobs/plan", {method: "POST", body: JSON.stringify({
      projectId: state.document.projectId, workerId: "local-ai-rewrite", sourceArtifactIds,
      destinationProfile: elements.aiAction.value, goal: elements.aiInstruction.value,
      selection: selection?.text || null, inferencePreset: elements.aiPreset.value,
      purpose: `Prepare ${elements.aiAction.value} as proposed Write Studio content`, actor: "local-owner",
    })});
    renderAiJob(job);
    elements.aiPlan.scrollIntoView({block: "nearest"});
  } catch (error) { setAiStatus(`Plan stopped safely: ${error.message}`, true); }
}

async function recoverAiJob() {
  const jobId = localStorage.getItem(aiRecoveryKey());
  if (!jobId || state.aiJob?.jobId === jobId) return;
  try {
    const job = await api(`/api/local-worker-jobs/${encodeURIComponent(jobId)}`);
    if (job.projectId === activeProject() && job.worker?.workerId === "local-ai-rewrite") renderAiJob(job);
  } catch { localStorage.removeItem(aiRecoveryKey()); }
}

function aiProposalText() { return String(state.aiJob?.result?.output?.proposedText || ""); }

function applyAiProposal() {
  const proposal = aiProposalText();
  if (!proposal || !["result_approved", "draft_saved"].includes(state.aiJob?.status)) throw new Error("Approve the result before applying it");
  const mode = elements.aiApplyMode.value;
  const current = elements.body.value;
  if (mode === "replace-selection") {
    const selection = state.aiSelection;
    if (!selection || current.slice(selection.start, selection.end) !== selection.text) throw new Error("The selected passage changed; create a new plan");
    elements.body.value = current.slice(0, selection.start) + proposal + current.slice(selection.end);
  } else if (mode === "replace-whole") {
    if (state.document.currentVersion !== state.aiJob.plan.source.version) throw new Error("The draft version changed; create a new plan");
    elements.body.value = proposal;
  } else {
    const cursor = elements.body.selectionStart;
    elements.body.value = current.slice(0, cursor) + proposal + current.slice(cursor);
  }
  onInput(); countWords(); setAiStatus("Proposal applied to the editor but not saved.");
}

async function saveAiVersion() {
  try {
    state.aiAppliedBaseVersion = state.document.currentVersion;
    applyAiProposal();
    const result = await api(`/api/write-projects/${encodeURIComponent(state.document.id)}/snapshot`, {method: "POST", body: JSON.stringify({
      title: elements.title.value, content: elements.body.value, baseVersion: state.document.currentVersion,
      label: `Approved AI · ${state.aiJob.plan.destinationProfile}`, actor: "local-owner",
    })});
    state.document = result; state.dirty = false; clearLocalRecovery(result.id); renderDocumentState();
    elements.aiRollbackVersion.hidden = false; setAiStatus(`Approved proposal saved as Write version ${result.currentVersion}.`);
    await refreshProject(result.projectId); await window.twisReloadArtifacts?.();
  } catch (error) { setAiStatus(`Save stopped safely: ${error.message}`, true); }
}

async function rollbackAiVersion() {
  if (!state.document || !state.aiAppliedBaseVersion) return;
  try {
    const result = await api(`/api/write-projects/${encodeURIComponent(state.document.id)}/restore`, {method: "POST", body: JSON.stringify({
      targetVersion: state.aiAppliedBaseVersion, baseVersion: state.document.currentVersion, confirmed: true, actor: "local-owner",
    })});
    state.document = result; state.restoreOperationId = result.restoreOperationId; state.dirty = false; renderDocumentState();
    elements.aiRollbackVersion.hidden = true; setAiStatus("AI-applied version rolled back through the governed Write restore path.");
  } catch (error) { setAiStatus(`Rollback stopped safely: ${error.message}`, true); }
}

function speakWriteText(text) {
  if (!("speechSynthesis" in window)) { setAiStatus("Local browser speech is unavailable.", true); return; }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text); utterance.lang = document.documentElement.lang || "en-US";
  utterance.onstart = () => setAiStatus("Reading aloud locally.");
  utterance.onend = () => setAiStatus("Read aloud complete.");
  utterance.onerror = () => setAiStatus("Read aloud stopped.", true);
  window.speechSynthesis.speak(utterance);
}

async function saveSnapshot() {
  if (!state.document) return;
  const label = elements.snapshotLabel.value.trim();
  if (!label) {
    elements.snapshotLabel.focus();
    return;
  }
  const generation = state.editGeneration;
  try {
    const result = await api(`/api/write-projects/${encodeURIComponent(state.document.id)}/snapshot`, {
      method: "POST",
      body: JSON.stringify({
        title: elements.title.value,
        content: elements.body.value,
        baseVersion: state.document.currentVersion,
        label,
        actor: "local-owner",
      }),
    });
    state.document = result;
    if (state.editGeneration === generation) {
      state.dirty = false;
      clearLocalRecovery(result.id);
    }
    elements.snapshotDialog.close();
    renderDocumentState();
    setStatus(`Snapshot “${label}” saved.`, "saved");
    await refreshProject(result.projectId);
    await window.twisReloadArtifacts?.();
  } catch (error) {
    setStatus(`Snapshot failed: ${error.message}`, "error");
  }
}

function prepareRestore(version) {
  state.restoreTarget = version;
  elements.restoreMessage.textContent =
    `Restore v${version.number} (${version.label || version.cause}) from ${formatDate(version.createdAt)}? ` +
    "The Workshop will save the current writing as a recovery version first.";
  elements.restoreDialog.showModal();
}

async function performRestore() {
  if (!state.document || !state.restoreTarget) return;
  if (state.dirty) {
    try {
      await saveNow("manual");
    } catch {
      elements.restoreDialog.close();
      return;
    }
  }
  try {
    const result = await api(`/api/write-projects/${encodeURIComponent(state.document.id)}/restore`, {
      method: "POST",
      body: JSON.stringify({
        targetVersion: state.restoreTarget.number,
        baseVersion: state.document.currentVersion,
        confirmed: true,
        actor: "local-owner",
      }),
    });
    state.document = result;
    state.restoreOperationId = result.restoreOperationId;
    state.dirty = false;
    state.editGeneration += 1;
    state.restoreTarget = null;
    elements.restoreDialog.close();
    renderDocumentState();
    setStatus("Version restored. Undo remains available until you make another saved change.", "saved");
    await refreshProject(result.projectId);
    await window.twisReloadArtifacts?.();
  } catch (error) {
    setStatus(`Restore failed: ${error.message}`, "error");
    elements.restoreDialog.close();
  }
}

async function rollbackRestore() {
  if (!state.restoreOperationId) return;
  try {
    const result = await api(
      `/api/write-restore-operations/${encodeURIComponent(state.restoreOperationId)}/rollback`,
      {
        method: "POST",
        body: JSON.stringify({confirmed: true, actor: "local-owner"}),
      },
    );
    state.document = result;
    state.restoreOperationId = null;
    state.dirty = false;
    state.editGeneration += 1;
    renderDocumentState();
    setStatus("Restore rolled back; your pre-restore writing is current again.", "saved");
    await refreshProject(result.projectId);
    await window.twisReloadArtifacts?.();
  } catch (error) {
    setStatus(`Restore rollback failed: ${error.message}`, "error");
  }
}

async function compareVersions() {
  if (!state.document) return;
  const left = elements.compareLeft.value;
  const right = elements.compareRight.value;
  if (!left || !right || left === right) {
    setStatus("Choose two different versions to compare.", "error");
    return;
  }
  try {
    const result = await api(
      `/api/write-projects/${encodeURIComponent(state.document.id)}/compare?left=${encodeURIComponent(left)}&right=${encodeURIComponent(right)}`,
    );
    const comparison = result.comparison;
    elements.compareSummary.replaceChildren();
    for (const message of [
      `v${left} → v${right}`,
      `${comparison.addedLines} added`,
      `${comparison.removedLines} removed`,
      `${comparison.changedLines} changed`,
    ]) {
      const badge = document.createElement("span");
      badge.textContent = message;
      elements.compareSummary.append(badge);
    }
    renderComparison(elements.compareDiff, comparison);
    elements.compareDialog.showModal();
  } catch (error) {
    setStatus(`Comparison failed: ${error.message}`, "error");
  }
}

async function createProposal() {
  if (!state.document) return;
  if (state.dirty) {
    try {
      await saveNow("manual");
    } catch {
      return;
    }
  }
  const command = elements.command.value.trim();
  setStatus("Preparing a source-preserving proposal…", "saving");
  try {
    const proposal = await api(`/api/write-projects/${encodeURIComponent(state.document.id)}/proposals`, {
      method: "POST",
      body: JSON.stringify({
        action: command ? "" : elements.action.value,
        command,
        baseVersion: state.document.currentVersion,
        actor: "local-owner",
      }),
    });
    renderProposal(proposal);
    setStatus("Proposal ready. Your writing is unchanged until approval.", "saved");
  } catch (error) {
    setStatus(`Proposal failed: ${error.message}`, "error");
  }
}

async function runSupportedAction() {
  const command = elements.command.value.trim();
  if (!command) {
    await createProposal();
    return;
  }
  const normalized = command.toLowerCase().replace(/\s+/g, " ");
  if (/\bcompare\b/.test(normalized)) {
    const versions = state.document?.versions || [];
    if (versions.length < 2) {
      setStatus("There are not yet two saved versions to compare.", "error");
      return;
    }
    elements.compareLeft.value = String(versions[1].number);
    elements.compareRight.value = String(versions[0].number);
    await compareVersions();
    return;
  }
  if (/\brestore\b/.test(normalized)) {
    const versions = state.document?.versions || [];
    const numbered = normalized.match(/\b(?:version|v)\s*(\d+)\b/);
    let target = numbered
      ? versions.find(version => version.number === Number(numbered[1]))
      : null;
    if (!target && /\byesterday\b/.test(normalized)) {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      target = versions.find(version => new Date(version.createdAt) < today);
    }
    if (!target) {
      setStatus("Name a saved version number to restore, or choose Restore in History.", "error");
      return;
    }
    prepareRestore(target);
    return;
  }
  if (/\bexport\b/.test(normalized)) {
    if (/\bmarkdown\b|\bmd\b/.test(normalized)) elements.exportFormat.value = "md";
    else if (/\bjson\b/.test(normalized)) elements.exportFormat.value = "json";
    else if (/\bplain\b|\btext\b|\btxt\b/.test(normalized)) elements.exportFormat.value = "txt";
    await exportDocument();
    return;
  }
  if (/\b(snapshot|make a copy|checkpoint)\b/.test(normalized)) {
    elements.snapshotLabel.value = "Owner-requested checkpoint";
    elements.snapshotDialog.showModal();
    queueMicrotask(() => elements.snapshotLabel.focus());
    return;
  }
  if (/\brecover\b/.test(normalized)) {
    if (state.pendingRecovery) {
      showRecovery();
      elements.recoveryBanner.scrollIntoView({behavior: "smooth", block: "center"});
      setStatus("Recovery draft is ready. Choose Load recovery or Discard recovery.", "recovery");
    } else {
      setStatus("No newer recovery draft exists for this writing project.", "saved");
    }
    return;
  }
  await createProposal();
}

async function decideProposal(decision) {
  if (!state.activeProposal) return;
  try {
    const result = await api(
      `/api/write-proposals/${encodeURIComponent(state.activeProposal.id)}/decision`,
      {
        method: "POST",
        body: JSON.stringify({
          decision,
          note: elements.proposalNote.value,
          actor: "local-owner",
        }),
      },
    );
    if (result.document) {
      state.document = result.document;
      state.dirty = false;
      state.editGeneration += 1;
    } else if (state.document) {
      state.document = await api(`/api/write-projects/${encodeURIComponent(state.document.id)}`);
    }
    renderProposal(result);
    renderDocumentState();
    setStatus(
      decision === "approve"
        ? (result.modifiesContent ? "Proposal approved and applied with a recovery version." : "Findings approved; writing remained unchanged.")
        : "Proposal rejected; writing remained unchanged.",
      "saved",
    );
    await refreshProject(state.document.projectId);
    await window.twisReloadArtifacts?.();
  } catch (error) {
    setStatus(`Proposal decision failed: ${error.message}`, "error");
  }
}

async function rollbackProposal() {
  if (!state.activeProposal) return;
  try {
    const result = await api(
      `/api/write-proposals/${encodeURIComponent(state.activeProposal.id)}/rollback`,
      {
        method: "POST",
        body: JSON.stringify({confirmed: true, actor: "local-owner"}),
      },
    );
    state.document = result.document;
    state.dirty = false;
    state.editGeneration += 1;
    renderProposal(result);
    renderDocumentState();
    setStatus("Applied proposal rolled back; the recovery text is current again.", "saved");
    await refreshProject(state.document.projectId);
    await window.twisReloadArtifacts?.();
  } catch (error) {
    setStatus(`Proposal rollback failed: ${error.message}`, "error");
  }
}

async function exportDocument() {
  if (!state.document) return;
  if (state.dirty) {
    try {
      await saveNow("manual");
    } catch {
      return;
    }
  }
  try {
    const result = await api(`/api/write-projects/${encodeURIComponent(state.document.id)}/exports`, {
      method: "POST",
      body: JSON.stringify({
        format: elements.exportFormat.value,
        includeProvenance: elements.exportProvenance.checked,
        actor: "local-owner",
      }),
    });
    elements.exportResult.textContent = `Exported ${result.filename} to ${result.path}`;
    setStatus("Export created with a receipt.", "saved");
  } catch (error) {
    elements.exportResult.textContent = "";
    setStatus(`Export failed: ${error.message}`, "error");
  }
}

async function showHistory(artifactId) {
  window.twisOpenRoom?.("write");
  await openProject(artifactId);
  elements.versions.scrollIntoView({behavior: "smooth", block: "center"});
}

async function showExport(artifactId) {
  window.twisOpenRoom?.("write");
  await openProject(artifactId);
  elements.exportFormat.focus();
  elements.exportFormat.scrollIntoView({behavior: "smooth", block: "center"});
}

async function loadRecovery() {
  if (!state.document || !state.pendingRecovery) return;
  elements.title.value = state.pendingRecovery.title;
  elements.body.value = state.pendingRecovery.content;
  state.pendingRecovery = null;
  state.dirty = true;
  state.editGeneration += 1;
  elements.recoveryBanner.hidden = true;
  countWords();
  const localRecoveryReady = saveLocalRecovery();
  schedulePersistence();
  if (localRecoveryReady) {
    setStatus("Recovery draft loaded — unsaved changes ready.", "dirty");
  }
  elements.body.focus();
}

async function discardRecovery() {
  if (!state.document) return;
  try {
    await api(`/api/write-projects/${encodeURIComponent(state.document.id)}/recovery`, {
      method: "DELETE",
    });
  } catch (error) {
    setStatus(`Could not discard durable recovery: ${error.message}`, "error");
    return;
  }
  clearLocalRecovery(state.document.id);
  state.pendingRecovery = null;
  state.dirty = false;
  elements.recoveryBanner.hidden = true;
  elements.title.value = state.document.title;
  elements.body.value = state.document.content || "";
  countWords();
  setStatus("Recovery draft discarded; last saved version kept.", "saved");
  await refreshProject(state.document.projectId);
}

elements.title.addEventListener("input", onInput);
elements.body.addEventListener("input", onInput);
elements.projectPicker.addEventListener("change", () => {
  if (elements.projectPicker.value) void openProject(elements.projectPicker.value);
});
elements.newButton.addEventListener("click", () => {
  elements.newTitle.value = "Untitled";
  elements.newContent.value = "";
  elements.newDialog.showModal();
  queueMicrotask(() => elements.newTitle.select());
});
elements.confirmNew.addEventListener("click", event => {
  event.preventDefault();
  const title = elements.newTitle.value.trim() || "Untitled";
  const content = elements.newContent.value;
  elements.newDialog.close();
  void createFromText(title, content);
});
elements.saveButton.addEventListener("click", () => void saveNow("manual"));
elements.snapshotButton.addEventListener("click", () => {
  elements.snapshotLabel.value = "";
  elements.snapshotDialog.showModal();
  queueMicrotask(() => elements.snapshotLabel.focus());
});
elements.confirmSnapshot.addEventListener("click", event => {
  event.preventDefault();
  void saveSnapshot();
});
elements.refreshHistory.addEventListener("click", () => state.document && void openProject(state.document.id));
elements.compareButton.addEventListener("click", () => void compareVersions());
elements.closeCompare.addEventListener("click", () => elements.compareDialog.close());
elements.confirmRestore.addEventListener("click", event => {
  event.preventDefault();
  void performRestore();
});
elements.rollbackRestoreButton.addEventListener("click", () => void rollbackRestore());
elements.propose.addEventListener("click", () => void runSupportedAction());
elements.approveProposal.addEventListener("click", () => void decideProposal("approve"));
elements.rejectProposal.addEventListener("click", () => void decideProposal("reject"));
elements.rollbackProposal.addEventListener("click", () => void rollbackProposal());
elements.exportButton.addEventListener("click", () => void exportDocument());
elements.loadRecovery.addEventListener("click", () => void loadRecovery());
elements.discardRecovery.addEventListener("click", () => void discardRecovery());
elements.aiAction.replaceChildren(...WRITE_AI_ACTIONS.map(action => Object.assign(document.createElement("option"), {value: action, textContent: action})));
elements.aiOpen.addEventListener("click", () => { captureAiSelection(); elements.aiStudio.scrollIntoView({block: "start"}); elements.aiAction.focus(); void loadAiSources(); });
elements.body.addEventListener("select", captureAiSelection);
elements.aiStartModel.addEventListener("click", () => void startAiModel());
elements.aiCreatePlan.addEventListener("click", () => void createAiPlan());
elements.aiApprovePlan.addEventListener("click", () => void aiJobAction("plan-decision", {decision: "approve", note: elements.aiPlanNote.value}));
elements.aiRejectPlan.addEventListener("click", () => void aiJobAction("plan-decision", {decision: "reject", note: elements.aiPlanNote.value}));
elements.aiRun.addEventListener("click", () => void aiJobAction("execute"));
elements.aiCancel.addEventListener("click", () => void aiJobAction("cancel"));
elements.aiApproveResult.addEventListener("click", () => void aiJobAction("result-decision", {decision: "approve", note: elements.aiResultNote.value}));
elements.aiRejectResult.addEventListener("click", () => void aiJobAction("result-decision", {decision: "reject", note: elements.aiResultNote.value}));
elements.aiCopy.addEventListener("click", async () => { try { await navigator.clipboard.writeText(aiProposalText()); setAiStatus("Approved proposal copied."); } catch { setAiStatus("Clipboard access was denied; select the proposal text to copy it.", true); } });
elements.aiApply.addEventListener("click", () => { try { applyAiProposal(); } catch (error) { setAiStatus(error.message, true); } });
elements.aiSaveVersion.addEventListener("click", () => void saveAiVersion());
elements.aiSaveDraft.addEventListener("click", () => void aiJobAction("save-draft", {confirmed: true}));
elements.aiRollbackVersion.addEventListener("click", () => void rollbackAiVersion());
elements.aiReadDraft.addEventListener("click", () => speakWriteText(elements.body.value));
elements.aiReadProposal.addEventListener("click", () => speakWriteText(aiProposalText()));
elements.aiStopSpeaking.addEventListener("click", () => { window.speechSynthesis?.cancel(); setAiStatus("Speaking stopped."); });

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden" && state.dirty) {
    saveLocalRecovery();
    void persistServerRecovery();
  }
});
window.addEventListener("pagehide", () => {
  if (state.dirty) {
    saveLocalRecovery();
    void persistServerRecovery();
  }
});
window.addEventListener("twis:artifacts-loaded", event => {
  const projectId = event.detail?.projectId;
  if (projectId) void refreshProject(projectId);
});

window.twisWriteSummaries = new Map();
window.twisWriteRoom = {
  createFromText,
  getState: () => ({
    artifactId: state.document?.id || null,
    projectId: state.document?.projectId || null,
    currentVersion: state.document?.currentVersion || 0,
    dirty: state.dirty,
    hasRecovery: Boolean(state.pendingRecovery),
    activeProposalId: state.activeProposal?.id || null,
    aiJobId: state.aiJob?.jobId || null,
    aiJobStatus: state.aiJob?.status || null,
    selectedText: elements.body.value.slice(elements.body.selectionStart, elements.body.selectionEnd),
  }),
  onRoomOpen,
  openProject,
  refreshProject,
  saveNow,
  showExport,
  showHistory,
};

renderDocumentState();
})();

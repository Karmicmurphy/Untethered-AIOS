(() => {
  "use strict";

  const $ = selector => document.querySelector(selector);
  const state = {
    workers: [],
    contracts: new Map(),
    sources: [],
    jobs: [],
    currentJob: null,
    requestedSource: "",
  };

  async function api(path, options = {}) {
    const response = await fetch(path, {
      headers: {"Content-Type": "application/json", ...(options.headers || {})},
      ...options,
    });
    let value = null;
    try {
      value = await response.json();
    } catch {
      value = null;
    }
    if (!response.ok) {
      const error = new Error(value?.error || `Local worker request failed (${response.status})`);
      error.code = value?.code || "local_worker_request_failed";
      error.details = value?.details || {};
      throw error;
    }
    return value;
  }

  function status(message, kind = "") {
    const target = $("#localWorkerKitStatus");
    if (!target) return;
    target.textContent = message;
    target.dataset.state = kind;
  }

  function actionError(error) {
    const messages = {
      approval_note_required: "Add a short approval note before approving.",
      stale_plan: "This plan is stale because the approved source changed. Prepare a new plan.",
      source_hash_mismatch: "The registered source changed. Re-register or restore it before using a worker.",
      duplicate_execution: "This worker job is already running.",
      worker_timeout: "The worker reached its time limit and failed without accepting output.",
      selection_not_in_source: "The selected text is no longer present in the current source.",
    };
    status(messages[error.code] || error.message || "The local worker action failed safely.", "failed");
  }

  function addCard(root, heading, values, wide = false) {
    const card = document.createElement("div");
    card.className = `truth-card${wide ? " wide" : ""}`;
    const title = document.createElement("small");
    title.textContent = heading;
    card.append(title);
    const body = document.createElement("b");
    if (Array.isArray(values)) {
      body.textContent = values.length ? values.join(" · ") : "None";
    } else {
      body.textContent = String(values ?? "");
    }
    card.append(body);
    root.append(card);
  }

  function ownerAction(workerId) {
    return {
      "approved-text-reader": "Inspect this approved file",
      "code-structure-inspector": "Show me the structure of this code",
      "note-proposal-worker": "Make a note from this content",
      "package-manifest-validator": "Validate this approved package",
    }[workerId] || "Use supported worker";
  }

  function renderCards() {
    const root = $("#localWorkerCards");
    if (!root) return;
    root.replaceChildren();
    for (const worker of state.workers) {
      const card = document.createElement("article");
      card.className = "local-worker-card";
      const title = document.createElement("h3");
      title.textContent = worker.name;
      const description = document.createElement("p");
      description.textContent = worker.description;
      const truth = document.createElement("ul");
      for (const line of [
        `Reads: ${worker.reads.join(", ")}`,
        `May create: ${worker.mayCreate.length ? worker.mayCreate.join(", ") : "nothing"}`,
        "Network and shell: denied",
        "Approval: required before the plan and result are accepted",
      ]) {
        const item = document.createElement("li");
        item.textContent = line;
        truth.append(item);
      }
      const choose = document.createElement("button");
      choose.className = "quiet";
      choose.type = "button";
      choose.textContent = ownerAction(worker.workerId);
      choose.addEventListener("click", () => {
        $("#localWorkerChoice").value = worker.workerId;
        updateWorkerChoice();
        $("#localWorkerSource").focus();
      });
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = "Advanced Worker Card";
      const pre = document.createElement("pre");
      pre.textContent = JSON.stringify(state.contracts.get(worker.workerId) || {}, null, 2);
      details.append(summary, pre);
      card.append(title, description, truth, choose, details);
      root.append(card);
    }
  }

  function renderWorkerOptions() {
    const select = $("#localWorkerChoice");
    const selected = select.value;
    select.replaceChildren(new Option("Choose an action", ""));
    for (const worker of state.workers) {
      select.add(new Option(`${ownerAction(worker.workerId)} — ${worker.name}`, worker.workerId));
    }
    if (state.workers.some(worker => worker.workerId === selected)) {
      select.value = selected;
    }
  }

  function renderSourceOptions() {
    const select = $("#localWorkerSource");
    const selected = state.requestedSource || select.value;
    const workerId = $("#localWorkerChoice").value;
    select.replaceChildren(new Option("Choose work from this project", ""));
    for (const source of state.sources) {
      if (workerId && !source.allowedWorkers.includes(workerId)) continue;
      select.add(new Option(`${source.title} — ${source.kind}`, source.artifactId));
    }
    if ([...select.options].some(option => option.value === selected)) {
      select.value = selected;
      state.requestedSource = "";
    }
  }

  function updateWorkerChoice() {
    const workerId = $("#localWorkerChoice").value;
    $("#localWorkerNoteTitleLabel").hidden = workerId !== "note-proposal-worker";
    $("#localWorkerPackageExpectations").hidden = workerId !== "package-manifest-validator";
    const selection = $("#localWorkerSelection").value.trim();
    $("#localWorkerSelectionLabel").hidden = workerId !== "note-proposal-worker" || !selection;
    const purpose = $("#localWorkerPurpose");
    if (!purpose.value.trim()) purpose.placeholder = ownerAction(workerId);
    renderSourceOptions();
  }

  function parseExpectations() {
    const members = [];
    const hashes = {};
    const lines = $("#localWorkerExpectedMembers").value.split(/\r?\n/);
    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line) continue;
      const equals = line.lastIndexOf("=");
      const path = (equals === -1 ? line : line.slice(0, equals)).trim().replaceAll("\\", "/");
      const hash = equals === -1 ? "" : line.slice(equals + 1).trim().toUpperCase();
      if (
        !path ||
        path.startsWith("/") ||
        /^[A-Za-z]:/.test(path) ||
        path.split("/").some(part => !part || part === "." || part === "..")
      ) {
        throw Object.assign(new Error(`Unsafe expected package path: ${path || "(blank)"}`), {
          code: "package_member_unsafe",
        });
      }
      if (members.includes(path)) {
        throw Object.assign(new Error(`Expected package path is repeated: ${path}`), {
          code: "expected_members_duplicate",
        });
      }
      members.push(path);
      if (hash) {
        if (!/^[A-F0-9]{64}$/.test(hash)) {
          throw Object.assign(new Error(`Expected hash for ${path} must be SHA-256.`), {
            code: "expected_hash_invalid",
          });
        }
        hashes[path] = hash;
      }
    }
    return {members, hashes};
  }

  function renderPlan(job) {
    const previousJobId = state.currentJob?.jobId || "";
    state.currentJob = job;
    if (previousJobId !== job.jobId) {
      $("#localWorkerPlanNote").value = "";
      $("#localWorkerResultNote").value = "";
    }
    const panel = $("#localWorkerPlanPanel");
    panel.hidden = false;
    $("#localWorkerPlanState").textContent = job.statusLabel;
    const root = $("#localWorkerPlanSummary");
    root.replaceChildren();
    addCard(root, "Worker chosen", job.worker.name);
    addCard(root, "Approved source", job.source.title);
    addCard(root, "Planned action", job.plan.purpose);
    addCard(root, "It will read", job.plan.reads);
    addCard(root, "It may create", job.plan.mayCreate);
    addCard(root, "It cannot access", job.plan.cannotAccess, true);
    addCard(root, "After completion", "Unattached and inactive");
    addCard(root, "Recovery", job.actions.recover ? "Interrupted safely; recovery available" : "No accepted output is recovered automatically");
    $("#localWorkerPlanAdvanced").textContent = JSON.stringify(job.advanced, null, 2);
    $("#approveLocalWorkerPlan").hidden = !job.actions.approvePlan;
    $("#rejectLocalWorkerPlan").hidden = !job.actions.rejectPlan;
    $("#runLocalWorkerJob").hidden = !job.actions.execute;
    $("#cancelLocalWorkerJob").hidden = !job.actions.cancel;
    $("#recoverLocalWorkerJob").hidden = !job.actions.recover;
    if (job.result && Object.keys(job.result).length) renderResult(job);
  }

  function addReadOnlyText(root, labelText, value) {
    const label = document.createElement("label");
    label.textContent = labelText;
    const area = document.createElement("textarea");
    area.rows = 12;
    area.readOnly = true;
    area.value = String(value ?? "");
    label.append(area);
    root.append(label);
  }

  function addPlainList(root, heading, values) {
    const section = document.createElement("section");
    const title = document.createElement("h4");
    title.textContent = heading;
    const list = document.createElement("ul");
    for (const value of values) {
      const item = document.createElement("li");
      item.textContent = String(value);
      list.append(item);
    }
    if (!values.length) {
      const item = document.createElement("li");
      item.textContent = "None";
      list.append(item);
    }
    section.append(title, list);
    root.append(section);
  }

  function renderResult(job) {
    const panel = $("#localWorkerResultPanel");
    const output = job.result?.output;
    if (!output) {
      panel.hidden = true;
      return;
    }
    panel.hidden = false;
    $("#localWorkerResultState").textContent = job.statusLabel;
    const root = $("#localWorkerResultSummary");
    root.replaceChildren();
    if (job.worker.workerId === "approved-text-reader") {
      addPlainList(root, "Exact source facts", [
        `${output.lines} lines`,
        `${output.bytes} bytes`,
        `${output.characters} characters`,
        `Encoding: ${output.encoding}`,
        "Source modified: no",
      ]);
      addReadOnlyText(root, "Readable content", output.content);
    } else if (job.worker.workerId === "code-structure-inspector") {
      addPlainList(root, "Proven facts", [
        `Lines: ${output.facts?.lines ?? 0}`,
        `Imports or dependencies: ${(output.facts?.importsOrDependencies || []).join(", ") || "none found"}`,
        `Functions: ${(output.facts?.functions || []).join(", ") || "none found"}`,
        `Classes: ${(output.facts?.classes || []).join(", ") || "none found"}`,
        `TODO/FIXME markers: ${(output.facts?.markers || []).length}`,
        "Source executed: no",
      ]);
      addPlainList(root, "Labeled heuristic findings", [
        `Probable type: ${output.heuristicFindings?.probableType || "Unknown"}`,
        `Basis: ${output.heuristicFindings?.basis || "No reliable basis"}`,
        `Repeated lines: ${(output.heuristicFindings?.repeatedLines || []).length}`,
      ]);
    } else if (job.worker.workerId === "note-proposal-worker") {
      addPlainList(root, "Proposal truth", [
        `Title: ${output.title}`,
        "Source preserved: yes",
        "Note created yet: no",
        "Approval is required before one new draft note is created",
      ]);
      addReadOnlyText(root, "Proposed note", output.content);
    } else if (job.worker.workerId === "package-manifest-validator") {
      addPlainList(root, output.validationPassed ? "Package validation passed" : "Package validation found issues", [
        `Format: ${output.facts?.format || "Unknown"}`,
        `Members inspected: ${output.facts?.memberCount ?? output.members?.length ?? 0}`,
        `Missing: ${(output.missingMembers || []).length}`,
        `Unexpected: ${(output.unexpectedMembers || []).length}`,
        `Unsafe: ${(output.unsafeMembers || []).length}`,
        `Duplicate: ${(output.duplicateMembers || []).length}`,
        `Hash mismatches: ${(output.hashMismatches || []).length}`,
        "Installed, executed, imported, or activated: no",
      ]);
      addPlainList(root, "Missing members", output.missingMembers || []);
      addPlainList(root, "Unexpected members", output.unexpectedMembers || []);
      addPlainList(root, "Unsafe or duplicate members", [
        ...(output.unsafeMembers || []),
        ...(output.duplicateMembers || []),
      ]);
    }
    addPlainList(root, "Governance state", [
      `Validated output: ${job.result.validation?.valid ? "yes" : "no"}`,
      `Owner accepted: ${job.result.accepted ? "yes" : "no"}`,
      `Attachment: ${job.attachmentStatus}`,
      `Activation: ${job.activationStatus}`,
      `Receipt-backed evidence entries: ${job.evidence.length}`,
    ]);
    $("#localWorkerResultAdvanced").textContent = JSON.stringify({
      output,
      validation: job.result.validation,
      decision: job.result.decision,
      acceptance: job.result.acceptance,
      evidence: job.evidence,
    }, null, 2);
    $("#approveLocalWorkerResult").hidden = !job.actions.approveResult;
    $("#rejectLocalWorkerResult").hidden = !job.actions.rejectResult;
    $("#localWorkerResultNoteLabel").hidden = !job.actions.approveResult && !job.actions.rejectResult;
    $("#rollbackLocalWorkerResult").hidden = !job.actions.rollback;
  }

  function renderHistory() {
    const root = $("#localWorkerHistory");
    root.replaceChildren();
    if (!state.jobs.length) {
      const empty = document.createElement("p");
      empty.className = "muted";
      empty.textContent = "No governed worker jobs for this project.";
      root.append(empty);
      return;
    }
    for (const job of state.jobs) {
      const item = document.createElement("article");
      item.className = "local-worker-job";
      const heading = document.createElement("div");
      const title = document.createElement("h4");
      title.textContent = job.worker.name;
      const source = document.createElement("p");
      source.className = "muted";
      source.textContent = `${job.source.title} · ${job.statusLabel}`;
      const governance = document.createElement("p");
      governance.className = "local-worker-governance";
      governance.textContent = `${job.evidence.length} evidence entr${job.evidence.length === 1 ? "y" : "ies"} · ${job.attachmentStatus} · ${job.activationStatus}`;
      heading.append(title, source, governance);
      const actions = document.createElement("div");
      actions.className = "row";
      const open = document.createElement("button");
      open.className = "quiet";
      open.textContent = "Open job";
      open.addEventListener("click", async () => {
        try {
          renderPlan(await api(`/api/local-worker-jobs/${encodeURIComponent(job.jobId)}`));
          $("#localWorkerPlanPanel").scrollIntoView({behavior: "smooth", block: "start"});
        } catch (error) {
          actionError(error);
        }
      });
      actions.append(open);
      if (["result_approved", "draft_saved"].includes(job.status)) {
        for (const [kind, label] of [["handoff", "Build Handoff"], ["prompt", "Build Prompt"]]) {
          const build = document.createElement("button");
          build.className = "quiet";
          build.textContent = label;
          build.addEventListener("click", () => window.twisOpenBuilder?.(kind));
          actions.append(build);
        }
      }
      if (job.actions.deleteHistory) {
        const remove = document.createElement("button");
        remove.className = "quiet";
        remove.textContent = "Clean job history";
        remove.addEventListener("click", () => void deleteHistory(job));
        actions.append(remove);
      }
      item.append(heading, actions);
      root.append(item);
    }
  }

  async function loadWorkerTruth() {
    const projectId = window.twisGetActiveProject?.() || "";
    if (!window.twisHasCompanion?.() || !projectId) {
      status("Local companion unavailable", "failed");
      return;
    }
    status("Loading current local worker state");
    $("#prepareLocalWorkerPlan").disabled = true;
    try {
      const [workers, sources, jobs] = await Promise.all([
        api("/api/local-workers"),
        api(`/api/local-worker-sources?projectId=${encodeURIComponent(projectId)}`),
        api(`/api/local-worker-jobs?projectId=${encodeURIComponent(projectId)}`),
      ]);
      const contracts = await Promise.all(
        workers.map(worker => api(`/api/local-workers/${encodeURIComponent(worker.workerId)}`)),
      );
      state.workers = workers;
      state.sources = sources;
      state.jobs = jobs;
      state.contracts = new Map(contracts.map(contract => [contract.workerId, contract]));
      renderCards();
      renderWorkerOptions();
      renderSourceOptions();
      renderHistory();
      updateEntryButtons();
      status(`${workers.length} fixed local workers ready`, "succeeded");
    } catch (error) {
      actionError(error);
    } finally {
      $("#prepareLocalWorkerPlan").disabled = false;
    }
  }

  async function preparePlan() {
    const projectId = window.twisGetActiveProject?.() || "";
    const workerId = $("#localWorkerChoice").value;
    const sourceArtifactId = $("#localWorkerSource").value;
    if (!workerId || !sourceArtifactId) {
      status("Choose a supported action and approved source first.", "failed");
      return;
    }
    $("#prepareLocalWorkerPlan").disabled = true;
    $("#localWorkerPlanPanel").hidden = true;
    $("#localWorkerResultPanel").hidden = true;
    try {
      const {members, hashes} = parseExpectations();
      const payload = {
        projectId,
        workerId,
        sourceArtifactId,
        purpose: $("#localWorkerPurpose").value.trim() || ownerAction(workerId),
        actor: "local-owner",
      };
      const selection = $("#localWorkerSelection").value;
      if (workerId === "note-proposal-worker" && selection.trim()) payload.selection = selection;
      if (workerId === "note-proposal-worker") {
        payload.title = $("#localWorkerNoteTitle").value.trim() || "Workshop note";
      }
      if (workerId === "package-manifest-validator") {
        payload.expectedMembers = members;
        payload.expectedHashes = hashes;
      }
      status("Validating bounded worker plan", "started");
      const job = await api("/api/local-worker-jobs/plan", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      renderPlan(job);
      await refreshHistory();
      status("Plan ready for owner review", "succeeded");
    } catch (error) {
      actionError(error);
    } finally {
      $("#prepareLocalWorkerPlan").disabled = false;
    }
  }

  async function postJobAction(action, payload = {}) {
    if (!state.currentJob) return null;
    return api(`/api/local-worker-jobs/${encodeURIComponent(state.currentJob.jobId)}/${action}`, {
      method: "POST",
      body: JSON.stringify({actor: "local-owner", ...payload}),
    });
  }

  async function decidePlan(decision) {
    if (decision === "approve" && !$("#localWorkerPlanNote").value.trim()) {
      status("Add a short approval note before approving.", "failed");
      $("#localWorkerPlanNote").focus();
      return;
    }
    try {
      status(decision === "approve" ? "Recording plan approval" : "Rejecting plan", "started");
      const job = await postJobAction("plan-decision", {
        decision,
        note: $("#localWorkerPlanNote").value,
      });
      renderPlan(job);
      await refreshHistory();
      status(decision === "approve" ? "Plan approved; the worker has not run yet" : "Plan rejected; nothing ran", "succeeded");
    } catch (error) {
      actionError(error);
    }
  }

  async function runJob() {
    try {
      status("Worker running with only its approved packet", "started");
      $("#runLocalWorkerJob").disabled = true;
      const job = await postJobAction("execute");
      renderPlan(job);
      await refreshHistory();
      status("Worker completed; result awaits a separate decision", "succeeded");
    } catch (error) {
      actionError(error);
      if (state.currentJob) {
        try {
          renderPlan(await api(`/api/local-worker-jobs/${encodeURIComponent(state.currentJob.jobId)}`));
        } catch {
          // The original safe failure remains owner-visible.
        }
      }
    } finally {
      $("#runLocalWorkerJob").disabled = false;
    }
  }

  async function decideResult(decision) {
    if (decision === "approve" && !$("#localWorkerResultNote").value.trim()) {
      status("Add a short approval note before approving.", "failed");
      $("#localWorkerResultNote").focus();
      return;
    }
    try {
      status(decision === "approve" ? "Recording result approval" : "Rejecting proposed result", "started");
      const job = await postJobAction("result-decision", {
        decision,
        note: $("#localWorkerResultNote").value,
      });
      renderPlan(job);
      await window.twisReloadArtifacts?.();
      await refreshHistory();
      status(
        decision === "approve"
          ? "Result approved; it remains unattached and inactive"
          : "Result rejected; no accepted mutation remains",
        "succeeded",
      );
    } catch (error) {
      actionError(error);
    }
  }

  async function cancelJob() {
    try {
      const job = await postJobAction("cancel");
      renderPlan(job);
      await refreshHistory();
      status("Job cancelled safely", "succeeded");
    } catch (error) {
      actionError(error);
    }
  }

  async function recoverJob() {
    try {
      const job = await postJobAction("recover");
      renderPlan(job);
      await refreshHistory();
      status("Interrupted job recovered to its approved, unrun plan", "succeeded");
    } catch (error) {
      actionError(error);
    }
  }

  async function rollbackJob() {
    if (!window.confirm("Roll back only the unchanged note created by this worker job?")) return;
    try {
      const job = await postJobAction("rollback", {confirmed: true});
      renderPlan(job);
      await window.twisReloadArtifacts?.();
      await refreshHistory();
      status("Created note rolled back; source and unrelated work were preserved", "succeeded");
    } catch (error) {
      actionError(error);
    }
  }

  async function deleteHistory(job) {
    if (!window.confirm("Clean this terminal job history? Its receipts will be preserved.")) return;
    try {
      await api(`/api/local-worker-jobs/${encodeURIComponent(job.jobId)}/delete`, {
        method: "POST",
        body: JSON.stringify({confirmed: true, actor: "local-owner"}),
      });
      if (state.currentJob?.jobId === job.jobId) {
        state.currentJob = null;
        $("#localWorkerPlanPanel").hidden = true;
        $("#localWorkerResultPanel").hidden = true;
      }
      await refreshHistory();
      status("Terminal job history cleaned; receipts preserved", "succeeded");
    } catch (error) {
      actionError(error);
    }
  }

  async function refreshHistory() {
    const projectId = window.twisGetActiveProject?.() || "";
    if (!projectId) return;
    state.jobs = await api(`/api/local-worker-jobs?projectId=${encodeURIComponent(projectId)}`);
    renderHistory();
  }

  function selectedTalkText() {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return "";
    const anchor = selection.anchorNode instanceof Element
      ? selection.anchorNode
      : selection.anchorNode?.parentElement;
    if (!anchor?.closest("#talkTranscript")) return "";
    return selection.toString().trim();
  }

  function selectedWriteText() {
    const editor = $("#docBody");
    if (!editor || editor.selectionStart === editor.selectionEnd) return "";
    return editor.value.slice(editor.selectionStart, editor.selectionEnd).trim();
  }

  async function openFromRoom(sourceArtifactId, workerId, selection = "") {
    if (!sourceArtifactId) {
      status("Open and save a Talk or Write source before choosing a worker.", "failed");
      return;
    }
    state.requestedSource = sourceArtifactId;
    $("#localWorkerSelection").value = selection;
    $("#localWorkerChoice").value = workerId;
    window.twisOpenRoom?.("work");
    await loadWorkerTruth();
    $("#localWorkerChoice").value = workerId;
    updateWorkerChoice();
    renderSourceOptions();
    if ($("#localWorkerSource").value !== sourceArtifactId) {
      status("That source is not eligible for the selected fixed worker.", "failed");
      return;
    }
    if (workerId === "note-proposal-worker" && !selection) {
      status("No text was selected, so the worker plan will use the complete current source.", "succeeded");
    } else {
      status("Supported action and approved source selected", "succeeded");
    }
    $("#localWorkerPurpose").focus();
  }

  function updateEntryButtons() {
    const talkOpen = Boolean(window.twisTalkRoom?.getState?.().artifactId);
    const writeOpen = Boolean(window.twisWriteRoom?.getState?.().artifactId);
    ["#talkWorkerRead", "#talkWorkerStructure", "#talkWorkerNote"].forEach(selector => {
      if ($(selector)) $(selector).disabled = !talkOpen;
    });
    ["#writeWorkerRead", "#writeWorkerStructure", "#writeWorkerNote"].forEach(selector => {
      if ($(selector)) $(selector).disabled = !writeOpen;
    });
  }

  function bind() {
    $("#localWorkerChoice").addEventListener("change", updateWorkerChoice);
    $("#prepareLocalWorkerPlan").addEventListener("click", () => void preparePlan());
    $("#refreshLocalWorkerKit").addEventListener("click", () => void loadWorkerTruth());
    $("#approveLocalWorkerPlan").addEventListener("click", () => void decidePlan("approve"));
    $("#rejectLocalWorkerPlan").addEventListener("click", () => void decidePlan("reject"));
    $("#runLocalWorkerJob").addEventListener("click", () => void runJob());
    $("#cancelLocalWorkerJob").addEventListener("click", () => void cancelJob());
    $("#recoverLocalWorkerJob").addEventListener("click", () => void recoverJob());
    $("#approveLocalWorkerResult").addEventListener("click", () => void decideResult("approve"));
    $("#rejectLocalWorkerResult").addEventListener("click", () => void decideResult("reject"));
    $("#rollbackLocalWorkerResult").addEventListener("click", () => void rollbackJob());

    $("#talkWorkerRead").addEventListener("click", () => void openFromRoom(
      window.twisTalkRoom?.getState?.().artifactId,
      "approved-text-reader",
    ));
    $("#talkWorkerStructure").addEventListener("click", () => void openFromRoom(
      window.twisTalkRoom?.getState?.().artifactId,
      "code-structure-inspector",
    ));
    $("#talkWorkerNote").addEventListener("click", () => void openFromRoom(
      window.twisTalkRoom?.getState?.().artifactId,
      "note-proposal-worker",
      selectedTalkText(),
    ));
    $("#writeWorkerRead").addEventListener("click", () => void openFromRoom(
      window.twisWriteRoom?.getState?.().artifactId,
      "approved-text-reader",
    ));
    $("#writeWorkerStructure").addEventListener("click", () => void openFromRoom(
      window.twisWriteRoom?.getState?.().artifactId,
      "code-structure-inspector",
    ));
    $("#writeWorkerNote").addEventListener("click", () => void openFromRoom(
      window.twisWriteRoom?.getState?.().artifactId,
      "note-proposal-worker",
      selectedWriteText(),
    ));

    window.addEventListener("twis:artifacts-loaded", () => {
      updateEntryButtons();
      if (location.hash === "#work") void loadWorkerTruth();
    });
    window.addEventListener("hashchange", () => {
      updateEntryButtons();
      if (location.hash === "#work") void loadWorkerTruth();
    });
    window.addEventListener("focus", updateEntryButtons);
    updateEntryButtons();
    if (location.hash === "#work") void loadWorkerTruth();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind, {once: true});
  } else {
    bind();
  }

  window.twisLocalWorkerKit = {
    refresh: loadWorkerTruth,
    openFromRoom,
    getState: () => ({
      currentJobId: state.currentJob?.jobId || null,
      workerCount: state.workers.length,
      sourceCount: state.sources.length,
      jobCount: state.jobs.length,
    }),
  };
})();

(() => {
  "use strict";

  const REFERENCE_WORKER_ID = "reference-metadata-worker";
  const INSPECTION_WORKER_ID = "artifact-compass-inspection-worker";
  const view = globalThis.twisWorkerHarnessView;
  if (!view) throw new Error("Worker Harness view model failed to load.");

  const $ = selector => document.querySelector(selector);
  const escapeHtml = view.escapeHtml;
  let currentPlan = null;
  let currentValidation = null;
  let loading = false;
  let actionBusy = false;
  let availableWorkers = [];
  let artifactOptions = [];
  let candidates = [];
  let eligibilityRefreshedAt = null;
  let actionLogStarted = false;

  async function request(path, options = {}) {
    const response = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options
    });
    let payload = null;
    try { payload = await response.json(); } catch { payload = {}; }
    if (!response.ok) {
      const code = payload.code ? `${payload.code}: ` : "";
      throw new Error(`${code}${payload.error || `HTTP ${response.status}`}`);
    }
    return payload;
  }

  function actor() {
    const value = $("#workerActor").value.trim();
    if (!value) throw new Error("A local human actor assertion is required. It is not authenticated identity.");
    return value;
  }

  function selectedWorker() {
    const value = $("#workerSelect").value;
    if (!availableWorkers.some(worker => worker.worker_id === value)) {
      throw new Error("The selected fixed worker is unavailable.");
    }
    return value;
  }

  function messageLabel(state) {
    return ({
      started: "Started",
      succeeded: "Succeeded",
      failed: "Failed",
      blocked: "Blocked",
      stale: "Stale",
      awaiting: "Awaiting owner action"
    })[state] || "Status";
  }

  function setMessage(message, state = "succeeded") {
    const element = $("#workerHarnessMessage");
    const label = messageLabel(state);
    element.textContent = `${label}: ${message}`;
    element.dataset.state = state;
    element.classList.toggle("warning", ["failed", "blocked", "stale"].includes(state));
    const log = $("#workerActionLog");
    if (!actionLogStarted) {
      log.replaceChildren();
      actionLogStarted = true;
    }
    const item = document.createElement("li");
    const time = new Date().toLocaleTimeString();
    item.textContent = `${time} - ${label}: ${message}`;
    log.prepend(item);
  }

  function humanize(value) {
    return String(value || "unavailable").replace(/_/g, " ");
  }

  function yesNo(value, trueLabel = "Allowed", falseLabel = "Denied") {
    return value === true ? trueLabel : falseLabel;
  }

  function renderLifecycle(state = "idle") {
    const model = view.lifecycleModel(state);
    $("#workerLifecycleOverview").innerHTML = model.steps.map(step =>
      `<div class="lifecycle-step ${escapeHtml(step.status)}"><b>${escapeHtml(humanize(step.name))}</b><small>${escapeHtml(step.status)}</small></div>`
    ).join("");
  }

  function currentSelection() {
    return {
      workerId: $("#workerSelect").value,
      artifactId: $("#inspectionArtifact").value,
      actor: $("#workerActor").value.trim()
    };
  }

  function clearPlan(reason = "No current execution plan.", state = "blocked", announce = false) {
    currentPlan = null;
    $("#runSelectedWorker").disabled = true;
    $("#workerPlanValidity").textContent = "No current plan";
    $("#workerPlanOutput").textContent = "No plan created.";
    $("#workerPlanSummary").innerHTML = `<p class="muted">${escapeHtml(reason)}</p>`;
    renderLifecycle(candidates[0]?.lifecycle_state || "idle");
    if (announce) setMessage(reason, state);
  }

  function selectedArtifactOption() {
    const artifactId = $("#inspectionArtifact").value;
    return artifactOptions.find(option => option.artifactId === artifactId) || null;
  }

  function renderArtifactDetails() {
    const option = selectedArtifactOption();
    const target = $("#inspectionArtifactDetails");
    if (!option) {
      target.innerHTML = '<span class="muted">Select an eligible artifact to see its exact identity.</span>';
      return;
    }
    const duplicates = option.duplicateHashGroup || [];
    target.innerHTML = `<div class="truth-grid">
      <div class="truth-card"><small>Title and distinct path</small><b>${escapeHtml(view.artifactLabel(option))}</b></div>
      <div class="truth-card"><small>Artifact ID</small><b class="mono">${escapeHtml(option.artifactId)}</b></div>
      <div class="truth-card"><small>Eligibility</small><b>${option.eligible ? "Eligible" : "Blocked"}</b></div>
      <div class="truth-card"><small>File type</small><b>${escapeHtml(option.fileType || "unsupported")}</b></div>
      <div class="truth-card"><small>Size</small><b>${escapeHtml(view.formatBytes(option.byteCount))}</b></div>
      <div class="truth-card"><small>Review status</small><b>${escapeHtml(option.reviewStatus)}</b></div>
      <div class="truth-card wide"><small>SHA-256</small><b class="mono">${escapeHtml(option.sha256)}</b></div>
      <div class="truth-card wide"><small>Duplicate identity</small><b>${duplicates.length > 1 ? `${duplicates.length} records share these exact bytes` : "No exact-hash duplicate group"}</b>${duplicates.length > 1 ? `<ul>${duplicates.map(item => `<li><span>${escapeHtml(item.title)}</span> - <code>${escapeHtml(view.shortArtifactPath(item.source_path))}</code> - <span class="mono">${escapeHtml(item.artifact_id)}</span></li>`).join("")}</ul>` : ""}</div>
    </div>`;
  }

  function renderArtifactOptions(options) {
    artifactOptions = Array.isArray(options) ? options : [];
    const eligible = artifactOptions.filter(option => option.eligible);
    const blocked = artifactOptions.filter(option => !option.eligible);
    const previous = $("#inspectionArtifact").value;
    $("#inspectionArtifact").innerHTML = eligible.length
      ? eligible.map(option => `<option value="${escapeHtml(option.artifactId)}">${escapeHtml(view.artifactLabel(option))}</option>`).join("")
      : '<option value="">No eligible public-safe artifacts</option>';
    if (eligible.some(option => option.artifactId === previous)) $("#inspectionArtifact").value = previous;
    $("#inspectionArtifact").disabled = !eligible.length;

    eligibilityRefreshedAt = new Date().toISOString();
    const summary = view.eligibilitySummary(artifactOptions, eligibilityRefreshedAt);
    const categoryText = Object.entries(summary.reasons)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([reason, count]) => `${humanize(reason)}: ${count}`)
      .join("; ") || "none";
    $("#inspectionEligibility").innerHTML = `
      <div class="eligibility-stat"><small>Eligible</small><b>${summary.eligible}</b></div>
      <div class="eligibility-stat"><small>Blocked</small><b>${summary.blocked}</b></div>
      <div class="eligibility-stat ${summary.sourceHashMismatches ? "alert" : ""}"><small>Source-hash mismatches</small><b>${summary.sourceHashMismatches}</b></div>
      <div class="eligibility-stat"><small>Blocked categories</small><b>${escapeHtml(categoryText)}</b></div>
      <div class="eligibility-stat"><small>Refreshed</small><b><time datetime="${escapeHtml(summary.refreshedAt)}">${escapeHtml(new Date(summary.refreshedAt).toLocaleString())}</time></b></div>`;
    $("#inspectionBlockedArtifacts").innerHTML = blocked.length
      ? `<ul>${blocked.map(option => `<li><b>${escapeHtml(option.title)}</b> - ${escapeHtml(view.shortArtifactPath(option.sourcePath))} - ${escapeHtml((option.blockedReasons || []).map(humanize).join(", "))}</li>`).join("")}</ul>`
      : "No ineligible artifacts were returned.";
    renderArtifactDetails();
  }

  function renderWorkerCard(validation, worker) {
    const summary = view.workerCardSummary(validation, worker);
    $("#workerCardPanel").hidden = false;
    $("#workerCardValidity").textContent = summary.valid ? "Validated" : "Rejected";
    $("#workerCardSummary").innerHTML = `
      <div class="truth-card"><small>Worker</small><b>${escapeHtml(summary.workerName)} ${escapeHtml(summary.version)}</b></div>
      <div class="truth-card"><small>Read authority</small><b>${escapeHtml(summary.readAuthority.join("; ") || "none")}</b></div>
      <div class="truth-card"><small>Write authority</small><b>${escapeHtml(summary.writeAuthority.join("; ") || "none")}</b></div>
      <div class="truth-card"><small>Network</small><b>${yesNo(summary.network)}</b></div>
      <div class="truth-card"><small>Shell</small><b>${yesNo(summary.shell)}</b></div>
      <div class="truth-card"><small>Destructive actions</small><b>${yesNo(summary.destructiveActions)}</b></div>
      <div class="truth-card"><small>Approval</small><b>${yesNo(summary.approvalRequired, "Required", "Not required")}</b></div>
      <div class="truth-card"><small>Automatic activation</small><b>${yesNo(summary.automaticActivation)}</b></div>
      <div class="truth-card"><small>Limits</small><b>${escapeHtml(`${summary.timeoutSeconds ?? "?"} s; ${summary.acceptedInputs.join(", ") || "input types unavailable"}`)}</b></div>
      <div class="truth-card wide"><small>Worker Card SHA-256</small><b class="mono">${escapeHtml(summary.workerCardHash || "unavailable")}</b></div>
      <div class="truth-card wide"><small>Unsupported capabilities</small><ul>${summary.unsupported.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div>`;
    $("#workerCardOutput").textContent = JSON.stringify(validation.card, null, 2);
  }

  function displayPlan(plan) {
    currentPlan = plan;
    const summary = view.planSummary(plan);
    const artifact = summary.selectedArtifact;
    $("#workerPlanSummary").innerHTML = `
      <div class="truth-card"><small>Selected artifact</small><b>${escapeHtml(artifact ? `${artifact.id} - ${view.shortArtifactPath(artifact.path)}` : "fixed reference fixture")}</b></div>
      <div class="truth-card"><small>Source SHA-256</small><b class="mono">${escapeHtml(artifact?.sha256 || plan.inputs?.[0]?.sha256 || "unavailable")}</b></div>
      <div class="truth-card"><small>Read root</small><b>${escapeHtml(Array.isArray(summary.readRoot) ? summary.readRoot.join("; ") : summary.readRoot)}</b></div>
      <div class="truth-card"><small>Write root</small><b>${escapeHtml(summary.writeRoot.join("; ") || "none")}</b></div>
      <div class="truth-card"><small>Permissions</small><b>${escapeHtml(Object.entries(summary.permissions).map(([key, value]) => `${humanize(key)}=${value}`).join("; "))}</b></div>
      <div class="truth-card"><small>Timeout and limits</small><b>${escapeHtml(`${summary.timeoutSeconds}s; input ${view.formatBytes(summary.maxInputBytes)}; output ${view.formatBytes(summary.maxOutputBytes)}`)}</b></div>
      <div class="truth-card"><small>Required tests</small><b>${escapeHtml(summary.requiredTests.join("; ") || "none")}</b></div>
      <div class="truth-card"><small>Recovery scope</small><b>${escapeHtml(summary.recoveryScope)}</b></div>
      <div class="truth-card"><small>Workspace generation</small><b>${escapeHtml(summary.workspaceGeneration)}</b></div>
      <div class="truth-card"><small>Automatic activation</small><b>${summary.autoActivation ? "Requested" : "Prohibited"}</b></div>
      <div class="truth-card wide"><small>Blocked roots</small><b>${escapeHtml(summary.blockedRoots.join("; ") || "none")}</b></div>
      <div class="truth-card wide"><small>Declared-only limitations</small>${summary.warnings.map(warning => `<div class="truth-warning">${escapeHtml(warning)}</div>`).join("")}</div>`;
    $("#workerPlanOutput").textContent = JSON.stringify(plan, null, 2);
    $("#workerPlanDetails").open = false;
    const current = view.isCurrentPlan(plan, currentSelection());
    $("#workerPlanValidity").textContent = current ? "Current valid plan" : "Stale or mismatched plan";
    $("#runSelectedWorker").disabled = !current;
    renderLifecycle(current ? "planned" : candidates[0]?.lifecycle_state || "idle");
  }

  function renderList(items, renderItem) {
    return items.length ? `<ul>${items.map(renderItem).join("")}</ul>` : '<p class="empty-evidence">None recorded.</p>';
  }

  function renderInspectionResult(output) {
    const sections = view.resultSections(output);
    return `<div class="result-grid">
      <section class="result-section"><h5>Source identity</h5><dl class="source-grid"><dt>Artifact ID</dt><dd class="mono">${escapeHtml(sections.sourceIdentity.artifactId)}</dd><dt>Path</dt><dd class="mono">${escapeHtml(sections.sourceIdentity.sourcePath)}</dd><dt>SHA-256</dt><dd class="mono">${escapeHtml(sections.sourceIdentity.sourceSha256)}</dd><dt>Type</dt><dd>${escapeHtml(sections.sourceIdentity.fileType)}</dd></dl></section>
      <section class="result-section"><h5>Counts and review</h5><p>${escapeHtml(sections.counts.bytes)} bytes; ${escapeHtml(sections.counts.lines)} lines; ${escapeHtml(sections.counts.words)} words</p><p>Review status: <b>${escapeHtml(sections.reviewStatus)}</b></p></section>
      <section class="result-section"><h5>Headings</h5>${renderList(sections.headings, item => `<li>H${escapeHtml(item.level)} line ${escapeHtml(item.line)} - ${escapeHtml(item.text)}</li>`)}</section>
      <section class="result-section"><h5>Symbols</h5>${renderList(sections.symbols, item => `<li>${escapeHtml(typeof item === "string" ? item : JSON.stringify(item))}</li>`)}</section>
      <section class="result-section"><h5>Links</h5>${renderList(sections.links, item => `<li>${escapeHtml(typeof item === "string" ? item : JSON.stringify(item))}</li>`)}</section>
      <section class="result-section"><h5>TODO/FIXME findings</h5>${renderList(sections.todoFixme, item => `<li>${escapeHtml(typeof item === "string" ? item : JSON.stringify(item))}</li>`)}</section>
      <section class="result-section"><h5>Duplicate group</h5>${renderList(sections.duplicateGroup, item => `<li>${escapeHtml(item.title)} - ${escapeHtml(view.shortArtifactPath(item.source_path))} - <span class="mono">${escapeHtml(item.artifact_id)}</span></li>`)}</section>
      <section class="result-section"><h5>Provenance references</h5>${renderList(sections.provenance, item => `<li><b>${escapeHtml(item.kind)}</b>: ${escapeHtml(item.value)}</li>`)}</section>
      <section class="result-section"><h5>Warnings</h5>${renderList(sections.warnings, item => `<li>${escapeHtml(typeof item === "string" ? item : JSON.stringify(item))}</li>`)}</section>
      <section class="result-section"><h5>Heuristic purpose</h5><div class="heuristic-label">${escapeHtml(sections.heuristic.disclaimer)}</div><p>${escapeHtml(sections.heuristic.label)}</p><p class="muted">Rule: ${escapeHtml(sections.heuristic.rule)}</p></section>
    </div>
    <details><summary>Technical view - canonical inspection JSON</summary><pre>${escapeHtml(JSON.stringify(output, null, 2))}</pre></details>`;
  }

  function renderApprovalPanel(candidate) {
    const awaiting = candidate.lifecycle_state === "awaiting_approval";
    const existingNote = candidate.approval?.note || "";
    const bindings = view.approvalBindings(candidate, $("#workerActor").value.trim(), existingNote);
    return `<section class="approval-bindings"><h5>Approval bindings</h5><dl class="source-grid">
      <dt>Candidate hash</dt><dd class="mono">${escapeHtml(bindings.candidateHash)}</dd>
      <dt>Source hash</dt><dd class="mono">${escapeHtml(bindings.sourceHash || "not applicable")}</dd>
      <dt>Worker Card hash</dt><dd class="mono">${escapeHtml(bindings.workerCardHash)}</dd>
      <dt>Execution-plan hash</dt><dd class="mono">${escapeHtml(bindings.executionPlanHash)}</dd>
      <dt>Output hash</dt><dd class="mono">${escapeHtml(bindings.outputHash)}</dd>
      <dt>Workspace generation</dt><dd>${escapeHtml(bindings.workspaceGeneration)}</dd>
      <dt>Actor assertion</dt><dd>${escapeHtml(candidate.approval?.human_actor_assertion || bindings.actorAssertion)} - not authenticated identity</dd>
      <dt>Approval note</dt><dd>${awaiting ? "Required before approval" : escapeHtml(existingNote || "No note recorded")}</dd>
    </dl>${awaiting ? `<label>Required approval note<textarea class="worker-approval-note approval-note-required" required maxlength="1000" rows="3" placeholder="State what you reviewed and approved."></textarea></label>` : ""}</section>`;
  }

  function renderProvenance(candidate) {
    const rows = view.provenanceRows(candidate);
    return `<details><summary>Readable provenance and receipts</summary><p class="muted">Hashes show byte equality. They are not signatures. Receipts are verified records, not immutable objects.</p><table class="evidence-table"><tbody>${rows.map(row => `<tr><th>${escapeHtml(row.kind)}</th><td>${escapeHtml(row.reference)}</td><td class="mono">${escapeHtml(row.hash || "hash recorded inside referenced evidence")}</td></tr>`).join("")}</tbody></table></details>`;
  }

  function renderAttachment(candidate) {
    const attachment = view.attachmentSummary(candidate);
    return `<div class="attachment-state ${escapeHtml(attachment.state)}"><b>${escapeHtml(attachment.label)}</b><ul class="safe-claim-list"><li>Source artifact is not modified.</li><li>Attachment grants no permissions.</li><li>Review status is unchanged.</li><li>Nothing executes at startup.</li></ul></div>`;
  }

  function renderRollback(candidate) {
    if (!["active", "rolled_back"].includes(candidate.lifecycle_state)) return "";
    const value = view.rollbackSummary(candidate);
    const completed = candidate.lifecycle_state === "rolled_back";
    return `<section class="rollback-panel"><h5>${completed ? "Verified rollback completion" : "Rollback review"}</h5><dl class="source-grid"><dt>Detach</dt><dd>${escapeHtml(value.detached)}</dd><dt>Recovery scope</dt><dd>${escapeHtml(value.recoveryScope)}</dd><dt>Current report hash</dt><dd class="mono">${escapeHtml(value.currentHash)}</dd><dt>Expected restored hash</dt><dd class="mono">${escapeHtml(value.expectedRestoredHash)}</dd><dt>Verified restored hash</dt><dd class="mono">${escapeHtml(value.restoredHash || "available after rollback")}</dd><dt>Source artifact</dt><dd>${value.sourceArtifactUnchanged ? "Verified unchanged" : "Not verified"}</dd></dl></section>`;
  }

  function actionButtons(candidate) {
    const actions = view.validActions(candidate.lifecycle_state);
    if (!actions.length) return '<span class="muted">No lifecycle action is valid in this state.</span>';
    return actions.map(action => {
      const labels = {
        approve: "Approve exact candidate",
        reject: "Reject candidate",
        activate: candidate.source_artifact ? "Attach approved report" : "Activate registry entry",
        rollback: candidate.source_artifact ? "Roll back attachment" : "Verify and roll back"
      };
      const style = ["approve", "activate"].includes(action) ? "primary" : "quiet";
      return `<button class="${style}" data-worker-action="${action}">${escapeHtml(labels[action])}</button>`;
    }).join("");
  }

  function candidateCard(candidate) {
    const source = candidate.source_artifact;
    const lifecycle = view.lifecycleModel(candidate.lifecycle_state);
    const tests = candidate.test_results || [];
    const report = source ? renderInspectionResult(candidate.output || {}) : `<details><summary>Technical view - candidate output</summary><pre>${escapeHtml(JSON.stringify(candidate.output || {}, null, 2))}</pre></details>`;
    return `<article class="worker-candidate" data-candidate-id="${escapeHtml(candidate.candidate_id)}">
      <div class="section-head"><div><h4>${escapeHtml(candidate.worker_id)} ${escapeHtml(candidate.worker_version)}</h4><span class="status">${escapeHtml(humanize(candidate.lifecycle_state))}</span></div><span class="badge">generation ${escapeHtml(candidate.workspace_generation)}</span></div>
      <div class="candidate-lifecycle">${lifecycle.steps.map(step => `<div class="lifecycle-step ${escapeHtml(step.status)}"><b>${escapeHtml(humanize(step.name))}</b><small>${escapeHtml(step.status)}</small></div>`).join("")}</div>
      ${renderAttachment(candidate)}
      <dl class="source-grid">
        <dt>Candidate ID</dt><dd class="mono">${escapeHtml(candidate.candidate_id)}</dd>
        <dt>Candidate hash</dt><dd class="mono">${escapeHtml(candidate.candidate_hash)}</dd>
        <dt>Source path</dt><dd class="mono">${escapeHtml(source?.source_path || "fixed reference fixture")}</dd>
        <dt>Source SHA-256</dt><dd class="mono">${escapeHtml(source?.sha256 || candidate.inputs?.[0]?.sha256 || "recorded in plan")}</dd>
        <dt>Transaction</dt><dd class="mono">${escapeHtml(candidate.transaction_id)}</dd>
        <dt>Tests</dt><dd>${tests.map(test => `${escapeHtml(test.test_id)}: ${test.passed ? "PASS" : "FAIL"}${test.source_unchanged === true ? "; source unchanged" : ""}`).join("; ") || "No test evidence"}</dd>
      </dl>
      ${report}
      ${source ? renderApprovalPanel(candidate) : candidate.lifecycle_state === "awaiting_approval" ? renderApprovalPanel(candidate) : ""}
      ${renderProvenance(candidate)}
      ${renderRollback(candidate)}
      <div class="worker-actions">${actionButtons(candidate)}</div>
    </article>`;
  }

  function renderCandidates() {
    $("#workerCandidates").innerHTML = candidates.length
      ? candidates.map(candidateCard).join("")
      : '<p class="muted">No candidates. Validate a Worker Card, create a current plan, then deliberately run the selected fixed worker.</p>';
    if (!currentPlan) renderLifecycle(candidates[0]?.lifecycle_state || "idle");
  }

  function resetValidation() {
    currentValidation = null;
    $("#workerCardPanel").hidden = true;
    $("#workerCardOutput").textContent = "";
  }

  function updateWorkerSelection({ announce = false } = {}) {
    const inspection = $("#workerSelect").value === INSPECTION_WORKER_ID;
    $("#artifactInspectionSelection").hidden = !inspection;
    resetValidation();
    clearPlan("Worker selection changed. Validate the selected Worker Card and create a new plan.", "stale", announce);
  }

  async function refresh() {
    if (loading) return setMessage("A governed-state refresh is already running.", "blocked");
    loading = true;
    setMessage("Refreshing fixed workers, artifact eligibility, and candidate evidence.", "started");
    try {
      const [workers, refreshedCandidates, options] = await Promise.all([
        request("/api/workers"),
        request("/api/candidates"),
        request("/api/artifacts/inspection-options")
      ]);
      availableWorkers = workers;
      candidates = refreshedCandidates;
      const inspectionAvailable = workers.some(worker => worker.worker_id === INSPECTION_WORKER_ID);
      if (!inspectionAvailable && $("#workerSelect").value === INSPECTION_WORKER_ID) {
        $("#workerSelect").value = REFERENCE_WORKER_ID;
      }
      const inspectionOption = $("#workerSelect").querySelector(`option[value="${INSPECTION_WORKER_ID}"]`);
      if (inspectionOption) inspectionOption.disabled = !inspectionAvailable;
      renderArtifactOptions(options);
      $("#artifactInspectionSelection").hidden = $("#workerSelect").value !== INSPECTION_WORKER_ID;
      resetValidation();
      clearPlan("Governed state was refreshed. Create a new plan before execution.");
      renderCandidates();
      $("#workerHarnessStatus").textContent = `${workers.length} fixed workers - no automatic attachment or activation`;
      setMessage("Real worker, artifact, candidate, attachment, receipt, and rollback evidence refreshed. Workshop SQLite and source artifacts were not modified.", "succeeded");
    } catch (error) {
      $("#workerHarnessStatus").textContent = "Local companion required";
      setMessage(error.message, view.messageKind(error));
    } finally {
      loading = false;
    }
  }

  async function validateWorker() {
    try {
      const workerId = selectedWorker();
      setMessage(`Validating the fixed ${workerId} Worker Card and its bounded authority.`, "started");
      const result = await request("/api/workers/validate", {
        method: "POST",
        body: JSON.stringify({ workerId })
      });
      if (!result.valid || !result.enforcement.allowed || !result.card) {
        throw new Error("Worker Card or bounded authority was rejected.");
      }
      currentValidation = { workerId, result };
      const worker = availableWorkers.find(item => item.worker_id === workerId) || {};
      renderWorkerCard(result, worker);
      setMessage("Worker Card validation succeeded. Read/write authority, denied permissions, limits, and unsupported capabilities are shown from the validated card.", "succeeded");
    } catch (error) {
      resetValidation();
      setMessage(error.message, view.messageKind(error));
    }
  }

  async function createPlan() {
    try {
      const workerId = selectedWorker();
      if (!currentValidation || currentValidation.workerId !== workerId) {
        throw new Error("Validate the currently selected Worker Card before planning.");
      }
      const body = { actor: actor() };
      if (workerId === INSPECTION_WORKER_ID) {
        const option = selectedArtifactOption();
        if (!option || !option.eligible) throw new Error("Select an eligible public-safe artifact first.");
        body.artifactId = option.artifactId;
      }
      setMessage("Creating a hash-bound execution plan from the current worker, artifact, actor, and workspace generation.", "started");
      const plan = await request(`/api/workers/${workerId}/plan`, {
        method: "POST", body: JSON.stringify(body)
      });
      displayPlan(plan);
      if (!view.isCurrentPlan(plan, currentSelection())) throw new Error("The returned plan does not match the current explicit selection.");
      setMessage("Execution plan created and current. Review its human-readable authority and exact JSON before running.", "awaiting");
    } catch (error) {
      clearPlan("No valid current plan is available.");
      setMessage(error.message, view.messageKind(error));
    }
  }

  async function runPlan() {
    if (!view.isCurrentPlan(currentPlan, currentSelection())) {
      clearPlan("Execution blocked because the plan is missing, stale, or does not match the current selection.", "stale");
      return setMessage("Execution requires a current plan for the exact worker, artifact, actor, and workspace generation.", "stale");
    }
    if (actionBusy) return setMessage("Another governed action is already running.", "blocked");
    actionBusy = true;
    $("#runSelectedWorker").disabled = true;
    renderLifecycle("running");
    setMessage("Running the one fixed worker under the reviewed plan. No automatic approval or attachment is permitted.", "started");
    try {
      const plan = currentPlan;
      const candidate = await request(`/api/workers/${plan.worker_id}/run`, {
        method: "POST",
        body: JSON.stringify({ planId: plan.plan_id, actor: actor() })
      });
      currentPlan = null;
      await refresh();
      renderLifecycle(candidate.lifecycle_state);
      setMessage(`Candidate ${candidate.candidate_id} passed declared tests and is awaiting explicit owner approval. It is not attached.`, "awaiting");
    } catch (error) {
      const kind = view.messageKind(error);
      if (kind === "stale") clearPlan("The execution plan became stale and was discarded.");
      else $("#runSelectedWorker").disabled = false;
      setMessage(error.message, kind);
    } finally {
      actionBusy = false;
    }
  }

  function promotionContext(candidate) {
    const context = {
      candidateHash: candidate.candidate_hash,
      workspaceGeneration: candidate.workspace_generation,
      actor: actor(),
      timestamp: new Date().toISOString()
    };
    if (candidate.source_artifact) {
      context.sourceArtifactHash = candidate.source_artifact.sha256;
      context.workerCardHash = candidate.worker_card_hash;
      context.executionPlanHash = candidate.plan_hash;
    }
    return context;
  }

  async function performCandidateAction(button) {
    if (actionBusy) return setMessage("Another governed action is already running.", "blocked");
    const card = button.closest("[data-candidate-id]");
    const candidateId = card.dataset.candidateId;
    const action = button.dataset.workerAction;
    actionBusy = true;
    try {
      const candidate = await request(`/api/candidates/${candidateId}`);
      if (!view.validActions(candidate.lifecycle_state).includes(action)) {
        throw new Error(`candidate_state_rejected: ${action} is not valid while the candidate is ${candidate.lifecycle_state}`);
      }
      if (action === "activate") {
        const message = candidate.source_artifact
          ? "Attach this approved inspection report? The source remains unchanged, no permission is granted, review state is unchanged, and nothing executes at startup."
          : "Register this approved harmless module? This does not execute it or grant permissions.";
        if (!confirm(message)) {
          setMessage("Attachment was cancelled; the approved candidate remains unattached.", "blocked");
          return;
        }
      }
      if (action === "rollback") {
        const rollback = view.rollbackSummary(candidate);
        if (!confirm(`Detach the bounded report and restore ${rollback.expectedRestoredHash}? The source artifact remains unchanged.`)) {
          setMessage("Rollback was cancelled; active attachment state is unchanged.", "blocked");
          return;
        }
      }
      const payload = promotionContext(candidate);
      if (action === "approve" || action === "reject") {
        const note = card.querySelector(".worker-approval-note")?.value.trim() || "";
        if (action === "approve" && !note) throw new Error("approval_note_required: an explicit approval note is required");
        payload.note = note;
      }
      card.querySelectorAll("[data-worker-action]").forEach(element => { element.disabled = true; });
      setMessage(`${humanize(action)} started for candidate ${candidateId}; exact hash and generation bindings will be revalidated.`, "started");
      const updated = await request(`/api/candidates/${candidateId}/${action}`, {
        method: "POST", body: JSON.stringify(payload)
      });
      await refresh();
      const finalState = updated.lifecycle_state === "approved" ? "Approved, not attached" : humanize(updated.lifecycle_state);
      setMessage(`Candidate ${candidateId}: ${finalState}.`, updated.lifecycle_state === "approved" ? "awaiting" : "succeeded");
    } catch (error) {
      card.querySelectorAll("[data-worker-action]").forEach(element => { element.disabled = false; });
      setMessage(error.message, view.messageKind(error));
    } finally {
      actionBusy = false;
    }
  }

  $("#validateSelectedWorker").addEventListener("click", validateWorker);
  $("#planSelectedWorker").addEventListener("click", createPlan);
  $("#runSelectedWorker").addEventListener("click", runPlan);
  $("#refreshWorkerCandidates").addEventListener("click", refresh);
  $("#refreshInspectionArtifacts").addEventListener("click", refresh);
  $("#workerSelect").addEventListener("change", () => updateWorkerSelection({ announce: true }));
  $("#inspectionArtifact").addEventListener("change", () => {
    renderArtifactDetails();
    clearPlan("Artifact selection changed. Create a new exact plan.", "stale", true);
  });
  $("#workerActor").addEventListener("input", () => {
    if (currentPlan) clearPlan("Actor assertion changed. The existing plan is no longer current.", "stale", true);
    renderCandidates();
  });
  $("#workerCandidates").addEventListener("click", event => {
    const button = event.target.closest("[data-worker-action]");
    if (button) performCandidateAction(button);
  });
  window.addEventListener("twis:modules-open", refresh);
  renderLifecycle("idle");
})();

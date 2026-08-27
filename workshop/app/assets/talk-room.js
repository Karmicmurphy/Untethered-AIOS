(() => {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const summaries = new Map();
  const RECOVERY_PREFIX = "twisTalk.recovery.v1.";
  let projectId = "";
  let sessions = [];
  let current = null;
  let recoveryTimer = null;
  let draftWasPasted = false;
  let selectedEntryId = "";
  let pendingRestoreVersion = null;
  let pendingTransfer = null;
  let lastRestoreOperation = "";
  let recognition = null;
  let listening = false;
  let localRecognitionAvailable = false;
  let localVoices = [];
  let activeUtterance = null;

  function text(value) {
    return String(value ?? "");
  }

  function formatTime(value) {
    if (!value) return "";
    const parsed = new Date(value);
    return Number.isNaN(parsed.valueOf()) ? "" : parsed.toLocaleString();
  }

  function setStatus(message, state = "") {
    const element = $("#talkSaveStatus");
    element.textContent = message;
    element.dataset.state = state;
  }

  function voiceStatus(message, state = "") {
    const element = $("#talkVoiceStatus");
    element.textContent = message;
    element.dataset.state = state;
  }

  async function api(path, options = {}) {
    const response = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    let value = null;
    try {
      value = await response.json();
    } catch {
      value = null;
    }
    if (!response.ok) {
      const error = new Error(
        value?.message || value?.error || `Talk request failed (${response.status})`,
      );
      error.code = value?.code || "talk_request_failed";
      error.details = value?.details || {};
      error.status = response.status;
      throw error;
    }
    return value;
  }

  function enabled(value) {
    [
      "#talkTitle",
      "#saveTalkTitle",
      "#talkDraft",
      "#talkEntryType",
      "#addTalkEntry",
      "#snapshotTalk",
      "#refreshTalkHistory",
      "#talkCompareLeft",
      "#talkCompareRight",
      "#compareTalkVersions",
      "#markTalkPassage",
      "#talkInspectionFilename",
      "#inspectTalkEntry",
      "#talkTransferMode",
      "#prepareTalkTransfer",
      "#talkExportFormat",
      "#exportTalkSession",
      "#talkCommand",
      "#runTalkCommand",
    ].forEach((selector) => {
      $(selector).disabled = !value;
    });
    [
      "#talkWorkerRead",
      "#talkWorkerStructure",
      "#talkWorkerNote",
    ].forEach(selector => {
      if ($(selector)) $(selector).disabled = !value;
    });
    $("#readTalkAloud").disabled = !value || localVoices.length === 0;
  }

  function recoveryKey(artifactId) {
    return `${RECOVERY_PREFIX}${artifactId}`;
  }

  function getBrowserRecovery(artifactId) {
    try {
      return JSON.parse(localStorage.getItem(recoveryKey(artifactId)) || "null");
    } catch {
      return null;
    }
  }

  function writeBrowserRecovery() {
    if (!current) return false;
    const value = {
      artifactId: current.id,
      baseVersion: current.currentVersion,
      content: $("#talkDraft").value,
      entryType: $("#talkEntryType").value,
      updatedAt: new Date().toISOString(),
    };
    try {
      if (value.content.trim()) {
        localStorage.setItem(recoveryKey(current.id), JSON.stringify(value));
      } else {
        localStorage.removeItem(recoveryKey(current.id));
      }
      return true;
    } catch {
      setStatus(
        "Browser recovery is unavailable. Add the entry now or keep this tab open.",
        "error",
      );
      return false;
    }
  }

  function clearBrowserRecovery(artifactId) {
    try {
      localStorage.removeItem(recoveryKey(artifactId));
    } catch {
      // Durable server recovery remains authoritative when browser storage is blocked.
    }
  }

  function scheduleRecovery() {
    if (!current) return;
    const browserSaved = writeBrowserRecovery();
    clearTimeout(recoveryTimer);
    const content = $("#talkDraft").value;
    if (!content.trim()) {
      setStatus(
        browserSaved ? "Draft cleared. Saved transcript unchanged." : "Draft cleared.",
        "saved",
      );
      return;
    }
    setStatus(
      browserSaved ? "Draft recovery ready; saving to local companion…" : "Saving durable recovery…",
      "saving",
    );
    recoveryTimer = setTimeout(async () => {
      const artifactId = current?.id;
      const baseVersion = current?.currentVersion;
      if (!artifactId) return;
      try {
        await api(`/api/talk-sessions/${artifactId}/recovery`, {
          method: "POST",
          body: JSON.stringify({
            content: $("#talkDraft").value,
            baseVersion,
            speaker: "owner",
            entryType: $("#talkEntryType").value,
          }),
        });
        if (current?.id === artifactId && current?.currentVersion === baseVersion) {
          setStatus("Unsaved draft is recovery-ready on this computer.", "recovery");
        }
      } catch (error) {
        if (error.code === "talk_version_conflict") {
          setStatus("Talk changed elsewhere. Reopen it before adding this draft.", "conflict");
        } else {
          setStatus(`Durable recovery failed: ${error.message}`, "error");
        }
      }
    }, 650);
  }

  function renderPicker() {
    const picker = $("#talkSessionPicker");
    const previous = current?.id || picker.value;
    picker.textContent = "";
    if (!sessions.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "No Talk sessions yet";
      picker.append(option);
      return;
    }
    const blank = document.createElement("option");
    blank.value = "";
    blank.textContent = "Choose a Talk session";
    picker.append(blank);
    sessions.forEach((session) => {
      const option = document.createElement("option");
      option.value = session.id;
      option.textContent = `${session.title} — ${session.entryCount} entries`;
      picker.append(option);
    });
    if (sessions.some((session) => session.id === previous)) {
      picker.value = previous;
    }
  }

  function renderSummaries() {
    summaries.clear();
    sessions.forEach((session) => {
      summaries.set(session.id, {
        schemaVersion: "talk-session-summary-v1",
        ...session,
      });
    });
    window.twisTalkSummaries = summaries;
    window.dispatchEvent(new CustomEvent("twis:talk-summaries"));
  }

  function entryCard(entry) {
    const card = document.createElement("article");
    card.className = `talk-entry talk-entry-${entry.speaker}`;
    card.dataset.entryId = entry.id;

    const header = document.createElement("div");
    header.className = "talk-entry-head";
    const checkLabel = document.createElement("label");
    checkLabel.className = "check";
    const check = document.createElement("input");
    check.type = "checkbox";
    check.dataset.talkEntryCheck = entry.id;
    check.addEventListener("change", () => {
      if (check.checked) selectedEntryId = entry.id;
      updateSelectionActions();
    });
    checkLabel.append(check, document.createTextNode(" Select"));
    const identity = document.createElement("span");
    identity.textContent = `${entry.speaker === "owner" ? "You" : entry.speaker} · ${entry.entryType} · ${formatTime(entry.createdAt)}`;
    header.append(identity, checkLabel);

    const content = document.createElement("p");
    content.className = "talk-entry-content";
    content.dataset.entryId = entry.id;
    content.textContent = entry.content;
    content.addEventListener("click", () => {
      selectedEntryId = entry.id;
      updateSelectionActions();
    });
    card.append(header, content);
    return card;
  }

  function updateSelectionActions() {
    const available = Boolean(current && selectedEntryId);
    $("#markTalkPassage").disabled = !available;
    $("#inspectTalkEntry").disabled = !available;
  }

  function renderTranscript() {
    const transcript = $("#talkTranscript");
    transcript.textContent = "";
    if (!current) {
      const message = document.createElement("p");
      message.className = "muted";
      message.textContent = "Create a Talk session to begin.";
      transcript.append(message);
      $("#talkEntryCount").textContent = "0 entries";
      return;
    }
    if (!current.entries.length) {
      const message = document.createElement("p");
      message.className = "muted";
      message.textContent = "This Talk is saved and empty. Add the first entry below.";
      transcript.append(message);
    } else {
      current.entries.forEach((entry) => transcript.append(entryCard(entry)));
    }
    $("#talkEntryCount").textContent =
      `${current.entryCount} entr${current.entryCount === 1 ? "y" : "ies"}`;
    transcript.scrollTop = transcript.scrollHeight;
    selectedEntryId = current.entries.at(-1)?.id || "";
    updateSelectionActions();
  }

  function renderHistory() {
    const list = $("#talkVersions");
    list.textContent = "";
    const left = $("#talkCompareLeft");
    const right = $("#talkCompareRight");
    left.textContent = "";
    right.textContent = "";
    if (!current) {
      const message = document.createElement("p");
      message.className = "muted";
      message.textContent = "No Talk session open.";
      list.append(message);
      return;
    }
    current.versions.forEach((version) => {
      [left, right].forEach((select) => {
        const option = document.createElement("option");
        option.value = String(version.number);
        option.textContent =
          `Version ${version.number} · ${version.label || version.cause} · ${version.entryCount} entries`;
        select.append(option);
      });
      const row = document.createElement("div");
      row.className = "write-version";
      const description = document.createElement("div");
      const strong = document.createElement("b");
      strong.textContent = `Version ${version.number}: ${version.label || version.cause}`;
      const small = document.createElement("small");
      small.textContent = `${version.entryCount} entries · ${formatTime(version.createdAt)}`;
      description.append(strong, small);
      const restore = document.createElement("button");
      restore.className = "quiet";
      restore.textContent =
        version.number === current.currentVersion ? "Current" : "Restore";
      restore.disabled = version.number === current.currentVersion;
      restore.addEventListener("click", () => {
        pendingRestoreVersion = version.number;
        $("#restoreTalkDialog").showModal();
      });
      row.append(description, restore);
      list.append(row);
    });
    left.value = String(current.versions.at(-1)?.number || current.currentVersion);
    right.value = String(current.currentVersion);
  }

  function renderPassages() {
    const list = $("#talkPassages");
    list.textContent = "";
    if (!current?.passages.length) {
      const message = document.createElement("p");
      message.className = "muted";
      message.textContent = "No marked passages.";
      list.append(message);
      return;
    }
    current.passages.forEach((passage) => {
      const card = document.createElement("blockquote");
      const quote = document.createElement("p");
      quote.textContent = passage.quote;
      const label = document.createElement("small");
      label.textContent = `${passage.label} · ${formatTime(passage.createdAt)}`;
      card.append(quote, label);
      list.append(card);
    });
  }

  function renderTransfer() {
    const transfers = current?.transfers || [];
    const actionable = transfers.find((transfer) =>
      ["awaiting_approval", "approved"].includes(transfer.status)
        && Number(transfer.sourceVersion) === current.currentVersion,
    );
    pendingTransfer = actionable || transfers[0] || null;
    const panel = $("#talkTransferPanel");
    panel.hidden = !pendingTransfer;
    if (!pendingTransfer) return;
    $("#talkTransferTitle").value = pendingTransfer.proposedTitle;
    $("#talkTransferPreview").value = pendingTransfer.proposedContent;
    $("#talkTransferNote").value = pendingTransfer.decisionNote || "";
    const currentBinding =
      Number(pendingTransfer.sourceVersion) === current.currentVersion;
    const awaiting =
      pendingTransfer.status === "awaiting_approval" && currentBinding;
    const approved = pendingTransfer.status === "approved" && currentBinding;
    const statusText = {
      awaiting_approval: "Awaiting approval",
      approved: "Write document created",
      rejected: "Rejected",
      rolled_back: "Rolled back",
    }[pendingTransfer.status] || pendingTransfer.status;
    $("#talkTransferStatus").textContent =
      !currentBinding
        && ["awaiting_approval", "approved"].includes(pendingTransfer.status)
        ? "Stale — Talk changed; prepare a new proposal"
        : statusText;
    $("#approveTalkTransfer").hidden = !awaiting;
    $("#rejectTalkTransfer").hidden = !awaiting;
    $("#rollbackTalkTransfer").hidden = !approved;
  }

  function chooseRecovery() {
    if (!current) return;
    const browser = getBrowserRecovery(current.id);
    const server = current.recovery;
    const candidates = [browser, server].filter(
      (value) =>
        value &&
        Number(value.baseVersion) === current.currentVersion &&
        text(value.content).trim(),
    );
    const newest = candidates.sort(
      (left, right) =>
        new Date(right.updatedAt || 0).valueOf() - new Date(left.updatedAt || 0).valueOf(),
    )[0];
    $("#talkRecoveryBanner").hidden = !newest;
    if (newest) {
      $("#talkRecoveryMessage").textContent =
        `A newer unsaved entry draft from ${formatTime(newest.updatedAt)} is available for review.`;
      $("#talkRecoveryBanner").dataset.content = newest.content;
      $("#talkRecoveryBanner").dataset.entryType = newest.entryType || "text";
    }
  }

  function renderCurrent() {
    const open = Boolean(current);
    enabled(open);
    $("#talkTitle").value = current?.title || "Untitled Talk";
    $("#talkVersionBadge").textContent = current
      ? `Saved version ${current.currentVersion} · ${current.versionCount} total`
      : "No saved version";
    $("#talkSessionPicker").value = current?.id || "";
    renderTranscript();
    renderHistory();
    renderPassages();
    renderTransfer();
    chooseRecovery();
    if (current) {
      setStatus(`Saved locally ${formatTime(current.lastSavedAt)}.`, "saved");
    } else {
      setStatus("Open or create a Talk session.");
    }
  }

  async function refreshProject(nextProjectId = null) {
    projectId = nextProjectId || window.twisGetActiveProject?.() || "";
    if (!window.twisHasCompanion?.() || !projectId) {
      sessions = [];
      renderPicker();
      enabled(false);
      setStatus("The local companion is required for durable Talk.", "error");
      return;
    }
    try {
      sessions = await api(
        `/api/talk-sessions?projectId=${encodeURIComponent(projectId)}`,
      );
      renderPicker();
      renderSummaries();
      if (current && current.projectId !== projectId) {
        current = null;
        renderCurrent();
      }
    } catch (error) {
      setStatus(`Could not load Talk sessions: ${error.message}`, "error");
    }
  }

  async function openSession(artifactId) {
    if (!artifactId) {
      current = null;
      renderCurrent();
      return;
    }
    clearTimeout(recoveryTimer);
    try {
      current = await api(`/api/talk-sessions/${encodeURIComponent(artifactId)}`);
      lastRestoreOperation = "";
      const recentRestore = current.versions.find(
        (version) => version.cause === "restore",
      );
      if (recentRestore?.number === current.currentVersion) {
        // The operation ID is returned only from the restore action. Reopening
        // keeps the history truthful without claiming rollback is still bound.
        lastRestoreOperation = "";
      }
      renderCurrent();
    } catch (error) {
      current = null;
      renderCurrent();
      setStatus(`Could not open Talk: ${error.message}`, "error");
    }
  }

  async function createSession() {
    const title = $("#newTalkTitle").value.trim() || "Untitled Talk";
    const initialContent = $("#newTalkContent").value;
    try {
      setStatus("Creating Talk session…", "saving");
      const created = await api("/api/talk-sessions", {
        method: "POST",
        body: JSON.stringify({ projectId, title, initialContent }),
      });
      $("#newTalkDialog").close();
      $("#newTalkContent").value = "";
      await refreshProject(projectId);
      await window.twisReloadArtifacts?.();
      await openSession(created.id);
    } catch (error) {
      setStatus(`Could not create Talk: ${error.message}`, "error");
    }
  }

  async function addEntry(event) {
    event?.preventDefault();
    if (!current) return;
    const content = $("#talkDraft").value;
    if (!content.trim()) {
      setStatus("Add something before saving this entry.", "error");
      return;
    }
    const artifactId = current.id;
    const voiceDraftApproved = $("#talkDraft").dataset.voiceDraftApproved === "true";
    try {
      clearTimeout(recoveryTimer);
      setStatus("Saving entry locally…", "saving");
      const updated = await api(`/api/talk-sessions/${artifactId}/entries`, {
        method: "POST",
        body: JSON.stringify({
          content,
          baseVersion: current.currentVersion,
          title: $("#talkTitle").value,
          speaker: "owner",
          entryType: $("#talkEntryType").value,
          source: voiceDraftApproved ? "voice-draft-approved" : (draftWasPasted ? "pasted" : "typed"),
        }),
      });
      current = updated;
      $("#talkDraft").value = "";
      delete $("#talkDraft").dataset.voiceDraftApproved;
      draftWasPasted = false;
      clearBrowserRecovery(artifactId);
      $("#talkRecoveryBanner").hidden = true;
      renderCurrent();
      await refreshProject(projectId);
      await window.twisReloadArtifacts?.();
    } catch (error) {
      if (error.code === "talk_version_conflict") {
        setStatus("This Talk changed after you opened it. Your draft is preserved.", "conflict");
      } else {
        setStatus(`Entry was not saved: ${error.message}`, "error");
      }
    }
  }

  async function saveTitle() {
    if (!current) return;
    try {
      setStatus("Saving Talk title locally…", "saving");
      const updated = await api(`/api/talk-sessions/${current.id}/title`, {
        method: "POST",
        body: JSON.stringify({
          title: $("#talkTitle").value,
          baseVersion: current.currentVersion,
        }),
      });
      current = updated;
      renderCurrent();
      await refreshProject(projectId);
      await window.twisReloadArtifacts?.();
      setStatus(
        updated.changed ? "Talk title saved." : "Talk title is already saved.",
        "saved",
      );
    } catch (error) {
      setStatus(`Talk title was not saved: ${error.message}`, "error");
    }
  }

  async function makeSnapshot() {
    if (!current) return;
    try {
      const updated = await api(`/api/talk-sessions/${current.id}/snapshot`, {
        method: "POST",
        body: JSON.stringify({
          baseVersion: current.currentVersion,
          label: $("#talkSnapshotLabel").value,
        }),
      });
      current = updated;
      $("#talkSnapshotDialog").close();
      $("#talkSnapshotLabel").value = "";
      renderCurrent();
      await refreshProject(projectId);
    } catch (error) {
      setStatus(`Snapshot was not saved: ${error.message}`, "error");
    }
  }

  async function compareVersions() {
    if (!current) return;
    try {
      const value = await api(
        `/api/talk-sessions/${current.id}/compare?left=${encodeURIComponent($("#talkCompareLeft").value)}&right=${encodeURIComponent($("#talkCompareRight").value)}`,
      );
      const comparison = value.comparison;
      $("#talkCompareSummary").textContent = comparison.changed
        ? `${comparison.addedEntries} added, ${comparison.removedEntries} removed, ${comparison.replacedEntries} replaced.`
        : "These transcript versions are the same.";
      const diff = $("#talkCompareDiff");
      diff.textContent = "";
      comparison.operations.forEach((operation) => {
        const card = document.createElement("section");
        const heading = document.createElement("h4");
        heading.textContent = operation.kind;
        const before = document.createElement("pre");
        before.textContent = `Before\n${operation.before.join("\n") || "Nothing"}`;
        const after = document.createElement("pre");
        after.textContent = `After\n${operation.after.join("\n") || "Nothing"}`;
        card.append(heading, before, after);
        diff.append(card);
      });
      $("#compareTalkDialog").showModal();
    } catch (error) {
      setStatus(`Comparison failed: ${error.message}`, "error");
    }
  }

  async function restoreVersion() {
    if (!current || pendingRestoreVersion === null) return;
    try {
      const updated = await api(`/api/talk-sessions/${current.id}/restore`, {
        method: "POST",
        body: JSON.stringify({
          targetVersion: pendingRestoreVersion,
          baseVersion: current.currentVersion,
          confirmed: true,
        }),
      });
      lastRestoreOperation = updated.restoreOperationId;
      current = updated;
      pendingRestoreVersion = null;
      $("#restoreTalkDialog").close();
      $("#rollbackTalkRestore").hidden = false;
      renderCurrent();
      setStatus("Earlier Talk restored after saving a recovery version.", "saved");
      await refreshProject(projectId);
    } catch (error) {
      setStatus(`Restore failed: ${error.message}`, "error");
    }
  }

  async function rollbackRestore() {
    if (!current || !lastRestoreOperation) return;
    try {
      current = await api(
        `/api/talk-restore-operations/${lastRestoreOperation}/rollback`,
        {
          method: "POST",
          body: JSON.stringify({ confirmed: true }),
        },
      );
      lastRestoreOperation = "";
      $("#rollbackTalkRestore").hidden = true;
      renderCurrent();
      setStatus("Restore undone. Later unrelated work was not changed.", "saved");
      await refreshProject(projectId);
    } catch (error) {
      setStatus(`Restore rollback was blocked: ${error.message}`, "error");
    }
  }

  function selectedTranscriptRange() {
    const selection = window.getSelection();
    const quote = selection?.toString() || "";
    if (!quote.trim() || !selection.rangeCount) return null;
    const range = selection.getRangeAt(0);
    const containerFor = (node) =>
      (node?.nodeType === Node.TEXT_NODE ? node.parentElement : node)
        ?.closest?.(".talk-entry-content");
    const startContent = containerFor(range.startContainer);
    const endContent = containerFor(range.endContainer);
    if (!startContent || startContent !== endContent) return null;
    const prefix = document.createRange();
    prefix.selectNodeContents(startContent);
    prefix.setEnd(range.startContainer, range.startOffset);
    const start = prefix.toString().length;
    return {
      entryId: startContent.dataset.entryId,
      startOffset: start,
      endOffset: start + quote.length,
      quote,
    };
  }

  async function markPassage() {
    if (!current) return;
    const range = selectedTranscriptRange();
    if (!range) {
      setStatus("Select text inside one Talk entry before marking it.", "error");
      return;
    }
    const label = prompt("Passage label:", "Important passage");
    if (label === null) return;
    try {
      await api(`/api/talk-sessions/${current.id}/passages`, {
        method: "POST",
        body: JSON.stringify({ ...range, label }),
      });
      await openSession(current.id);
      setStatus("Passage marked without changing the transcript.", "saved");
    } catch (error) {
      setStatus(`Passage was not marked: ${error.message}`, "error");
    }
  }

  function checkedEntryIds() {
    return [
      ...document.querySelectorAll("[data-talk-entry-check]:checked"),
    ].map((input) => input.dataset.talkEntryCheck);
  }

  async function prepareTransfer() {
    if (!current) return;
    const mode = $("#talkTransferMode").value;
    const entryIds = checkedEntryIds();
    if (mode === "entries" && !entryIds.length) {
      setStatus("Check at least one transcript entry to copy.", "error");
      return;
    }
    try {
      pendingTransfer = await api(`/api/talk-sessions/${current.id}/transfers`, {
        method: "POST",
        body: JSON.stringify({
          baseVersion: current.currentVersion,
          selection: { mode, entryIds },
          title: `${current.title} — Write copy`,
        }),
      });
      $("#talkTransferPanel").hidden = false;
      $("#talkTransferTitle").value = pendingTransfer.proposedTitle;
      $("#talkTransferPreview").value = pendingTransfer.proposedContent;
      $("#talkTransferStatus").textContent = "Awaiting approval";
      $("#approveTalkTransfer").hidden = false;
      $("#rejectTalkTransfer").hidden = false;
      $("#rollbackTalkTransfer").hidden = true;
      await openSession(current.id);
      setStatus("Talk-to-Write preview prepared. Source recovery point saved.", "saved");
    } catch (error) {
      setStatus(`Talk-to-Write preview failed: ${error.message}`, "error");
    }
  }

  async function decideTransfer(decision) {
    if (!pendingTransfer) return;
    const note = $("#talkTransferNote").value;
    if (decision === "approve" && !note.trim()) {
      $("#talkTransferStatus").textContent = "Awaiting approval";
      setStatus(
        "Transfer decision failed: Add a short approval note before creating the Write document",
        "error",
      );
      $("#talkTransferNote").focus();
      return;
    }
    try {
      pendingTransfer = await api(
        `/api/talk-transfers/${pendingTransfer.id}/decision`,
        {
          method: "POST",
          body: JSON.stringify({ decision, note }),
        },
      );
      if (decision === "approve") {
        $("#talkTransferStatus").textContent = "Write document created";
        $("#approveTalkTransfer").hidden = true;
        $("#rejectTalkTransfer").hidden = true;
        $("#rollbackTalkTransfer").hidden = false;
        setStatus("Write document created. Original Talk remains unchanged.", "saved");
        await window.twisReloadArtifacts?.();
      } else {
        $("#talkTransferStatus").textContent = "Rejected";
        $("#approveTalkTransfer").hidden = true;
        $("#rejectTalkTransfer").hidden = true;
        setStatus("Talk-to-Write proposal rejected. Nothing was copied.", "saved");
      }
      await openSession(current.id);
    } catch (error) {
      setStatus(`Transfer decision failed: ${error.message}`, "error");
    }
  }

  async function rollbackTransfer() {
    if (!pendingTransfer) return;
    if (
      !confirm(
        "Remove only the unchanged Write document created by this transfer? The Talk source and receipts remain.",
      )
    ) {
      return;
    }
    try {
      await api(`/api/talk-transfers/${pendingTransfer.id}/rollback`, {
        method: "POST",
        body: JSON.stringify({ confirmed: true }),
      });
      $("#talkTransferStatus").textContent = "Rolled back";
      $("#rollbackTalkTransfer").hidden = true;
      setStatus("Talk-to-Write transfer rolled back safely.", "saved");
      await window.twisReloadArtifacts?.();
      await openSession(current.id);
    } catch (error) {
      setStatus(`Transfer rollback was blocked: ${error.message}`, "error");
    }
  }

  async function exportSession() {
    if (!current) return;
    try {
      const value = await api(`/api/talk-sessions/${current.id}/exports`, {
        method: "POST",
        body: JSON.stringify({
          format: $("#talkExportFormat").value,
          includeProvenance: $("#talkExportProvenance").checked,
        }),
      });
      $("#talkExportResult").textContent = `Exported ${value.filename} locally.`;
      setStatus("Talk export saved with a receipt.", "saved");
    } catch (error) {
      $("#talkExportResult").textContent = error.message;
      setStatus(`Export failed: ${error.message}`, "error");
    }
  }

  function inspectionRows(result) {
    const container = $("#talkInspectionResult");
    container.textContent = "";
    const summary = document.createElement("p");
    summary.textContent =
      `${result.probableType}; ${result.lines} lines; ${result.characters} characters. This is lexical evidence, not semantic understanding.`;
    container.append(summary);
    const groups = [
      ["Imports or dependencies", result.importsOrDependencies],
      ["Functions", result.functions],
      ["Classes", result.classes],
      [
        "TODO / FIXME",
        result.markers.map((marker) => `Line ${marker.line}: ${marker.text}`),
      ],
      [
        "Repeated lines",
        result.repeatedLines.map((item) => `${item.count}× ${item.text}`),
      ],
    ];
    groups.forEach(([label, values]) => {
      const section = document.createElement("section");
      const heading = document.createElement("h4");
      heading.textContent = label;
      const list = document.createElement("ul");
      if (!values.length) {
        const item = document.createElement("li");
        item.textContent = "None found by the bounded lexical rules.";
        list.append(item);
      } else {
        values.forEach((value) => {
          const item = document.createElement("li");
          item.textContent = text(value);
          list.append(item);
        });
      }
      section.append(heading, list);
      container.append(section);
    });
    $("#talkInspectionPanel").hidden = false;
  }

  async function inspectEntry() {
    if (!current || !selectedEntryId) {
      setStatus("Choose a Talk entry to inspect.", "error");
      return;
    }
    try {
      const value = await api(`/api/talk-sessions/${current.id}/inspections`, {
        method: "POST",
        body: JSON.stringify({
          entryId: selectedEntryId,
          filename: $("#talkInspectionFilename").value,
        }),
      });
      inspectionRows(value.result);
      setStatus("Deterministic inspection completed without executing source.", "saved");
    } catch (error) {
      setStatus(`Inspection failed: ${error.message}`, "error");
    }
  }

  function openApprovedArtifactInspection() {
    window.twisOpenRoom?.("flashriver-review");
    setStatus(
      "Artifact Inspection opened. Its existing selection, plan, approval, and receipt gates remain in force.",
      "saved",
    );
  }

  async function runCommand() {
    try {
      const value = await api("/api/talk/commands", {
        method: "POST",
        body: JSON.stringify({ command: $("#talkCommand").value }),
      });
      if (!value.supported) {
        $("#talkCommandResult").textContent = value.message;
        return;
      }
      $("#talkCommandResult").textContent =
        "Supported. The corresponding visible owner action was opened; nothing runs silently.";
      const actions = {
        new_session: () => $("#newTalkDialog").showModal(),
        save_entry: () => addEntry(),
        show_recovery: () => {
          chooseRecovery();
          $("#talkRecoveryBanner").scrollIntoView({ block: "center" });
        },
        snapshot: () => $("#talkSnapshotDialog").showModal(),
        compare: compareVersions,
        speak: () => speakText(transcriptText()),
        stop_speaking: stopSpeaking,
        inspect: openApprovedArtifactInspection,
        talk_to_write: prepareTransfer,
        export: exportSession,
      };
      actions[value.action]?.();
    } catch (error) {
      $("#talkCommandResult").textContent = error.message;
    }
  }

  function transcriptText() {
    return (current?.entries || [])
      .map((entry) => `${entry.speaker}: ${entry.content}`)
      .join("\n\n");
  }

  function setVoiceButtons() {
    $("#startTalkListening").disabled = !localRecognitionAvailable || listening;
    $("#stopTalkListening").disabled = !listening;
    $("#talkVoiceDraft").disabled = !localRecognitionAvailable;
    $("#acceptTalkVoiceDraft").disabled =
      !localRecognitionAvailable || !$("#talkVoiceDraft").value.trim();
    const ttsReady = localVoices.length > 0 && Boolean(current);
    $("#readTalkAloud").disabled = !ttsReady;
    $("#pauseTalkReading").disabled = !activeUtterance;
    $("#stopTalkReading").disabled = !activeUtterance;
  }

  async function auditVoice() {
    try {
      await api("/api/talk/voice-capabilities");
    } catch {
      // The UI still reports browser capability truth when the companion is offline.
    }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    localRecognitionAvailable = false;
    if (
      SR &&
      "processLocally" in SR.prototype &&
      typeof SR.available === "function"
    ) {
      try {
        const status = await SR.available({
          langs: [navigator.language || "en-US"],
          processLocally: true,
          quality: "dictation",
        });
        localRecognitionAvailable = status === "available";
      } catch {
        localRecognitionAvailable = false;
      }
    }
    const loadVoices = () => {
      localVoices =
        "speechSynthesis" in window
          ? window.speechSynthesis
              .getVoices()
              .filter((voice) => voice.localService === true)
          : [];
      const recognitionTruth = localRecognitionAvailable
        ? "On-device dictation is available and stays in a review draft."
        : "Local speech-to-text is not proven here. Network recognition is disabled.";
      const synthesisTruth = localVoices.length
        ? `${localVoices.length} installed local voice${localVoices.length === 1 ? "" : "s"} available for read-aloud.`
        : "No browser voice is proven local, so read-aloud is unavailable.";
      $("#talkVoiceTruth").textContent = `${recognitionTruth} ${synthesisTruth} Raw audio is never retained.`;
      setVoiceButtons();
    };
    loadVoices();
    if ("speechSynthesis" in window) {
      window.speechSynthesis.addEventListener("voiceschanged", loadVoices, {
        once: true,
      });
    }
  }

  function stopListening() {
    if (recognition) {
      try {
        recognition.abort();
      } catch {
        // Recognition may already have ended.
      }
    }
    recognition = null;
    listening = false;
    voiceStatus("Microphone off. Nothing is recording.", "saved");
    setVoiceButtons();
  }

  function startListening() {
    if (!localRecognitionAvailable || listening) {
      voiceStatus(
        "Local speech-to-text is unavailable. Network recognition remains disabled.",
        "error",
      );
      return;
    }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SR();
    recognition.processLocally = true;
    recognition.lang = navigator.language || "en-US";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => {
      listening = true;
      voiceStatus("Listening locally. Press Stop listening to end immediately.", "listening");
      setVoiceButtons();
    };
    recognition.onresult = (event) => {
      let draft = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        draft += event.results[index][0].transcript;
      }
      $("#talkVoiceDraft").value = draft.trim();
      setVoiceButtons();
    };
    recognition.onerror = (event) => {
      voiceStatus(`Dictation failed: ${event.error}. Text Talk is unchanged.`, "error");
    };
    recognition.onend = () => {
      recognition = null;
      listening = false;
      if (!$("#talkVoiceDraft").value.trim()) {
        voiceStatus("Microphone off. No transcript was added.", "saved");
      } else {
        voiceStatus("Microphone off. Review the transcript draft before adding it.", "saved");
      }
      setVoiceButtons();
    };
    try {
      recognition.start();
    } catch (error) {
      recognition = null;
      listening = false;
      voiceStatus(`Dictation did not start: ${error.message}`, "error");
      setVoiceButtons();
    }
  }

  function toggleListening() {
    if (listening) stopListening();
    else startListening();
  }

  function acceptVoiceDraft() {
    const draft = $("#talkVoiceDraft").value.trim();
    if (!draft) return;
    const composer = $("#talkDraft");
    composer.value = `${composer.value}${composer.value ? "\n" : ""}${draft}`;
    composer.dataset.voiceDraftApproved = "true";
    $("#talkVoiceDraft").value = "";
    scheduleRecovery();
    setVoiceButtons();
    voiceStatus("Reviewed voice text copied to the composer. It is not permanent yet.", "saved");
  }

  function stopSpeaking() {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    activeUtterance = null;
    voiceStatus("Reading stopped.", "saved");
    setVoiceButtons();
  }

  function speakText(value) {
    const content = text(value).trim();
    if (!content || !localVoices.length || !("speechSynthesis" in window)) {
      voiceStatus(
        "No proven local voice is available. Text Talk remains fully usable.",
        "error",
      );
      return;
    }
    stopSpeaking();
    const utterance = new SpeechSynthesisUtterance(content.slice(0, 20000));
    utterance.voice = localVoices[0];
    utterance.onstart = () => {
      activeUtterance = utterance;
      voiceStatus(`Reading with installed local voice ${utterance.voice.name}.`, "speaking");
      setVoiceButtons();
    };
    utterance.onend = () => {
      activeUtterance = null;
      voiceStatus("Reading finished.", "saved");
      setVoiceButtons();
    };
    utterance.onerror = (event) => {
      activeUtterance = null;
      voiceStatus(`Read-aloud failed: ${event.error}. Text Talk is unchanged.`, "error");
      setVoiceButtons();
    };
    window.speechSynthesis.speak(utterance);
  }

  function pauseSpeaking() {
    if (!activeUtterance || !("speechSynthesis" in window)) return;
    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
      $("#pauseTalkReading").textContent = "Pause reading";
      voiceStatus("Reading resumed.", "speaking");
    } else {
      window.speechSynthesis.pause();
      $("#pauseTalkReading").textContent = "Resume reading";
      voiceStatus("Reading paused.", "saved");
    }
  }

  function loadRecovery() {
    const banner = $("#talkRecoveryBanner");
    $("#talkDraft").value = banner.dataset.content || "";
    $("#talkEntryType").value = banner.dataset.entryType || "text";
    banner.hidden = true;
    setStatus("Recovery loaded for review. Add it to Talk when ready.", "recovery");
    writeBrowserRecovery();
  }

  async function discardRecovery() {
    if (!current) return;
    try {
      await api(`/api/talk-sessions/${current.id}/recovery`, {
        method: "DELETE",
        body: "{}",
      });
      clearBrowserRecovery(current.id);
      $("#talkRecoveryBanner").hidden = true;
      $("#talkDraft").value = "";
      current.recovery = null;
      current.hasRecovery = false;
      setStatus("Unsaved recovery discarded. Saved transcript unchanged.", "saved");
      await refreshProject(projectId);
    } catch (error) {
      setStatus(`Recovery was not discarded: ${error.message}`, "error");
    }
  }

  function showHistory(artifactId) {
    window.twisOpenRoom?.("talk");
    openSession(artifactId).then(() => {
      $("#talkVersions").scrollIntoView({ block: "center" });
    });
  }

  function showExport(artifactId) {
    window.twisOpenRoom?.("talk");
    openSession(artifactId).then(() => {
      $("#talkExportFormat").focus();
    });
  }

  function showTransfer(artifactId) {
    window.twisOpenRoom?.("talk");
    openSession(artifactId).then(() => {
      $("#talkTransferMode").focus();
    });
  }

  function onRoomOpen() {
    refreshProject().then(() => {
      if (!current && sessions.length) openSession(sessions[0].id);
    });
    auditVoice();
  }

  $("#talkSessionPicker").addEventListener("change", (event) =>
    openSession(event.target.value),
  );
  $("#newTalkSession").addEventListener("click", () => {
    $("#newTalkTitle").value = "Untitled Talk";
    $("#newTalkContent").value = "";
    $("#newTalkDialog").showModal();
  });
  $("#confirmNewTalk").addEventListener("click", (event) => {
    event.preventDefault();
    createSession();
  });
  $("#talkComposer").addEventListener("submit", addEntry);
  $("#saveTalkTitle").addEventListener("click", saveTitle);
  $("#talkDraft").addEventListener("input", scheduleRecovery);
  $("#talkDraft").addEventListener("paste", () => {
    draftWasPasted = true;
  });
  $("#talkEntryType").addEventListener("change", scheduleRecovery);
  $("#loadTalkRecovery").addEventListener("click", loadRecovery);
  $("#discardTalkRecovery").addEventListener("click", discardRecovery);
  $("#snapshotTalk").addEventListener("click", () =>
    $("#talkSnapshotDialog").showModal(),
  );
  $("#confirmTalkSnapshot").addEventListener("click", (event) => {
    event.preventDefault();
    makeSnapshot();
  });
  $("#refreshTalkHistory").addEventListener("click", () =>
    current && openSession(current.id),
  );
  $("#compareTalkVersions").addEventListener("click", compareVersions);
  $("#closeTalkCompare").addEventListener("click", () =>
    $("#compareTalkDialog").close(),
  );
  $("#confirmTalkRestore").addEventListener("click", (event) => {
    event.preventDefault();
    restoreVersion();
  });
  $("#rollbackTalkRestore").addEventListener("click", rollbackRestore);
  $("#markTalkPassage").addEventListener("click", markPassage);
  $("#inspectTalkEntry").addEventListener("click", inspectEntry);
  $("#openApprovedArtifactInspection").addEventListener(
    "click",
    openApprovedArtifactInspection,
  );
  $("#prepareTalkTransfer").addEventListener("click", prepareTransfer);
  $("#approveTalkTransfer").addEventListener("click", () =>
    decideTransfer("approve"),
  );
  $("#rejectTalkTransfer").addEventListener("click", () =>
    decideTransfer("reject"),
  );
  $("#rollbackTalkTransfer").addEventListener("click", rollbackTransfer);
  $("#exportTalkSession").addEventListener("click", exportSession);
  $("#runTalkCommand").addEventListener("click", runCommand);
  $("#leaveTalk").addEventListener("click", () => window.twisOpenRoom?.("home"));
  $("#startTalkListening").addEventListener("click", startListening);
  $("#stopTalkListening").addEventListener("click", stopListening);
  $("#acceptTalkVoiceDraft").addEventListener("click", acceptVoiceDraft);
  $("#talkVoiceDraft").addEventListener("input", setVoiceButtons);
  $("#readTalkAloud").addEventListener("click", () => speakText(transcriptText()));
  $("#pauseTalkReading").addEventListener("click", pauseSpeaking);
  $("#stopTalkReading").addEventListener("click", stopSpeaking);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") writeBrowserRecovery();
  });
  window.addEventListener("beforeunload", writeBrowserRecovery);

  window.twisTalkRoom = {
    getState: () => ({
      artifactId: current?.id || null,
      projectId,
      currentVersion: current?.currentVersion || 0,
      selectedEntryId: selectedEntryId || null,
    }),
    onRoomOpen,
    refreshProject,
    openSession,
    showHistory,
    showExport,
    showTransfer,
    toggleListening,
    speakText,
    stopSpeaking,
  };
  window.twisTalkSummaries = summaries;
  auditVoice();
})();

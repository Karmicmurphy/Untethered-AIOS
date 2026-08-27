(() => {
  "use strict";

  const LIFECYCLE = ["planned", "running", "awaiting_approval", "approved", "active", "rolled_back"];
  const ACTIONS = {
    awaiting_approval: ["approve", "reject"],
    approved: ["activate"],
    active: ["rollback"]
  };

  const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[character]);

  function shortArtifactPath(value) {
    const normalized = String(value || "").replace(/\\/g, "/");
    const marker = "/docs/";
    const index = normalized.toLowerCase().lastIndexOf(marker);
    if (index >= 0) return `docs\\${normalized.slice(index + marker.length).replace(/\//g, "\\")}`;
    const parts = normalized.split("/").filter(Boolean);
    return parts.slice(-3).join("\\") || "path unavailable";
  }

  function artifactLabel(option) {
    return `${String(option?.title || "Untitled")} - ${shortArtifactPath(option?.sourcePath)}`;
  }

  function formatBytes(value) {
    if (!Number.isFinite(value) || value < 0) return "unavailable";
    if (value < 1024) return `${value} B`;
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KiB`;
    return `${(value / (1024 * 1024)).toFixed(1)} MiB`;
  }

  function eligibilitySummary(options, refreshedAt) {
    const values = Array.isArray(options) ? options : [];
    const eligible = values.filter(option => option.eligible === true);
    const blocked = values.filter(option => option.eligible !== true);
    const reasons = {};
    blocked.forEach(option => (option.blockedReasons || []).forEach(reason => {
      reasons[reason] = (reasons[reason] || 0) + 1;
    }));
    return {
      eligible: eligible.length,
      blocked: blocked.length,
      sourceHashMismatches: reasons.source_hash_mismatch || 0,
      reasons,
      refreshedAt: refreshedAt || null
    };
  }

  function workerCardSummary(validation, worker = {}) {
    const card = validation?.card || {};
    return {
      workerName: card.worker_id || worker.worker_id || "unavailable",
      version: card.version || worker.version || "unavailable",
      readAuthority: Array.isArray(card.allowed_read_roots) ? card.allowed_read_roots : [],
      writeAuthority: Array.isArray(card.allowed_write_roots) ? card.allowed_write_roots : [],
      blockedRoots: Array.isArray(card.blocked_roots) ? card.blocked_roots : [],
      network: card.network_allowed === true,
      shell: card.shell_allowed === true,
      destructiveActions: card.destructive_actions_allowed === true,
      approvalRequired: card.approval_required === true,
      automaticActivation: worker.auto_activation === true,
      timeoutSeconds: card.timeout_seconds,
      tests: Array.isArray(card.test_commands) ? card.test_commands : [],
      acceptedInputs: Array.isArray(card.accepted_input_types) ? card.accepted_input_types : [],
      producedOutputs: Array.isArray(card.produced_output_types) ? card.produced_output_types : [],
      unsupported: [
        "Arbitrary workers",
        "Authenticated human identity",
        "OS-level network isolation",
        "Unrestricted shell",
        "Destructive actions",
        "Automatic activation"
      ],
      valid: validation?.valid === true && validation?.enforcement?.allowed === true,
      workerCardHash: validation?.worker_card_hash || null
    };
  }

  function planSummary(plan) {
    const selected = plan?.selected_artifact || {};
    return {
      selectedArtifact: selected.artifact_id ? {
        id: selected.artifact_id,
        path: selected.source_path,
        sha256: selected.sha256,
        fileType: selected.file_type,
        byteCount: selected.byte_count,
        reviewStatus: selected.review_status
      } : null,
      worker: `${plan?.worker_id || "unavailable"} ${plan?.worker_version || ""}`.trim(),
      readRoot: plan?.requested_read_root || plan?.canonical_read_roots || [],
      writeRoot: plan?.canonical_write_roots || [],
      blockedRoots: plan?.blocked_roots || [],
      permissions: plan?.requested_permissions || {},
      timeoutSeconds: plan?.timeout_seconds,
      maxInputBytes: plan?.max_input_bytes,
      maxOutputBytes: plan?.max_output_bytes,
      maxCapturedStreamBytes: plan?.max_captured_stream_bytes,
      requiredTests: plan?.required_tests || [],
      recoveryScope: plan?.recovery_point_plan?.restore_scope || "unavailable",
      workspaceGeneration: plan?.workspace_generation,
      autoActivation: plan?.auto_activate === true,
      planId: plan?.plan_id,
      planHash: plan?.plan_hash,
      warnings: [
        "Actor assertion is local text, not authenticated identity.",
        "Network denial is application and host policy, not OS-level network isolation.",
        "Hashes prove byte equality, not identity or signature authority."
      ]
    };
  }

  function validActions(lifecycleState) {
    return [...(ACTIONS[lifecycleState] || [])];
  }

  function lifecycleModel(lifecycleState) {
    const state = String(lifecycleState || "idle");
    if (!LIFECYCLE.includes(state)) {
      return {
        state,
        steps: LIFECYCLE.map(name => ({ name, status: "upcoming" })),
        actions: validActions(state)
      };
    }
    const current = LIFECYCLE.indexOf(state);
    return {
      state,
      steps: LIFECYCLE.map((name, index) => ({
        name,
        status: index < current ? "complete" : index === current ? "current" : "upcoming"
      })),
      actions: validActions(state)
    };
  }

  function attachmentSummary(candidate) {
    const state = candidate?.lifecycle_state;
    if (state === "active") return { state: "active", label: "Report attached and active" };
    if (state === "rolled_back") return { state: "rolled_back", label: "Attachment rolled back; history preserved" };
    if (state === "approved") return { state: "approved", label: "Candidate approved, not attached" };
    return { state: "not_attached", label: "Report is not attached" };
  }

  function resultSections(output = {}) {
    return {
      sourceIdentity: {
        artifactId: output.artifact_id,
        sourcePath: output.source_path,
        sourceSha256: output.source_sha256,
        fileType: output.file_type
      },
      counts: {
        bytes: output.byte_count,
        lines: output.line_count,
        words: output.word_count
      },
      headings: output.headings || [],
      symbols: output.code_symbols || [],
      links: output.links || [],
      todoFixme: output.todo_fixme_markers || [],
      duplicateGroup: output.duplicate_hash_group || [],
      reviewStatus: output.review_status || "unavailable",
      provenance: output.provenance_references || [],
      warnings: output.warnings || [],
      heuristic: {
        label: output.likely_document_purpose?.label || "unavailable",
        rule: output.likely_document_purpose?.rule || "unavailable",
        classification: output.likely_document_purpose?.classification || "unavailable",
        disclaimer: "Heuristic - not established fact"
      }
    };
  }

  function approvalBindings(candidate, actorAssertion = "", note = "") {
    return {
      candidateHash: candidate?.candidate_hash,
      sourceHash: candidate?.source_artifact?.sha256,
      workerCardHash: candidate?.worker_card_hash,
      executionPlanHash: candidate?.plan_hash,
      outputHash: candidate?.output_hash,
      workspaceGeneration: candidate?.workspace_generation,
      actorAssertion,
      actorIdentityAuthenticated: candidate?.approval?.identity_authenticated === true,
      approvalNote: note
    };
  }

  function provenanceRows(candidate) {
    const values = [
      ["Artifact", candidate?.source_artifact?.artifact_id, candidate?.source_artifact?.sha256],
      ["Worker Card", candidate?.worker_card_path, candidate?.worker_card_hash],
      ["Plan", candidate?.plan_id, candidate?.plan_hash],
      ["Transaction", candidate?.transaction_id, null],
      ["Test", candidate?.test_results_path, candidate?.test_evidence_hash],
      ["Candidate", candidate?.candidate_id, candidate?.candidate_hash],
      ["Approval", candidate?.approval?.timestamp, candidate?.approval?.candidate_hash],
      ["Attachment", candidate?.activation?.timestamp, candidate?.activation?.artifact_attachment?.report_sha256],
      ["Rollback", candidate?.rollback?.timestamp, candidate?.rollback?.restored_sha256]
    ];
    const rows = values
      .filter(([, reference, hash]) => reference || hash)
      .map(([kind, reference, hash]) => ({ kind, reference: reference || "recorded", hash: hash || null }));
    (candidate?.receipt_paths || []).forEach((path, index) => rows.push({
      kind: `Receipt ${index + 1}`,
      reference: path,
      hash: null
    }));
    return rows;
  }

  function rollbackSummary(candidate) {
    return {
      detached: candidate?.activation?.artifact_attachment?.report_path || candidate?.candidate_output_path || "bounded candidate output",
      recoveryScope: candidate?.rollback?.scope || candidate?.recovery_point?.kind || "one bounded output and attachment registry status",
      currentHash: candidate?.output_hash,
      expectedRestoredHash: candidate?.rollback?.expected_sha256 || candidate?.recovery_point?.sha256,
      restoredHash: candidate?.rollback?.restored_sha256 || null,
      sourceArtifactUnchanged: candidate?.test_results?.every(test => test.source_unchanged !== false) !== false
    };
  }

  function isCurrentPlan(plan, selection) {
    if (!plan || !selection) return false;
    if (!plan.plan_id || !plan.plan_hash || !Number.isInteger(plan.workspace_generation)) return false;
    if (plan.worker_id !== selection.workerId || plan.initiating_actor !== selection.actor) return false;
    if (plan.auto_activate !== false) return false;
    if (selection.workerId === "artifact-compass-inspection-worker") {
      return plan.selected_artifact?.artifact_id === selection.artifactId;
    }
    return true;
  }

  function messageKind(error) {
    const value = String(error?.message || error || "").toLowerCase();
    if (/stale|generation|hash_mismatch|state_rejected|changed/.test(value)) return "stale";
    if (/required|denied|blocked|invalid|unsupported|unavailable/.test(value)) return "blocked";
    return "failed";
  }

  globalThis.twisWorkerHarnessView = Object.freeze({
    LIFECYCLE: [...LIFECYCLE],
    approvalBindings,
    artifactLabel,
    attachmentSummary,
    eligibilitySummary,
    escapeHtml,
    formatBytes,
    isCurrentPlan,
    lifecycleModel,
    messageKind,
    planSummary,
    provenanceRows,
    resultSections,
    rollbackSummary,
    shortArtifactPath,
    validActions,
    workerCardSummary
  });
})();

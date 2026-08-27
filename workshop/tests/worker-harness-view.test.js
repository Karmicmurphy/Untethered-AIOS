import test from "node:test";
import assert from "node:assert/strict";

await import("../app/assets/worker-harness-view.js");

const view = globalThis.twisWorkerHarnessView;

const rootAgent = {
  artifactId: "artifact-root",
  title: "AGENT.md",
  sourcePath: "C:\\TWIS\\data\\projects\\flashriver\\docs\\AGENT.md",
  eligible: true,
  blockedReasons: []
};
const copiedAgent = {
  artifactId: "artifact-copy",
  title: "AGENT.md",
  sourcePath: "C:\\TWIS\\data\\projects\\flashriver\\docs\\agent_files\\AGENT.md",
  eligible: true,
  blockedReasons: []
};

test("duplicate artifact labels preserve title and distinct shortened paths", () => {
  assert.equal(view.artifactLabel(rootAgent), "AGENT.md - docs\\AGENT.md");
  assert.equal(view.artifactLabel(copiedAgent), "AGENT.md - docs\\agent_files\\AGENT.md");
  assert.notEqual(view.artifactLabel(rootAgent), view.artifactLabel(copiedAgent));
});

test("eligibility totals and reason categories reflect the returned options", () => {
  const refreshedAt = "2026-07-22T02:00:00.000Z";
  const summary = view.eligibilitySummary([
    rootAgent,
    copiedAgent,
    { eligible: false, blockedReasons: ["private_source", "unsupported_extension"] },
    { eligible: false, blockedReasons: ["source_hash_mismatch"] }
  ], refreshedAt);
  assert.deepEqual(summary, {
    eligible: 2,
    blocked: 2,
    sourceHashMismatches: 1,
    reasons: { private_source: 1, unsupported_extension: 1, source_hash_mismatch: 1 },
    refreshedAt
  });
});

test("Worker Card summary uses validated card values rather than decorative claims", () => {
  const validation = {
    valid: true,
    enforcement: { allowed: true },
    worker_card_hash: "A".repeat(64),
    card: {
      worker_id: "artifact-compass-inspection-worker",
      version: "0.4.0",
      allowed_read_roots: ["C:\\public\\docs"],
      allowed_write_roots: ["C:\\harness\\inspection-output"],
      blocked_roots: ["C:\\private"],
      network_allowed: false,
      shell_allowed: false,
      destructive_actions_allowed: false,
      approval_required: true,
      timeout_seconds: 5,
      test_commands: ["artifact-inspection-output-v0.4"],
      accepted_input_types: ["text/markdown"],
      produced_output_types: ["application/json"]
    }
  };
  const summary = view.workerCardSummary(validation, { auto_activation: false });
  assert.equal(summary.workerName, validation.card.worker_id);
  assert.deepEqual(summary.readAuthority, validation.card.allowed_read_roots);
  assert.deepEqual(summary.writeAuthority, validation.card.allowed_write_roots);
  assert.equal(summary.network, false);
  assert.equal(summary.shell, false);
  assert.equal(summary.destructiveActions, false);
  assert.equal(summary.approvalRequired, true);
  assert.equal(summary.automaticActivation, false);
  assert.equal(summary.workerCardHash, validation.worker_card_hash);
});

test("plan summary is a direct human-readable projection of exact plan JSON", () => {
  const plan = {
    worker_id: "artifact-compass-inspection-worker",
    worker_version: "0.4.0",
    plan_id: "plan-1",
    plan_hash: "B".repeat(64),
    initiating_actor: "owner",
    selected_artifact: {
      artifact_id: "artifact-root",
      source_path: rootAgent.sourcePath,
      sha256: "C".repeat(64),
      file_type: "text/markdown",
      byte_count: 2462,
      review_status: "unreviewed"
    },
    requested_read_root: "C:\\public\\docs",
    canonical_write_roots: ["C:\\harness\\inspection-output"],
    blocked_roots: ["C:\\private"],
    requested_permissions: { network: false, approval_required: true },
    timeout_seconds: 5,
    max_input_bytes: 524288,
    max_output_bytes: 131072,
    max_captured_stream_bytes: 16384,
    required_tests: ["artifact-inspection-output-v0.4"],
    recovery_point_plan: { restore_scope: "one bounded output" },
    workspace_generation: 2,
    auto_activate: false
  };
  const summary = view.planSummary(plan);
  assert.equal(summary.selectedArtifact.id, plan.selected_artifact.artifact_id);
  assert.equal(summary.selectedArtifact.sha256, plan.selected_artifact.sha256);
  assert.equal(summary.readRoot, plan.requested_read_root);
  assert.deepEqual(summary.writeRoot, plan.canonical_write_roots);
  assert.deepEqual(summary.permissions, plan.requested_permissions);
  assert.equal(summary.recoveryScope, plan.recovery_point_plan.restore_scope);
  assert.equal(summary.workspaceGeneration, plan.workspace_generation);
  assert.equal(summary.autoActivation, false);
});

test("run eligibility rejects missing, selection-mismatched, actor-mismatched, and auto-activating plans", () => {
  const selection = { workerId: "artifact-compass-inspection-worker", artifactId: "artifact-root", actor: "owner" };
  const plan = {
    worker_id: selection.workerId,
    plan_id: "plan-1",
    plan_hash: "D".repeat(64),
    workspace_generation: 2,
    initiating_actor: selection.actor,
    selected_artifact: { artifact_id: selection.artifactId },
    auto_activate: false
  };
  assert.equal(view.isCurrentPlan(plan, selection), true);
  assert.equal(view.isCurrentPlan(null, selection), false);
  assert.equal(view.isCurrentPlan(plan, { ...selection, artifactId: "other" }), false);
  assert.equal(view.isCurrentPlan(plan, { ...selection, actor: "other" }), false);
  assert.equal(view.isCurrentPlan({ ...plan, auto_activate: true }, selection), false);
});

test("only valid lifecycle actions are available", () => {
  assert.deepEqual(view.validActions("planned"), []);
  assert.deepEqual(view.validActions("running"), []);
  assert.deepEqual(view.validActions("awaiting_approval"), ["approve", "reject"]);
  assert.deepEqual(view.validActions("approved"), ["activate"]);
  assert.deepEqual(view.validActions("active"), ["rollback"]);
  assert.deepEqual(view.validActions("rolled_back"), []);
});

test("attachment state distinguishes approved, active, and rolled back", () => {
  assert.equal(view.attachmentSummary({ lifecycle_state: "approved" }).label, "Candidate approved, not attached");
  assert.equal(view.attachmentSummary({ lifecycle_state: "active" }).label, "Report attached and active");
  assert.equal(view.attachmentSummary({ lifecycle_state: "rolled_back" }).label, "Attachment rolled back; history preserved");
});

test("inspection purpose is explicitly labeled heuristic and not fact", () => {
  const sections = view.resultSections({
    likely_document_purpose: {
      classification: "heuristic_not_fact",
      label: "general_text_document",
      rule: "no_more_specific_rule_matched"
    }
  });
  assert.equal(sections.heuristic.disclaimer, "Heuristic - not established fact");
  assert.equal(sections.heuristic.classification, "heuristic_not_fact");
});

test("HTML and imported text are escaped before template rendering", () => {
  assert.equal(
    view.escapeHtml('<img src=x onerror="alert(1)">& imported'),
    "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;&amp; imported"
  );
});

test("provenance and receipts retain references without calling hashes signatures", () => {
  const rows = view.provenanceRows({
    candidate_id: "candidate-1",
    candidate_hash: "A".repeat(64),
    worker_card_path: "card.json",
    worker_card_hash: "B".repeat(64),
    plan_id: "plan-1",
    plan_hash: "C".repeat(64),
    transaction_id: "transaction-1",
    receipt_paths: ["receipt-1.json"]
  });
  assert.ok(rows.some(row => row.kind === "Candidate" && row.hash === "A".repeat(64)));
  assert.ok(rows.some(row => row.kind === "Receipt 1" && row.reference === "receipt-1.json"));
  assert.equal(JSON.stringify(rows).includes("signature"), false);
});

test("stale and blocked errors are classified for visible owner messages", () => {
  assert.equal(view.messageKind(new Error("workspace_generation_mismatch")), "stale");
  assert.equal(view.messageKind(new Error("approval_note_required")), "blocked");
  assert.equal(view.messageKind(new Error("unexpected failure")), "failed");
});

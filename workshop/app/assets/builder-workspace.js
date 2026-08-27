(() => {
  "use strict";
  const $ = selector => document.querySelector(selector);
  const profiles = {
    handoff: ["Codex Build Handoff", "ChatGPT Continuation Handoff", "Human Technical Handoff", "Project Recovery Handoff"],
    prompt: ["Codex Implementation Prompt", "ChatGPT Research Prompt", "Local Model Task Prompt", "Human Work Order"],
    draft: ["Rewrite clearly", "Shorten without losing meaning", "Expand rough notes", "Change tone", "Organize into a structured document"],
    compare: ["General comparison", "Factual consistency", "Implementation differences", "Project status differences", "Requirement coverage", "Conflicting claims", "Missing evidence"],
    visual: ["Song or album cover", "Story or scene artwork", "Character concept", "Poster or promotional image", "Product or invention concept", "Memorial or emotional artwork", "General image concept"],
    music: ["Full original song", "Song from existing story or source", "Instrumental composition", "Song rewrite or alternate arrangement", "Soundtrack or cinematic cue", "Memorial or emotional song", "Commercial, theme, or promotional music", "General music concept"],
    video: ["Cinematic scene", "Music video", "Short-form vertical", "Talking / performance", "Surreal visual", "Documentary / story", "Product / demonstration", "Image-to-video concept"],
    build: ["Add feature", "Fix defect", "UI refinement", "Local tool", "Integration", "Refactor bounded area", "Test/verification task", "Deployment work order"],
    module: ["TWIS native capability", "Agent Skill", "Local Python worker", "Local JavaScript worker", "Disposable worker", "MCP server wrapper", "MCP client adapter", "WASI component proposal", "Comfy workflow adapter", "Cloudflare free-tier worker", "Local tool", "Worker", "Adapter", "Importer", "Exporter", "Media tool", "Research tool", "System utility", "Experimental module"],
    ai: ["Rewrite while preserving meaning"],
  };
  const workerTypes = {
    handoff: "handoff-proposal-builder", prompt: "prompt-proposal-builder", draft: "draft-workshop",
    compare: "evidence-compare", visual: "visual-brief-builder", music: "song-production-brief-builder", video: "video-production-brief-builder",
    build: "build-work-order-builder", module: "module-proposal-builder", ai: "local-ai-rewrite",
  };
  const state = { sources: [], job: null, preselectSourceId: null };
  const recoveryKey = projectId => `twis.builder.job.${projectId}`;

  async function api(path, body) {
    const response = await fetch(path, body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const value = await response.json().catch(() => ({}));
    if (!response.ok) { const error = new Error(value.error || `Builder request failed (${response.status})`); error.code = value.code; throw error; }
    return value;
  }
  function setStatus(message, failed = false) { const node = $("#builderStatus"); if (node) { node.textContent = message; node.dataset.state = failed ? "failed" : ""; } }
  function showError(error) {
    const known = {
      approval_note_required: "Add an approval note.", stale_plan: "The plan is stale because a selected source changed.",
      builder_goal_invalid: "Enter a valid bounded instruction.", builder_profile_unsupported: "Choose a supported fixed preset.",
      builder_sources_invalid: "Select an eligible source or enter nonblank owner notes within this builder's source limit.",
      builder_controls_invalid: "Review the bounded Visual Brief fields.", save_requires_approval: "Approve the proposal before saving.",
      export_requires_approval: "Approve the proposal before exporting.",
    };
    setStatus(known[error.code] || error.message || "The builder stopped safely.", true);
  }
  function selectedIds() { return [...document.querySelectorAll("#builderSources input:checked")].map(node => node.value); }
  function currentType() { return $("#builderType")?.value || "handoff"; }
  function updateSelectionSummary() {
    const count = selectedIds().length;
    const node = $("#builderSourceCount");
    if (!node) return;
    const type = currentType();
    const notes = type === "visual" && Boolean($("#builderVisualNotes")?.value.trim());
    const musicNotes = type === "music" && Boolean($("#builderMusicNotes")?.value.trim());
    const lyrics = type === "music" && Boolean($("#builderMusicLyrics")?.value.trim());
    const videoNotes = type === "video" && Boolean($("#builderVideoNotes")?.value.trim());
    const buildNotes = type === "build" && Boolean($("#builderBuildNotes")?.value.trim());
    const moduleNotes = type === "module" && Boolean($("#builderModuleNotes")?.value.trim());
    node.textContent = type === "compare" ? `${count} selected · minimum 2 · maximum 8`
      : type === "visual" ? `${count} selected · maximum 4 · owner notes ${notes ? "present" : "empty"}`
        : type === "music" ? `${count} selected · maximum 4 · music notes ${musicNotes ? "present" : "empty"} · lyrics ${lyrics ? "present" : "empty"}`
        : type === "video" ? `${count} selected · maximum 4 · video notes ${videoNotes ? "present" : "empty"}`
        : type === "build" ? `${count} selected · maximum 4 · build input ${buildNotes ? "present" : "controls only"}`
        : type === "module" ? `${count} selected · maximum 4 · module input ${moduleNotes ? "present" : "controls only"}`
        : type === "ai" ? `${count} selected · exactly 1 required · registered source remains unchanged`
        : `${count} selected`;
  }
  function renderSources() {
    const root = $("#builderSources");
    if (!root) return;
    const previouslySelected = new Set(selectedIds());
    root.replaceChildren();
    const workerId = workerTypes[currentType()];
    const usable = state.sources.filter(source => source.allowedWorkers?.includes(workerId));
    if (!usable.length) { root.append(Object.assign(document.createElement("p"), { className: "muted", textContent: "No current registered text sources are available." })); updateSelectionSummary(); return; }
    for (const source of usable) {
      const label = document.createElement("label"); label.className = "builder-source";
      const check = Object.assign(document.createElement("input"), { type: "checkbox", value: source.artifactId });
      check.checked = previouslySelected.has(source.artifactId) || source.artifactId === state.preselectSourceId;
      const details = document.createElement("span");
      const title = document.createElement("b"); title.textContent = source.title;
      const shortHash = source.sha256 ? `${source.sha256.slice(0, 12)}…${source.sha256.slice(-8)}` : "hash verified when selected";
      const meta = document.createElement("small"); meta.textContent = `${source.kind} · ID ${source.artifactId} · SHA-256 ${shortHash} · ${source.bytes} bytes · ${source.projectId} · ${source.accessState} · ${source.sourceState}`;
      const remove = Object.assign(document.createElement("button"), { type: "button", className: "link", textContent: "Remove" });
      remove.hidden = !check.checked;
      remove.addEventListener("click", () => { check.checked = false; remove.hidden = true; updateSelectionSummary(); });
      check.addEventListener("change", () => {
        const maximum = currentType() === "compare" ? 8 : currentType() === "ai" ? 1 : ["visual", "music", "video", "build", "module"].includes(currentType()) ? 4 : null;
        if (maximum && selectedIds().length > maximum) { check.checked = false; setStatus(`This builder accepts at most ${maximum} sources.`, true); }
        remove.hidden = !check.checked; updateSelectionSummary();
      });
      details.append(title, meta, remove); label.append(check, details); root.append(label);
    }
    updateSelectionSummary();
  }
  function renderProfiles() {
    const select = $("#builderProfile"); if (!select) return;
    const type = currentType();
    select.replaceChildren(...profiles[type].map(label => Object.assign(document.createElement("option"), { value: label, textContent: label })));
    $("#builderRoughLabel").hidden = type !== "draft";
    $("#builderVisualControls").hidden = type !== "visual";
    $("#builderMusicControls").hidden = type !== "music";
    $("#builderVideoControls").hidden = type !== "video";
    $("#builderBuildControls").hidden = type !== "build";
    $("#builderModuleControls").hidden = type !== "module";
    $("#builderAiControls").hidden = type !== "ai";
    const label = $("#builderGoalLabel");
    label.firstChild.textContent = ["video", "music", "build", "module"].includes(type) ? "4. Optional owner instructions" : type === "ai" ? "4. Optional rewrite instruction" : type === "visual" ? "4. Additional visual instructions" : type === "compare" ? "4. Optional comparison instructions" : type === "draft" ? "4. Optional writing instructions" : "4. Goal or continuation instruction";
    $("#builderGoal").placeholder = type === "ai" ? "For example: make the language calm and direct while preserving every factual claim." : type === "video" ? "Optional finishing instructions for the video-production brief." : type === "music" ? "Optional finishing instructions for the song-production brief." : type === "visual" ? "Optional finishing instructions for the visual brief." : type === "compare" ? "For example: prioritize requirements that disagree." : type === "draft" ? "For example: use a calm professional tone." : "Describe the exact continuation or task.";
    renderSources();
  }
  async function load() {
    const projectId = window.twisGetActiveProject?.() || "";
    if (!projectId || !window.twisHasCompanion?.()) return;
    try {
      state.sources = await api(`/api/local-worker-sources?projectId=${encodeURIComponent(projectId)}`); renderSources(); setStatus("Registered sources current");
      const recoveredId = sessionStorage.getItem("twis.builder.job") || localStorage.getItem(recoveryKey(projectId));
      if (recoveredId && !state.job) {
        const recovered = await api(`/api/local-worker-jobs/${encodeURIComponent(recoveredId)}`);
        if (recovered.projectId === projectId) render(recovered);
        else { sessionStorage.removeItem("twis.builder.job"); localStorage.removeItem(recoveryKey(projectId)); }
      }
    } catch (error) { showError(error); }
  }
  function render(job) {
    state.job = job;
    sessionStorage.setItem("twis.builder.job", job.jobId); localStorage.setItem(recoveryKey(job.projectId), job.jobId);
    $("#builderPlan").hidden = false; $("#builderPlanState").textContent = job.statusLabel;
    const summary = $("#builderPlanSummary"); summary.replaceChildren();
    const entries = [["Builder", job.worker.name], ["Purpose or preset", job.plan.destinationProfile], ["Instructions", job.plan.ownerGoal || "No additional instructions"], ["Sources", job.sources.map(source => `${source.title} (${source.artifactId}, ${source.sha256})`).join("\n")], ["May create", job.plan.mayCreate.join(" · ") || "Nothing before separate save"], ["Cannot access", job.plan.cannotAccess.join(" · ")]];
    const capabilityContext = job.plan.capabilityRegistryContext;
    if (capabilityContext) entries.splice(3, 0,
      ["Capability decision", `${capabilityContext.recommended?.name || capabilityContext.discoveredCandidates?.[0]?.name || "Create our own proposal"} · ${capabilityContext.decision}`],
      ["Bound registry evidence", `registry ${capabilityContext.registryHash} · hardware ${capabilityContext.hardwareProfileHash} · context ${capabilityContext.contextHash}`]
    );
    for (const [name, value] of entries) { const card = document.createElement("div"); card.className = "truth-card"; card.append(Object.assign(document.createElement("small"), { textContent: name }), Object.assign(document.createElement("b"), { textContent: value })); summary.append(card); }
    $("#builderApprovePlan").hidden = !job.actions.approvePlan; $("#builderRejectPlan").hidden = !job.actions.rejectPlan; $("#builderRun").hidden = !job.actions.execute; $("#builderRecover").hidden = !job.actions.recover; $("#builderCancel").disabled = !job.actions.cancel;
    const hasResult = Boolean(job.result?.output?.text); $("#builderResult").hidden = !hasResult;
    if (hasResult) { $("#builderProposal").textContent = job.result.output.text; $("#builderValidation").textContent = `${job.statusLabel} · ${job.result.validation?.valid ? "contract valid" : "not validated"}`; }
    const exports = job.result?.exports || [];
    $("#builderExportResult").textContent = exports.length ? `Export history: ${exports.map(record => `${record.format.toUpperCase()} · ${record.path}`).join(" | ")}` : "";
    $("#builderApproveResult").hidden = !job.actions.approveResult; $("#builderRejectResult").hidden = !job.actions.rejectResult; $("#builderSave").hidden = !job.actions.saveDraft;
    const isDraft = job.worker.workerId === "draft-workshop"; const supportsAll = ["evidence-compare", "visual-brief-builder", "song-production-brief-builder", "video-production-brief-builder", "build-work-order-builder", "module-proposal-builder", "local-ai-rewrite"].includes(job.worker.workerId);
    $("#builderExportTxt").hidden = !job.actions.export; $("#builderExportMd").hidden = !job.actions.export || (!isDraft && !supportsAll); $("#builderExportJson").hidden = !job.actions.export || isDraft; $("#builderRollback").hidden = !job.actions.rollbackDraft;
    setStatus(job.statusLabel);
  }
  async function action(name, body = {}) {
    if (!state.job) return;
    try {
      render(await api(`/api/local-worker-jobs/${encodeURIComponent(state.job.jobId)}/${name}`, { actor: "local-owner", ...body }));
      if (["save-draft", "rollback"].includes(name)) await window.twisReloadArtifacts?.();
    }
    catch (error) { showError(error); }
  }
  function visualControls() {
    return {
      conceptTitle: $("#visualConceptTitle").value, centralSubject: $("#visualCentralSubject").value, setting: $("#visualSetting").value,
      moodEmotion: $("#visualMoodEmotion").value, visualStyle: $("#visualStyle").value, composition: $("#visualComposition").value,
      cameraViewpoint: $("#visualCameraViewpoint").value, lighting: $("#visualLighting").value, colorDirection: $("#visualColorDirection").value,
      aspectRatio: $("#visualAspectRatio").value, requiredText: $("#visualRequiredText").value, prohibitedText: $("#visualProhibitedText").value,
      requiredElements: $("#visualRequiredElements").value, prohibitedElements: $("#visualProhibitedElements").value, realismLevel: $("#visualRealismLevel").value,
      referenceSourcePriority: $("#visualReferenceSourcePriority").value, additionalInstructions: $("#builderGoal").value,
    };
  }
  function productionControls() {
    const ids = ["workingTitle", "centralSubject", "emotionalArc", "genre", "subgenre", "tempoBpm", "tonalCenter", "timeSignature", "vocalType", "vocalDelivery", "instrumentation", "rhythmGroove", "songStructure", "intro", "verseTreatment", "chorusTreatment", "bridgeBreakdown", "soloInstrumental", "ending", "productionTexture", "recordingCharacter", "dynamicBuild", "referenceInfluences", "requiredElements", "prohibitedElements", "lyricBoundaries", "explicitLanguagePreference", "approximateDuration", "additionalInstructions", "referenceSourcePriority"];
    return Object.fromEntries(ids.map(key => [key, $(`#music-${key}`).value]));
  }
  function videoControls() {
    const ids = ["workingTitle", "productionGoal", "coreConcept", "intendedAudience", "targetDuration", "aspectRatio", "resolutionIntent", "visualStyle", "pacing", "cameraLanguage", "environmentLocation", "subjectCharacterNotes", "wardrobeAppearance", "propsObjects", "lighting", "colorPalette", "composition", "lensFraming", "cameraMovement", "subjectMovement", "shotIdeas", "transitionStyle", "storySequence", "openingBeat", "mainProgression", "closingBeat", "audioDialogue", "narrationVoice", "musicNotes", "soundDesignNotes", "onScreenText", "effectsCompositing", "continuityRequirements", "productionConstraints", "safetyLegalConsent", "referenceSourcePriority", "unresolvedDecisions", "additionalInstructions"];
    return Object.fromEntries(ids.map(key => [key, $(`#video-${key}`).value]));
  }
  function buildControls() {
    const ids = ["workingTitle", "capabilityRequest", "buildGoal", "existingContext", "desiredOutcome", "inScope", "outOfScope", "requirements", "constraints", "relevantFilesComponents", "uiRequirements", "backendRequirements", "dataPersistence", "externalDependencies", "securitySafety", "performanceLimits", "failureBehavior", "acceptanceCriteria", "testingExpectations", "deploymentExpectations", "rollbackExpectations", "referenceSourcePriority", "unresolvedDecisions", "additionalInstructions"];
    return Object.fromEntries(ids.map(key => [key, $(`#build-${key}`).value]));
  }
  function moduleControls() {
    const ids = ["moduleName", "scaffoldType", "purpose", "problemSolved", "targetRoom", "inputs", "outputs", "localCloudBoundary", "dependencies", "hardwareExpectations", "dataStorageNeeds", "permissionsCapabilities", "uiNeeds", "risks", "licensingNotes", "integrationPoints", "testingRequirements", "recoveryRequirements", "rollbackRequirements", "acceptanceCriteria", "failureBehavior", "referenceSourcePriority", "unresolvedDecisions", "additionalInstructions"];
    return Object.fromEntries(ids.map(key => [key, $(`#module-${key}`).value]));
  }
  async function prepare() {
    try {
      const type = currentType(); const projectId = window.twisGetActiveProject?.() || ""; const instructions = $("#builderGoal").value;
      const request = {
        projectId, workerId: workerTypes[type], sourceArtifactIds: selectedIds(),
        roughText: type === "draft" ? $("#builderRoughText").value : type === "visual" ? $("#builderVisualNotes").value : undefined,
        visualControls: type === "visual" ? visualControls() : undefined,
        musicNotes: type === "music" ? $("#builderMusicNotes").value : undefined,
        musicLyrics: type === "music" ? $("#builderMusicLyrics").value : undefined,
        productionControls: type === "music" ? productionControls() : undefined,
        videoNotes: type === "video" ? $("#builderVideoNotes").value : undefined,
        videoControls: type === "video" ? videoControls() : undefined,
        buildNotes: type === "build" ? $("#builderBuildNotes").value : undefined,
        buildControls: type === "build" ? buildControls() : undefined,
        moduleNotes: type === "module" ? $("#builderModuleNotes").value : undefined,
        moduleControls: type === "module" ? moduleControls() : undefined,
        inferencePreset: type === "ai" ? $("#builderInferencePreset").value : undefined,
        destinationProfile: $("#builderProfile").value, goal: instructions, actor: "local-owner",
        purpose: ["draft", "compare", "visual", "music", "video", "build", "module", "ai"].includes(type) ? `Prepare ${$("#builderProfile").value}` : instructions,
      };
      render(await api("/api/local-worker-jobs/plan", request)); $("#builderPlan").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) { showError(error); }
  }
  function open(type) {
    const projectId = window.twisGetActiveProject?.() || "";
    const requestedWorkerId = workerTypes[type];
    if (state.job && state.job.worker?.workerId !== requestedWorkerId) {
      state.job = null;
      sessionStorage.removeItem("twis.builder.job");
      if (projectId) localStorage.removeItem(recoveryKey(projectId));
      $("#builderPlan").hidden = true;
      $("#builderResult").hidden = true;
      $("#builderExportResult").textContent = "";
      setStatus("Ready");
    }
    $("#builderType").value = type;
    state.preselectSourceId = ["draft", "ai"].includes(type) ? window.twisWriteRoom?.getState?.().artifactId || null : null;
    renderProfiles(); document.querySelector('[data-room="work"]')?.click(); $("#builderWorkspace")?.scrollIntoView({ behavior: "smooth", block: "start" }); void load();
  }
  async function reopen(jobId) {
    try {
      const job = await api(`/api/local-worker-jobs/${encodeURIComponent(jobId)}`);
      const types = { "handoff-proposal-builder": "handoff", "prompt-proposal-builder": "prompt", "draft-workshop": "draft", "local-ai-rewrite": "ai", "evidence-compare": "compare", "visual-brief-builder": "visual", "song-production-brief-builder": "music", "video-production-brief-builder": "video", "build-work-order-builder": "build", "module-proposal-builder": "module" };
      $("#builderType").value = types[job.worker.workerId] || "handoff"; renderProfiles(); document.querySelector('[data-room="work"]')?.click(); render(job); $("#builderWorkspace")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) { showError(error); }
  }
  async function reopenBuilderDraftArtifact(artifactId) {
    try {
      const projectId = window.twisGetActiveProject?.() || "";
      if (!projectId) return;
      const jobs = await api(`/api/local-worker-jobs?projectId=${encodeURIComponent(projectId)}`);
      const match = jobs.find(job => ["visual-brief-builder", "song-production-brief-builder", "video-production-brief-builder", "build-work-order-builder", "module-proposal-builder", "local-ai-rewrite"].includes(job.worker?.workerId) && job.result?.savedDraft?.artifactId === artifactId);
      if (match) await reopen(match.jobId);
    } catch (error) { showError(error); }
  }
  function ensureMusicUi() {
    if (!$("#builderType option[value=music]")) $("#builderType").append(Object.assign(document.createElement("option"), { value: "music", textContent: "Song Production Brief Builder" }));
    const workKind = $("#workKind");
    if (workKind && !workKind.querySelector('option[value="song-production-brief-draft"]')) workKind.append(Object.assign(document.createElement("option"), { value: "song-production-brief-draft", textContent: "Song Production Brief outputs" }));
    if (!$("#builderMusicControls")) $("#builderVisualControls").insertAdjacentHTML("afterend", `<section id="builderMusicControls" class="builder-visual-controls" hidden>
      <label>Temporary music notes<textarea id="builderMusicNotes" rows="4" maxlength="524288" placeholder="Hash-bound job input; not registered permanently."></textarea></label>
      <label>Owner-supplied lyrics or fragments<textarea id="builderMusicLyrics" rows="6" maxlength="524288" placeholder="Preserved exactly; never rewritten in Release 0.13."></textarea></label>
      <details open><summary>Core direction</summary><div class="builder-optional-grid"><label>Working title<input id="music-workingTitle"></label><label>Central subject<input id="music-centralSubject"></label><label>Emotional or story arc<input id="music-emotionalArc"></label><label>Genre<input id="music-genre"></label><label>Subgenre<input id="music-subgenre"></label><label>Reference-source priority<input id="music-referenceSourcePriority"></label></div></details>
      <details><summary>Tempo, vocals, and instruments</summary><div class="builder-optional-grid"><label>Tempo or BPM<input id="music-tempoBpm"></label><label>Key or tonal center<input id="music-tonalCenter"></label><label>Time signature<input id="music-timeSignature"></label><label>Vocal type<input id="music-vocalType"></label><label>Vocal delivery<input id="music-vocalDelivery"></label><label>Instrumentation<textarea id="music-instrumentation" rows="3"></textarea></label><label>Rhythm and groove<input id="music-rhythmGroove"></label></div></details>
      <details><summary>Song sections</summary><div class="builder-optional-grid"><label>Song structure<input id="music-songStructure"></label><label>Intro<input id="music-intro"></label><label>Verse treatment<input id="music-verseTreatment"></label><label>Chorus treatment<input id="music-chorusTreatment"></label><label>Bridge or breakdown<input id="music-bridgeBreakdown"></label><label>Solo or instrumental section<input id="music-soloInstrumental"></label><label>Ending<input id="music-ending"></label><label>Dynamic build<input id="music-dynamicBuild"></label></div></details>
      <details><summary>Production and boundaries</summary><div class="builder-optional-grid"><label>Production texture<input id="music-productionTexture"></label><label>Recording character<input id="music-recordingCharacter"></label><label>Reference influences<input id="music-referenceInfluences"></label><label>Required elements<textarea id="music-requiredElements" rows="3"></textarea></label><label>Prohibited elements<textarea id="music-prohibitedElements" rows="3"></textarea></label><label>Lyric boundaries<textarea id="music-lyricBoundaries" rows="3"></textarea></label><label>Explicit-language preference<input id="music-explicitLanguagePreference"></label><label>Approximate duration<input id="music-approximateDuration"></label><label>Additional instructions<textarea id="music-additionalInstructions" rows="3"></textarea></label></div></details>
    </section>`);
  }
  function ensureVideoUi() {
    if (!$("#builderType option[value=video]")) $("#builderType").append(Object.assign(document.createElement("option"), { value: "video", textContent: "Video Production Brief Builder" }));
    const workKind = $("#workKind");
    if (workKind && !workKind.querySelector('option[value="video-production-brief-draft"]')) workKind.append(Object.assign(document.createElement("option"), { value: "video-production-brief-draft", textContent: "Video Production Brief outputs" }));
    if (!$("#builderVideoControls")) $("#builderMusicControls").insertAdjacentHTML("afterend", `<section id="builderVideoControls" class="builder-visual-controls" hidden>
      <p class="muted">This shot-planning station prepares a governed production brief only. It does not render, upload, publish, or submit video.</p>
      <label>Temporary owner video notes<textarea id="builderVideoNotes" rows="5" maxlength="524288" placeholder="Describe the video concept. Hash-bound job input; not registered permanently."></textarea></label>
      <details open><summary>Core production direction</summary><div class="builder-optional-grid"><label>Working title<input id="video-workingTitle"></label><label>Production goal<input id="video-productionGoal"></label><label>Core concept<textarea id="video-coreConcept" rows="3"></textarea></label><label>Intended audience / use<input id="video-intendedAudience"></label><label>Target duration<input id="video-targetDuration"></label><label>Aspect ratio<input id="video-aspectRatio"></label><label>Resolution intent<input id="video-resolutionIntent"></label><label>Reference-source priority<input id="video-referenceSourcePriority"></label></div></details>
      <details><summary>Story, subject, and location</summary><div class="builder-optional-grid"><label>Story / sequence overview<textarea id="video-storySequence" rows="3"></textarea></label><label>Opening beat<textarea id="video-openingBeat" rows="2"></textarea></label><label>Main progression<textarea id="video-mainProgression" rows="3"></textarea></label><label>Closing beat<textarea id="video-closingBeat" rows="2"></textarea></label><label>Environment / location<textarea id="video-environmentLocation" rows="3"></textarea></label><label>Subject / character notes<textarea id="video-subjectCharacterNotes" rows="3"></textarea></label><label>Wardrobe / appearance<textarea id="video-wardrobeAppearance" rows="3"></textarea></label><label>Props / objects<textarea id="video-propsObjects" rows="3"></textarea></label></div></details>
      <details><summary>Visual, camera, and motion</summary><div class="builder-optional-grid"><label>Visual style<input id="video-visualStyle"></label><label>Color / palette<input id="video-colorPalette"></label><label>Lighting<input id="video-lighting"></label><label>Composition<input id="video-composition"></label><label>Camera language<input id="video-cameraLanguage"></label><label>Lens / framing intent<input id="video-lensFraming"></label><label>Camera movement<input id="video-cameraMovement"></label><label>Subject movement<input id="video-subjectMovement"></label><label>Shot ideas<textarea id="video-shotIdeas" rows="4"></textarea></label><label>Transitions<input id="video-transitionStyle"></label><label>Pacing / rhythm<input id="video-pacing"></label><label>Effects / compositing<textarea id="video-effectsCompositing" rows="3"></textarea></label></div></details>
      <details><summary>Audio, text, continuity, and boundaries</summary><div class="builder-optional-grid"><label>Dialogue<textarea id="video-audioDialogue" rows="3"></textarea></label><label>Narration / voice<textarea id="video-narrationVoice" rows="3"></textarea></label><label>Music notes<textarea id="video-musicNotes" rows="3"></textarea></label><label>Sound design<textarea id="video-soundDesignNotes" rows="3"></textarea></label><label>On-screen text<textarea id="video-onScreenText" rows="3"></textarea></label><label>Continuity requirements<textarea id="video-continuityRequirements" rows="3"></textarea></label><label>Production constraints<textarea id="video-productionConstraints" rows="3"></textarea></label><label>Safety / legal / consent<textarea id="video-safetyLegalConsent" rows="3"></textarea></label><label>Unresolved decisions<textarea id="video-unresolvedDecisions" rows="3"></textarea></label><label>Additional instructions<textarea id="video-additionalInstructions" rows="3"></textarea></label></div></details>
    </section>`);
  }
  function ensureBuildUi() {
    if (!$("#builderType option[value=build]")) $("#builderType").append(Object.assign(document.createElement("option"), { value: "build", textContent: "Build Work Order Builder" }));
    const workKind = $("#workKind");
    if (workKind && !workKind.querySelector('option[value="build-work-order-draft"]')) workKind.append(Object.assign(document.createElement("option"), { value: "build-work-order-draft", textContent: "Build Work Order outputs" }));
    if (!$("#builderBuildControls")) $("#builderVideoControls").insertAdjacentHTML("afterend", `<section id="builderBuildControls" class="builder-visual-controls" hidden>
      <p class="muted">This blueprint table prepares a governed implementation work order only. It cannot execute code, invoke a shell, modify files, submit to Codex, or deploy.</p>
      <label>Temporary owner build notes<textarea id="builderBuildNotes" rows="5" maxlength="524288" placeholder="Describe the requested build. Hash-bound job input; not registered permanently."></textarea></label>
      <details open><summary>Objective and capability decision</summary><div class="builder-optional-grid"><label>Working title<input id="build-workingTitle"></label><label>Capability request<textarea id="build-capabilityRequest" rows="3" placeholder="Describe the capability you need. The registry will bind verified local options and hardware fit into the plan."></textarea></label><label>Build goal<textarea id="build-buildGoal" rows="3"></textarea></label><label>Existing context<textarea id="build-existingContext" rows="3"></textarea></label><label>Desired outcome<textarea id="build-desiredOutcome" rows="3"></textarea></label><label>In scope<textarea id="build-inScope" rows="3"></textarea></label><label>Out of scope<textarea id="build-outOfScope" rows="3"></textarea></label><label>Reference-source priority<input id="build-referenceSourcePriority"></label></div></details>
      <details><summary>Requirements and architecture</summary><div class="builder-optional-grid"><label>Requirements<textarea id="build-requirements" rows="4"></textarea></label><label>Constraints<textarea id="build-constraints" rows="4"></textarea></label><label>Files / components likely involved<textarea id="build-relevantFilesComponents" rows="3"></textarea></label><label>UI requirements<textarea id="build-uiRequirements" rows="3"></textarea></label><label>Backend requirements<textarea id="build-backendRequirements" rows="3"></textarea></label><label>Data / persistence<textarea id="build-dataPersistence" rows="3"></textarea></label><label>External dependencies<textarea id="build-externalDependencies" rows="3"></textarea></label></div></details>
      <details><summary>Safety, verification, and delivery</summary><div class="builder-optional-grid"><label>Security / safety<textarea id="build-securitySafety" rows="3"></textarea></label><label>Performance limits<textarea id="build-performanceLimits" rows="3"></textarea></label><label>Failure behavior<textarea id="build-failureBehavior" rows="3"></textarea></label><label>Acceptance criteria<textarea id="build-acceptanceCriteria" rows="4"></textarea></label><label>Testing expectations<textarea id="build-testingExpectations" rows="4"></textarea></label><label>Deployment expectations<textarea id="build-deploymentExpectations" rows="3"></textarea></label><label>Rollback expectations<textarea id="build-rollbackExpectations" rows="3"></textarea></label><label>Unresolved decisions<textarea id="build-unresolvedDecisions" rows="3"></textarea></label><label>Additional instructions<textarea id="build-additionalInstructions" rows="3"></textarea></label></div></details>
    </section>`);
  }
  function ensureModuleUi() {
    if (!$("#builderType option[value=module]")) $("#builderType").append(Object.assign(document.createElement("option"), { value: "module", textContent: "Module Proposal Builder" }));
    const workKind = $("#workKind");
    if (workKind && !workKind.querySelector('option[value="module-proposal-draft"]')) workKind.append(Object.assign(document.createElement("option"), { value: "module-proposal-draft", textContent: "Module Proposal outputs" }));
    if (workKind && !workKind.querySelector('option[value="ai-writing-proposal-draft"]')) workKind.append(Object.assign(document.createElement("option"), { value: "ai-writing-proposal-draft", textContent: "Local AI writing proposals" }));
    if (!$("#builderModuleControls")) $("#builderBuildControls").insertAdjacentHTML("afterend", `<section id="builderModuleControls" class="builder-visual-controls" hidden>
      <p class="muted">This parts-vault desk records proposals only. It cannot install, download, execute, activate, or fetch a module or dependency.</p>
      <label>Temporary owner module notes<textarea id="builderModuleNotes" rows="5" maxlength="524288" placeholder="Describe the proposed module. Hash-bound job input; not registered permanently."></textarea></label>
      <details open><summary>Identity and purpose</summary><div class="builder-optional-grid"><label>Module name<input id="module-moduleName"></label><label>Proposed scaffold<select id="module-scaffoldType"><option>TWIS native capability</option><option>Agent Skill</option><option>Local Python worker</option><option>Local JavaScript worker</option><option>Disposable worker</option><option>MCP server wrapper</option><option>MCP client adapter</option><option>WASI component proposal</option><option>Comfy workflow adapter</option><option>Cloudflare free-tier worker</option><option selected>Capability proposal only</option></select></label><label>Purpose<textarea id="module-purpose" rows="3"></textarea></label><label>Problem it solves<textarea id="module-problemSolved" rows="3"></textarea></label><label>Target room<input id="module-targetRoom"></label><label>Inputs<textarea id="module-inputs" rows="3"></textarea></label><label>Outputs<textarea id="module-outputs" rows="3"></textarea></label><label>Reference-source priority<input id="module-referenceSourcePriority"></label></div></details>
      <details><summary>Runtime and integration</summary><div class="builder-optional-grid"><label>Local / cloud boundary<textarea id="module-localCloudBoundary" rows="3"></textarea></label><label>Dependencies<textarea id="module-dependencies" rows="3"></textarea></label><label>Hardware expectations<textarea id="module-hardwareExpectations" rows="3"></textarea></label><label>Data / storage needs<textarea id="module-dataStorageNeeds" rows="3"></textarea></label><label>Permissions / capabilities<textarea id="module-permissionsCapabilities" rows="3"></textarea></label><label>UI needs<textarea id="module-uiNeeds" rows="3"></textarea></label><label>Integration points<textarea id="module-integrationPoints" rows="3"></textarea></label><label>Licensing notes<textarea id="module-licensingNotes" rows="3"></textarea></label></div></details>
      <details><summary>Safety and completion</summary><div class="builder-optional-grid"><label>Risks<textarea id="module-risks" rows="3"></textarea></label><label>Failure behavior<textarea id="module-failureBehavior" rows="3"></textarea></label><label>Testing requirements<textarea id="module-testingRequirements" rows="3"></textarea></label><label>Recovery requirements<textarea id="module-recoveryRequirements" rows="3"></textarea></label><label>Rollback requirements<textarea id="module-rollbackRequirements" rows="3"></textarea></label><label>Acceptance criteria<textarea id="module-acceptanceCriteria" rows="4"></textarea></label><label>Unresolved decisions<textarea id="module-unresolvedDecisions" rows="3"></textarea></label><label>Additional instructions<textarea id="module-additionalInstructions" rows="3"></textarea></label></div></details>
    </section>`);
  }
  function bind() {
    if (!$("#builderWorkspace")) return;
    ensureMusicUi(); ensureVideoUi(); ensureBuildUi(); ensureModuleUi(); renderProfiles(); $("#builderType").addEventListener("change", renderProfiles); $("#builderPrepare").addEventListener("click", () => void prepare()); $("#builderVisualNotes").addEventListener("input", updateSelectionSummary); $("#builderMusicNotes").addEventListener("input", updateSelectionSummary); $("#builderMusicLyrics").addEventListener("input", updateSelectionSummary); $("#builderVideoNotes").addEventListener("input", updateSelectionSummary); $("#builderBuildNotes").addEventListener("input", updateSelectionSummary); $("#builderModuleNotes").addEventListener("input", updateSelectionSummary);
    $("#builderApprovePlan").addEventListener("click", () => void action("plan-decision", { decision: "approve", note: $("#builderPlanNote").value })); $("#builderRejectPlan").addEventListener("click", () => void action("plan-decision", { decision: "reject", note: $("#builderPlanNote").value })); $("#builderRun").addEventListener("click", () => void action("execute")); $("#builderCancel").addEventListener("click", () => void action("cancel")); $("#builderRecover").addEventListener("click", () => void action("recover"));
    $("#builderApproveResult").addEventListener("click", () => void action("result-decision", { decision: "approve", note: $("#builderResultNote").value })); $("#builderRejectResult").addEventListener("click", () => void action("result-decision", { decision: "reject", note: $("#builderResultNote").value })); $("#builderSave").addEventListener("click", () => void action("save-draft", { confirmed: true })); $("#builderRollback").addEventListener("click", () => void action("rollback", { confirmed: true }));
    for (const [id, format] of [["#builderExportTxt", "txt"], ["#builderExportMd", "md"], ["#builderExportJson", "json"]]) $(id).addEventListener("click", async () => { await action("export", { format, includeProvenance: true, confirmed: true }); const record = state.job?.result?.exports?.at(-1); $("#builderExportResult").textContent = record ? `Exported ${record.format.toUpperCase()}: ${record.path}` : ""; });
    document.querySelectorAll("[data-builder-open]").forEach(button => button.addEventListener("click", () => open(button.dataset.builderOpen)));
    document.addEventListener("click", event => { const button = event.target.closest?.("#workList [data-open]"); if (button) void reopenBuilderDraftArtifact(button.dataset.open); });
    window.addEventListener("twis:project-changed", () => void load()); window.addEventListener("twis:artifacts-loaded", () => void load()); void load();
  }
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", bind) : bind();
  window.twisOpenBuilder = open; window.twisOpenBuilderJob = reopen;
})();

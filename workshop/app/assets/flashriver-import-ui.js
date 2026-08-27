(() => {
  const EXPECTED_SHA = "6ef7317722202769b08d74a434519871736e055d1864fa5eb6c6fb547cb40108";
  const $ = (s) => document.querySelector(s);

  function toast(text) {
    const el = $("#toast");
    if (!el) return;
    el.textContent = text;
    el.classList.add("show");
    setTimeout(() => el.classList.remove("show"), 2200);
  }

  const FLASHRIVER_PROJECT_ID = "flashriver-source-archive";

  async function postJson(path, body) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const text = await res.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }
    if (!res.ok) throw new Error(data.error || text || `HTTP ${res.status}`);
    return data;
  }

  function summarize(data) {
    const m = data.manifest || {};
    return {
      ok: data.ok,
      projectId: data.projectId,
      artifactCount: data.artifactCount,
      sha256: m.sha256,
      zipTest: m.zipTest,
      fileCount: m.fileCount,
      publicSafeDocsImported: m.publicSafeDocsImported,
      privateSourcesCopied: (m.privateSourcesCopied || []).length,
      visualsCopied: (m.visualsCopied || []).length,
      manifestPath: (data.manifest || {}).path || "sources/flashriver/.../FLASHRIVER_INTAKE_MANIFEST.json"
    };
  }

  async function importFlashriver() {
    const result = $("#flashriverResult");
    const path = $("#flashriverPath")?.value.trim();
    const sha = $("#flashriverSha")?.value.trim() || EXPECTED_SHA;
    if (!result) return;
    if (!path) {
      result.textContent = "Paste the local FlashRiver ZIP path first.";
      toast("FlashRiver path required");
      return;
    }
    result.textContent = "Importing FlashRiver package…";
    try {
      const data = await postJson("/api/import-flashriver", {
        path,
        expectedSha256: sha,
        projectId: FLASHRIVER_PROJECT_ID,
        title: "FlashRiver Source Archive"
      });
      result.textContent = JSON.stringify(summarize(data), null, 2);
      toast("FlashRiver package imported");
      const review = $("#reviewFlashriver");
      if (review) review.dataset.ready = "1";
      window.dispatchEvent(new CustomEvent("twis:select-project", {
        detail: { projectId: data.projectId || FLASHRIVER_PROJECT_ID, openWork: false }
      }));
    } catch (err) {
      result.textContent = "FlashRiver import failed: " + err.message;
      toast("FlashRiver import failed");
    }
  }

  function reviewFlashriver() {
    window.dispatchEvent(new CustomEvent("twis:select-project", {
      detail: { projectId: FLASHRIVER_PROJECT_ID, openWork: false, openReview: true, showAll: true }
    }));
  }

  function boot() {
    const sha = $("#flashriverSha");
    if (sha && !sha.value) sha.value = EXPECTED_SHA;
    const btn = $("#importFlashriver");
    if (btn && !btn.dataset.flashriverBound) {
      btn.onclick = importFlashriver;
      btn.dataset.flashriverBound = "1";
    }
    const review = $("#reviewFlashriver");
    if (review && !review.dataset.flashriverBound) {
      review.onclick = reviewFlashriver;
      review.dataset.flashriverBound = "1";
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();

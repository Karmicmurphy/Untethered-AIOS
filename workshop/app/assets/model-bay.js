(() => {
  "use strict";
  const $ = selector => document.querySelector(selector);
  let current = null;
  async function request(path, body) {
    const response = await fetch(path, body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const value = await response.json().catch(() => ({}));
    if (!response.ok) { const error = new Error(value.error || `Local AI request failed (${response.status})`); error.code = value.code; throw error; }
    return value;
  }
  function card(label, value) {
    const node = document.createElement("div"); node.className = "truth-card";
    node.append(Object.assign(document.createElement("small"), { textContent: label }), Object.assign(document.createElement("b"), { textContent: String(value ?? "NOT EXPOSED") }));
    return node;
  }
  function render(value) {
    current = value;
    const model = value.models?.[0] || {};
    const state = model.state || "UNKNOWN";
    $("#modelBayState").textContent = state;
    $("#controlModelBayState").textContent = state;
    $("#controlModelBayDetail").textContent = `${model.displayName || "Registered model"} · ${value.runtime?.bindingAddress || "127.0.0.1"}:${value.runtime?.port || 8876} · ${model.runtimeRunning ? "runtime running" : "runtime stopped"}`;
    const truth = $("#modelBayTruth"); truth.replaceChildren(
      card("Registered model", model.displayName), card("Model state", state), card("Enabled", model.enabled === true ? "YES" : "NO"),
      card("Model file", model.modelFile?.present ? `${model.modelFile.size || model.fileSize} bytes` : "MISSING"),
      card("Model hash", model.modelFile?.hashVerified === true ? "VERIFIED" : model.modelFile?.hashVerified === false ? `FAILED · ${model.modelFile?.error}` : "NOT CHECKED"),
      card("Runtime", `${model.runtimeVersion || "unknown"} · ${model.runtimeExecutable?.present ? "PRESENT" : "MISSING"}`),
      card("Binding", model.runtimeBinding || "127.0.0.1:8876"), card("Auto-start", value.settings?.autoStart ? "ON" : "OFF")
    );
    $("#modelBayEvidence").textContent = JSON.stringify({ routes: value.router, lastReadyVerification: model.lastReadyVerification, lastInference: value.lastInference, lastError: value.lastError }, null, 2);
    $("#modelBayMessage").textContent = state === "READY" ? "Real localhost inference passed the bounded health assertion." : state === "INSTALLED" ? "Runtime and model are installed; start the model to make inference available." : state === "LOADED_NOT_VERIFIED" ? "Runtime is loaded but READY is withheld until real inference passes." : `Local AI state: ${state}`;
    $("#modelBayStart").disabled = !model.installed || model.runtimeRunning || value.settings?.localAiEnabled === false;
    $("#modelBayHealth").disabled = !model.runtimeRunning;
    $("#modelBayStop").disabled = !model.runtimeRunning;
    if ($("#localAiEnabled")) $("#localAiEnabled").checked = value.settings?.localAiEnabled !== false;
  }
  function fail(error) { $("#modelBayMessage").textContent = `${error.code || "local_ai_error"}: ${error.message}`; $("#modelBayState").textContent = "ERROR"; }
  async function refresh(verify = false) { try { render(await request(`/api/local-ai/status${verify ? "?verify=true" : ""}`)); } catch (error) { fail(error); } }
  async function action(path, message) {
    $("#modelBayMessage").textContent = message;
    for (const id of ["#modelBayVerify", "#modelBayStart", "#modelBayHealth", "#modelBayStop"]) $(id).disabled = true;
    try { render(await request(path, {})); } catch (error) { fail(error); await refresh(false); }
  }
  function bind() {
    if (!$("#modelBay")) return;
    $("#modelBayVerify").addEventListener("click", () => void refresh(true));
    $("#modelBayStart").addEventListener("click", () => void action("/api/local-ai/runtime/start", "Loading the one registered CPU model and running a real health inference…"));
    $("#modelBayHealth").addEventListener("click", () => void action("/api/local-ai/health-test", "Running the bounded TWIS_LOCAL_MODEL_OK inference…"));
    $("#modelBayStop").addEventListener("click", () => void action("/api/local-ai/runtime/stop", "Stopping only the registered llama.cpp process…"));
    $("#saveLocalAI")?.addEventListener("click", async () => { try { await request("/api/local-ai/settings", { localAiEnabled: $("#localAiEnabled").checked }); $("#localAiSettingsStatus").textContent = "Local AI setting saved. Auto-start remains OFF."; await refresh(false); } catch (error) { $("#localAiSettingsStatus").textContent = error.message; } });
    window.addEventListener("twis:modules-open", () => void refresh(false));
    void refresh(false);
  }
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", bind) : bind();
  window.twisModelBayRefresh = refresh;
})();

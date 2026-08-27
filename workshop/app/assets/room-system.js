(() => {
  "use strict";
  const $ = selector => document.querySelector(selector);
  const savedRoom = (() => {
    try { return JSON.parse(localStorage.getItem("twisHolo.full.v1") || "{}").lastRoom || "control"; }
    catch { return "control"; }
  })();
  const thresholdRooms = new Set(["sanctuary", "crossroads"]);
  const virtualRooms = new Set(["sanctuary", "crossroads", "new-idea"]);
  const unfinishedRooms = new Set();

  function currentRoom() {
    const route = decodeURIComponent(location.hash.replace(/^#/, ""));
    if (route) return route;
    return $(".room.active")?.dataset.panel || "sanctuary";
  }

  function updateMode() {
    const room = currentRoom();
    document.body.classList.add("room-system");
    document.body.classList.toggle("room-mode-sanctuary", room === "sanctuary");
    document.body.classList.toggle("room-mode-crossroads", room === "crossroads");
    document.body.classList.toggle("room-mode-threshold", thresholdRooms.has(room));
    document.body.dataset.workshopRoom = room;
  }

  function addRoomReturns() {
    const represented = new Set();
    for (const panel of document.querySelectorAll(".room")) {
      if (virtualRooms.has(panel.dataset.panel) || represented.has(panel.dataset.panel) || panel.querySelector(":scope > .room-return")) continue;
      represented.add(panel.dataset.panel);
      const button = document.createElement("button");
      button.type = "button";
      button.className = "room-return quiet";
      button.textContent = "← Crossroads";
      button.addEventListener("click", () => window.twisOpenRoom?.("crossroads"));
      panel.prepend(button);
    }
  }

  function addTruthLabels() {
    for (const room of unfinishedRooms) {
      const panel = $(`.room[data-panel="${room}"]`);
      if (!panel || panel.querySelector(":scope > .room-foundation-notice")) continue;
      const notice = document.createElement("p");
      notice.className = "room-foundation-notice";
      notice.textContent = "FOUNDATION ONLY · No governed room tool is claimed here.";
      panel.insertBefore(notice, panel.children[1] || null);
    }
    const capabilities = $("#homeControlDeck .shell-capabilities");
    if (capabilities && !capabilities.querySelector('[data-room="talk"]')) {
      const talk = document.createElement("button");
      talk.type = "button";
      talk.dataset.room = "talk";
      talk.innerHTML = "<b>TALK</b><i>ACTIVE ROOM</i><small>Existing durable Talk flow</small>";
      talk.addEventListener("click", () => window.twisOpenRoom?.("talk"));
      capabilities.append(talk);
    }
  }

  function bindExistingActions() {
    $("#sanctuaryContinue")?.addEventListener("click", () => {
      const destination = ["sanctuary", "crossroads", "new-idea"].includes(savedRoom) ? "control" : savedRoom;
      window.twisOpenRoom?.(destination);
    });
  }

  function boot() {
    addRoomReturns();
    addTruthLabels();
    bindExistingActions();
    updateMode();
    window.addEventListener("hashchange", updateMode);
    const workspace = $(".workspace");
    if (workspace) new MutationObserver(updateMode).observe(workspace, { subtree: true, attributes: true, attributeFilter: ["class"] });
    window.twisOpenCrossroads = () => window.twisOpenRoom?.("crossroads");
  }
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", boot) : boot();
})();

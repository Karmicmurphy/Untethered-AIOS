(() => {
  const FLASHRIVER_PROJECT_ID = "flashriver-source-archive";
  const FLASHRIVER_REVIEW_ROOM = "flashriver-review";
  const ROOMS = new Set([
    "sanctuary", "crossroads", "control", "new-idea", "home", "talk", "write", "music", "image", "video", "research",
    "code", "import", "work", "modules", "settings", FLASHRIVER_REVIEW_ROOM
  ]);

  function hasProject(projects, projectId) {
    return Array.isArray(projects) && projects.some((project) => project?.id === projectId);
  }

  function roomFromHash(hash) {
    const raw = String(hash || "").replace(/^#/, "");
    if (!raw) return "";
    try {
      return decodeURIComponent(raw);
    } catch {
      return "";
    }
  }

  function resolveRoom({ hash = "", lastRoom = "home", projects = [] } = {}) {
    const routeRoom = roomFromHash(hash);
    const candidate = ROOMS.has(routeRoom) ? routeRoom : (ROOMS.has(lastRoom) ? lastRoom : "home");
    if (candidate === FLASHRIVER_REVIEW_ROOM && !hasProject(projects, FLASHRIVER_PROJECT_ID)) {
      return "work";
    }
    return candidate;
  }

  function resolveActiveProject({ projects = [], savedProjectId = "", room = "home" } = {}) {
    if (room === FLASHRIVER_REVIEW_ROOM && hasProject(projects, FLASHRIVER_PROJECT_ID)) {
      return FLASHRIVER_PROJECT_ID;
    }
    if (hasProject(projects, savedProjectId)) return savedProjectId;
    return projects[0]?.id || "";
  }

  function hashForRoom(room) {
    return `#${encodeURIComponent(ROOMS.has(room) ? room : "home")}`;
  }

  globalThis.twisNavigationState = Object.freeze({
    FLASHRIVER_PROJECT_ID,
    FLASHRIVER_REVIEW_ROOM,
    resolveRoom,
    resolveActiveProject,
    hashForRoom
  });
})();

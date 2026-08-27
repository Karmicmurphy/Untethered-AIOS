import test from "node:test";
import assert from "node:assert/strict";

await import("../app/assets/navigation-state.js");

const navigation = globalThis.twisNavigationState;
const projects = [
  { id: "thousand-year-hangover" },
  { id: "flashriver-source-archive" }
];

test("refresh restores the FlashRiver Review route from persisted state", () => {
  assert.equal(navigation.resolveRoom({ hash: "", lastRoom: "flashriver-review", projects }), "flashriver-review");
  assert.equal(navigation.resolveRoom({ hash: "#flashriver-review", lastRoom: "work", projects }), "flashriver-review");
  assert.equal(navigation.hashForRoom("flashriver-review"), "#flashriver-review");
});

test("active project persists unless the dedicated review route requires FlashRiver", () => {
  assert.equal(navigation.resolveActiveProject({ projects, savedProjectId: "thousand-year-hangover", room: "work" }), "thousand-year-hangover");
  assert.equal(navigation.resolveActiveProject({ projects, savedProjectId: "thousand-year-hangover", room: "flashriver-review" }), "flashriver-source-archive");
  assert.equal(navigation.resolveActiveProject({ projects, savedProjectId: "missing-project", room: "work" }), "thousand-year-hangover");
});

test("a stale review route falls back safely when the FlashRiver project is absent", () => {
  assert.equal(navigation.resolveRoom({ hash: "#flashriver-review", lastRoom: "flashriver-review", projects: [{ id: "ordinary" }] }), "work");
});

test("room-system routes survive refresh without weakening legacy routes", () => {
  for (const room of ["sanctuary", "crossroads", "control", "new-idea", "talk", "write", "work", "import"]) {
    assert.equal(navigation.resolveRoom({ hash: `#${room}`, lastRoom: "home", projects }), room);
    assert.equal(navigation.hashForRoom(room), `#${room}`);
  }
});

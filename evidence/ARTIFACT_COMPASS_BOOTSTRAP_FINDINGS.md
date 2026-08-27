# Artifact Compass Bootstrap Findings — Efficiency + UI

Updated: 2026-08-27

Purpose: prevent Codex from spending local agentic allowance rediscovering public research that has already been completed. Codex should validate local fit and unresolved facts, not repeat this sweep unless evidence has materially changed.

## 1. Codex efficiency finding

Official OpenAI guidance states Codex usage can vary with model, task location, complexity, context, reasoning, speed, and tools, and that long-running tasks can consume substantially more usage than short requests.

Current operational conclusion:

`KEEP` — bounded one-turn execution packets.

`KEEP` — current repo instructions/checkpoints instead of repeatedly pasting project history.

`KEEP` — ChatGPT/GitHub public research and architecture before Codex local execution.

`KEEP` — batch implementation + focused tests + fixes + full tests + evidence into one reversible Codex turn where practical.

`DEFER` — expensive/high-reasoning model selection for routine mechanical work when a lighter available model can do it reliably.

`REJECT` — broad Codex prompts that ask it to research, redesign, implement, test, and re-audit the whole project with no bounded successor.

`REJECT` — automatic paid-credit reload as a development strategy.

Local validation required:

- current account usage/reset shown in Codex Settings/Usage or `/status` where supported;
- which model/reasoning options are actually offered in the installed Codex client.

Source checked:

- OpenAI Help Center — `Using Codex with your ChatGPT plan`, current 2026-08-27.
- OpenAI Help Center — flexible credits guide, current 2026-08-27.

## 2. UI technology findings

### Existing static/local shell

Classification: `KEEP`

Reason:

The current Workshop already uses a low-dependency browser shell. A full framework rewrite adds regression risk and consumes development time without inherently creating a high-end visual result.

Stack position:

`Workshop browser shell / UI foundation`

### Lit

Classification: `TEST`

Reason:

Lit builds standard interoperable Web Components, can progressively enhance plain HTML, has a small runtime footprint, and does not require a Lit-specific compiler/workflow for modern browsers.

Use only where repeated stateful behavior justifies a component abstraction.

Do not migrate the whole Workshop merely to use Lit.

Stack position:

`Reusable owner-facing UI components`

Proof experiment:

Convert or add one bounded stateful component without changing the room architecture; compare code size, behavior, load responsiveness, and testability.

Source checked:

- Lit official documentation, current 2026-08-27.

### Motion mini

Classification: `TEST`

Reason:

Motion provides a very small mini animation path (official docs currently describe the mini HTML/SVG animate implementation at roughly 2.3 kB) and can use browser-native acceleration where supported.

Use for a few difficult/polished micro-interactions only. Native CSS/WAAPI remains first choice.

Stack position:

`Interaction polish / motion adapter`

Proof experiment:

One control/panel transition where native code becomes meaningfully more complex; verify no visible jank on target laptop.

Source checked:

- Motion official documentation, current 2026-08-27.

### Native View Transition API

Classification: `KEEP/TEST`

Reason:

Modern browsers now expose a native mechanism for transitions between DOM/view states. MDN lists the core interface as newly baseline across latest browser versions in 2025, with some varying support.

Use with feature detection and graceful fallback. Do not make UI correctness depend on it.

Stack position:

`Room/context transition primitive`

Source checked:

- MDN View Transition API, current 2026-08-27.

### Modern CSS surface primitives

Classification: `KEEP`

Useful primitives include:

- CSS custom properties;
- `color-mix()` for controlled tonal variants;
- restrained `backdrop-filter` where performance evidence allows;
- transforms/opacity for motion;
- SVG for precision icons/meters;
- container/responsive CSS where already supported by target browser.

Rule:

Visual hierarchy comes before effects. Blur/glass is optional and must not become the product identity.

### React/Tailwind/shadcn full migration

Classification: `REJECT` for the current program.

Reason:

No verified current gap requires replacing the existing browser architecture. A migration would broaden scope, increase dependency/build complexity, and spend Codex/local verification effort without proving a better owner outcome.

This does not mean those technologies are universally bad. They are a poor current stack-position fit.

### Three.js / broad WebGL UI

Classification: `DEFER`

Potential future use:

- isolated spatial visualization;
- special creative room/canvas;
- visualizer where measurable owner value exists.

Do not use WebGL as the default UI renderer or permanent animated background on target hardware.

## 3. High-end visual direction

Classification: `KEEP`

Direction:

`obsidian / precision / depth / restrained light / tactile surfaces / cinematic motion / industrial craft / quiet power`

Reject:

- generic SaaS dashboards;
- rainbow neon;
- glowing borders everywhere;
- fake hologram clutter;
- tiny HUD text;
- random gradients;
- stock AI robots;
- gratuitous 3D;
- animation with no state meaning.

High-end means controlled hierarchy, spacing, typography, material depth, responsive interaction, and carefully rationed light/motion.

See:

- `docs/UI_DESIGN_SYSTEM.md`
- `skills/high-end-ui/SKILL.md`

## 4. Work-sharing decision

Classification: `KEEP`

Default division:

`ChatGPT/GitHub`:

- public Artifact Compass research;
- architecture;
- design system;
- dependency evaluation;
- repo docs/skills/contracts;
- GitHub patching and review;
- successor packets.

`Codex local`:

- authoritative Workshop authentication;
- local Windows file/runtime access;
- candidate implementation where live bytes matter;
- local tests;
- browser lifecycle/UI verification;
- performance measurements;
- protected-state/rollback evidence.

This split is intended to reduce repeated context and local agentic usage while keeping Codex focused on tasks that actually require its local execution environment.

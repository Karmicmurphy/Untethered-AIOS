# Untethered AIOS — High-End UI Design System

## Direction

The interface must feel like a serious private creative operating environment, not a generic SaaS dashboard, gamer HUD, template marketplace app, or neon sci-fi toy.

Keywords:

`obsidian / precision / depth / restrained light / tactile surfaces / cinematic motion / industrial craft / quiet power`

The Workshop should look expensive because the hierarchy, spacing, materials, motion, and details are controlled—not because every surface glows.

## Non-negotiable visual rules

- Dark-first.
- No rainbow neon.
- No excessive gradients.
- No fake hologram clutter.
- No giant glowing borders around every card.
- No tiny unreadable HUD labels.
- No random glassmorphism everywhere.
- No stock SaaS blue/purple dashboard look.
- No childish robot/AI iconography.
- No visual effect without a functional hierarchy reason.
- Motion must communicate state, continuity, or physicality—not decoration for decoration's sake.

## Surface hierarchy

Use four visual depths:

1. **Void** — application background; near-black, subtly dimensional.
2. **Deck** — primary room/workspace surface.
3. **Instrument** — active panels, editors, mixers, inspectors.
4. **Control** — buttons, knobs, chips, toggles, meters.

Depth comes primarily from luminance, edge definition, inset/outset contrast, shadow softness, and spacing. Blur is optional and restrained.

## Color strategy

Use a small semantic system:

- neutral near-black background family;
- warm/cool graphite surfaces;
- one primary luminous accent;
- one secondary accent only where it carries meaning;
- clear success/warning/failure states;
- off-white primary text, not pure white everywhere.

Generate tonal variants with CSS custom properties and `color-mix()` rather than hand-maintaining dozens of arbitrary colors.

The brand accent must not become a flood fill. Most of the interface remains neutral so active states feel valuable.

## Typography

- Strong display/title treatment with compact tracking.
- Highly readable body/control typography.
- Monospace only for code, hashes, machine state, timing, IDs, and technical evidence.
- Avoid all-caps paragraphs.
- Use typographic scale and weight before adding boxes/borders.
- Prefer locally available/system font stacks unless a bundled open font materially improves the identity.

## Layout

- Clear room title + task context.
- Large working canvas/editor area.
- Secondary controls collapse or dock rather than permanently shrinking the workspace.
- Persistent navigation should be calm and compact.
- Contextual controls appear near the object they affect.
- Owner-facing primary actions must be visually obvious.
- Dense technical evidence belongs in inspectors/drawers, not the creative surface.

## Motion

Motion budget is intentionally small.

Preferred order:

1. native CSS transitions;
2. Web Animations API;
3. View Transition API with feature detection;
4. Motion mini for polished sequences/springs where native primitives become awkward.

Use transform/opacity first for performance.

Typical durations:

- control response: 80–140 ms;
- panel transition: 160–260 ms;
- room/context transition: 220–380 ms;
- deliberate cinematic reveal: rarely >500 ms.

Respect `prefers-reduced-motion`.

## Component strategy

Do not rewrite the current Workshop into a framework just for visuals.

Preferred implementation:

- native HTML/CSS/JS remains valid;
- Lit is a `TEST` candidate for reusable stateful components because it produces interoperable Web Components with small runtime overhead;
- Motion mini is a `TEST` candidate for select high-end micro-interactions;
- native custom elements remain acceptable where Lit adds no value;
- Three.js/WebGL is `DEFER` for isolated visual canvases or spatial rooms only—never the default UI renderer.

## Candidate component vocabulary

High-value reusable elements may include:

- `twis-room-shell`
- `twis-command-bar`
- `twis-process-strip`
- `twis-capability-chip`
- `twis-artifact-card`
- `twis-inspector-drawer`
- `twis-receipt-viewer`
- `twis-meter`
- `twis-knob`
- `twis-transport`
- `twis-toast`
- `twis-modal-gate`

Do not componentize plain static markup merely to create architecture.

## High-end interaction details

- Buttons depress/settle rather than pulse/glow.
- Focus states are precise and clearly accessible.
- Selection should feel anchored to the selected object.
- Loading should show real process state whenever possible, not generic spinning circles.
- Destructive/live actions should look different from ordinary controls without becoming alarming everywhere.
- Audio/video controls should feel like instruments, not web forms.
- Sliders/meters should have tactile track, thumb, and value hierarchy.
- Empty states should be visually intentional and explain the next useful action.

## Performance law

High-end does not mean heavy.

For the target Workshop hardware:

- avoid large framework rewrites;
- avoid permanent animated backgrounds;
- avoid expensive full-screen blur/filter chains;
- pause offscreen animation;
- lazy-load rare heavy visual modules;
- keep first interaction fast;
- measure before adding 3D/WebGL effects.

## Responsive law

Desktop is the primary creative workstation, but the shell must degrade intentionally on smaller windows/mobile field views.

No horizontal overflow.
No microscopic controls.
No critical hover-only behavior.

## Visual verification gate

A high-end UI candidate is not PASS from code review alone.

Codex must eventually verify on the local runtime:

- desktop room shell;
- narrower window/mobile layout where applicable;
- no overflow/clipping;
- keyboard focus;
- reduced motion;
- no console errors;
- no unintended external requests;
- acceptable CPU responsiveness on target hardware.

Screenshots should be compared for hierarchy and polish, not merely presence of elements.

## Artifact Compass classification — bootstrap

`KEEP` — existing static/local browser shell and owner-visible room model.

`KEEP` — native CSS custom properties, modern CSS, SVG, Canvas where already appropriate.

`TEST` — Lit for bounded reusable stateful components, not a full rewrite.

`TEST` — Motion mini for selective micro-interactions, not a permanent animation dependency everywhere.

`KEEP/TEST` — native View Transitions where supported, with graceful fallback.

`DEFER` — Three.js/WebGL as a specialized visual surface only.

`REJECT` — full React/Tailwind/shadcn migration solely to make the app look modern.

`REJECT` — large UI framework/theme dependency that dictates the Workshop's visual identity.

## Design review question

Before accepting any UI change ask:

`Does this look more intentional, more legible, more tactile, and more distinctly Twis—or did we merely add effects?`

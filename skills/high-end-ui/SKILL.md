# Skill: High-End UI Execution

Use this skill for any owner-facing Workshop/Untethered interface change.

Read `docs/UI_DESIGN_SYSTEM.md` first.

## Goal

Create a premium, deliberate, high-end interface without turning the Workshop into generic SaaS, gamer neon, or a heavy framework rewrite.

## Implementation order

1. Preserve existing functional behavior.
2. Fix hierarchy, spacing, typography, and interaction states first.
3. Establish semantic design tokens.
4. Improve surfaces and controls.
5. Add motion only where it improves continuity/state understanding.
6. Add reusable components only where state/behavior repetition justifies them.
7. Verify target-hardware responsiveness.

## Technology defaults

- `KEEP`: existing static/local browser shell.
- `KEEP`: native HTML/CSS/JS, CSS custom properties, SVG/Canvas.
- `TEST`: Lit for bounded stateful reusable Web Components.
- `TEST`: Motion mini for selective micro-interactions.
- `KEEP/TEST`: native View Transition API with fallback.
- `DEFER`: WebGL/Three.js except isolated visual surfaces.
- `REJECT`: framework migration solely for visual fashion.

Any change to those classifications requires a fresh Artifact Compass reason.

## Visual anti-patterns

Reject:

- rainbow neon;
- glow on everything;
- excessive blur/glass;
- random gradients;
- tiny HUD typography;
- stock AI robot imagery;
- generic Tailwind/shadcn dashboard appearance;
- gratuitous 3D;
- motion with no state meaning;
- giant dependency for one small effect.

## Verification

A UI candidate requires local/browser evidence before PASS:

- desktop layout;
- narrow/mobile behavior where applicable;
- no horizontal overflow;
- keyboard focus;
- reduced-motion behavior;
- no console errors;
- no unintended external network requests;
- acceptable responsiveness on target hardware.

High-end means controlled detail and responsiveness, not maximum visual effects.

# Commercial MVP HTML Workbench Goal Packet

## Purpose

Codex Desktop does not support the `/goal` command in this workspace. This
document emulates the useful parts of `/goal` by giving future workers a single
tracked goal packet to treat as the top-level task contract.

This file is not a scratch plan. It is a durable coordination artifact for the
next implementation slice.

## How This Emulates `/goal`

The intended `/goal` behavior is:

- pin one objective above ordinary chat drift.
- define the exact documents to read.
- keep constraints and non-goals visible throughout the session.
- define success criteria before implementation begins.
- require self-QA and iteration before handoff.
- force an honest final report against the goal.

In Codex Desktop, use this file plus the bootstrap prompt below. The worker must
treat this packet as the active goal contract until the slice is complete or a
tracked blocker is recorded.

## Environment Setup

Workspace:

- `<local-clone-path>`

Branch:

- `codex/phase17-render-stability`

Operating posture:

- Do not commit or push unless explicitly requested.
- Do not use `git add .`.
- Preserve unrelated local changes.
- Treat `PLAN.md` as scratch only.
- Record durable decisions in tracked docs.
- Use the repo's existing build/test patterns first.
- If dependencies are missing, install only what is necessary for the selected
  web surface, record what was installed, and keep generated artifacts inside
  the workspace.
- Start a local server only when needed for browser smoke, and report the URL.
- Stop any server started for validation unless the user asks to keep it open.

Required startup reads:

- `AGENTS.md`
- `docs/ACTIVE_BACKLOG.md`
- `docs/AGENT_TASK_INDEX.md`
- relevant files under `docs/agent-rules/`
- `docs/COMMERCIAL_MVP_WEB_SURFACE_PRD.md`
- `docs/COMMERCIAL_MVP_PRODUCT_BOUNDARY_PRD.md`
- `docs/COMMERCIAL_MVP_HTML_WORKBENCH_SPEC.md`
- `docs/COMMERCIAL_MVP_HOST_AI_DESIGN_GUIDE_SPEC.md`
- `docs/COMMERCIAL_MVP_EXPORT_HOOK_CONTRACT.md`
- `docs/COMMERCIAL_MVP_BENCHMARK_QA_RUBRIC.md`
- `docs/COMMERCIAL_MVP_PRESENTATION_DESIGN_GUIDE.md`
- latest relevant Commercial MVP entries in
  `docs/REFERENCE_PIPELINE_WORK_LOG.md`

Benchmark files:

- `benchmark HTML reference`
- `benchmark PPTX reference`

Benchmark files are quality references only. They must not be copied or
hardcoded.

## Active Goal

Build the first real commercial vertical slice for A.DreamMaker / PPT Maker.

PPT Maker is a host-AI guidance extension. It helps host AI create high-quality
fixed-canvas HTML slides, lets the user make basic local edits to save token-like values,
and hands the current work back to host AI through honest `Export PDF` and
`Export PPTX` hooks.

The primary deliverable is an editable fixed-canvas HTML slide workbench. The
result must be a usable early slide editor, not a plausible-looking shell.

## Hard Constraints

Do not:

- continue SlideIR proof-shell polish as the primary work.
- hardcode the provided sample HTML/PPTX.
- copy the benchmark brand content, exact coordinates, raw DOM, image URLs, filenames, or
  sample-specific business text.
- use Python code to directly fabricate the final sample-like deck.
- present fake export completion as a real PDF/PPTX result.
- build embedded backend AI chat.
- add a third mode beyond Assistant and Auto.
- expose raw prompts, sources, local paths, raw filenames, external document identifiers, package
  internals, credentials, DB URLs, encoded asset assets, private image URLs, or
  backend chain-of-thought in public summaries or handoff envelopes.

Allowed:

- SlideIR may remain internal evidence, patch, or export infrastructure.
- Browser smoke may use local generated fixtures if they are generic and not
  benchmark-copied.
- A new workbench surface may be created if adapting the old SlideIR editor
  would trap the implementation in proof-shell behavior.

## Implementation Requirements

The implementation must:

1. Add or designate the HTML slide workbench surface.
2. Use the design-guide/system-prompt package to guide benchmark-family HTML
   slide generation.
3. Render a generic 10+ slide deck that is not copied from the benchmark.
4. Show a dominant fixed 16:9 canvas.
5. Implement direct canvas text editing that mutates local work state.
6. Implement object select, move, resize, duplicate, delete, and z-order for
   common slide objects.
7. Implement slide navigation for 10+ slides.
8. Keep diagnostics hidden in normal user mode.
9. Implement `Export PDF` and `Export PPTX` as host-AI handoff hooks with
   honest states: `handoff_ready`, `handoff_sent`, `awaiting_host_ai`,
   `proposal_ready`, `blocked`, and `final_received`.
10. Preserve sanitized operation summaries and private-boundary checks.
11. Support Korean UI/text wrapping quality in smoke coverage.

## Self-QA Loop

Before handoff, the worker must:

1. run build and focused validators.
2. run browser smoke at 1440, 1600, 1920, ultrawide, and narrow widths.
3. test direct text editing on the canvas.
4. test object move/resize.
5. test 10+ slide navigation.
6. test PDF/PPTX export hook states.
7. compare screenshots against the benchmark quality family.
8. scan for hardcoded benchmark content, exact coordinates, image URLs, local
   paths, raw filenames, encoded asset assets, private markers, and fake export
   success.
9. fix P1/P2 issues found during smoke.
10. rerun the same checks.

Validator success alone is not acceptance.

## Success Criteria

- The user can edit text directly on the canvas.
- The user can select and manipulate common slide objects.
- The deck has 10+ slides and visibly moves toward benchmark-family HTML slide
  quality.
- The UI looks and behaves more like an early slide editor than a proof shell.
- Export buttons behave as honest host-AI hooks.
- Diagnostics are hidden in normal user mode.
- The worker records evidence and candidly reports remaining gaps.

## Bootstrap Prompt

Use this prompt in Codex Desktop instead of `/goal`:

```text
Treat docs/COMMERCIAL_MVP_HTML_WORKBENCH_GOAL_PACKET.md as the active goal
contract for this session. Read it first, then perform its required startup
reads. Do not proceed as a planning-only or readiness-only task unless you find
a blocker that prevents implementation.

Implement the first real commercial vertical slice for A.DreamMaker / PPT
Maker: an editable fixed-canvas HTML slide workbench that helps host AI produce
benchmark-family HTML slides, lets the user make basic local edits, and hands
the current work back to host AI through honest Export PDF / Export PPTX hooks.

Do not continue SlideIR proof-shell polishing as the primary work. Do not
hardcode the provided sample HTML/PPTX. Do not copy the benchmark brand content, exact
coordinates, raw DOM, image URLs, filenames, or sample-specific business text.
Do not use Python code to directly fabricate the final sample-like deck. Do not
present fake export completion as a real PDF/PPTX result.

Build the user-facing workbench, run the self-QA loop in the goal packet, fix
P1/P2 issues found by smoke, and report results against the goal with evidence.
Do not commit or push unless explicitly requested.
```

# Commercial MVP HTML Slide Workbench Spec

## Purpose

This spec defines the first real user-facing editor surface for the Commercial
MVP. The workbench exists so users can make basic slide corrections before
asking host AI to create final PDF/PPTX output.

## Product Standard

The workbench must feel like an early practical slide editor, not a proof shell.
It does not need to be a full PowerPoint clone, but it must let a user directly
edit common visible slide content.

## Required Surface

- A PC-first app shell.
- Left slide navigation for at least 10 slides.
- A dominant fixed 16:9 slide canvas.
- Persistent top toolbar for common editing actions. Text styling, font size,
  font family, color, alignment, duplicate/delete, layer order, undo/redo, and
  zoom/fit controls must be visible primary controls.
- Optional right-side advanced panel for less common precise edits.
- The right-side panel is a contextual inspector, not a product-status shelf.
  Normal users should see selected-object controls and secondary precision
  edits there, not raw product scaffolds, backend handoff state, billing
  ledgers, internal asset/package status, or debug summaries.
- Assistant/Auto mode state separated from slide navigation.
- Assistant/Auto controls must describe host-AI generation/revision behavior,
  not ordinary canvas editing modes.
- App chrome dark/light mode, while slide canvas appearance remains governed by
  the slide/theme tokens.
- English/Korean UI switching for toolbar, panel, status, and export-hook text.
- Diagnostics, operation logs, signatures, and private evidence hidden from
  normal user mode.

## Product Information Architecture

The following placement rules are required before the workbench can be treated
as a commercial product shell:

- Master style belongs in a deck/theme style surface with preview, apply,
  override, reset, and lock semantics. The inspector may show the selected
  object's resolved role/token, but it must not expose only raw master-style
  ids or schema defaults.
- AI revision memory belongs in a bounded revision/history or host-AI context
  surface. It must be distinct from undo/redo and must not expose raw prompts,
  private sources, or backend reasoning.
- Reference Design Library belongs in a library/design-reuse surface. It may
  provide recipe pickers, previews, and apply controls, but it should not appear
  as object metadata in the inspector.
- Style Memory belongs in account/project preference management with visible
  inspect, reset, and delete controls.
- Published viewer controls belong in share/publish flows and viewer settings.
- Referral and credits belong in account, billing, onboarding, or entitlement
  surfaces.
- Local font/image links belong in brand-assets or connection setup flows using
  safe refs only.
- Host-AI export belongs in top-level export controls, a modal/drawer, and a
  job-status surface. Normal UI may show honest states, but raw handoff
  envelopes and diagnostics remain hidden.

If these capabilities are included in a fixture or QA build, they must be
clearly marked as preview/diagnostic and hidden from normal mode by default.

CLI, MCP, browser UI, and handoff reports must use the same product-boundary
truth. Reference Design Library recipes are content-free when either the older
`content_free_preview.placeholder_labels_only` field or the current
`synthetic_placeholder_preview.placeholder_labels_only` field is true. A false
negative in CLI/MCP or export reports is a P1 blocker because host AI would
receive incorrect boundary status.

Top-level product surfaces may use drawers or modals, but they must preserve a
clear canvas editing model. A drawer can cover part of the visual canvas only
when it has obvious close/apply/focus behavior, does not mutate slide content
implicitly, and browser smoke proves the underlying 16:9 work area remains
usable at 1440, 1600, 1920, ultrawide, and narrow widths.

## Required Editing Behavior

Direct text editing:

- User can edit visible slide text directly on the canvas.
- Double-click or equivalent inline edit is acceptable.
- Editing must mutate local work state, not only the transient DOM.
- Korean text input, wrapping, and line-height must be tested.
- Real user typing must be tested on the rendered canvas: caret placement,
  selection, input, commit, and state mutation must work at the active canvas
  scale.
- Text objects must support rich text runs for selection-range styling. At
  minimum, a selected range inside one text object can change color, bold,
  italic, underline, font family, and font size without changing the whole text
  object.
- Text objects must carry a text style role. Required roles are `Title`, `H1`,
  `H2`, `H3`, `Body`, `Caption`, and `Bullet`.
- Each text style role must support font family token, font size, weight, color,
  line height, paragraph spacing, and overflow policy. Letter spacing defaults
  to `0`.
- Bullet behavior must be paragraph-level state with a bounded level, not only
  a literal bullet character inserted into a plain string. `Bullet` may be its
  own role, and `Body` paragraphs may also carry bullet state.
- Text object state should support paragraphs containing rich text runs so a
  selected phrase can override bold, color, font family, or size without
  changing the whole paragraph or losing the text role.
- A technical inspector-only textarea is not sufficient.

Object editing:

- Select visible objects.
- Select multiple visible objects by shift-click or marquee where implemented.
- Show selection handles or clear focus state.
- Move objects by drag.
- Resize common objects using box-based geometry. V2 does not need
  rotation-aware resize handles.
- Duplicate selected object.
- Delete selected object.
- Change z-order.
- Align multiple selected objects left, center, right, top, middle, and bottom
  where claimed.
- Distribute multiple selected objects horizontally or vertically where claimed.
- Support both align-to-selection and align-to-slide modes where claimed.
- Rotate PPT Maker-created shapes and inserted images with fixed buttons:
  counterclockwise/clockwise 15 degrees, counterclockwise/clockwise 90 degrees,
  and reset. Freeform rotation is deferred.
- Flip PPT Maker-created shapes and inserted images horizontally and vertically
  where claimed.
- Text box rotation is excluded from V2 scope.
- Shape objects may expose corner radius as a numeric value or safe radius
  token.
- Preserve undo/redo for user edits.
- Preserve AI revision memory separately from undo/redo. Undo/redo restores
  local edit states; revision memory records public-safe host-AI generations,
  proposals, handoffs, accept/reject decisions, and local edit summaries.

Slide editing:

- Navigate a 10+ slide deck.
- Add, duplicate, delete, or reorder slides where implemented.
- Switching slides must preserve the current work state.

Asset/image editing:

- Image replacement uses safe refs and crop/fit metadata.
- Raw local paths, raw filenames, binary blobs, EXIF, and encoded asset assets must not
  appear in public summaries or host-AI handoff envelopes.

Design package editing:

- Workbench state must support `theme_id`, `master_style_id`,
  `layout_recipe_id`, `component_recipe_id`, and `token_set_id` references.
- Master style defines shared typography roles, palette defaults, shape
  defaults, and common slide chrome. It is not required to define full slide
  layout in V2.
- Layout recipes define editable object regions and visual hierarchy. They are
  not hardcoded sample coordinates.
- Theme tokens define palette, typography roles, spacing, radius, stroke, and
  app/canvas chrome rules.
- Layout recipes, font stacks, color palettes, icon sets, and style tokens may
  come from the approved asset system when entitlement and package evidence
  allow it. Public UI and host-AI handoffs may expose only safe ids and
  sanitized summaries, never package internals.

## Work State

The implementation may use a structured HTML-slide model, sanitized HTML
document state, or a hybrid. It must be able to:

- distinguish demo fixtures from server/host-AI generated workbench input.
- identify editable text blocks.
- represent text style roles, paragraphs, paragraph-level bullet state, rich
  text `runs[]`, and active selection ranges.
- identify common movable/resizable objects.
- resolve theme, master, layout, component, and token references.
- record shape/image transform fields such as rotation, flipX, flipY, and
  box-based resize bounds.
- record shape corner radius or radius token values where claimed.
- record operation summaries.
- record AI revision memory and proposal history.
- serialize a compact safe work state or work-state reference for export hooks.
- reject script/style/embed payloads and unsafe pasted rich HTML.

## Visual Requirements

- The canvas should remain white unless the slide declares a different
  background.
- The workbench should avoid operator/report language in normal UI.
- The first deck fixture must be generic, 10+ slides, and not copied from the
  benchmark.
- The deck should visibly use benchmark-family composition: large hierarchy,
  structured sections, cards, diagrams, image/icon slots, headers/footers, and
  consistent page numbers.
- The canvas display size should be automatic by default. It must fit the
  available stage area while preserving the fixed 16:9 logical canvas, and it
  must provide explicit zoom/fit controls.
- UI chrome should use scalable text units and remain usable under browser or
  OS text scaling.

## Acceptance

The workbench is acceptable only when browser smoke proves:

- 10+ slide navigation works.
- direct canvas text editing changes visible content and local state through
  real user interaction, not only a smoke API.
- Korean typing, caret/selection, and commit behavior work on the scaled canvas.
- partial rich-text styling works inside one text object.
- text style roles exist for Title, H1, H2, H3, Body, Caption, and Bullet.
- paragraph-level bullet editing is represented in state where claimed.
- object move/resize changes visible content and local state.
- duplicate/delete/z-order operate on selected objects where claimed.
- multi-select, align, distribute, fixed-step shape/image rotation, shape/image
  flip, and shape radius controls work where claimed.
- text box rotation remains unavailable or clearly disabled in V2.
- the persistent toolbar is visible and exposes primary edit controls.
- master/theme/layout/token references are present and fixture data is labeled
  separately from generated workbench input.
- approved asset-system design-package inputs are represented as safe
  references when used, with package internals hidden.
- diagnostics are hidden in normal mode.
- dark/light and English/Korean switching work when claimed.
- Assistant/Auto UI is understandable as host-AI behavior, not a third edit
  mode.
- AI revision memory is preserved separately from undo/redo when claimed.
- Korean text does not visibly overlap in smoke cases.
- the UI remains usable at 1440, 1600, 1920, ultrawide, and narrow inspection
  widths.

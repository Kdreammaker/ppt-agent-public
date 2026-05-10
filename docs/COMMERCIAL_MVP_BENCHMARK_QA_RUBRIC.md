# Commercial MVP Benchmark QA Rubric

## Purpose

This rubric defines how to judge whether the next Commercial MVP slice is
actually moving toward a sellable slide product.

The benchmark files are quality references only:

- `benchmark HTML reference`
- `benchmark PPTX reference`

They must not be hardcoded or copied.

## Scoring Targets

If the benchmark is `100`:

- Initial Commercial MVP target: visual quality at least `75`, basic editing
  usability at least `70`.
- Public paid readiness target: visual quality at least `85`, basic editing
  usability at least `80`.
- The prior SlideIR proof shell is below the commercial target and must not be
  used as the quality reference.

## Review Dimensions

Visual slide quality:

- 10+ slide deck structure.
- clear visual hierarchy.
- professional Korean proposal typography.
- consistent header/footer/page numbering.
- controlled spacing and alignment.
- meaningful image/icon/card/diagram usage.
- no accidental text or object overlap.
- no obviously broken first slide.

Editing usability:

- direct canvas text editing.
- real user caret/selection/typing behavior on the scaled canvas.
- partial rich-text styling inside one text object.
- text style roles for Title, H1, H2, H3, Body, Caption, and Bullet.
- paragraph-level bullet state rather than bullet-only literal strings.
- persistent toolbar visibility for primary edit actions.
- object selection clarity.
- multi-object selection where claimed.
- move/box-based resize behavior.
- duplicate/delete/z-order behavior.
- alignment and distribution behavior where claimed.
- fixed-step shape/image rotation and flip where claimed.
- shape corner-radius behavior where claimed.
- text rotation unavailable or clearly disabled in V2.
- slide navigation across 10+ slides.
- undo/redo where claimed.
- AI revision memory is separate from undo/redo where claimed.
- automatic canvas fit and zoom behavior across side panels and narrow views.
- app chrome dark/light mode and English/Korean switching where claimed.
- normal UI hides diagnostics.

Host-AI guidance quality:

- design guide is specific enough to influence output.
- guide contains reusable recipes rather than sample copies.
- guide/design package separates theme token-like values, master styles, text style roles,
  layout recipes, component recipes, and slide content.
- server or approved asset-system supplied layout/font/palette/style-token
  inputs are represented through safe manifests when used.
- generated fixture deck is generic and not benchmark-derived.
- demo fixtures are clearly labeled and are not the only product data path.
- output visibly follows benchmark-family composition.

Export-hook honesty:

- `Export PDF` and `Export PPTX` behave as host-AI handoff hooks.
- no fake final success.
- status language is clear to a non-technical user.
- proposal/blocker states are public-safe.

Private-boundary safety:

- no raw prompts in public reports.
- no local paths or raw filenames.
- no Drive/Docs IDs.
- no package internals.
- no credentials or token-like values, DB URLs, encoded asset assets, or private image URLs.

## Required Smoke Evidence

A worker must run or produce equivalent evidence for:

- 1440 desktop.
- 1600 desktop.
- 1920 desktop.
- ultrawide desktop.
- narrow inspection width.
- direct text edit.
- caret/selection/typing smoke on the rendered scaled canvas, including Korean
  input.
- text style role and paragraph-level bullet smoke.
- partial rich-text styling smoke.
- persistent toolbar smoke.
- object move/resize.
- multi-select align/distribute smoke where claimed.
- fixed-step shape/image rotation and flip smoke where claimed.
- shape corner-radius smoke where claimed.
- negative text-rotation smoke for V2.
- 10+ slide navigation.
- canvas fit/zoom smoke.
- fixture-vs-generated data boundary check.
- master/theme/layout/token reference check.
- dark/light and English/Korean smoke when claimed.
- AI revision memory smoke when claimed.
- PDF export hook state.
- PPTX export hook state.
- diagnostics hidden in normal mode.
- hardcoded benchmark marker scan.
- private-boundary scan.

## Hardcoding Scan

The worker must scan for:

- the benchmark brand sample business content.
- exact sample coordinates used as product fixtures.
- sample image URLs.
- raw benchmark DOM copied into product code.
- sample filenames used as output logic.
- unlabeled static fixture data presented as generated host-AI output.
- server or asset-system package internals exposed through design package
  manifests.
- local absolute paths.
- encoded asset image blobs.
- fake export success strings that imply final PDF/PPTX exists.

## Self-QA Loop

The worker must:

1. implement.
2. run build and focused validators.
3. run browser smoke.
4. inspect screenshots against the benchmark family.
5. fix P1/P2 visual, editing, boundary, or export-hook blockers.
6. rerun the same checks.
7. report unresolved blockers candidly with concrete next actions.

Validator success alone is not acceptance. A visibly broken editor or
non-editable canvas fails even if scripts pass.

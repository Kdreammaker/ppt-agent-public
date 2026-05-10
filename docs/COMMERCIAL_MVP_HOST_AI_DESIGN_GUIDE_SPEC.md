# Commercial MVP Host-AI Design Guide Spec

## Purpose

This spec defines the guidance layer that helps host AI create benchmark-family
HTML slides. The concrete guide currently begins at
`docs/COMMERCIAL_MVP_PRESENTATION_DESIGN_GUIDE.md`, but this spec defines what
that guide must accomplish and how it must be used.

## Role

The guide acts like a `DESIGN.md` or system-design instruction package for
presentation generation. Host AI should read it before generating or revising
HTML slides.

The guide is not a template deck and not a hidden code generator.

The guide may be delivered as a local tracked document, a server-provided
manifest, or an approved asset-system design package. Server/asset-system
delivery is allowed only when the manifest is versioned, public-safe, and
validated before use. The workbench and handoff envelopes must record the
version and safe ids used, not raw package internals.

## Required Guide Content

The guide must cover:

- fixed 16:9 canvas rules.
- Korean-first typography and line-height rules.
- color, contrast, and palette guidance.
- spacing, safe area, alignment, and z-order rhythm.
- page-number, header, and footer consistency.
- visual-density guidance for proposal decks.
- component recipes for common slide archetypes.
- master style definitions for shared typography roles, palette defaults, shape
  defaults, and common slide chrome. V2 master style is not a full layout
  master.
- required text style roles: `Title`, `H1`, `H2`, `H3`, `Body`, `Caption`, and
  `Bullet`.
- text role defaults for font family token, font size, weight, color, line
  height, paragraph spacing, and overflow policy. Letter spacing defaults to
  `0`.
- paragraph-level bullet guidance with bounded levels.
- layout recipes with editable object regions and hierarchy guidance.
- theme token sets for palette, typography roles, spacing, radius, stroke,
  elevation, and app/canvas chrome behavior.
- rich text run guidance for partial styling inside one text object.
- canvas fit/zoom guidance for fixed logical canvas display.
- asset slot and icon/image usage guidance.
- self-QA checklist.
- public/private boundary reminders.

Required component recipes:

- cover/title slide.
- section header.
- executive summary.
- problem/opportunity slide.
- solution overview.
- process/timeline.
- comparison/table slide.
- metric-card slide.
- image-plus-insight slide.
- icon-label grid.
- closing/next-step slide.

## Benchmark Use

The guide may summarize reusable qualities from the user-provided benchmark
files:

- fixed-canvas proposal rhythm.
- Korean business typography.
- dense but readable composition.
- image/icon/card usage.
- consistent headers, footers, and page numbers.

The guide must not copy:

- the benchmark brand business content.
- exact slide text.
- exact coordinates.
- raw DOM.
- image URLs.
- filenames.
- local paths.
- benchmark-specific brand output.

## Design Package Sources

Allowed sources:

- local tracked docs for baseline guidance.
- product server manifests for current versioned guide, theme, master, and
  layout recipe packages.
- approved asset-system packages for layouts, font stacks, color palettes,
  icons, illustrations, and style tokens.

Required manifest fields:

- `design_guide_version`
- `design_package_id`
- `manifest_hash`
- `source_kind`: `tracked_doc`, `server_manifest`, or `approved_asset_system`
- `theme_id`
- `master_style_ids`
- `layout_recipe_ids`
- `component_recipe_ids`
- `text_style_role_ids`
- `token_set_ids`
- `asset_system_package_ref` when applicable.

Asset-system package consumption must remain plan/entitlement gated. Starter
and Manager cannot receive Leader-only package content. Public-safe surfaces may
show only safe ids, resolved token names, and sanitized package summaries.

## Host-AI Generation Expectations

Host AI should:

- classify deck intent, audience, language, and visual density.
- choose layout recipes and component presets.
- choose a master style, text role set, and theme token set before composing
  individual slides.
- plan each slide before writing final HTML.
- generate fixed-canvas HTML slide output.
- emit editable object records, including rich text runs where partial styling
  is used.
- emit text objects with role and paragraph state. Bullet lists must use
  paragraph-level bullet metadata, not only visible bullet characters.
- include safe design-package references in the generated work state.
- run self-QA and revise before handing output to PPT Maker.

PPT Maker should:

- expose the guide to host AI as compact reusable instructions.
- resolve and validate server/asset-system design manifests before exposing
  them to host AI.
- avoid sending private raw source material in guide references.
- validate that generated output does not contain unsafe payload families.
- record the guide version used in export handoff envelopes.

## Acceptance

The guide package is acceptable when a new worker or host AI can read the
tracked docs and understand how to produce a generic 10+ slide benchmark-family
HTML deck without copying the benchmark.

For the next implementation slice, acceptance also requires a concrete design
package contract that separates theme token-like values, master styles, text style roles,
layout recipes, component recipes, and slide content, plus a safe path for
server or approved asset-system package inputs.

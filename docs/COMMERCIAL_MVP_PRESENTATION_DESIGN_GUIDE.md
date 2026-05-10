# Commercial MVP Presentation Design Guide

Version: `commercial_mvp_presentation_design_guide.v1`

This guide is the reusable design instruction layer for host-AI-authored
presentation output. It defines quality rules and component patterns for
fixed-canvas proposal decks without copying any private benchmark deck, raw DOM,
image URL, filename, exact coordinate set, or sample-specific business content.

## Role Boundary

- Host AI owns interpretation, writing, visual direction, revision decisions,
  and deliverable planning.
- PPT Maker owns sanitized handoff envelopes, tool execution mediation, bounded
  patch application, preview/status, evidence, account/credit/asset checks, and
  public/private safety.
- Export PDF and Export PPTX are host-AI handoff hooks. They must not render
  directly from the browser DOM.

## Canvas

- Use a fixed 16:9 slide canvas.
- The HTML workbench uses a 1600 by 900 logical coordinate space unless a later
  versioned design package explicitly defines another widescreen logical size.
- Keep layout deterministic across HTML preview and PPTX/native projections.
- Browser display may scale uniformly; content must not reflow by viewport.
- Leave safe margins of at least 72 logical px on desktop proposal slides unless
  a deliberate full-bleed asset slot is declared.
- Workbench display must auto-fit the available stage area and may expose zoom
  controls. Auto-fit changes display scale only; it must not rewrite slide
  geometry.

## Design Packages

- Treat this guide as the baseline local package:
  `commercial_mvp_presentation_design_guide.v1`.
- A product server or approved asset system may provide newer design packages
  with safe ids for theme token-like values, master styles, text style roles, layout
  recipes, component
  recipes, and token sets.
- Asset-system supplied layouts, font stacks, color palettes, icons,
  illustrations, and style tokens require entitlement, approval,
  materialization, and public/private checks before use.
- Public UI, reports, and export handoffs may reference only safe ids, resolved
  token names, and sanitized summaries. Do not expose package internals.

## Master Styles And Layout Recipes

- Master styles define shared typography roles, palette defaults, shape
  defaults, and common slide chrome. They are not required to own full slide
  layouts in V2.
- Layout recipes define editable object regions, hierarchy, density budget,
  alignment anchors, and optional asset slots for one slide archetype.
- Component recipes define reusable objects such as cards, metric blocks,
  timelines, comparison tables, image-plus-insight blocks, icon grids, and
  closing action blocks.
- Slide content should reference `theme_id`, `master_style_id`,
  `layout_recipe_id`, `component_recipe_id`, and `token_set_id` instead of
  duplicating slide-specific design instructions.

## Text Style Roles

- Required roles: `Title`, `H1`, `H2`, `H3`, `Body`, `Caption`, and `Bullet`.
- Each role may define font family token, font size, font weight, color token,
  line height, paragraph spacing, and overflow policy.
- Letter spacing defaults to `0`; avoid negative letter spacing.
- `Title` is for cover or deck-level primary titles.
- `H1` is for slide-level primary headings.
- `H2` and `H3` are for section labels, card headings, or hierarchy inside a
  dense slide.
- `Body` is for normal explanatory copy and may contain paragraph-level bullet
  state.
- `Caption` is for low-emphasis notes, labels, chart explanations, and compact
  footer text.
- `Bullet` defines default bullet indentation, marker style, line height, and
  spacing. Bullet behavior must be stored as paragraph metadata with a bounded
  `level`, not only as a literal bullet character in text.
- Asset-system or server design packages may provide role presets. Public
  handoffs may reference only safe role ids and resolved token names.

## Korean-First Typography

- Treat Korean text as first-class, not as translated filler.
- Use font tokens rather than private font files: `heading`, `body`, `caption`,
  and `mono`.
- Font stacks may come from an approved asset-system design package as
  metadata or approved package evidence. Do not expose private font files or
  package internals in public handoffs.
- Prefer line height from 1.12 to 1.24 for Korean body text. Large headings may
  use 1.08 to 1.36 when mixed scripts, underline, or browser preview metrics
  need additional breathing room.
- Avoid negative letter spacing.
- Keep heading blocks to one or two lines. If a title needs more space, reduce
  size or revise copy before overlapping another object.
- For mixed Korean/English decks, keep labels short and align number-heavy
  content on consistent baselines.

## Color And Tokens

- Default canvas background is white unless the slide explicitly declares a
  background.
- Use a restrained neutral base with one strong accent and one support color.
- Use A.DreamMaker yellow only as an accent, emphasis, or selected-control
  color, not as a full-slide wash.
- Keep text contrast high on white canvas: primary text should sit near black or
  deep neutral; captions may use muted neutral.
- Use validated hex colors only. Do not depend on uncontrolled gradients,
  filters, blend modes, or private asset-derived palettes.
- Color palettes may come from approved asset-system theme tokens. When used,
  record only safe palette/token ids and resolved public-safe color roles.

## Rich Text Runs

- Text objects may contain multiple style runs.
- Use runs for selected-word emphasis, mixed-language labels, highlighted
  metrics, and short callouts inside one text box.
- A run may carry text, role, font family token, font size, weight, italic,
  underline, color token or safe hex color, and optional link-disabled metadata.
- Text objects should be structured as paragraphs containing runs. Paragraphs
  may carry role, alignment, bullet flag, bullet level, spacing, and overflow
  policy.
- Rich text runs must still obey Korean line-height and wrapping rules. Do not
  create many tiny runs that make user editing brittle.

## Spacing Rhythm

- Use a 16 px base spacing rhythm with common steps of 8, 16, 24, 32, 48, and
  72 logical px.
- Align related objects to shared x/y anchors.
- Keep at least 16 logical px between independent text boxes and at least 24
  logical px between cards, diagrams, or image slots.
- Use 8 px radius or less for ordinary cards unless the deck style explicitly
  calls for a stronger shape language.

## Headers, Footers, And Page Numbers

- Keep page-number format and position consistent across the deck.
- Use structured footers for short context labels, date/status labels, and page
  numbers.
- Avoid exposing implementation words such as fixture, signature, payload,
  package, or diagnostics in user-facing slide text.
- Headers should identify the slide purpose, not repeat the whole project
  prompt.

## Component Presets

- Comparison diagrams: use two or three balanced columns with concise headings,
  one evidence row, and a clear decision/status row.
- Process timelines: use 3 to 5 steps, numbered markers, consistent spacing,
  and a final outcome marker.
- Icon-label cards: pair one simple icon or safe placeholder with one short
  label and one supporting phrase.
- Metric cards: emphasize one value, one label, and one short caveat. Keep units
  visible.
- Image frames: reserve explicit asset slots with fit/crop guidance. Use safe
  refs only in PPT Maker state.
- Disclaimers: place them in a compact footer or low-emphasis note block, never
  over primary visuals.
- Structured footers/headers: keep repeated objects stable in size and position
  across slides.

## Asset Slots

- Use asset slots when a real visual is needed but the current handoff has only
  approved safe refs or placeholders.
- An asset slot may include safe asset ref, dimensions, fit mode, crop mode,
  zoom, and focal x/y.
- Do not include workspace locations, source file names, binary previews,
  encoded asset blobs, private links, EXIF details, package internals, or
  unapproved asset records.

## Visual Density

- Proposal decks should feel complete and deliberate, but not crowded.
- A dense slide may use many objects only when hierarchy is clear: one primary
  message, one supporting structure, and a small set of evidence details.
- Prefer fewer well-aligned objects over many loosely placed labels.
- If a slide needs more than 7 substantial objects, group them into a diagram,
  table, timeline, or card set.

## Self-QA Rubric

Before handoff, check:

- Canvas remains fixed 16:9.
- Title lines do not overlap at 1440, 1600, 1920, ultrawide, or 640 inspection
  widths.
- No unintended object overlap or broken composition is visible.
- Korean text uses safe line height and wraps cleanly.
- Header, footer, and page number treatment is consistent.
- Export-hook envelope is sanitized and does not include prompt text, private
  sources, workspace locations, source file names, cloud document IDs, package
  internals, credentials, browser markup dumps, encoded asset blobs, private
  image links, or reasoning traces.
- Proposal preview/apply/reject behavior is bounded and truthful.
- Diagnostics and operation logs remain hidden from normal users.
- Demo fixtures are labeled as fixtures and are not presented as generated
  host-AI output.
- Master/theme/layout/token references are present when a design package is
  used.
- Rich text runs survive direct editing and partial style changes.
- App chrome language/theme changes do not mutate slide design tokens unless
  the user explicitly edits those tokens.

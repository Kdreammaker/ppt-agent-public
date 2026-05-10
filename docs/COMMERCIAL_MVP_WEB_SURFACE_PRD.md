# Commercial MVP Web Surface PRD

## 1. Product Goal

PPT Maker / A.DreamMaker is a host-AI assistive extension whose core job is to
help an external host AI create better presentations with less token waste and
less user friction.

The product is not a standalone AI chat app, not a Python slide generator, and
not a SlideIR proof viewer. The user-facing product must guide host AI toward
high-quality slide production, show the generated work in an editable HTML
slide workbench, let the user make common corrections before final export, and
then hand the current work back to host AI for PDF or PPTX creation through a
sanitized export hook.

The expected production quality for slides created through this product is at
least comparable to the user-provided benchmark files:

- `benchmark HTML reference`
- `benchmark PPTX reference`

These files are quality benchmarks only. Product code, fixtures, prompts,
validators, and guides must not hardcode their business content, exact DOM,
object coordinates, image URLs, filenames, local paths, or sample-specific
branding.

This PRD is the product-boundary source. Implementation work must also use the
segmented companion specs:

- `docs/COMMERCIAL_MVP_PRODUCT_BOUNDARY_PRD.md`
- `docs/COMMERCIAL_MVP_HTML_WORKBENCH_SPEC.md`
- `docs/COMMERCIAL_MVP_HOST_AI_DESIGN_GUIDE_SPEC.md`
- `docs/COMMERCIAL_MVP_EXPORT_HOOK_CONTRACT.md`
- `docs/COMMERCIAL_MVP_BENCHMARK_QA_RUBRIC.md`

When there is tension between a prior SlideIR proof-shell note and these
segmented specs, the segmented specs control the next user-facing
implementation slice.

## 2. Product Positioning

Primary display brand:

- `A.DreamMaker`

Durable full brand:

- `ADOTDREAMMAKER`

Product category:

- Host-AI assistive PPT/PDF slide-making extension.
- AI-guidance and slide-editing workbench for high-quality HTML slide output.
- Commercial control plane for free-tier credits, paid fair-use entitlement,
  account/session limits, referral attribution, and asset/design-package
  mediation.

The product boundary:

- Host AI owns interpretation, planning, writing, source-use judgment, visual
  direction, revision decisions, asset-need judgment, and final PDF/PPTX
  creation when the user asks for export.
- PPT Maker owns reusable design guidance, system prompts, tool mediation,
  sanitized handoff envelopes, HTML slide workbench display and basic editing,
  proposal/patch review, validation evidence, account/free-credit and paid
  entitlement controls, asset/design-package mediation, and public/private
  safety.
- PPT Maker may run local checks, render previews, preserve user edits, and
  mediate export requests, but must not become an embedded independent backend
  AI authoring chat.

Assistant and Auto remain the only modes. Assistant is the default mode.

## 3. Core User Problem

The user wants AI to generate professional presentations, but raw AI generation
often wastes tokens on small corrections after the deck is already mostly
right. The user needs a practical local editor where they can fix obvious
issues directly before asking host AI to create final PDF/PPTX output.

The required workflow is:

1. User gives a deck request to host AI.
2. Host AI uses PPT Maker's presentation-design guide and tool contracts to
   produce high-quality fixed-canvas HTML slide output.
3. PPT Maker displays the generated HTML deck in a familiar slide editor.
4. User performs common direct edits locally: text edits, object movement,
   resize, alignment, delete/duplicate, image slot replacement, and slide
   ordering where supported.
5. PPT Maker records edits in a safe local work state and a sanitized operation
   summary.
6. User clicks `Export PDF` or `Export PPTX`.
7. PPT Maker sends a sanitized host-AI handoff hook with current work state,
   edit summary, quality requirements, and target export kind.
8. Host AI creates the final PDF or PPTX using the current work, without PPT
   Maker pretending that a local fixture is a real final export.

### Reference Design Reuse

A core commercial need is reusing a user's existing slide style. Many users do
not want a brand-new template each time; they want to update content while
preserving a previously used company, client, or personal slide style.

The required product shape is local-host-AI-first:

1. The user provides an existing PPTX/PDF/HTML deck to the local host AI or
   local workspace toolchain.
2. The local host AI analyzes the file and extracts design-only structure.
3. PPT Maker receives and stores only the sanitized design recipe in the user's
   account or project library.
4. Future generations can reference that design recipe without re-uploading or
   storing the original deck content.

This is not a server-AI ingestion flow. PPT Maker must not require the product
server to receive original PPTX/PDF files for this feature. The product server
may store design recipes, safe previews, and library metadata, but must not
store source slide content unless a future separately approved feature changes
that boundary.

The initial benchmark family now includes the original root sample pair and
the three local sample pairs representing IR, sales, and portfolio deck
families. These samples may be analyzed only to derive design recipes,
quality rubrics, and visual-density targets. They must not be copied into
fixtures, public pages, generated decks, prompts, coordinates, image URLs, raw
DOM, filenames, or business text.

Allowed stored design data:

- theme tokens: palette, font roles, spacing, radius, stroke, and density.
- master styles: Title/H1/H2/H3/Body/Caption/Bullet defaults.
- layout recipes: relative positions, regions, image slots, hierarchy,
  alignment, and density.
- component recipes: KPI cards, comparison tables, timelines, section covers,
  proof blocks, image-plus-copy blocks, and closing slides.
- slide archetypes: cover, agenda, problem, solution, roadmap, appendix, and
  similar content-free categories.
- object geometry summaries expressed as relative boxes and z-order patterns.
- synthetic/content-free previews that use placeholder text rather than source
  deck text.

Blocked stored design data:

- original PPTX/PDF/HTML source files.
- source slide images or full screenshots.
- original slide text, company names, customer names, people names, and
  business-specific content.
- local paths, raw filenames, private URLs, raw prompts, or host-AI reasoning.

The user-facing library name may be `Reference Design Library`, `Style
Library`, or a similarly clear label. UX copy should say `디자인만 추출`,
`내용 제외하고 스타일 저장`, or equivalent, rather than vague consent language.

### Published HTML Canvas Viewer

PPT Maker should reduce the need for direct Google Drive, Dropbox, or similar
cloud-drive integrations by providing its own read-only HTML canvas viewer.
The viewer is a published deck version, not a shared editor.

Viewer requirements:

- generate a view-only link for a specific published deck version.
- expose the viewer renderer, not the editing workbench or privileged APIs.
- prohibit edits from the viewer link.
- support watermark or `Made with` attribution for free-tier shared views.
- support paid removal of share watermark.
- support optional future controls such as expiration, password, noindex, and
  download permission.
- never expose raw workbench state, private asset URLs, local paths, package
  internals, or service credentials.

External cloud-drive connections are deferred. Users who need Drive/Dropbox
access should use their local host-AI environment, CLI, or MCP integrations
from Codex Desktop, Cursor, Antigravity, Claude Code, or similar tools. PPT
Maker's own product priority is the viewer link and safe handoff envelopes.

### Product Surface Placement

The normal editor UI must not expose internal scaffold blocks as if they were
ordinary user-facing controls. The right inspector is for selected-object
properties and secondary precision editing. It may show object text, style,
position, size, transform, crop/fit, shape radius, and accessibility/status
fields that directly explain the selected object.

The following capabilities are product features, but they do not belong as
raw always-visible blocks in the right inspector:

- Master style: expose as a deck/theme style surface with preview, apply,
  override, reset, and lock semantics. Do not show only `master_style_id`,
  role ids, or schema defaults to normal users.
- AI revision memory: expose as a bounded revision/history surface or host-AI
  context summary. It must not look like hidden model memory, raw prompts, or
  backend reasoning.
- Reference Design Library: expose as a library/template/design-reuse surface,
  not as selected-object metadata. It should make clear that only design is
  stored and content is excluded.
- Style Memory: expose as account/project preferences with inspect, reset,
  and delete controls. It is not undo/redo and not per-slide diagnostics.
- Published viewer: expose through share/publish controls and viewer settings,
  not through the object inspector.
- Referral and credits: expose through account/billing/onboarding surfaces.
  Do not place free-credit ledgers inside the editing inspector.
- Local font/image links: expose as a brand-assets or connection setup flow
  using safe refs only. Do not show raw local paths, filenames, or package
  internals.
- Host-AI export: expose through top-level export buttons, a modal or drawer,
  and honest job state such as handoff sent, awaiting host AI, proposal ready,
  blocked, or final received. Do not show raw envelope internals in normal UI.

Diagnostics, operation logs, package internals, raw work state, validation
signatures, and private evidence remain hidden from normal mode.

### Asset-System Consumption Standard

Claiming asset-system use requires more than safe-reference scaffolding. A
commercial workbench may say it uses the asset system only when it has evidence
of an approved package or approved design package, entitlement status,
manifest-safe ids, materialization or render-use evidence where applicable, and
public/private boundary validation.

Until that evidence exists, copy and UI must say the product is asset-system
ready or safe-reference ready, not that approved assets have been fused into
the deck. Valid consumption should follow this shape:

1. Check entitlement and approved-package availability.
2. Receive or resolve a manifest-safe package/design-package reference.
3. Validate license, checksum/version, allowed slot use, and blocked private
   markers.
4. Map only safe ids into theme token-like values, layout recipes, component recipes,
   image/icon slots, or font stacks.
5. Render through those safe ids and record evidence without exposing package
   internals, local paths, raw filenames, or private URLs.

### Sample-To-Design Extraction Standard

The product should support PPTX/PDF/HTML style reuse through a design
extraction pipeline, but the pipeline must extract content-free design recipes
instead of copying a deck. A future importer may parse PPTX OOXML, render slide
previews locally for measurement, parse HTML/CSS, and normalize both paths into
one design IR. The stored output should include palette, typography roles,
layout archetypes, component recipes, image-slot treatment, chart/table style,
density, spacing rhythm, and synthetic previews with placeholder content.

It must not store original files, raw DOM, source screenshots, source text,
business names, image URLs, local paths, or filenames.

### Host-AI Install And Internal Full Beta Gate

Internal full beta means a named internal audience can run the intended
workbench, viewer, CLI/MCP, and host-AI handoff flows end-to-end in the
approved local/preview environment. It does not imply public launch, external
distribution, production OAuth, payment, DNS, Supabase, Vercel, Cloudflare, or
asset-system mutations unless a separate approval names those exact actions.

Before internal full beta, the product must clear these gates:

- CLI, MCP, workbench UI, and export handoff reports must agree on
  Reference Design Library content-free status. A recipe with either
  `content_free_preview.placeholder_labels_only=true` or
  `synthetic_placeholder_preview.placeholder_labels_only=true` is content-free.
  Any handoff that reports otherwise is a P1 host-AI contract blocker.
- Published viewer Free and Paid views must fit the full 1600x900 slide at the
  required desktop, ultrawide, and narrow widths without editable controls.
- Generated work-state loading must be separate from fixture data and must
  ingest deck objects, design package ids, theme token-like values, revision memory,
  export state, and safe asset refs.
- Normal KO/EN UI must localize primary toolbar, inspector, product-surface,
  status, and export labels. Developer diagnostics may remain English only when
  hidden from normal mode.
- Top-level product drawers may preserve the canvas dimensions, but they must
  not create ambiguous edit targets or cover the canvas without a clear close,
  apply, or focus policy.
- Host-AI install testing must be recorded against a named host client, using
  the installable CLI/MCP golden path rather than only local helper scripts.
- Asset-system copy must remain `asset-system-ready` unless an approved
  package or approved design package is actually resolved, consumed, rendered
  where applicable, and evidenced through safe ids.

The immediate path to internal full beta is three substantive work units:

1. Correct contract and UX hardening: fix the CLI/MCP content-free summary
   mismatch, close remaining KO/EN normal-mode copy gaps, and verify product
   drawer edit policy.
2. Host-AI install connection: install or load the workbench tools in a named
   host client, open the workbench, emit PDF/PPTX handoffs, process proposal
   and final-return guards, and record evidence.
3. Internal full beta rehearsal: run the full internal workflow with the
   intended internal audience and sample task families, record blockers, and
   reserve public/external launch decisions for a later approval.

### Internal Full Beta Sequencing

Use internal full beta as the dividing line between preparation work and
feedback-driven product work.

Finish before the internal full beta rehearsal:

- Keep the decision packet unambiguous: internal full beta is go only for the
  local/preview Codex CLI path; public closed beta remains no-go.
- Prepare the rehearsal runbook: tester roles, task prompts, success criteria,
  stop criteria, evidence roots, issue severity, feedback template, and
  rollback/cleanup steps.
- Verify the local/preview Codex CLI golden path and clearly label external
  host clients as unproven until tested separately.
- Provide safe non-fixture IR, Sales, and Portfolio generated work-state
  evidence with design package, theme, revision, export, and safe asset refs.
- Keep screenshot gallery, go/no-go dashboard, generated quality report, and
  boundary/negative-test reports current.
- Make sure normal users can understand the current beta limits: no live
  account/payment, no production export completion, no approved asset-package
  consumption, and no public deployment.

Do after running the internal full beta, because user behavior should guide the
right fix:

- Toolbar, drawer, and editing-flow adjustments based on observed confusion,
  friction, repeated misclicks, or slow workflows.
- Reference Design Library apply semantics and before/after explanations based
  on whether testers understand design-only reuse.
- Master Style and Style Memory wording and controls based on whether testers
  confuse them with undo, hidden AI memory, or per-object editing.
- Export handoff wording based on whether testers mistake handoff for final
  PDF/PPTX completion.
- Generated deck quality improvements based on which task family, slide type,
  or visual element testers judge weak.
- Free/Paid plan and beta-account copy based on actual expectation gaps.

Do only after internal full beta produces real usage signals or after an
explicit deployment/account approval:

- Public closed beta UX polish, support process, onboarding simplification, and
  external tester instructions.
- Production OAuth/account/payment implementation and billing webhooks.
- Vercel project creation/deploy, Cloudflare DNS/gateway deployment, and
  Supabase production mutations.
- Stronger approved asset/design-package consumption claims.
- Public repo refresh, public installer/package publication, workspace-code
  issuance, or external beta distribution.
- Commercial pricing/package decisions that depend on tester willingness to
  pay, perceived value, or support burden.

### Commercial-Grade And Public Closed Beta Candidate Gate

The final pre-user-full-beta hardening pass should be treated as the last broad
product-improvement unit before switching to debugging and QA-only work. It
must not stop at local validators. The worker must use every practical
evidence source available: named host-client install attempts, CLI/MCP calls,
browser smoke, screenshots, generated work states, public/private scans,
decision packets, and manual product review.

After each QA pass, the worker must immediately record findings and run the
next improvement loop. Repeat this loop up to five times:

1. Run smoke, screenshots, validators, boundary scans, and product review.
2. Classify findings as P1/P2/P3 and record them in the work log or decision
   packet.
3. Fix P1/P2 issues and any low-risk P3 polish that improves commercial
   readiness.
4. Re-run focused validation and screenshot QA.
5. Stop early only if the product reaches public closed beta candidate quality
   with no open P1/P2 issues, no honesty gaps, and a clear go/no-go packet.

Public closed beta candidate quality is higher than internal full beta. It
requires:

- real named host-client golden-path evidence, or a specific external blocker
  packet if the named client cannot be invoked from the local environment.
- IR, sales, and portfolio generated work states that are not fixtures and are
  visually credible against the benchmark family without copying source
  content.
- normal users can understand and use the workbench, Master Style, Style
  Memory, Reference Design Library, viewer, and export handoff without seeing
  scaffold/raw contract language.
- PDF/PPTX export remains honest: handoff/proposal/final states are clear, and
  final success appears only with a real safe host-result reference.
- asset-system claims remain `asset-system-ready` unless approved package or
  approved design-package consumption evidence exists.
- Supabase, Vercel, Cloudflare, remote public repo, and remote private repo
  status are checked and reported. Read-only checks are allowed; deployments,
  OAuth/payment activation, DNS changes, repo pushes, production database
  mutations, and external asset-system mutations require explicit approval.
- commercial completeness is assessed against the PRD, not just technical
  operation. The final decision must say whether each planned product surface
  is merely functioning, beta-usable, or commercially credible.

## 4. Non-Negotiable Direction Change

The SlideIR local editor shell work is no longer the user-facing product center.
It remains useful as an internal safety, patch, evidence, or compatibility
layer, but it must not define the commercial editor experience.

The next product center is:

- an AI-authored fixed-canvas HTML slide workbench;
- direct basic editing on visible slide objects;
- reusable design-system/system-prompt guidance that helps host AI generate
  slides at benchmark quality;
- honest host-AI export hooks for PDF/PPTX;
- self-QA loops that judge visual output against the benchmark family.

Future work must not continue polishing a SlideIR proof shell unless it directly
unblocks the HTML workbench or export hook.

## 5. Benchmark Interpretation

The benchmark HTML file demonstrates a quality family, not a template:

- 11-slide proposal deck structure.
- fixed 16:9 HTML slide containers.
- Korean-first professional proposal typography.
- dense but intentional absolute-positioned composition.
- multiple image/icon placements.
- structured header, footer, page number, and section rhythm.
- visual hierarchy with large display type, small labels, cards, charts,
  diagrams, and image frames.
- rich color palette and controlled spacing.

The current measured benchmark characteristics are useful QA signals:

- 11 slide containers.
- 27 image tags.
- 37 remote image-like URL references.
- 87 `position:absolute` declarations.
- 182 font-size declarations.
- 53 z-index declarations.
- 26 distinct hex colors.

These signals prove that benchmark-level output requires a richer HTML slide
composition system than the current two-slide SlideIR fixture shell. They must
not be copied as hardcoded output.

The benchmark PPTX file demonstrates the final-product expectation:

- native PowerPoint output should feel like a real proposal deck.
- text, pictures, shapes, and common visual objects should remain useful to the
  user after export where feasible.
- Korean line breaks, spacing, header/footer consistency, and object alignment
  are quality requirements, not cosmetic extras.

## 6. Quality Bar

If the benchmark output is `100`, the product target is:

- Initial commercial MVP: at least `75` for visual slide quality and `70` for
  basic editing usability.
- Public paid readiness: at least `85` for visual slide quality and `80` for
  basic editing usability.
- Current SlideIR shell quality should be treated as below commercial bar and
  should not be used as the reference for future acceptance.

Quality is judged by user-visible results, not by validator pass counts alone.
Validators are required, but a green validator cannot overrule a visibly broken
canvas, non-editable text, fake export completion, or benchmark-inferior deck.

## 7. Required Architecture

### Host-AI Guidance Layer

PPT Maker must maintain a versioned presentation-design guide, similar in role
to a `DESIGN.md` or system design instruction package. The guide should include:

- slide canvas rules.
- typography scale and Korean line-height/wrapping rules.
- color and contrast guidance.
- spacing, safe area, and alignment rules.
- component recipes: title slides, section headers, timelines, process flows,
  metric cards, comparison tables, insight cards, image-plus-copy layouts,
  icon-label grids, quote/proof blocks, and closing slides.
- asset slot guidance and public/private asset boundaries.
- output QA checklist.
- examples expressed as reusable patterns, not copied benchmark content.

Host AI should read this guide before generating or revising HTML slides.

The guide must evolve from a prose-only document into a versioned design
package contract. PPT Maker may provide this package from local tracked docs,
from the product server, or from the approved asset system when the user's plan
and entitlement allow it. Regardless of source, the package must expose stable
public-safe identifiers rather than raw private records:

- `design_guide_version`
- `design_package_id`
- `manifest_hash`
- `theme_id`
- `master_style_id`
- `layout_recipe_id`
- `component_recipe_id`
- `token_set_id`
- `asset_system_package_ref` when an approved asset-system package supplies
  layout, font, palette, icon, illustration, or style-token guidance.

Asset-system supplied layout recipes, font stacks, color palettes, shape
styles, icon families, and master-style guidance are allowed only after the
same approval/materialization/public-private checks used by the asset-system
boundary. Starter and Manager must not receive or consume Leader-only package
details. Public UI and handoff envelopes may reference only safe ids, resolved
token names, and sanitized summaries.

The design package must separate theme token-like values, master styles, text style roles,
layout recipes, component recipes, and user/host-AI content state. For V2,
master style is not a full PowerPoint-style layout master. It is the shared
style layer for typography roles, palette defaults, shape defaults, and common
slide chrome. Slide content should refer to the selected design package, master
style, layout, and component ids rather than duplicating a slide-specific
`design.md` for every page.

Required text style roles:

- `Title`
- `H1`
- `H2`
- `H3`
- `Body`
- `Caption`
- `Bullet`

Each role must be able to define font family token, font size, weight, color,
line height, paragraph spacing, and overflow policy. Letter spacing should
default to `0`. Bullet behavior must be stored at paragraph level, not by
silently prepending decorative text to a plain string. `Bullet` may be used as
a standalone role, and `Body` paragraphs may also set `bullet=true` and a
bounded `level` for mixed body/bullet text.

### HTML Slide Workbench

The primary editor surface must render generated fixed-canvas HTML slides as the
main canvas. It should feel like a practical slide editor, not an operator
evidence panel.

Required baseline behavior:

- left slide navigation for 10+ slides.
- selected slide displayed as a dominant 16:9 canvas.
- direct text editing from the canvas, preferably double-click or inline edit.
- object selection with visible handles.
- object move, resize, duplicate, delete, and z-order controls.
- basic alignment helpers.
- multi-object selection with alignment and distribution helpers where claimed.
- shape/image rotation through bounded buttons, not freeform rotation, where
  claimed.
- shape/image horizontal and vertical flip where claimed.
- shape corner-radius adjustment where claimed.
- image slot replacement using safe refs, not raw local paths in public state.
- undo/redo.
- keyboard-friendly selection and text editing where feasible.
- localized Korean labels for user-facing controls.
- diagnostics hidden from normal user mode.

The workbench must not be only a textarea inspector that edits hidden model
fields. Text editing must be visible and natural.

The next workbench iteration must treat the current static demo deck as a demo
fixture only. It must introduce a workbench state schema that can accept a
server/host-AI generated deck plus a design package. Fixture slides may remain
for smoke tests, but they must be clearly labeled as fixtures and must not be
the product's only data path.

User-facing editor requirements for the next substantive slice:

- persistent top toolbar for common editing actions. Text style, font size,
  font family, color, alignment, duplicate/delete, z-order, undo/redo, and
  zoom/fit must be visible primary controls rather than hidden in diagnostics or
  a technical inspector.
- real direct text-edit UX. A user must be able to click or double-click a
  visible text object, see a caret/selection, type Korean text, and see the
  local state mutate without using a hidden API or inspector-only textarea.
- rich text runs inside one text object. A single text box must support
  selection-range color, bold, italic, underline, font family, and font-size
  changes without forcing the whole object to share one style.
- text objects must carry a text style role such as `Title`, `H1`, `H2`, `H3`,
  `Body`, `Caption`, or `Bullet`. Run-level styling may override only the
  selected range; it must not destroy the role assignment for the whole object.
- paragraph-level bullet state is required for bullet lists. Bullet text must
  support at least one bounded level in V2, with future room for deeper levels.
- text box rotation is out of V2 scope. Rotation controls apply only to PPT
  Maker-created shapes and inserted images until direct text editing,
  selection, Korean input, and rich-text runs are stable.
- object resize uses box-based geometry in V2. Rotation, flip, align, and
  distribute operations should update explicit object properties while keeping
  the stored resize box stable.
- shape/image rotation is bounded to fixed steps: clockwise/counterclockwise
  `15deg`, clockwise/counterclockwise `90deg`, and reset. Freeform drag
  rotation is deferred.
- shape/image objects should support `flipX` and `flipY` where claimed.
- shape objects should expose editable `cornerRadius` or a safe radius token.
- automatic canvas fitting. The 16:9 logical canvas remains fixed, but browser
  display must fit the available stage area using measured container size,
  side-panel widths, current zoom, browser zoom, and narrow layout behavior.
- system font-size accessibility. UI chrome must use scalable units and remain
  usable when browser or OS text scaling is increased.
- app chrome dark/light theme. This must not mutate the slide's own declared
  canvas theme unless the user explicitly changes slide/theme tokens.
- English/Korean UI switching. Locale switching must affect toolbar labels,
  status text, panels, export-hook text, and mode descriptions.
- Assistant/Auto controls must be explained as host-AI generation/revision
  behavior, not as ordinary object editing modes. They should be visually
  separated from slide editing controls.
- AI revision memory distinct from undo/redo. The workbench must preserve
  public-safe summaries of prior host-AI generations, export handoffs,
  proposals, user accept/reject decisions, and local edit summaries so a later
  host-AI revision can continue from prior work without exposing raw prompts or
  private sources.
- Style Memory is a separate account/project capability. It stores durable
  public-safe preference signals such as preferred typography roles, palette
  choices, rejected layouts, accepted component recipes, logo-placement
  patterns, density preferences, and recurring local edits. It must be visible,
  explainable, editable, and deletable by the user. It must not be a black-box
  memory of private content.

### Work State

The editable work state may include:

- sanitized HTML slide document or a structured HTML-slide model.
- design package reference, theme token-like values, master style reference, text style
  role definitions, layout recipe
  reference, and component recipe references.
- object records derived from the generated slide output.
- text objects with role, paragraph, bullet, rich-text `runs[]`, and
  selection-aware editing metadata.
- shape/image object transform fields such as `rotation`, `flipX`, `flipY`,
  and box-based resize bounds.
- shape object radius fields such as `cornerRadius` or radius token reference.
- operation log for user edits.
- AI revision memory, proposal history, accepted/rejected proposal state, and
  host-AI handoff history.
- Style Memory references and summaries for the current account/project.
- Reference Design Library recipe ids and content-free preview metadata.
- published-view version metadata and viewer-share status.
- safe asset refs and crop/fit metadata.
- proposal status and export hook status.

The work state must not expose:

- raw prompts.
- private sources.
- local paths.
- raw filenames.
- Drive/Docs identifiers.
- package internals.
- credentials or tokens.
- encoded asset image blobs.
- backend chain-of-thought.

### SlideIR Role

SlideIR remains allowed as an internal safety and export-compatibility layer,
but it is not the commercial editor's user-facing source of truth unless it can
represent benchmark-level HTML output without losing visual quality.

Allowed SlideIR uses:

- bounded patch application.
- compatibility mapping.
- native Office evidence.
- safe operation summaries.
- private-boundary validation.

Blocked SlideIR misuse:

- continuing to polish the current proof shell as if it were the final product.
- limiting HTML generation to the current constrained object vocabulary when it
  cannot meet the benchmark quality.
- claiming commercial editability while text can only be edited in a technical
  inspector.

### Export Hooks

`Export PDF` and `Export PPTX` are host-AI hooks.

When clicked, PPT Maker must:

- package target export kind: `pdf` or `pptx`.
- include safe project/deck/slide labels.
- include current Assistant/Auto mode.
- include current sanitized work state or compact work reference.
- include user edit operation summary.
- include design-guide version.
- include design package, text style role, paragraph/bullet, rich-text run,
  shape/image transform, and revision-memory summaries where present.
- include output quality requirements and validation expectations.
- send or prepare a host-AI request envelope compatible with the shared
  CLI/MCP contract.
- show honest status: `handoff ready`, `handoff sent`, `awaiting host AI`,
  `proposal ready`, `blocked`, or `final received`.

PDF/PPTX export handoff is not the main paid-plan boundary. Because host AI
creates final PDF/PPTX output, users may be able to ask host AI to produce files
outside PPT Maker. Commercial value should therefore come from editing,
reference design reuse, Style Memory, asset/design packages, viewer sharing,
and handoff convenience rather than pretending export itself can be reliably
locked.

PPT Maker must not:

- claim `complete` when no real PDF/PPTX exists.
- create final slides through hardcoded Python deck generation.
- parse arbitrary browser DOM as a hidden PPTX renderer.
- expose raw DOM, private user content, local paths, or image binaries in the
  default handoff.

## 8. Explicit Non-Goals

The Commercial MVP must not include:

- embedded independent AI authoring chat inside PPT Maker.
- third mode beyond Assistant and Auto.
- hardcoded sample deck output.
- Python code that directly fabricates the final user deck to mimic the sample.
- fake export success fixtures presented as real output.
- arbitrary HTML import from untrusted files as a production export path.
- HTML screenshots inserted into PPTX as a substitute for editable output.
- full PowerPoint clone scope.
- payment, deployment, or hosted generation unless separately approved.
- first-party Google Drive, Dropbox, or broad cloud-drive file management.
- server-side original-deck ingestion for Reference Design Library creation.

## 9. Commercial Stack Direction

The commercial stack direction remains:

- Cloudflare gateway.
- Supabase Postgres.
- Vercel dashboard/admin.
- local CLI as the installable first-run surface.
- thin MCP adapter over the same CLI/package APIs for host-AI clients.

Current status:

- deploy is not attached.
- payment is not attached.
- hosted generation is not attached.
- The new Commercial MVP Supabase production-target project is
  `slides-maker-prod` in Northeast Asia (Seoul), project ref
  `tnbjlydrneugaouirtnq`. Use this project for the next production-oriented
  auth/account/control-plane wiring instead of the older `slides-maker`
  experiment project.
- Cloudflare is represented by gateway route contracts and local fixture smoke,
  not by a production Worker deployment.
- Vercel is represented by local/Vercel-ready static surfaces, not by an
  external deployment.
- MCP is currently a developer-preview companion and must remain a thin wrapper
  over the same CLI/package APIs. It must not create a separate renderer,
  composer, upload path, workspace scanner, or hidden product flow.
- The HTML workbench must stop being an isolated local demo and become part of
  the installable CLI/MCP golden path before external install testing.
- account dashboard remains a placeholder until separate auth/payment/backend
  work is accepted.
- local dashboard state is untrusted.
- server/control-plane entitlement is authoritative.
- asset-system access remains Leader-only.
- Starter and Manager remain blocked from approved package requests and
  consumption.

### Production Domain And Cloud Roles

Use `kkumjangi.com` for the Commercial MVP public/product domains. `soolomon.com`
belongs to another project and must not be used for this product.

Target domain map:

- `slides-maker.kkumjangi.com`: public landing page, SEO entry, signup CTA, and
  product education.
- `app.slides-maker.kkumjangi.com`: logged-in app shell, account dashboard, and
  HTML workbench.
- `api.slides-maker.kkumjangi.com`: Cloudflare gateway for trusted server-side
  API boundaries.

Role split:

- Vercel owns public landing, logged-in frontend routes, account dashboard, and
  the hosted HTML workbench shell.
- Cloudflare owns API gateway behavior: entitlement, free-tier credit and
  paid fair-use guards, session/account checks, asset/design-package preflight,
  export-handoff mediation, referral event mediation, rate limits, CORS, and
  service-role protection.
- Supabase owns Google OAuth, user identity, account membership, entitlement,
  free-tier credit ledger, referral attribution/reward ledgers, deck-run
  metadata, Reference Design Library metadata, Style Memory profiles,
  published-view records, export-handoff records, and RLS-backed account data.

Security principles:

- browser/Vercel frontend may use only public Supabase anon auth flows.
- Supabase service role must never reach browser/client code.
- protected mutations must go through Cloudflare gateway or Supabase
  security-definer RPCs invoked by the gateway.
- Vercel is UI delivery, not the trust boundary for privileged mutations.
- Cloudflare gateway must validate authenticated account/session context before
  privileged requests.

### Signup And Google OAuth

The landing page must include a real signup/login path before external product
testing. Google OAuth through Supabase Auth is the preferred first provider.

Required signup behavior:

- public landing CTA: `Google로 시작하기` / `Start with Google`.
- Supabase Auth Google provider enabled for `slides-maker-prod`.
- redirect allowlist includes the selected Vercel preview and production
  callback URLs.
- first login creates or links a product account through the controlled
  account/member/entitlement bootstrap path.
- default initial free-credit, paid fair-use, referral, and session posture is
  explicit and public-safe.
- account dashboard and workbench entry require an authenticated session.

Supabase project settings baseline:

- region: Northeast Asia (Seoul).
- Data API enabled.
- automatic RLS enabled.
- automatic exposure of new tables disabled or treated as a blocker until table
  grants/RLS are explicitly reviewed. Commercial tables must not become
  publicly reachable just because a migration created them.
- Postgres default engine.

The project was renamed from the initial typo to `slides-maker-prod`; future
docs, env names, and setup reports should use the corrected name and the project
ref above.

### Initial Plan And Monetization Boundary

At first commercial launch, prefer one free plan plus one paid plan. Splitting
paid tiers into two plans is deferred because it increases pricing, support,
entitlement, UX, and QA complexity before product-market fit is proven.

Initial free plan direction:

- free credits are limited and may be replenished through referral rewards.
- the editor should be visible enough for users to understand the paid value,
  but full practical editing can remain paid-gated.
- free users may publish view-only links with watermark or attribution.
- free users may receive limited Reference Design Library or Style Memory
  previews, but recurring reuse should be paid.

Initial paid plan direction:

- avoid visible per-edit credit accounting for normal paid use.
- use internal fair-use and abuse controls rather than making paid users feel
  every small correction costs credits.
- include the practical HTML editor, Style Memory, watermark-free viewer
  sharing, local/approved asset library use, and useful Reference Design
  Library capacity.
- include asset-system-derived approved design packages only through safe
  manifests and entitlement checks.
- keep advanced team collaboration, multi-seat shared workspaces, and broad
  cloud-drive management deferred.

The paid-plan value proposition is not more direct AI compute. It is less
repeated prompting, stronger reuse of the user's own design patterns, safer
asset/style management, better local editing, and clean viewer sharing.

Referral scaffolding should exist early even if final reward policy is still
open. Record referral code, attribution, activation event, reward ledger, and
fraud/abuse signals. Rewards should be tied to activation events such as first
deck creation, first published viewer link, or paid conversion rather than raw
signup alone.

### Asset-System Internalization Strategy

PPT Maker should not import the raw-reference assetization factory into the
product. The useful integration unit is the already-approved result:

- approved asset packages.
- theme tokens.
- font, icon, illustration, palette, and policy metadata.
- layout and component recipes.
- license and usage-scope records.
- safe source/provenance ids.

The product may internalize these approved results into its own Supabase-backed
design-package and asset-library model, customized for PPT Maker. It must not
pull raw reference holdings, assetization worklogs, approval internals, or
external workspace paths into the user-facing product.

## 10. Public/Private Boundary

All user-facing summaries, handoff envelopes, validation reports, and work logs
must avoid exposing:

- raw prompt text unless explicitly approved for local-only debug.
- raw source documents.
- generated full slide bodies in public reports.
- local filesystem paths.
- raw filenames.
- Drive/Docs IDs or URLs.
- package manifests or internals.
- credentials or token-like values, DB URLs, or connection strings.
- private image URLs, encoded asset assets, EXIF, or local image binaries.

Normal UI may display the user's visible slide content because the user is
editing it. Public-safe reports and external handoffs must remain compact and
sanitized.

## 11. Installation And External Smoke

The product must be installable and testable by a new host AI or a new local
operator without hidden conversation context.

Acceptance requires:

- a clean setup path.
- clear run instructions.
- local smoke that opens the actual editor/workbench.
- a CLI command or documented local command that starts or opens the HTML
  workbench from a clean checkout.
- a CLI command or documented local command that emits a sanitized workbench
  export-handoff envelope for PDF and PPTX.
- MCP manifest/tool documentation that maps to the same CLI/package behavior,
  even if the MCP adapter remains developer preview.
- a host-AI style task that asks the system to generate or revise a deck using
  the design guide.
- an Assistant-mode path with Assistant as default.
- an Auto-mode path that remains the only alternate mode and does not create a
  third mode.
- a Codex Desktop and Antigravity-style host-AI walkthrough path using only
  tracked docs, CLI commands, and local artifacts.
- browser screenshots or equivalent visual evidence.
- direct text-edit smoke.
- export-hook smoke for PDF and PPTX handoff states.
- handoff smoke proving no fake final PDF/PPTX completion is displayed without
  a real result reference.
- report/workthrough artifacts written during implementation, including
  sanitized progress reports, validation JSON, browser-smoke evidence, and a
  final tracked work-log entry.
- no dependence on `PLAN.md` or local handoff scratch files.

If a new AI is asked to install and operate the product, it should be able to
follow tracked repository docs and produce the same kind of workbench behavior
without special private instructions.

### Remote And Deployment Readiness

The next one-piece work unit must treat repo/install readiness as part of the
product, not as a later cleanup item.

Required checks:

- record current branch, local/remote divergence, and uncommitted/untracked
  implementation files in the final report.
- do not push or publish unless explicitly instructed.
- if a clean install test is claimed, run it from tracked files or clearly state
  that the test used local uncommitted files.
- keep Vercel, Cloudflare, and Supabase production operations disabled unless a
  later task explicitly approves deployment or remote mutation.
- local Supabase/Cloudflare/Vercel readiness may be fixture-backed, but the UI
  and reports must label it as local fixture or local contract state.

### Required Workthrough Logging

During the next implementation, workers must leave public-safe progress
evidence as they go. This does not mean exposing private prompts, paths,
package internals, or raw slide bodies.

Required evidence:

- intermediate JSON or Markdown reports under the selected workspace/report
  output root for build, state validation, browser smoke, export hook smoke,
  install smoke, and CLI/MCP contract smoke.
- a concise `Workthrough` or equivalent section in
  `docs/REFERENCE_PIPELINE_WORK_LOG.md` before handoff.
- final report links or paths for the evidence roots.
- blocker records with concrete next actions when a required smoke cannot run.

Report hygiene:

- repo-root generated report leakage must be avoided unless a tracked report is
  intentionally updated.
- public-safe reports must use compact labels, safe ids, and relative/sanitized
  artifact references.
- raw prompts, raw sources, local absolute paths, raw filenames, credentials,
  package internals, external document identifiers, encoded asset assets, and backend chain-of-thought
  remain blocked from public summaries and handoff envelopes.

## 12. Acceptance Criteria For The Next Slice

The next implementation slice is not another SlideIR shell polish pass. It must
build or re-center the product around the AI-authored HTML slide workbench.

Required implementation:

- create or clearly designate the HTML slide workbench surface.
- use the benchmark files only to derive reusable design guidance and QA
  expectations.
- implement or wire a design-guide/system-prompt package that tells host AI how
  to generate benchmark-family fixed-canvas HTML slides.
- load a 10+ slide generated deck fixture that is not the the benchmark brand sample and does
  not copy benchmark content.
- render a dominant fixed 16:9 slide canvas.
- support direct canvas text editing that mutates the local work state.
- support object selection, move, resize, duplicate, delete, and z-order for
  common slide objects.
- restore a persistent editor toolbar with primary text/object/layer/zoom
  controls.
- support rich text runs so a selected range inside one text object can change
  color, bold/italic/underline, font family, and font size.
- introduce master style, text style role, theme token, layout recipe, and
  component recipe references in the workbench state.
- support text roles for Title, H1, H2, H3, Body, Caption, and Bullet, with
  paragraph-level bullet state.
- support bounded multi-select editing: align/distribute, box-based resize,
  shape/image fixed-step rotation and flip, and shape corner radius where
  claimed. Text box rotation and freeform rotation remain deferred.
- support server or approved asset-system supplied design packages for layouts,
  font stacks, color palettes, and style tokens without leaking package
  internals.
- implement automatic canvas fit/zoom behavior that works with side panels,
  narrow viewports, and browser/system text scaling.
- add app chrome dark/light mode and English/Korean UI switching.
- make Assistant/Auto controls clearly describe host-AI generation/revision
  behavior, separate from ordinary slide editing controls.
- preserve AI revision memory distinct from local undo/redo.
- add account/project Style Memory as a public-safe, user-visible preference
  profile.
- add Reference Design Library scaffolding for local-host-AI extracted
  design-only recipes from existing PPTX/PDF/HTML decks.
- add published HTML canvas viewer scaffolding for read-only link sharing.
- add referral scaffolding for free-credit acquisition and activation-based
  rewards.
- represent the initial commercial posture as Free plus one Paid plan, with
  two paid tiers deferred.
- preserve a sanitized operation summary.
- implement honest `Export PDF` and `Export PPTX` host-AI hook states.
- wire the HTML workbench into the local install/CLI path enough that a new
  operator or host AI can open it from tracked docs.
- update the CLI/MCP-facing contract or manifest so the workbench and export
  handoff are represented as high-level local tools or commands.
- preserve Supabase, Cloudflare, and Vercel as local contract/fixture readiness
  unless explicitly approved for remote deployment or mutation.
- produce intermediate report/workthrough artifacts during implementation, not
  only a final prose summary.
- keep diagnostics hidden in normal user mode.
- support Korean UI labels and Korean text wrapping/line-height checks.
- maintain public/private boundary checks.

Required self-QA loop:

- run build and focused validators.
- run browser smoke at 1440, 1600, 1920, ultrawide, and narrow inspection
  widths.
- manually inspect screenshots against the benchmark family.
- test direct text editing on the canvas.
- test real typing, caret, and selection behavior on the scaled canvas,
  including Korean input.
- test object movement and resize.
- test slide navigation over 10+ slides.
- test toolbar visibility and primary controls.
- test partial rich-text styling inside one text object.
- test text role defaults and paragraph-level bullet state.
- test multi-select alignment/distribution where claimed.
- test box-based resize, shape/image fixed-step rotation, shape/image flip, and
  shape corner radius where claimed.
- test that text box rotation is unavailable or clearly disabled in V2.
- test master/theme/layout references and fixture-vs-generated data boundaries.
- test canvas auto-fit/zoom with side panels, narrow width, and browser/system
  text scaling where feasible.
- test dark/light mode and English/Korean UI switching when claimed.
- test Assistant/Auto explanation and AI revision memory when claimed.
- test Style Memory state, visibility, and public/private boundaries when
  claimed.
- test Reference Design Library recipes are design-only and content-free when
  claimed.
- test published viewer links are read-only and do not expose editor/private
  state when claimed.
- test referral scaffolding and free-credit ledger behavior when claimed.
- test that paid-plan UX does not present normal paid editing as per-edit
  credit consumption.
- test PDF/PPTX export hook states without fake final success.
- test local install/open-workbench path from tracked docs.
- test CLI/MCP contract smoke for Assistant and Auto paths where claimed.
- test that Supabase/Cloudflare/Vercel status is honest local contract or
  fixture state, not implied production deployment.
- record intermediate report/workthrough evidence.
- scan for hardcoded benchmark content, sample URLs, sample coordinates, raw
  local paths, raw filenames, and private markers.
- fix P1/P2 issues found by smoke, then rerun the same checks.
- record unresolved blockers with concrete next actions if they cannot be
  fixed in the slice.

Definition of done:

- the workbench is visibly closer to a real slide editor than to a proof shell.
- text can be edited directly.
- the generated deck quality is judged against the benchmark family.
- export hooks are honest host-AI handoffs.
- no hardcoded sample deck behavior exists.
- no Python direct deck fabrication is used to pass the visual benchmark.
- validation evidence and screenshot smoke are recorded.
- installation/CLI/MCP/export-handoff evidence is recorded.
- deployment status is honest: no production Supabase, Cloudflare, or Vercel
  mutation is implied unless it actually happened with approval.

## 13. Current Status

Accepted foundations that remain useful:

- commercial control-plane foundation.
- local gateway/account/free-credit/paid-fair-use entitlement boundaries.
- public/private scanning patterns.
- Assistant/Auto mode boundary.
- Leader-only asset-system boundary.
- previous SlideIR bridge and native Office evidence, as internal compatibility
  infrastructure only.
- reusable presentation design guide draft.

Current blockers:

- CLI/MCP `open` and export-handoff summaries must correctly report
  Reference Design Library recipes as content-free when the current
  `synthetic_placeholder_preview` schema is used. A false negative here blocks
  host-AI install testing because it misstates the public/private boundary.
- Host-AI install testing is still unproven until a named host client runs the
  installable golden path and records workbench open, handoff, return, and
  guard evidence.
- Asset-system use remains ready/scaffold posture until an approved package or
  approved design package is actually consumed with entitlement, safe-id,
  render-use, and boundary evidence.
- Product drawers preserve the canvas dimensions, but must finish the user
  interaction policy so they do not feel like hidden scaffolding over the edit
  surface.
- KO/EN localization is improved, but normal-mode inspector/status copy must be
  fully checked for leftover scaffold English.
- Visual richness is closer to a real editor shell, but benchmark-grade
  generation still depends on approved design packages, stronger host-AI
  generated work states, and internal full-beta workflow rehearsal.
- Public landing, login, signup, payment, OAuth, and deployment copy must stay
  preview/honest until real approved remote mutations are performed.

The next sequence should target internal full beta readiness in three work
units: contract/UX hardening, named host-AI install connection, then internal
full beta rehearsal. Do not add another readiness-only slice unless it removes
one of the blockers above.

## 14. Follow-Up Worker Prompt

Use this prompt for the next implementation worker:

```text
Task: Build the first commercial-grade AI-authored HTML slide workbench for
A.DreamMaker / PPT Maker.

Read first:
- AGENTS.md.
- docs/ACTIVE_BACKLOG.md.
- docs/AGENT_TASK_INDEX.md and the relevant rule files.
- docs/COMMERCIAL_MVP_WEB_SURFACE_PRD.md.
- docs/COMMERCIAL_MVP_PRODUCT_BOUNDARY_PRD.md.
- docs/COMMERCIAL_MVP_HTML_WORKBENCH_SPEC.md.
- docs/COMMERCIAL_MVP_HOST_AI_DESIGN_GUIDE_SPEC.md.
- docs/COMMERCIAL_MVP_EXPORT_HOOK_CONTRACT.md.
- docs/COMMERCIAL_MVP_BENCHMARK_QA_RUBRIC.md.
- docs/COMMERCIAL_MVP_PRESENTATION_DESIGN_GUIDE.md.
- Latest relevant Commercial MVP entries in
  docs/REFERENCE_PIPELINE_WORK_LOG.md.

Goal:
Stop improving the SlideIR proof shell. Build or re-center the user-facing
surface around an editable fixed-canvas HTML slide workbench. PPT Maker's job is
to guide host AI to produce benchmark-quality HTML slides, let the user make
basic edits locally to save token-like values, and hand the current work to host AI through
honest Export PDF / Export PPTX hooks.

Reference quality:
Use the user-provided `benchmark HTML reference` and `benchmark PPTX reference`
only as quality benchmarks. Do not copy the benchmark brand content, exact coordinates, raw
DOM, image URLs, filenames, or sample-specific business text. Do not hardcode
the sample. Do not write Python code that directly fabricates the final
sample-like deck.

Implementation scope:
1. Create or designate the HTML slide workbench surface.
2. Add a reusable design-guide/system-prompt package, similar to DESIGN.md,
   that host AI can use to generate benchmark-family fixed-canvas HTML slides.
3. Provide a 10+ slide generated fixture deck that is generic and not copied
   from the benchmark.
4. Render a dominant 16:9 canvas with familiar slide navigation.
5. Implement direct canvas text editing that mutates local work state.
6. Implement object select/move/resize/duplicate/delete/z-order for common
   slide objects.
7. Keep diagnostics hidden in normal user mode.
8. Implement Export PDF and Export PPTX as honest host-AI handoff hooks:
   handoff ready/sent/awaiting/proposal/blocker/final received, not fake
   complete.
9. Preserve sanitized operation summaries and private-boundary checks.
10. Keep Assistant and Auto as the only modes, with Assistant default.

Self-QA loop:
- Run build and focused validators.
- Run browser smoke at 1440, 1600, 1920, ultrawide, and narrow widths.
- Test direct text editing on the canvas.
- Test object movement/resize and 10+ slide navigation.
- Test export-hook states for PDF and PPTX.
- Compare screenshots against the benchmark quality family.
- Scan for hardcoded benchmark content, exact coordinates, image URLs, local
  paths, raw filenames, private markers, encoded asset assets, and fake export success.
- Fix P1/P2 issues found during smoke and repeat the same checks before
  reporting.

Deliverable:
Report findings honestly. If the result is still a shell rather than a usable
editor, say so and fix it before handoff or record concrete blockers.
```

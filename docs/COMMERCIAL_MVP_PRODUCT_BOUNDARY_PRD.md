# Commercial MVP Product Boundary PRD

## Purpose

This document is the working product-boundary PRD for the next Commercial MVP
implementation slice. It narrows `docs/COMMERCIAL_MVP_WEB_SURFACE_PRD.md` into
the decisions that prevent workers from drifting back into SlideIR proof-shell
polish.

## Product Thesis

PPT Maker / A.DreamMaker is a host-AI guidance extension. Its value is helping
host AI generate better slide work, giving the user a practical HTML editing
surface for small corrections, and sending the corrected work back to host AI
for final PDF/PPTX creation.

PPT Maker should reduce token waste by letting the user fix obvious deck issues
locally instead of asking host AI to regenerate for every small text or layout
change.

## Actors

- User: the person requesting, reviewing, and lightly editing the deck.
- Host AI: the external AI assistant that interprets the user's request, writes
  the deck, chooses visual direction, and creates final PDF/PPTX output after an
  export handoff.
- PPT Maker: the extension/workbench that provides guidance, preview, local
  editing, safe handoff, free-credit/paid-entitlement controls, referral
  attribution, design-library storage, asset mediation, and evidence.
- Asset system: a Leader-only source for already-approved package assets,
  design token-like values, recipes, and metadata.

## Responsibility Split

Host AI owns:

- interpretation of the user request.
- deck plan and narrative.
- writing and revision decisions.
- visual direction and asset-need judgment.
- generation of benchmark-family HTML slide output.
- final PDF/PPTX creation after export handoff.

PPT Maker owns:

- reusable design guide and system-prompt package.
- versioned design package mediation, including safe references to master
  styles, text style roles, layout recipes, theme token-like values, and approved
  asset-system supplied fonts/palettes/layout/style tokens.
- tool execution and safe handoff mediation.
- editable HTML slide workbench.
- local user edit operation tracking.
- proposal preview/apply/reject where patches are bounded.
- public/private scans and validation evidence.
- account, free-credit, fair-use, session, and entitlement boundaries.
- Leader-only asset-system mediation.
- Reference Design Library storage for design-only recipes extracted by local
  host AI from existing PPTX/PDF/HTML decks.
- account/project Style Memory profiles that summarize public-safe user design
  preferences without storing private source content.
- published HTML canvas viewer records for read-only deck sharing.
- referral attribution and reward-ledger scaffolding for the free tier.
- installable local CLI path and thin MCP/host-AI contract alignment for the
  same product behavior.
- public-safe reports, walkthrough logs, and final evidence records for each
  substantive work unit.

## Required Product Shape

- Assistant and Auto are the only modes.
- Assistant is the default.
- Public landing is a real product entrypoint, not only a placeholder. It must
  live at `slides-maker.kkumjangi.com` for the production-oriented path.
- Google OAuth signup/login through Supabase Auth is the preferred first
  authentication path.
- The logged-in app/workbench should use `app.slides-maker.kkumjangi.com`.
- The trusted gateway should use `api.slides-maker.kkumjangi.com`.
- The user-facing center is the fixed-canvas HTML slide workbench.
- `Export PDF` and `Export PPTX` are host-AI hooks, not fake local completion.
- PDF/PPTX handoff itself is not the primary paywall because host AI owns final
  file generation. Paid value should come from editor access, design reuse,
  Style Memory, approved asset/design packages, viewer sharing, and handoff
  convenience.
- The HTML workbench must be reachable through tracked install/CLI instructions
  before external install testing.
- MCP remains a thin wrapper over the same local CLI/package behavior; it must
  not create a separate renderer, composer, upload path, or workspace scanner.
- Codex Desktop and Antigravity-style host-AI clients must be able to follow
  tracked docs without hidden conversation context.
- Static demo decks are fixtures only. They must be labeled as such and must not
  be presented as host-AI generated output or sample-derived output.
- Existing PPTX/PDF/HTML deck reuse must be local-host-AI-first: the local host
  AI extracts design-only recipe data, and PPT Maker stores only sanitized
  design recipes. Original files, source slide images, and source content must
  not be uploaded to or stored by the product server for this feature.
- First-party Google Drive/Dropbox-style cloud drive file management is
  deferred. Users should rely on their local host-AI/MCP environment for those
  integrations while PPT Maker prioritizes its own read-only viewer links.
- Layout, font, palette, icon, illustration, and style-token guidance may come
  from the approved asset system only through safe manifests and entitlement
  checks.
- The workbench must support text style roles for `Title`, `H1`, `H2`, `H3`,
  `Body`, `Caption`, and `Bullet`, with role defaults supplied by local docs,
  server manifest, or approved asset-system design package.
- Bullet behavior must be represented as paragraph state, not only visible
  characters in a plain string.
- V2 object transform scope is bounded: box-based resize, multi-select
  align/distribute where claimed, shape/image fixed-step rotation and flip, and
  shape corner radius. Text box rotation and freeform rotation remain out of
  scope until direct editing is stable.
- SlideIR may remain internal infrastructure, but must not define the commercial
  editor experience unless it reaches benchmark-level expressiveness.

## Hard Blocks

Do not:

- build an embedded independent AI authoring chat in PPT Maker.
- add a third mode.
- hardcode the sample HTML/PPTX content.
- copy benchmark coordinates, image URLs, DOM, filenames, or the benchmark brand business
  content.
- use Python code to directly fabricate final sample-like user decks.
- claim export completion without a real host-AI result.
- continue SlideIR-only shell polish as the next user-facing slice.
- expose raw prompts, sources, local paths, raw filenames, external document identifiers, package
  internals, credentials, DB URLs, encoded asset assets, or private image URLs in
  public summaries or handoff envelopes.

## Commercial Stack Boundary

The stack direction remains:

- Cloudflare gateway.
- Supabase Postgres.
- Vercel dashboard/admin.

Production-oriented targets:

- Supabase project: `slides-maker-prod`, ref `tnbjlydrneugaouirtnq`, region
  Northeast Asia (Seoul).
- Public landing domain: `slides-maker.kkumjangi.com`.
- Product app domain: `app.slides-maker.kkumjangi.com`.
- Gateway domain: `api.slides-maker.kkumjangi.com`.
- Domain family: `kkumjangi.com`. Do not use `soolomon.com` for this product.

Not attached in this slice:

- payment.
- hosted generation.
- production asset retrieval.
- broad first-party cloud-drive file management.
- server-side original-deck ingestion for reference design extraction.

Deployment and remote mutation may be performed only when the user explicitly
approves that work unit. Once approved, the worker may directly configure
Vercel, Supabase, and Cloudflare using available CLI/API credentials, while
preserving public/private boundaries and secret hygiene.

Asset-system access remains Leader-only. Starter and Manager remain blocked
from approved package requests and consumption. PPT Maker may internalize
already-approved asset-system results into its own design-package/library model,
but must not import raw reference holdings, assetization workflow internals,
approval logs, or external workspace paths.

Supabase baseline for the new production-oriented project:

- Data API enabled.
- automatic RLS enabled.
- automatic exposure of new tables disabled or treated as a pre-launch blocker.
- Google OAuth enabled before real signup is claimed.
- protected commercial tables require explicit grants/RLS review.
- service role remains server/gateway-only.

Vercel and Cloudflare role boundary:

- Vercel hosts landing, app shell, account dashboard, and workbench UI.
- Cloudflare handles trusted API/gateway behavior, CORS, rate limits,
  entitlement checks, free-tier credit and paid fair-use guards, asset/design
  package preflight, referral mediation, export-handoff mediation, and Supabase
  service-role protection.
- Supabase owns Auth, account/membership/entitlement/deck-run data, RLS,
  referral records, Reference Design Library metadata, Style Memory profiles,
  published-view records, and free-tier credit ledgers.

## Initial Plan Boundary

Launch should prefer one free plan plus one paid plan. A second paid plan is
deferred until product usage shows a clear need, because multiple paid tiers
increase entitlement logic, support, QA, landing copy, and billing operations.

Free plan:

- limited credits for guided generation/advanced mediation.
- referral-earned credits after activation events, not raw signup alone.
- visible editor preview and enough surface to understand value, but full
  practical editor use may be paid-gated.
- view-only share links may carry watermark or attribution.
- limited or preview-only Reference Design Library and Style Memory.

Paid plan:

- no visible per-edit credit accounting for normal paid workflows.
- internal fair-use/abuse controls remain allowed.
- full practical HTML editor, Style Memory, useful Reference Design Library
  capacity, watermark-free viewer sharing, local/approved asset library, and
  approved design packages where entitled.
- no claim that PPT Maker provides better host-AI models, larger host-AI
  context, or priority host-AI compute; those belong to the user's host AI.

Team collaboration, multi-seat shared workspaces, broad cloud-drive sync, and
native collaborative editing are deferred. The near-term sharing primitive is
the published read-only HTML canvas viewer.

## Acceptance For Direction

A slice satisfies this boundary only if it visibly advances a user-facing HTML
workbench or honest export-hook flow. Validator-only or proof-only work is not
sufficient unless it removes a named blocker for those surfaces.

For the next one-piece work unit, acceptance also requires install/CLI/MCP
readiness evidence:

- landing page and signup plan reflect `slides-maker.kkumjangi.com` and Google
  OAuth.
- initial entitlement copy reflects Free plus one Paid plan, with free credits
  and referral scaffolding but no paid per-edit credit UX.
- Reference Design Library, Style Memory, and published viewer sharing are
  either implemented or explicitly blocked with next actions.
- Vercel, Cloudflare, and Supabase setup status is verified and reported
  honestly.
- tracked instructions or commands open the HTML workbench.
- Assistant is the default path and Auto is the only alternate path.
- PDF/PPTX export produces sanitized host-AI handoff envelopes.
- CLI/MCP-facing contracts describe the same capabilities.
- intermediate reports and a tracked work-log Workthrough section are written.
- final report records branch, remote divergence, evidence paths, residual
  blockers, and commit/push status.

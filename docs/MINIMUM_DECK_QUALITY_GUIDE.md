# Minimum Deck Quality Guide

Date: 2026-04-22

This guide defines the minimum human-visible quality floor for delivery-quality PPT generation. It exists because operational validation can pass while a first draft still feels visually weak to a human reviewer.

The guide is a durable system contract, not a hidden prompt. Codex, Claude, Antigravity, other agents, and human operators should be able to apply the same checklist before sending a deck to Drive or Slack.

## Scope

This guide applies when a user asks for a deliverable PowerPoint deck or when a generated deck may be shared outside the local debugging loop.

It does not apply when the user explicitly asks for:

- a quick draft
- a raw experiment
- a template smoke test
- a diagnostic build where visual polish is not the goal

Even in quick-draft mode, the system should not deliver files with broken package structure, blank slides, missing required text, or obvious placeholder residue.

## Design Judgment Model

Design judgment should be explainable and reviewable. The preferred path is Codex/self-review based on rendered previews, deck reports, and this checklist.

Do not introduce opaque LLM-judge automation as the primary design decision path. Optional LLM assistance may summarize or suggest improvements later, but final quality decisions must remain grounded in:

- rendered slide previews
- deterministic validation reports
- template metadata
- slot maps
- selection rationale
- human-readable self-review notes

## Two-Pass Delivery Rule

For delivery-quality PPT generation, the first build should receive at least two review/improvement passes unless the user explicitly asks for a quick draft.

The expected flow is:

1. Build the initial deck from the spec.
2. Render or inspect previews and reports.
3. Write a first self-review note listing visible quality defects and safe improvements.
4. Apply improvements that do not violate template-first rules.
5. Render or inspect the revised deck.
6. Write a second self-review note with the final delivery decision.
7. Deliver only if blockers are resolved or explicitly accepted by the user.

Safe improvements include:

- shortening text to fit verified slots
- selecting a less dense production template
- improving title/subtitle hierarchy through available slots
- replacing placeholder-like text
- removing empty optional content from unfilled slots
- using approved font/theme defaults
- avoiding repetitive dense slides when a better production alternative exists

Unsafe improvements include:

- drawing ad hoc slide chrome with Python coordinates
- making raw, generated, or candidate references production-selectable
- stretching a 16:9 template into 4:3 or 9:16 output
- hard-coding local external asset paths into tracked specs or config
- using brand assets without explicit user request and guideline review

## Minimum Visual Quality Checks

Before delivery, review the deck against these checks.

### Typography

- Korean decks should use `맑은 고딕`, `Pretendard`, or another approved Korean-capable fallback.
- Title and H1 text should be visibly larger than body text.
- Titles should usually be bold when the template supports it.
- Body text should remain readable in rendered previews.
- Avoid mixing many font families inside the same deck unless the template already defines that system.

### Layout And Hierarchy

- Every slide should have a clear primary focal point.
- Do not leave large empty template slots that read as broken layout.
- Do not crowd small number, label, or footer slots with sentence-length text.
- Avoid repetitive dense/text-heavy slides when the selector has a viable lighter alternative.
- Preserve template alignment and spacing instead of drawing replacement layouts.

### Content Fit

- No important text should be clipped, cut off mid-word, or hidden behind other objects.
- Long Korean text should be reviewed with weighted CJK text budgets.
- If deterministic cutoff occurs, the self-review should confirm that the shortened text still communicates the intended point.
- Speaker-note style details should not be forced into small slide body slots.

### Placeholder And Residue Cleanup

- No visible placeholder text should remain, including instructions such as "write the detailed".
- Unfilled optional slots should be cleared when the spec asks for cleanup.
- Template helper labels, debug labels, or candidate metadata should not appear in the delivered deck.

### Template Eligibility

- Use production templates and finalized library metadata only.
- Templates marked `curate_before_use` may inform review, but should not become unattended delivery choices until explicitly cleared.
- Raw references, generated references, and candidate slides must remain review inputs only.

### Asset Eligibility

- Built-in template assets are allowed when they are already part of production templates.
- External asset use must be registry-first, active-status, policy-checked, and stored by durable asset IDs or copied approved assets, not by raw local path guesses.
- Brand assets require explicit user request and official guideline review.

## Must Block Delivery Now

Block delivery, fix first, or ask the user to explicitly accept the risk when any of these are present:

- generated PPTX fails package validation
- rendered slide is blank or missing expected text
- visible placeholder residue remains
- required title or main content is missing
- important text is visibly clipped or unreadable
- non-production raw/candidate reference source is selected as a production template
- external asset path is hard-coded into tracked runtime config
- user-requested Slack/Drive delivery evidence is missing

## Can Improve In Phase 5

These should be improved through Phase 5, but do not automatically block B22 unless they create obvious delivery failure:

- richer visual recommendation UI
- automated render-review-revise-rerender loop
- complete typography, palette, icon, and image intelligence
- dynamic chart/table rendering
- industry-specific story grammar
- aspect-aware 4:3 or 9:16 production support
- deeper reference-to-template generation

## Self-Review Report Template

Use this structure in a deck project report, work log, or Slack-ready completion note:

```text
Deck:
Build:
Review pass:

Visual strengths:
- 

Defects found:
- 

Changes made:
- 

Remaining accepted caveats:
- 

Delivery decision:
```

For B24 and later automation, this template can become the durable self-correction report structure.

## Validation Surface

Use existing reports first:

- `outputs/reports/*_design_review.json`
- `outputs/reports/*_design_review.md`
- `outputs/reports/*_deck_slot_map.json`
- `outputs/reports/*_slide_selection_rationale.json`
- `outputs/reports/template_text_readback_diagnostics.json`
- `outputs/reports/visual_baseline_drift.json`

Recommended commands:

```powershell
python scripts/build_deck.py data/specs/template_slide_sample_spec.json
python scripts/validate_deck_design_review.py --gate-config config/deck_design_review_gate.json --enforce-gate-config
python scripts/run_regression_gate.py
```

For docs-only B22 changes, focused document review plus `git diff --check` is sufficient. Code or runtime config changes still require focused validation, the full regression gate when meaningful, and `graphify update .`.

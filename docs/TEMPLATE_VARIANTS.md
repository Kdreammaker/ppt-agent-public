# Template Variants

This workspace uses a slide-library approach instead of a single slide-master template. Each curated library PPTX remains source-specific, and the unified selector works through `config/reference_catalog.json`.

## How to Pick Slides
- Human flow: browse `outputs/previews/template_index/INDEX.md` and each library contact sheet.
- System flow: use `slide_selector` in deck specs with `purpose`, `scope`, `preferred_variant`, `fallback_variants`, `required_tags`, and optional quality filters.
- Matching order: exact `purpose` -> exact `scope` -> `generic` scope fallback -> `preferred_variant` -> `design_tier` -> `quality_score` -> `default_rank`.
- Quality filters: use `min_quality_score` and `usage_policies=["production_ready"]` when visual finish matters more than structural compatibility.

## Core Purpose Groups
- `cover`
  - `cover/right-hero`: generic corporate opener from the primary library.
  - `cover/narrative-sales`: sales-first opener for partner proposals.
  - `cover/finance-sales`: finance and AI sales opener.
  - `cover/portfolio`: personal and portfolio opener.
- `toc`
  - `toc/simple-index`: minimal index slide with a compact list.
  - `toc/visual-tiles`: visual four-block table of contents.
- `summary`
  - `summary/two-panel`: balanced report summary for meetings and briefs.
  - `summary/4up-message-grid`: compact message grid for recommendation summaries.
  - `summary/service-intro-cards`: service summary with card emphasis.
  - `summary/service-components`: summary for offering components or product scope.
- `issue`
  - `issue/2x2-cards`: reusable issue or risk framing.
  - `issue/pain-story`: sales-oriented pain narrative.
- `strategy`
  - `strategy/quadrant`: choice framing or positioning.
  - `strategy/checkpoint-flow`: phased plan with checkpoints.
  - `strategy/4-step-solution`: staged recommendation flow.
  - `strategy/sales-step-story`: sales motion or rollout steps.
- `timeline`
  - `timeline/horizontal-roadmap`: generic roadmap.
  - `timeline/company-history`: company history and milestone use.
- `analysis`
  - `analysis/competition-matrix`: competitive analysis.
  - `analysis/prioritization-metric`: weighted prioritization.
  - `analysis/before-after`: transformation or comparison.
  - `analysis/project-case-*`: portfolio case-study variants.
- `chart`
  - `chart/financial-timeline`: financial history chart slide.
  - `chart/financial-mix`: mix or composition chart slide.
  - `chart/proof-metrics`: proof-point metrics slide.
- `closing`
  - `closing/goal-grid`: generic close or next-step grid.
  - `closing/discussion-next-step`: discussion-driven sales close.
  - `closing/finance-cta`: finance sales CTA.
  - `closing/portfolio-thank-you`: portfolio close.

## Recommended Defaults
- General business report: `scope=report` with generic fallback enabled.
- Sales proposal: `scope=sales`, then let generic `toc`, `summary`, and `issue` slides fill missing purposes.
- Portfolio deck: `scope=portfolio` for cover and case slides, with generic fallback for report-style structure slides.
- Data-heavy or market report: prefer `template_library_02_v1` candidates with `min_quality_score>=4.0`.
- Case-study or proof deck: prefer `template_library_03_v1` candidates with `usage_policies=["production_ready"]`.
- Structure-only internal deck: allow `template_library_04_v1`, but use custom layout builders rather than raw overlay replacement.

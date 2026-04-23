# Responsive Blueprint Contract

Date: 2026-04-22

This document records the B28 design contract for future aspect-aware PPT rendering.

## Current Policy

Production generation remains `16:9` only. Requests for `4:3` still fail fast with the existing message in `scripts/build_deck.py`.

B28 does not enable `4:3` or `9:16` output. It defines the migration contract and adds diagnostics so future work can decide when dedicated aspect assets are ready.

## Why Stretching Is Not Allowed

The current template blueprints store many slide positions as absolute inches. Stretching those coordinates to a different canvas can break:

- composition and reading order
- text fit and font hierarchy
- image crop intent
- header, footer, and page-number placement
- visual smoke and drift baselines

Aspect support must come from dedicated templates and aspect-specific blueprints, not automatic resizing of current `16:9` decks.

## Proposed Schema Shape

Future responsive blueprint records should keep the current inch-based `bounds` for 16:9 compatibility and add explicit aspect-aware geometry:

```json
{
  "slot": "title",
  "bounds": {"left": 0.75, "top": 0.62, "width": 7.5, "height": 0.82},
  "responsive_bounds": {
    "source_aspect": "16:9",
    "normalized": {"left_pct": 0.05625, "top_pct": 0.08267, "width_pct": 0.5625, "height_pct": 0.10933},
    "targets": {
      "4:3": {"left": 0.62, "top": 0.58, "width": 6.4, "height": 0.82},
      "9:16": {"left": 0.32, "top": 0.7, "width": 3.55, "height": 1.1}
    },
    "safe_zone": "hero_text",
    "font_scale": {"4:3": 0.92, "9:16": 0.78},
    "fit_policy": "aspect_specific_review_required"
  }
}
```

The `targets` values must be reviewed or generated from dedicated target-aspect templates. They should not be accepted purely because a normalized conversion is mathematically possible.

## Required Runtime Gates

Before any non-16:9 output is production-enabled:

- `DeckSpec.aspect_ratio` must select only templates whose metadata declares the same aspect.
- `config/template_blueprints.json` or its sharded files must include aspect-specific bounds for every editable slot and zone used by that aspect.
- `scripts/inspect_template_aspect_ratios.py` must show dedicated template libraries for the target aspect.
- `scripts/analyze_responsive_blueprint_readiness.py` must report no unresolved migration blockers for the selected library.
- Visual smoke, package validation, design-quality review, and visual drift baselines must run per aspect.
- The full regression gate must keep `16:9` behavior unchanged.

## B28 Diagnostic Report

Run:

```powershell
python scripts/analyze_responsive_blueprint_readiness.py
```

The report writes:

- `outputs/reports/responsive_blueprint_readiness.json`
- `outputs/reports/responsive_blueprint_readiness.md`

The current diagnostic inspects absolute-inch blueprint fields and produces a prototype normalized conversion preview for one template. This is diagnostic-only and does not authorize production aspect conversion.

## Migration Requirements

Real `4:3` support requires:

- curated `4:3` source PPTX libraries
- `4:3` template blueprints generated from those libraries
- aspect-aware template selection and rationale fields
- dedicated visual smoke previews and drift baselines
- at least one production-quality `4:3` sample deck

Real `9:16` support requires the same, plus mobile/vertical typography and density rules. It should be treated as a separate product decision, not a side effect of `4:3` work.

## Explicit Non-Goals

- Do not stretch or crop existing `16:9` templates into production `4:3` or `9:16`.
- Do not silently reinterpret existing inch coordinates as relative coordinates.
- Do not weaken the current `4:3` fail-fast behavior.
- Do not copy or mutate external asset-system files to fill aspect-specific template gaps unless a future human-approved bundle delegates that work.

# Template Design DNA

`config/template_design_dna.json` adds selection metadata on top of the curated template catalog. It is generated from `config/reference_catalog.json` and `config/template_blueprints.json`, then corrected by optional human-curated overrides from `config/template_design_dna_overrides.json`.

The metadata helps agents and humans explain template fit without editing template geometry or changing generated deck output.

## Fields

- `density`: inherited density signal from the reference catalog.
- `tone`: editorial fit such as executive, analytical, sales, technical, or portfolio.
- `structure`: story, grid, metric, process, timeline, or comparison.
- `visual_weight`: text-heavy, balanced, or visual-first.
- `content_capacity`: editable text, image, and chart slot counts plus estimated text budget.
- `footer_supported`: whether the selected blueprint exposes `footer_note`.
- `best_for`: short fit notes for template selection.
- `avoid_for`: short caution notes for poor-fit use cases.
- `review_notes`: optional human review note, usually added through overrides.
- `override_applied`: whether a generated record received a curated override.

## Future Sequence Roles

Future metadata may add `story_roles` to describe where a template fits in a deck-level narrative arc:

```json
{
  "story_roles": [
    "opener",
    "context_setter",
    "deep_dive_data",
    "breather",
    "summary",
    "closer"
  ]
}
```

This is a direction only. Selector scoring must not depend on `story_roles` until the labels have been reviewed against real decks and design review warnings.

## Build Command

```powershell
python scripts/build_template_design_dna.py
```

The deck builder reads this file when present and includes the DNA fields in slide selection rationale reports.

Validate Design DNA and overrides:

```powershell
python scripts/validate_template_design_dna.py
```

## Override Layer

`config/template_design_dna_overrides.json` is the curated correction layer. It is keyed by stable `slide_id` and merged after generated fields are computed.

Supported override fields:

- `density`
- `tone`
- `structure`
- `visual_weight`
- `content_capacity`
- `footer_supported`
- `best_for`
- `avoid_for`
- `review_notes`

Unknown slide ids or unsupported fields fail validation. This keeps `config/template_design_dna.json` generated and deterministic while still allowing human design judgment to correct heuristic metadata.

Example:

```json
{
  "version": "1.0",
  "slides": {
    "template_library_04_v1.cover_brand_right_v1": {
      "tone": ["executive", "conservative"],
      "best_for": ["formal executive report opening"],
      "avoid_for": ["high-emotion sales pitch"],
      "review_notes": "Use when clarity and restraint matter more than visual novelty."
    }
  }
}
```

## Boundaries

- Do not use Design DNA to draw new slide chrome.
- Do not change template geometry for this metadata layer.
- Do not make selector scoring depend on these fields until the metadata has been reviewed across clean regression runs.

# Industry-Aware Spec Composer

Date: 2026-04-22

This document records the B27 contract for industry-aware intake-to-spec generation.

## Purpose

`scripts/compose_deck_spec_from_intake.py` now treats `deck_type` as only one input to story planning. The composer also reads `industry`, tone, audience, and the durable taxonomy at `config/industry_storyline_taxonomy.json`.

The goal is not to make every industry perfect in one pass. The B27 floor is that different industries get different deterministic storyline grammar, template families, and selector guardrails before optional intelligence is added later.

## Taxonomy Contract

Each industry profile can define:

- `preferred_scope`: fallback template scope when intake does not specify one.
- `template_sequence`: production template keys used for deterministic first drafts.
- `purpose_sequence`: slide purpose rhythm.
- `storyline_roles`: semantic roles used for tags and future asset queries.
- `selector_defaults`: production-safe selector guardrails.
- `clear_unfilled_image_slots_without_assets`: whether stale template sample images should be removed when no source images are available.
- `residual_text_patterns`: fixed template text fragments to remove when templates carry non-generic sample copy.

Supported first profiles are `business`, `travel`, `food_and_beverage`, `healthcare`, `entertainment`, `exhibition`, `technology`, `finance`, and `other`.

## Runtime Behavior

When an intake has no explicit `brand_or_template_scope.preferred_template_keys`, the composer uses the industry profile sequence. Generated specs include `recipe: industry:<name>` so downstream reports can distinguish the composer path.

When a profile sets `clear_unfilled_image_slots_without_assets=true` and the intake has no discovered image assets, generated slides set `clear_unfilled_image_slots=true`. The renderer then removes unfilled named image placeholders instead of preserving misleading sample imagery from the source template.

The composer also fills common portfolio and case-study slot names such as `name`, `tag_1`, `case_number`, `period`, `role`, `outcome_*`, `capability_*`, and `text_*`.

## Current Samples

- `data/intake/business_growth_review.json`
- `data/intake/travel_experience_plan.json`
- `data/specs/business_growth_review_spec.json`
- `data/specs/travel_experience_plan_spec.json`

The B27 regression test `scripts/test_industry_spec_composer.py` asserts that business and travel produce different recipes and template sequences.

## Known Boundaries

Some legacy template text is not yet fully modeled as editable design DNA. B27 removes the most misleading template image artifacts and profile-level fixed text, but complete visual improvement belongs to later Phase 5 review and template-DNA work.

Do not make raw/generated/candidate references production-selectable to improve industry coverage. Only finalized template or library metadata may influence runtime selection.

Do not connect to the external asset workspace as a mutating actor in B27. The external asset-system integration boundary remains read-only planning until explicit delegation is granted.

## Validation

```powershell
python scripts/validate_deck_intake.py
python scripts/test_industry_spec_composer.py
python scripts/compose_deck_spec_from_intake.py data/intake/business_growth_review.json
python scripts/compose_deck_spec_from_intake.py data/intake/travel_experience_plan.json
python scripts/build_deck.py data/specs/business_growth_review_spec.json
python scripts/build_deck.py data/specs/travel_experience_plan_spec.json
python scripts/run_regression_gate.py
graphify update .
```

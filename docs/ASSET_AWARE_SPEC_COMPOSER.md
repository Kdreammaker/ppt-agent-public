# Asset-Aware Spec Composer

Date: 2026-04-22

B31 connects the industry-aware composer to the B25 PPT asset catalog without copying binaries, uploading local files, or mutating the external asset workspace.

## Contract

Composer output may include top-level `asset_intents`. These are metadata recommendations, not rendered assets.

Each intent records:

- `industry`, `tone`, `purpose`, `slot`, and `aspect_ratio`
- `role`: `image_placeholder`, `icon`, `chart_preset`, `palette`, `typography`, or `theme`
- `asset_id` and `asset_class` from `config/ppt_asset_catalog.json`
- `source_policy`: `finalized_catalog`, `local_user_asset_policy`, or `external_registry_reference`
- `materialization`: whether the item is metadata-only, local config/code, or requires later runtime materialization
- `license_action` and `risk_level`
- a `query` object that records why the composer selected or requested the asset

## Current Behavior

The composer reads only finalized catalog metadata from `config/ppt_asset_catalog.json`. It filters for assets with:

- `production_eligible: true`
- `allowed_for_ppt: true`
- low or medium risk for icon recommendations
- approved source policies

For the B31 samples:

- Business drafts receive neutral-modern theme, palette, typography, dashboard/report icon metadata, simple bar-chart preset, and user-supplied/generated image placeholder policy.
- Travel drafts receive blue-green theme, palette, typography, calendar/route-friendly icon metadata, simple bar-chart preset, and user-supplied/generated image placeholder policy.

Image placeholders use `image_policy.user_supplied_or_generated`. This records the need for a hero/photo/thumbnail slot without scanning raw folders or copying image binaries.

External icons remain `external_registry_reference` metadata. B31 does not materialize those files into PPTX output.

## Guardrails

- Do not scan raw external folders as the source of truth.
- Do not hard-code absolute paths to `C:\Users\kimjo\Downloads\assets achivement for work`.
- Do not copy external asset binaries during composer work.
- Do not use assets that are not present in the finalized catalog.
- Do not use assets with `production_eligible: false` or `allowed_for_ppt: false`.
- Keep local user assets opt-in; image intent is allowed, but file use requires a later consented step.

## Validation

```powershell
python scripts/build_ppt_asset_catalog.py
python scripts/validate_ppt_asset_catalog.py
python scripts/validate_asset_aware_composer.py
python scripts/test_industry_spec_composer.py
python scripts/run_regression_gate.py
```

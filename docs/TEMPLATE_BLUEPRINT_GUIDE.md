# Template Blueprint Guide

`config/template_blueprints.json` is the fillable layer that sits on top of curated library slides. The authoritative visual assets remain in `assets/slides/templates/decks/*.pptx`, while the blueprint describes what can be edited safely.

`config/template_design_dna.json` stores selection metadata derived from the reference catalog and blueprints. It describes tone, structure, visual weight, capacity, and footer support without changing template geometry.

For the current migration checkpoint, remaining work, and recommended next bundles, see [TEMPLATE_FIRST_ROADMAP.md](<docs/TEMPLATE_FIRST_ROADMAP.md>).

For the next post-CTO execution bundles, see [TEMPLATE_FIRST_NEXT_EXECUTION_PLAN.md](<docs/TEMPLATE_FIRST_NEXT_EXECUTION_PLAN.md>).

## Blueprint Model
- `slide_id`
  - Stable identifier in the form `library_id.template_key`.
- `preserve_shapes`
  - Shape indices that should survive when a slide is patched in place.
- `remove_shapes`
  - Shape indices that should be removed before text or images are applied.
- `editable_text_slots`
  - Named text targets with shape identity, bounds, fingerprint, font role, line rules, and protected tokens.
- `editable_image_slots`
  - Picture targets with shape identity and bounds.
- `editable_chart_slots`
  - Reserved chart zones. Current builder supports simple bar-chart injection.
- `editable_table_slots`
  - Reserved table zones. Current builder supports rectangular text tables with optional headers.
- `overlay_safe_zones`
  - Reserved areas for adding content without disturbing existing structure.
- `header_zone`, `footer_zone`, `page_zone`
  - Common positions for section header, footer bar, and page number.
- `text_rules`
  - Wrap language, protected tokens, section number mode, and page number mode.

## Editing Strategy
- `mode=patch`
  - Prefer editing in-place on top of existing shapes.
- `mode=overlay`
  - Keep complex group objects intact and overlay new text or image content in safe zones.

## Deck Spec Usage
- Direct template selection:
  - Use `template_key` to pick one slide by key.
- Purpose-based selection:
  - Use `slide_selector` with `purpose`, `scope`, and optional variant preferences.
- Blueprint-driven content fill:
  - Prefer `layout: "template_slide"` for new production specs.
  - Existing `layout: "blueprint_overlay"` specs remain supported as a compatibility alias.
  - Use `text_slots` for named slot fills.
  - Avoid positional `text_values` for new specs; it is a legacy convenience path that depends on blueprint slot order.
  - Use `text_values` only for temporary smoke fixtures, then migrate stable samples to explicit `text_slots`.
  - Use `image_slots`, `chart_slots`, and `table_slots` for visual replacements.

## Slot Target Resolution
- New authoring should name template shapes with `slot:<slot_name>` whenever possible.
- Placeholder text may also include a token such as `{{title}}` or `{{hero_image}}`.
- Existing library blueprints may keep `shape_index`, `shape_name`, and `fingerprint` for compatibility.
- Runtime resolution uses this policy:
  - First use `shape_index` when it still points to the expected text or image shape and matches the recorded identity.
  - If the index is stale, fall back to `shape_name`, then `{{slot}}` token, then `fingerprint`, then bounds.
  - Ambiguous or missing matches fail with the `slide_id` and slot name so the template can be repaired.
- Treat `shape_index` as a compatibility key, not the primary key for new production templates.
- Use `scripts/manage_template_slot_names.py --slide-id <id> --slots <slot...>` to audit individual slots before applying names.
- Use `--apply` only for intentionally selected slides; avoid whole-library rename passes until the audit is clean.
- Use the full audit report command before planning a rename batch:
  - `python scripts/manage_template_slot_names.py --output-json outputs/reports/template_slot_name_audit.json --output-md outputs/reports/template_slot_name_audit.md --summary`
- Preserve applied slot names across curated library rebuilds with the manifest:
  - `python scripts/manage_template_slot_names.py --write-manifest config/template_slot_name_manifest.json`
  - `python scripts/manage_template_slot_names.py --manifest config/template_slot_name_manifest.json --apply-manifest`

## Maintenance Workflow
Only promote templates through this explicit workflow. Raw decks under `assets/slides/references` are not a runtime template library, and adding a PPTX there must not affect deck selection by itself.

1. Update `config/template_library_catalog.json`.
2. Rebuild curated libraries with `scripts/build_template_libraries.py --apply-slot-name-manifest`.
3. Rebuild metadata with `scripts/build_reference_catalog.py`.
4. Rebuild Design DNA metadata with `scripts/build_template_design_dna.py`.
5. Audit or apply stable slot names with `scripts/manage_template_slot_names.py`.
6. Render previews with `scripts/render_template_thumbnails.py`.
7. Validate with `scripts/validate_template_blueprints.py`.
8. Validate generated PPTX package integrity with `scripts/validate_pptx_package.py`.
9. Run rendered visual smoke checks with `scripts/validate_visual_smoke.py`.
10. Run informational visual baseline drift checks with `scripts/validate_visual_drift.py`.

Recommended rebuild-safe sequence:

```powershell
python scripts/build_template_libraries.py --apply-slot-name-manifest
python scripts/build_reference_catalog.py
python scripts/build_template_design_dna.py
python scripts/validate_template_blueprints.py
python scripts/manage_template_slot_names.py --output-json outputs/reports/template_slot_name_audit.json --output-md outputs/reports/template_slot_name_audit.md --summary
```

Recommended visual smoke command for a single template deck:

```powershell
python scripts/validate_visual_smoke.py outputs/decks/template_slide_sample_system.pptx outputs/reports/template_slide_sample_visual_smoke.json --spec data/specs/template_slide_sample_spec.json --keep-images
```

For full regression, run the same command across the four core decks and five template/sample decks, writing one `*_visual_smoke.json` report per deck under `outputs/reports/`.

Recommended visual baseline drift commands:

```powershell
python scripts/validate_visual_drift.py --init-baseline
python scripts/validate_visual_drift.py
```

The baseline images live under `outputs/baselines/visual_drift/`. The drift report is informational in the current workflow and is written to `outputs/reports/visual_baseline_drift.json` and `outputs/reports/visual_baseline_drift.md`.

When visual smoke reports `major_text_missing` warnings, generate the text readback diagnostic report:

```powershell
python scripts/diagnose_template_text_readback.py --output-json outputs/reports/template_text_readback_diagnostics.json --output-md outputs/reports/template_text_readback_diagnostics.md
```

Use `likely_unmapped_slot` rows to prioritize blueprint override fixes. Use `sequential_text_values_risk` rows to decide whether a sample spec should move from positional `text_values` to explicit `text_slots`. The current regression sample set has been cleaned so diagnostics should report no problem rows.

## Current Defaults
- Page numbers render only in the bottom-right zone.
- Section numbers are treated as header content, not page numbers.
- Template slots preserve template text-frame settings by default.
- Slot-level `fit_strategy` controls text fitting:
  - `preserve_template`: replace text without forcing code-side wrapping.
  - `shrink`: enable PowerPoint shrink-to-fit for that placeholder.
  - `manual_wrap`: use `max_chars_per_line` as a fallback only when explicitly requested.

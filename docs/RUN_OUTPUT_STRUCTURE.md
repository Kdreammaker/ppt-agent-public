# Run Output Structure

Date: 2026-04-19

## Purpose

The current system writes compatibility outputs to flat folders:

```text
outputs/decks/
outputs/reports/
```

Those paths are stable and must continue to work for the current regression gate, ad hoc scripts, and downstream operators.

For production authoring, the system now supports two scopes:

- **Run scope**: execution-oriented records for automation, validation, and CI traceability.
- **Project scope**: writer-facing bundles where a deck author can find the deck, design brief, assets, previews, and reports in one place.

## Target Structure

```text
outputs/
  projects/
    <project_id>/
      README.md
      project_manifest.json
      deck/
      docs/
      assets/
        images/
      specs/
      reports/
      previews/
      exports/
  runs/
    <run_id>/
      decks/
      reports/
      specs/
      previews/
  decks/
    latest compatibility decks
  reports/
    latest compatibility reports
```

Recommended `run_id` format:

```text
YYYYMMDD-HHMMSS-<deck_slug>
```

Example:

```text
outputs/runs/20260419-143000-ai-automation-exec-briefing/
```

Recommended `project_id` format:

```text
<deck_slug>
```

Example:

```text
outputs/projects/korea_q2_seasonal_seafood_guide_v2/
```

## Directory Roles

- `outputs/runs/<run_id>/decks/`: PPTX files produced during one authoring run.
- `outputs/runs/<run_id>/reports/`: run-specific rationale, slot map, overflow, visual smoke, design quality, design review, and audit reports.
- `outputs/runs/<run_id>/specs/`: the exact spec used for the run, including report-informed revisions.
- `outputs/runs/<run_id>/previews/`: rendered slide images or visual smoke images used during review.
- `outputs/projects/<project_id>/deck/`: writer-facing final PPTX file.
- `outputs/projects/<project_id>/docs/`: design brief, content brief, and other authoring notes.
- `outputs/projects/<project_id>/assets/images/`: image assets referenced by the spec.
- `outputs/projects/<project_id>/specs/`: source spec used to generate the deck.
- `outputs/projects/<project_id>/reports/`: validation and authoring reports.
- `outputs/projects/<project_id>/previews/`: rendered slide images and PDFs used for review.
- `outputs/projects/<project_id>/exports/`: optional downstream exports.
- `outputs/decks/`: latest compatibility deck outputs for existing scripts and users.
- `outputs/reports/`: latest compatibility report outputs for existing scripts, CI artifact upload, and regression checks.

## Compatibility Policy

The first migration pass must preserve current paths.

Deck builders may later copy or mirror outputs into `outputs/runs/<run_id>/...`, but they should still write the existing compatibility files until every consumer has moved to run-scoped paths.

Existing compatibility outputs include:

- `outputs/decks/<deck_name>.pptx`
- `outputs/reports/<deck_name>_slide_selection_rationale.json`
- `outputs/reports/<deck_name>_slide_selection_rationale.md`
- `outputs/reports/<deck_name>_deck_slot_map.json`
- `outputs/reports/<deck_name>_deck_slot_map.md`
- `outputs/reports/<deck_name>_text_overflow.json`
- `outputs/reports/<deck_name>_text_overflow.md`
- `outputs/reports/<deck_name>_visual_smoke.json`
- `outputs/reports/<deck_name>_quality.json`

The latest aliases remain compatibility-only:

- `outputs/reports/slide_selection_rationale.json`
- `outputs/reports/slide_selection_rationale.md`
- `outputs/reports/deck_slot_map.json`
- `outputs/reports/deck_slot_map.md`

## Regression Runs

Regression gate outputs should continue to use compatibility paths because `scripts/run_regression_gate.py` asserts those files directly.

Regression reports should remain suitable for CI artifact upload from:

```text
outputs/reports/
```

Run-scoped regression folders can be added later, but only after the gate explicitly knows which run id it created and all report assertions read from that folder or a stable manifest.

## Ad Hoc Authoring Runs

Ad hoc production authoring should prefer project-scoped folders for human work and run-scoped folders for automation traceability.

Recommended command:

```powershell
python scripts/ppt_system.py build data/specs/example.json --validate --auto-project --auto-run-id
```

When `config/output_delivery_policy.json` is enabled, the wrapper also mirrors project-scoped output into the configured Google Drive Desktop workspace and writes a delivery manifest:

```text
outputs/projects/<project_id>/delivery_manifest.json
G:/My Drive/S_project/ppt-workspace-codex/projects/<project_id>/delivery_manifest.json
```

The Drive Desktop step copies files for private sync. Public editable link permissions are a separate explicit sharing action, so the default delivery manifest records `drive_desktop_sync` + `private` unless a human asks for a public link.

Use `--project-id <slug>` when a deck belongs to an existing client or content project.

Deck specs may also define:

- `project_id`
- `design_brief_path`
- `doc_paths`

Recommended run manifest fields:

- `schema_version`
- `run_id`
- `created_at`
- `source.input_spec_path`
- `source.output_deck_path`
- `bundle.run_root`
- `bundle.deck_path`
- `bundle.spec_path`
- `bundle.report_paths`
- `bundle.preview_paths`
- `validation_results`
- `known_caveats`

The manifest also keeps compatibility aliases for older consumers:

- `input_spec_path`
- `output_deck_path`
- `run_deck_path`
- `run_spec_path`
- `report_paths`

The manifest should be written as:

```text
outputs/runs/<run_id>/run_manifest.json
```

Validate a run manifest with:

```powershell
python scripts/validate_run_manifest.py outputs/runs/<run_id>/run_manifest.json
```

The project manifest is written as:

```text
outputs/projects/<project_id>/project_manifest.json
```

Project manifests follow the stable schema documented in `docs/PROJECT_MANIFEST.md` and use only `BASE_DIR`-relative POSIX paths.

## Project Versioning Policy

Project-scoped bundles are writer-facing latest bundles. Rebuilding the same `project_id` may overwrite the previous bundle in place.

Use run-scoped output under `outputs/runs/<run_id>/` when a durable historical execution record is needed. Use explicit project ids such as `client_pitch_v2` when the current workflow needs human-readable project version separation.

Future options such as `--project-version`, `--no-overwrite-project`, versioned deck subfolders, or a manifest `version` field should be added only after the current latest-bundle behavior is stable.

## Migration Steps

1. Keep all current compatibility outputs.
2. Add optional `run_id` support to deck-building or wrapper scripts.
3. Copy the input spec into `outputs/runs/<run_id>/specs/`.
4. Copy deck-specific reports into run-scoped reports while preserving compatibility report folders.
5. Copy visual smoke preview images into the run-scoped preview folder when validation produced previews.
6. Add a run manifest that records validation outputs and copied run-scoped artifacts.
7. Add optional project output support for writer-facing bundles.
8. Update docs and CI only after current regression assertions remain green.

## Non-Goals For This Pass

- Do not break `outputs/decks/` or `outputs/reports/`.
- Do not require the regression gate to use run folders yet.
- Do not move existing historical outputs.
- Do not treat latest alias files as durable run records.

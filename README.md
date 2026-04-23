# PPT Authoring System Workspace

This workspace is organized around a template-library-first PPT authoring workflow.

## Public-Thin Smoke Path

For a public-safe install/build smoke that does not require private template binaries, raw references, telemetry, upload, or gateway credentials:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts\ppt_cli_workspace.py init --workspace outputs\public_smoke_workspace --force-readme
python scripts\ppt_cli_workspace.py healthcheck --workspace outputs\public_smoke_workspace
python scripts\build_deck.py data\specs\public_smoke_blank_spec.json
```

Expected PPTX:

```text
outputs/decks/public_thin_smoke.pptx
```

Full template-library builds may require private template binaries that are intentionally excluded from the public-thin clean export.

## Main Folders
- `assets/slides/references`
  - Raw reference PPTX files only. Files here are not used directly by generation.
- `assets/slides/categorizing`
  - Ignored working area for split PNG/PPTX slide review: `png/{unlabeled,good_candidate,normal_candidate,weak_candidate}` and `pptx/{unlabeled,good_candidate,normal_candidate,weak_candidate}`.
- `assets/slides/library`
  - Classified reference slide records under `good`, `normal`, and `weak`.
- `assets/slides/templates`
  - Promoted/analyzed template assets used by production catalogs and blueprints.
- `config`
  - Theme files, catalogs, schemas, and blueprints.
- `data/specs`
  - JSON deck specs.
- `docs`
  - System guides and workflow notes.
- `scripts`
  - Builders, catalog generators, renderers, and validators.
- `system`
  - Shared Python utilities.
- `outputs/decks`
  - Generated PPTX decks.
- `outputs/projects`
  - Writer-facing project bundles with deck, docs, assets, previews, reports, and manifest.
- `outputs/previews/template_index`
  - Human-browsable preview images and contact sheets.

## Key Files
- `config/template_library_catalog.json`
  - Source-of-truth list for curated library builds.
- `config/reference_catalog.json`
  - Unified slide metadata for search and automatic selection.
- `config/template_blueprints.json`
  - Fillable slot definitions and header/footer/page zones.
- `config/deck_spec.schema.json`
  - JSON schema for deck specs.

## Main Scripts
- `scripts/build_template_libraries.py`
  - Builds promoted template deck files from curated source definitions.
- `scripts/build_reference_catalog.py`
  - Generates the unified reference catalog and template blueprints.
- `scripts/render_template_thumbnails.py`
  - Renders or synthesizes slide preview images and contact sheets.
- `scripts/validate_template_blueprints.py`
  - Verifies that catalogs and blueprints match real slide assets.
- `scripts/build_deck.py`
  - Builds final decks from JSON specs using either direct template keys or purpose-based selection.
- `scripts/ppt_system.py`
  - Operator-facing wrapper for intake validation, deck builds, validation, run-scoped output, and project-scoped output.
- `scripts/compose_deck_spec_from_intake.py`
  - Deterministically composes a draft deck spec from a validated intake JSON file.

## Suggested Workflow
1. Update `config/template_library_catalog.json`.
2. Run `build_template_libraries.py`.
3. Run `build_reference_catalog.py`.
4. Run `render_template_thumbnails.py`.
5. Run `validate_template_blueprints.py`.
6. Build a deck from a spec in `data/specs`.

To start from intake, compose the draft spec first:

```powershell
python scripts/ppt_system.py compose-spec data/intake/report_exec_briefing.json
```

For writer-facing output, prefer the wrapper:

```powershell
python scripts/ppt_system.py build data/specs/example.json --validate --auto-project
```

This preserves compatibility outputs under `outputs/decks/` and `outputs/reports/`, then mirrors the deck, spec, docs, referenced images, rendered previews, and reports into `outputs/projects/<project_id>/`.

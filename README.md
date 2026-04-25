# PPT Authoring System Workspace

This workspace is organized around a template-library-first PPT authoring workflow.

## Install A Ready Workspace

For a new public install, use one command. This creates `ppt-agent-public/` and a ready `workspace/` tree under the target:

```powershell
python scripts\ppt_install.py --target "<install-root>\ppt-maker"
```

If an AI agent has already cloned the public repo, run this from the repo root instead:

```powershell
python scripts\ppt_install.py --workspace "<install-root>\ppt-maker\workspace"
```

User files uploaded in chat or selected from disk should be imported into the workspace before use:

```powershell
python scripts\ppt_workspace_assets.py import --workspace "<workspace>" --file "<file>" --type image
python scripts\ppt_workspace_assets.py import --workspace "<workspace>" --file "<file>" --type font
python scripts\ppt_workspace_assets.py list --workspace "<workspace>"
python scripts\ppt_workspace_assets.py validate --workspace "<workspace>"
```

Workspace manifests live under `.ppt-agent/` and may contain local paths for that user's machine. Do not commit workspace contents, uploaded assets, private connector files, generated reports, Drive IDs, approval records, or raw private asset payloads.

## Public CLI And Private Runtime Path

This public repository is the installable CLI control plane. It installs runtime dependencies, initializes workspaces, runs public-safe smoke checks, and provides the connector that entitled users or operators use to install and call the private PPT runtime.

The private layer remains responsible for full template-library based high-quality PPT generation, private template binaries, private Design DNA, premium assets, real activation counters, revocation, rotation, audit, and signed private package or gateway responses. The public smoke deck is only a fallback and install check; the useful production flow is the private runtime build path.

Public-safe local smoke, requiring no private template binaries, raw references, telemetry, upload, or gateway credentials:

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

Full template-library builds require private capabilities that are intentionally excluded from the public clean export.

Private runtime connection, for entitled users/operators:

```powershell
python scripts\ppt_workspace_entitlement.py activate --workspace outputs\public_smoke_workspace --workspace-code <workspace-code>
python scripts\ppt_private_connector.py configure --workspace outputs\public_smoke_workspace --enable --private-package-repo-env PPT_AGENT_PRIVATE_PACKAGE_REPO --private-build-command-env PPT_AGENT_PRIVATE_BUILD_COMMAND_JSON
python scripts\ppt_private_connector.py status --workspace outputs\public_smoke_workspace --github-check
python scripts\ppt_private_connector.py install --workspace outputs\public_smoke_workspace
python scripts\ppt_private_connector.py build --workspace outputs\public_smoke_workspace --spec data\specs\business_growth_review_spec.json --execute
```

The connector writes local request summaries under `.ppt-agent/gateway_requests/`. It does not print tokens, store raw workspace codes, upload files, or include private templates in this repository. Real high-quality generation is performed by the private runtime command or gateway after entitlement, package access, and operator/user approval are in place.

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
- `scripts/compose_deck_plan_from_intake.py`
  - Creates a reviewable deck plan before slide content is written or rendered.
- `scripts/compose_deck_spec_from_plan.py`
  - Converts the approved or recorded deck plan into a deck spec with plan traceability.

## Suggested Workflow
1. Update `config/template_library_catalog.json`.
2. Run `build_template_libraries.py`.
3. Run `build_reference_catalog.py`.
4. Run `render_template_thumbnails.py`.
5. Run `validate_template_blueprints.py`.
6. Build a deck from a spec in `data/specs`.

To start from intake, compose the plan-first draft spec:

```powershell
python scripts/ppt_system.py compose-spec data/intake/report_exec_briefing.json
```

The compatibility path is still available when needed:

```powershell
python scripts/ppt_system.py compose-spec data/intake/report_exec_briefing.json --direct-intake
```

For writer-facing output, prefer the wrapper:

```powershell
python scripts/ppt_system.py build data/specs/example.json --validate --auto-project
```

This preserves compatibility outputs under `outputs/decks/` and `outputs/reports/`, then mirrors the deck, spec, docs, referenced images, rendered previews, and reports into `outputs/projects/<project_id>/`.

# Project Manifest

`project_manifest.json` is the stable machine-readable contract for a writer-facing project bundle under `outputs/projects/<project_id>/`.

The manifest is generated output. Do not commit generated manifests from `outputs/`; commit only the schema, validator, and source configuration that produce them.

## Schema

The canonical schema is:

```text
config/project_manifest.schema.json
```

Generated manifests use `schema_version: "1.0"` and store every path relative to the repository `BASE_DIR` with POSIX separators. Absolute local paths are intentionally excluded so project bundles can be inspected by agents, reviewers, and CI without depending on one developer machine.

## Shape

```json
{
  "schema_version": "1.0",
  "project_id": "template_slide_sample_system",
  "created_at": "2026-04-19T00:00:00Z",
  "source": {
    "input_spec_path": "data/specs/template_slide_sample_spec.json",
    "output_deck_path": "outputs/decks/template_slide_sample_system.pptx"
  },
  "bundle": {
    "project_root": "outputs/projects/template_slide_sample_system",
    "deck_path": "outputs/projects/template_slide_sample_system/deck/template_slide_sample_system.pptx",
    "spec_path": "outputs/projects/template_slide_sample_system/specs/template_slide_sample_spec.json",
    "doc_paths": [],
    "image_paths": [],
    "report_paths": [],
    "preview_paths": []
  },
  "validation_results": [],
  "known_caveats": []
}
```

## Validation

Build and validate a sample project bundle:

```powershell
python scripts/ppt_system.py build data/specs/template_slide_sample_spec.json --validate --auto-project
python scripts/validate_project_manifest.py outputs/projects/template_slide_sample_system/project_manifest.json
```

The validator checks the stable contract without requiring a third-party JSON Schema package.

## Overwrite Policy

Project bundles are writer-facing latest bundles. Rebuilding the same `project_id` may overwrite files in that project folder by default.

Use `outputs/runs/<run_id>/` for durable historical execution records. Use explicit project ids such as `client_pitch_v2` when a human-readable version split is needed today.

Future versioning options can include:

- `--project-version`
- `--no-overwrite-project`
- `deck/v1` and `deck/v2` bundle folders
- a manifest `version` field

Those options are intentionally deferred until the latest-bundle behavior has been exercised by real authoring workflows.

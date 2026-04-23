# CI and PR Regression Gate

This project uses `scripts/run_regression_gate.py` as the single local and CI gate for the template-first deck workflow.

## Local Gate

Run the full gate from the repository root:

```powershell
python scripts/run_regression_gate.py
```

The gate compiles core modules, validates template blueprints and Template Design DNA, builds regression decks, runs package checks, audits template slot names, verifies text readback, and checks visual smoke, design quality, design review, and drift reports.

The gate clears LLM summarization environment variables before running so the baseline remains deterministic even if a developer has local mock or provider settings configured.

## Pull Request Gate

The GitHub Actions workflow at `.github/workflows/regression-gate.yml` runs the same command on pull requests, pushes to `main` or `master`, and manual dispatches.

CI installs the Python dependencies from `requirements.txt` plus LibreOffice for PPTX-to-PDF rendering used by visual smoke checks. `scripts/validate_visual_smoke.py` resolves the renderer from `LIBREOFFICE_SOFFICE`, `PATH`, common Linux paths, or common Windows install paths.

The workflow uploads `outputs/reports/` as the `regression-reports` artifact on every run, including failed runs.

## Current Invariants

- Template slot audit: `ok=958`, `rename_available=0`, `manifest_count=958`
- Template Design DNA coverage: every reference catalog slide has metadata
- Template Design DNA overrides: strict validation rejects unknown slide ids and unsupported fields
- Text readback: `total_rows=174`, `present=174`
- Slide selection rationale reports: one deck-specific report per generated regression deck
- Deck slot map reports: one deck-specific report per generated regression deck
- Deck design review reports: aggregate plus deck-specific reports, with CI-blocking baseline thresholds from `config/deck_design_review_gate.json`
- Visual drift warning slides: `0`
- Text cutoff events: `9`

If a template library change intentionally adds or removes slot-bearing shapes, update the manifest, regenerate blueprints, and revise the invariant values in `scripts/run_regression_gate.py` in the same change.

## Failure Triage

- Blueprint validation failures usually mean a generated blueprint or override no longer matches the schema.
- Design DNA validation failures usually mean `config/template_design_dna_overrides.json` references an unknown `slide_id`, uses an unsupported field, or generated metadata no longer covers every reference catalog slide.
- Slot audit failures usually mean a template shape name changed without updating `config/template_slot_name_manifest.json`.
- Text readback failures usually mean a spec references a missing slot or a slot cannot be written back into the generated deck.
- Visual smoke failures may mean LibreOffice rendering is unavailable, the PPTX failed conversion, or rendered slides are blank/missing expected text.
- Text cutoff changes should be reviewed as content-fit changes. Deterministic cutoff remains the default behavior; optional LLM summarization must stay opt-in and must pass the same slot budget validation.

## Hard-Fail Versus Informational Checks

Hard-fail checks:

- Python compile failures
- LLM guardrail smoke test failures
- template blueprint validation failures
- template slot identity invariant changes
- Template Design DNA coverage or override validation failures
- deck build failures
- PPTX package validation failures
- visual smoke errors and warnings
- design quality errors and warnings for configured quality reports
- deck design review regressions beyond `config/deck_design_review_gate.json`
- text readback invariant changes
- visual drift structural errors
- missing rationale or slot map reports

Informational checks:

- deck design review findings within the current threshold baseline
- visual baseline drift warning slides, as long as structural errors remain zero
- text cutoff events, as long as the expected deterministic baseline remains unchanged

Deck design review is enforced in the regression gate with:

```powershell
python scripts/validate_deck_design_review.py --gate-config config/deck_design_review_gate.json --enforce-gate-config
```

The current thresholds preserve the existing curated-template baseline and block regressions. Lower the thresholds only when the template library or regression specs are intentionally cleaned up in the same change.

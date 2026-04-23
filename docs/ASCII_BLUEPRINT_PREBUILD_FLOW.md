# ASCII Blueprint Pre-Build Flow

Date: 2026-04-22

B33 adds a cheap structure approval checkpoint before PPTX or HTML files are generated.

## Purpose

The ASCII blueprint is for approving story structure, slide order, title hierarchy, and major content regions in the terminal or conversation. It is not a visual preview, thumbnail, layout mock, or visual QA replacement for PPTX, HTML, PDF, or PNG rendering.

## Commands

Render from an existing deck spec:

```powershell
python scripts/render_ascii_blueprint.py data/specs/travel_experience_plan_spec.json --kind spec
```

Render from an intake without building final deck files:

```powershell
python scripts/render_ascii_blueprint.py data/intake/business_growth_review.json --kind intake
```

Use the wrapper:

```powershell
python scripts/ppt_system.py blueprint data/intake/business_growth_review.json --kind intake --approval-mode assistant
```

Validate the sample set:

```powershell
python scripts/validate_ascii_blueprint.py
```

## Outputs

The command writes report artifacts only:

```text
outputs/reports/<deck_id>_ascii_blueprint.md
outputs/reports/<deck_id>_ascii_blueprint.json
```

The JSON report declares:

- `blueprint_role: pre_build_structure_approval`
- `final_file_generation_required: false`
- `final_outputs_generated: []`
- slide order, title/subtitle hierarchy, layout/template key, and region lists

## Included Regions

Each slide reports:

- TITLE: title, headline, subtitle, and related hierarchy slots
- CONTENT: body, metric, summary, and other text/content slots
- IMAGE: filled or blueprint-defined image placeholders
- CHART: filled or blueprint-defined chart placeholders
- TABLE: filled or blueprint-defined table placeholders

## Mode Behavior

- Assistant Mode: show the ASCII structure blueprint in the conversation and wait for an explicit approve, revise, continue, or skip decision before building final files.
- Auto Mode: record the blueprint as a pre-build checkpoint and continue only when a workflow policy says the structure is approved or intentionally skipped.

## Guardrails

- Do not create PPTX or HTML files as part of the ASCII blueprint step.
- Do not present the ASCII blueprint as a visual preview. Use HTML/PPTX preview or rendered thumbnails when the user needs to judge layout, spacing, typography, imagery, or final appearance.
- Do not treat ASCII as proof of final visual quality.
- Do not expose raw/generated/candidate references as production template choices.
- Keep this step cheap enough to run before every first draft when a human wants structure approval.

# Deck Intake Guide

Deck intake files capture presentation intent before a concrete deck spec exists. They are portable inputs for humans, Codex, Claude, Antigravity, and other automation agents.

The intake contract lives at `config/deck_intake.schema.json`. Sample intakes live under `data/intake/`.

## Purpose

Use intake files when the operator knows the audience, purpose, constraints, and desired tone, but has not yet selected exact template slides or written `data/specs/*.json`.

Intake files must not replace deck specs. They sit one step earlier:

```text
intent -> data/intake/*.json -> ASCII blueprint -> data/specs/*.json -> outputs/decks/*.pptx / outputs/html/
```

## Required Fields

- `audience`: primary audience, knowledge level, and decision role.
- `presentation_context`: setting, delivery mode, duration, presenter role, and locale when known.
- `primary_goal`: the outcome the deck should drive.
- `deck_type`: report, sales, portfolio, strategy, training, status update, proposal, analysis, or other.
- `industry`: business, travel, food_and_beverage, healthcare, entertainment, exhibition, technology, finance, or other.
- `tone`: one or more tone signals for selection and editing.
- `slide_count_range`: minimum and maximum expected slides.
- `brand_or_template_scope`: preferred template scope, library, theme, and template preferences.
- `content_density`: low, medium, or high.
- `variation_level`: single path, light variants, or variant review.
- `review_requirements`: whether rationale, slot map, or variant review outputs are expected.
- `must_include` and `must_avoid`: durable constraints that must survive handoff.

## Mapping To Deck Spec

Use the intake to write a normal deck spec:

- `deck_type` and `brand_or_template_scope.preferred_scope` map to `slide_selector.scope`.
- `industry` maps through `config/industry_storyline_taxonomy.json` to the first-draft storyline rhythm, template sequence, selector defaults, and sample-template cleanup rules.
- `primary_goal`, `must_include`, and `presentation_context.setting` guide slide purposes and ordering.
- `tone`, `content_density`, and `variation_level` guide template variant choice and later rationale reports.
- `brand_or_template_scope.theme_path` maps to top-level `theme_path`.
- `output_preferences.output_spec_path` and `output_preferences.output_deck_path` identify durable outputs.
- `review_requirements.requires_rationale_report` maps to future slide selection rationale reports.
- `review_requirements.requires_slot_map` maps to future deck slot map reports.
- `review_requirements.approval_mode=assistant`, `operator_review`, or `stakeholder_review` maps the composed spec to Assistant-style review flow; generated outputs should wait for an explicit approve, revise, continue, or skip decision after the structure blueprint.

Deck specs created from intake should still use `layout: "template_slide"` and write slide content through named `text_slots`, `image_slots`, and `chart_slots`.

For a deterministic first draft, run:

```powershell
python scripts/compose_deck_spec_from_intake.py data/intake/report_exec_briefing.json
```

Or through the operator wrapper:

```powershell
python scripts/ppt_system.py compose-spec data/intake/report_exec_briefing.json
```

The composer does not call an LLM. It maps intake intent, industry profile, preferred template keys, scope, theme, output preferences, and must-include items into a buildable draft deck spec that operators can review before building.

For a pre-build structure checkpoint without creating PPTX or HTML files, run:

```powershell
python scripts/ppt_system.py blueprint data/intake/report_exec_briefing.json --kind intake --approval-mode assistant
```

The ASCII blueprint is structure-only. It does not show exact visual layout, typography, spacing, imagery, or final appearance. Use HTML/PPTX preview or rendered thumbnails for visual approval.

B27 industry-aware behavior is documented in `docs/INDUSTRY_AWARE_SPEC_COMPOSER.md`.

## Validation

Validate all sample intakes:

```powershell
python scripts/validate_deck_intake.py
```

Validate one intake:

```powershell
python scripts/validate_deck_intake.py data/intake/report_exec_briefing.json
```

The validator checks the JSON contract and prints a compact summary for each valid intake.

## Boundaries

- Do not put slide-level `header` or `footer` fields in intake-derived specs.
- Do not use intake to request Python-drawn headers, footers, cards, labels, or rectangles.
- Do not make LLM calls mandatory. Intake may describe desired summarization, but deterministic generation must remain possible.
- Do not treat `blueprint_overlay` as the preferred new authoring mode.

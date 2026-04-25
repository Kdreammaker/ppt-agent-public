# Deck Spec

## Authoring Model

New decks should use `layout: "template_slide"`. Python imports a curated library slide, selects it by `template_key` or `slide_selector`, and injects data into verified `slot:<name>` shapes.

`layout: "blueprint_overlay"` remains available as a compatibility alias, but new specs should treat curated PPTX templates and blueprint slots as the design source of truth.

Python must not draw slide chrome such as headers, footers, cards, or labels with coordinates. Header/footer content belongs in template-controlled slots such as `footer_note`.

This deck spec is an agent-agnostic contract. Codex, Claude, Antigravity, other automation agents, and human operators should all create decks by writing the same spec files, using the same template slots, and running the same validation commands.

## Required Top-Level Fields

- `name`
- `theme_path`
- `output_path`
- `slides`

## Recommended Top-Level Fields

- `project_id`
- `reference_catalog_path`
- `blueprint_path`
- `mode_policy`
- `design_brief_path`
- `doc_paths`
- `asset_intents`

`project_id` names the writer-facing output bundle under `outputs/projects/<project_id>/`.
If omitted, `scripts/ppt_system.py build --auto-project` uses the deck output filename stem.

`design_brief_path` and `doc_paths` let a spec attach authoring documents to the project bundle.
They are copied into `outputs/projects/<project_id>/docs/` when project output is enabled.

`mode_policy` selects the runtime design mode policy. Supported values are `auto` and `assistant`; when omitted, `auto` is used. Mode policies live in `config/mode_policies/` and are recorded in slide selection rationale reports.

`asset_intents` records metadata-only recommendations from the composer for image placeholders, illustrations, icons, chart presets, palettes, typography, and themes. These records cite approved `config/ppt_asset_catalog.json` asset IDs and policy metadata, including `semantic_context`, `template_media_policy`, `license_action`, and `risk_level`; they do not copy binaries or grant permission to scan local/external folders.

HTML final output is built from the same deck spec with `scripts/build_html_deck.py` or `python scripts/ppt_system.py html <spec>`. HTML is a browser/share/presentation artifact; PPTX and Google Slides remain the preferred human-editable outputs.

## Slide Source Selection

- `template_key`: selects one exact curated library slide.
- `slide_selector`: selects by purpose, scope, variant, tags, quality score, and usage policy.
- `source_mode`: usually omitted for imported template slides; use `blank` only for deliberate blank-source compatibility paths.

Selection priority is:

1. Scope match
2. Preferred and fallback variant order
3. Preferred design tier
4. Quality score
5. Default rank
6. Template key

Mode policy scoring is applied after hard selector constraints. This lets `config/mode_policies/*.json` use Design DNA, graph, pattern, tone, density, structure, visual-weight, and quality signals as an ambiguity resolver without making raw or candidate references selectable.

## Supported Layouts

- `template_slide`: primary production path.
- `blueprint_overlay`: compatibility alias for template slot injection.

Legacy coordinate drawing layouts and component canvas paths are retired from active production specs.

## Common Slide Fields

- `slide_selector`
- `template_key`
- `source_mode`
- `keep_shape_indices`
- `text_slots`
- `image_slots`
- `chart_slots`
- `table_slots`
- `slot_overrides`
- `clear_unfilled_slots`
- `clear_residual_placeholders`
- `clear_residual_text_patterns`
- `images`
- `bar_charts`

## Text Slots

Prefer explicit `text_slots`:

```json
{
  "layout": "template_slide",
  "slide_selector": {
    "purpose": "summary",
    "scope": "report",
    "preferred_variant": "summary/two-panel",
    "tone": ["executive"],
    "preferred_density": "medium"
  },
  "text_slots": {
    "title": "Quarterly performance summary",
    "subtitle": "Template style is preserved while content is injected.",
    "footer_note": "Internal review | template-first system"
  }
}
```

`text_values` is still supported for samples and compatibility, but stable specs should prefer named slots so content does not shift when templates gain new optional slots.

## Chart And Table Slots

Dynamic chart and table content should use named template slots, not ad hoc Python layout coordinates.

```json
{
  "layout": "template_slide",
  "template_key": "core_technology_v1",
  "chart_slots": {
    "trend_chart": {
      "chart_type": "bar",
      "categories": ["Q1", "Q2", "Q3", "Q4"],
      "values": [18, 27, 35, 46]
    }
  },
  "table_slots": {
    "metric_table": {
      "headers": ["Metric", "Now", "Target"],
      "rows": [
        ["Cycle", "14d", "7d"],
        ["Score", "82", "92"],
        ["Risk", "Med", "Low"]
      ]
    }
  }
}
```

The deck schema rejects mismatched chart category/value lengths and non-rectangular table rows. The sample validation command is:

```powershell
python scripts/validate_chart_table_slots.py
```

## Footer Slots

Footer text is injected through normal template slots. Current curated templates expose `footer_note` on supported slides. Do not add spec-level `footer`; it is no longer part of the public deck spec.

If a selected template does not expose the footer slot you need, update the curated template library and blueprint manifest deliberately, then update the regression gate invariants.

## Theme

`theme_path` defines colors, font family, and role-based font sizes. It does not define header/footer drawing behavior.

Header and footer visual structure is controlled by the PowerPoint template or explicit template slots.

Specs may optionally set PowerPoint theme accent colors at package level after the deck is generated:

```json
{
  "theme_accent_overrides": {
    "accent1": "#0F6F78",
    "accent2": "#E86F51"
  }
}
```

This swaps `ppt/theme/theme1.xml` accent slots without redrawing template shapes. Supported keys are `accent1` through `accent6`. Normal template slot injection remains the source of slide content.

## CJK Text Budget

Text guardrails use a weighted budget for East Asian wide/full-width characters. Korean, Japanese, Chinese, and full-width punctuation count wider than ASCII before deterministic cutoff or optional summarization is accepted.

The slot capacity fields stay the same (`max_chars_per_line` and `max_lines`), but overflow reports include weighted unit details when CJK text triggers a tighter fit decision.

## Validation

Use the standard gate after meaningful changes:

```powershell
python scripts/run_regression_gate.py
```

For an ad hoc deck build with a writer-facing project bundle:

```powershell
python scripts/ppt_system.py build data/specs/example.json --validate --auto-project
```

This keeps compatibility outputs in `outputs/decks/` and `outputs/reports/`, then mirrors the deck, spec, docs, referenced images, validation reports, and rendered previews into `outputs/projects/<project_id>/`.

For HTML final output:

```powershell
python scripts/ppt_system.py html data/specs/example.json --validate
```

This writes `outputs/html/<deck_id>/index.html` plus `html_manifest.json`. Use `scripts/validate_html_output.py --browser-screenshot` for focused Playwright screenshot validation when browser evidence is required.

The gate validates Python compile, blueprint schema, slot identities, deck builds, PPTX packages, visual smoke, design quality, text readback, overflow reports, and visual drift structural errors.

For cross-agent operation and handoff rules, see `docs/AGENT_HANDOFF_GUIDE.md`.

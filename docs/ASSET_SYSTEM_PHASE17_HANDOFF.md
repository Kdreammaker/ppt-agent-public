# Asset System Handoff: Phase 17 Final Summary

Date: 2026-04-28

Status: Ready for asset-system owner review.

## Scope

This handoff covers the final Phase 17 guide-packet consumer work after the
B178-B185 sparse-request and strategy-routing expansion.

The asset-system relevant contract remains:

- `guide-data.public.json` is the primary machine input.
- HTML guide output is human review evidence only.
- PPTX output is rendered with native PowerPoint objects.
- Approved package assets are inserted only after manifest/checksum/size
  validation.
- Missing approved assets use native shape/mockup fallbacks and are reported.
- Visible slides must not expose content guidance, slot IDs, layout recipe IDs,
  debug labels, private paths, Drive IDs, or raw source metadata.

## Current Validation Result

Final validation passed on 2026-04-28.

Commands run:

```powershell
python -m py_compile system\guide_packet.py system\strategy_router.py scripts\ppt_agent.py scripts\mcp_adapter.py scripts\validate_auto_strategy_registry.py scripts\validate_intent_taxonomy.py scripts\validate_strategy_router.py scripts\validate_guide_packet_pipeline.py scripts\validate_agent_skill_contract.py scripts\validate_agent_skill_smoke.py
python scripts\validate_auto_strategy_registry.py
python scripts\validate_intent_taxonomy.py
python scripts\validate_strategy_router.py
python scripts\validate_guide_packet_pipeline.py
python scripts\validate_agent_skill_contract.py
python scripts\validate_agent_skill_smoke.py
```

Observed results:

- `validate_auto_strategy_registry.py`: pass, 23 strategies, 24 mappings
- `validate_intent_taxonomy.py`: pass, 12 families, 42 examples
- `validate_strategy_router.py`: pass, 30 fixtures, 12 Auto builds, 24 registry mappings checked, 12 Auto visual diffs checked
- `validate_guide_packet_pipeline.py`: pass
- `validate_agent_skill_contract.py`: pass
- `validate_agent_skill_smoke.py`: pass

The latest guide-packet pipeline Auto output reported:

- rendered preview average mean difference: `54.335`
- slides over threshold: `15 / 15`
- machine-plan changed recipes: `15`
- Variant A strategy: `investor_open`
- Variant B strategy: `operator_dense`

The strategy-router validation also wrote:

- `outputs/projects/strategy-router-validation/registry-layout-recipe-diff-report.json`

That report shows:

- registry mappings checked: `24`
- zero recipe diffs: `0`
- minimum recipe diff: `6`

## B178-B185 Additions Relevant To Asset System

### Sparse Request Intake

The system now creates public-safe machine-facing intake artifacts for vague
requests before guide packet composition:

- `request-intake.json`
- `source-summary.json`
- `intent-profile.json`
- `routing-report.json`

Unreadable source content is recorded as an assumption or blocker. It is not
converted into fabricated slide facts.

### Intent And Strategy Routing

The system now includes:

- `config/deck_intent_taxonomy.json`
- `config/variant_strategy_registry.json`
- `system/strategy_router.py`

The strategy registry defines 23 canonical strategy profiles, aliases, 24
recommended A/B mappings, and a `general_unknown_intent` fallback.

### Machine-Facing A/B Plans

Auto mode now routes Variant A and Variant B through strategy-specific
machine-facing documents before rendering.

Variant-specific `deck-plan.json` and `renderer-contract.json` include:

- `strategy_id`
- `layout_recipe`
- `content_emphasis`
- `evidence_treatment`
- `visual_asset_role`
- `palette_emphasis`
- `typography_role_bias`
- `chart_or_table_style`
- `density_budget`
- variant-level `strategy_contract`

The renderer now consumes `layout_recipe` through recipe families and recipe
tokens before drawing native PowerPoint shapes. It no longer relies on
variant-letter layout branching.

### Auto Variant Validation

Validation now checks both:

- machine-plan recipe differences, and
- rendered-preview visual differences.

This closes the previous gap where A/B plans could differ by metadata while
rendered previews remained identical.

## Asset Slot And Approved Asset Behavior

The original asset-system sample packet still has no approved package assets.
Therefore these warning states remain expected and non-blocking:

- `used-assets-report.json.status: warning`
- `final-qa.json.approved_assets_used.status: not_applicable`
- `final-qa.json.asset_slots_fallbacks.status: warning`

All expected sample slots remain recorded:

- `hero_mockup`
- `problem_icons`
- `edge_bleed_visual`
- `phone_screen`
- `background_texture`

Native fallback/mockup handling is expected for this fixture.

## Public Repo Push Boundary

Safe for the public repo:

- Runtime code:
  - `system/guide_packet.py`
  - `system/strategy_router.py`
  - `scripts/ppt_agent.py`
  - `scripts/mcp_adapter.py`
  - validation scripts
- Public-safe config:
  - `config/deck_intent_taxonomy.json`
  - `config/variant_strategy_registry.json`
  - `config/ppt-maker-design-guide-packet.schema.json`
- Public/synthetic fixtures:
  - `data/fixtures/lumaloop_guide`
  - `data/fixtures/strategy_router`
- Public-safe docs:
  - `README.md`
  - `AGENTS.md`
  - `skills/ppt-agent/SKILL.md`
  - sanitized handoff summaries that do not contain local paths or private
    asset payloads.

Do not push to public:

- `.env*`
- local generated outputs under `outputs/projects`
- downloaded private asset packages
- real user logs, including external-service chat logs
- local screenshots/thumbnails generated during exploration
- private source documents, source summaries from real user files, Drive IDs,
  tokens, raw manifests, or absolute local paths.

## Private Repo / Internal Storage Boundary

Keep internally or in the private repo:

- full validation output directories and generated PPTX/previews;
- original asset-system fixture/schema copies when they are not intended for
  public release;
- approved asset package manifests, checksums, and file-size evidence;
- private QA reports that include local evidence paths;
- real user logs and external-service behavior notes;
- source-ingestion fixtures based on real user files.

## Requests For Asset-System Owner

Please review:

1. Whether the current guide-packet schema still matches asset-system canonical
   expectations after strategy metadata is added to generated plans.
2. Whether the native fallback records in `used-assets-report.json` and
   `final-qa.json` are sufficient for asset provenance audit.
3. Whether future approved asset packages should expose additional manifest
   fields for crop/mask handling, especially phone screens, mockups,
   background images, and right-edge bleed visuals.
4. Whether the asset system wants to own or validate any strategy-level visual
   asset requirements, such as strategy-specific preferred slots or density
   budgets.

## Non-Blocking Follow-Up

`event_operations_ko` passed visual diff validation but has a narrower margin
than the other Auto fixtures. This is not a blocker, but it is a good candidate
for later variant-quality tuning.

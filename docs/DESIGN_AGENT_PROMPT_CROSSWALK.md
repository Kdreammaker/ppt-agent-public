# Design Agent Prompt Crosswalk

Date: 2026-04-21

This document makes design-agent behavior auditable without copying any hidden or external prompt text into the runtime. It records the durable system surface that now carries those ideas: intake files, deck specs, mode policies, template catalogs, reports, validation gates, and reference review workflows.

## Boundary

- This is not a prompt transplant.
- This file does not preserve private wording, examples, or chain-of-thought style instructions from any prior agent prompt.
- The production contract remains file-based and agent-agnostic: Codex, Claude, Antigravity, another automation agent, or a human operator should be able to follow the same artifacts.
- Raw references and generated candidate slides remain review inputs only. They are not production-selectable templates until explicitly promoted.

## Behavior Crosswalk

| Design-agent behavior | Durable implementation | Current artifact |
| --- | --- | --- |
| Capture audience, goal, tone, constraints, and review expectations before writing slide content. | Deck intake schema and guide define portable pre-spec intent. | `config/deck_intake.schema.json`, `docs/DECK_INTAKE_GUIDE.md`, `data/intake/*.json` |
| Convert intent into a deterministic deck contract. | Specs remain normal JSON and build without mandatory LLM calls. | `config/deck_spec.schema.json`, `docs/DECK_SPEC.md`, `data/specs/*.json`, `scripts/compose_deck_spec_from_intake.py` |
| Prefer curated template structure over ad hoc drawing. | Production deck specs use `template_slide`, `slide_selector`, verified `slot:<name>` shapes, and blueprint metadata. | `config/reference_catalog.json`, `config/template_blueprints.json`, `config/template_slot_name_manifest.json`, `scripts/build_deck.py` |
| Keep raw/generated references out of runtime selection. | Curation policy, labels, promotion tooling, and validators separate raw, candidate, and finalized library material. | `config/reference_curation_catalog.json`, `scripts/apply_reference_review_labels.py`, `scripts/promote_reference_candidates.py`, `scripts/validate_reference_curation.py` |
| Use design intent to choose appropriate templates. | Selection uses purpose, scope, preferred variants, design tier, quality score, and default rank; rationale reports show the selected and rejected candidates. | `scripts/build_deck.py`, `outputs/reports/*_slide_selection_rationale.json`, `outputs/reports/*_slide_selection_rationale.md` |
| Explain how content fit into the selected layout. | Slot maps expose filled, unfilled, and unavailable text/image/chart slots. | `outputs/reports/*_deck_slot_map.json`, `outputs/reports/*_deck_slot_map.md` |
| Preserve typography, color, and content density signals in a reusable form. | Template Design DNA records purpose, scope, tone, density, visual weight, content capacity, footer support, and avoid/best-fit notes. | `config/template_design_dna.json`, `config/template_design_dna_overrides.json`, `docs/MODE_POLICY_GUIDE.md` |
| Allow auto mode to proceed with reasonable assumptions when intent is sufficient. | Auto mode policy defines default assumptions, retrieval weights, fallback rules, variant strategy, and comparison rubric. | `config/mode_policies/auto_mode_policy.json`, `docs/MODE_POLICY_GUIDE.md` |
| Allow assistant mode to ask early when design intent is missing. | Assistant mode policy defines required questions, optional questions, design brief fields, style negotiation fields, and confirmation points. | `config/mode_policies/assistant_mode_policy.json`, `docs/MODE_POLICY_GUIDE.md` |
| Use graph and pattern knowledge when choosing or explaining design options. | Knowledge graph links templates to audience, purpose, tone, layout, and quality signals; pattern catalog is generated from reviewed good library metadata. | `config/reference_knowledge_graph.json`, `config/template_pattern_catalog.json`, `scripts/build_reference_knowledge_graph.py`, `scripts/build_template_pattern_catalog.py` |
| Avoid reinforcing weak output. | Generated decks are captured as raw references, split into slide assets, labeled, and only promoted through explicit review. | `scripts/ppt_system.py`, `scripts/parse_reference_deck.py`, `assets/slides/categorizing/records/*_slide_quality_labels.json` |
| Verify visual and package quality before handoff. | Build validation runs package checks, visual smoke, design quality, design review, text overflow reports, and full regression gate. | `scripts/validate_pptx_package.py`, `scripts/validate_visual_smoke.py`, `scripts/validate_design_quality.py`, `scripts/validate_deck_design_review.py`, `scripts/run_regression_gate.py` |
| Deliver output through a durable handoff channel. | Project manifests and delivery manifests record local bundle, Drive Desktop sync, Slack status, and evidence paths. | `scripts/deliver_project_output.py`, `scripts/send_delivery_slack_message.py`, `config/output_delivery_policy.json`, `docs/OUTPUT_DELIVERY_WORKFLOW.md` |

## Execution Model

1. Capture intent in `data/intake/*.json` when a deck does not yet have a concrete spec.
2. Compose or hand-author `data/specs/*.json` using durable fields, not hidden agent memory.
3. Select curated templates through `template_key` or `slide_selector`.
4. Inject content through verified slots and record rationale/slot-map reports.
5. Run validation and visual QA.
6. Deliver through project manifests, Drive Desktop sync, and Slack evidence.
7. Capture generated decks as raw references only.
8. Label useful generated slides and promote only after explicit review.

## Gaps And Backlog Links

These are durable follow-up gaps, not hidden prompt rules:

- Runtime mode policy integration is still pending. B11 should make `config/mode_policies/*.json` influence selection/rationale behavior directly rather than serving only as documentation/config.
- The pattern catalog is currently empty because it intentionally reads only finalized `good` library metadata. It should remain empty until genuinely good reviewed slides are promoted.
- Graph and pattern retrieval exists as durable data, but candidate weighting is not yet fully wired into runtime selection. B11 should connect it without making raw/candidate references selectable.
- Blank-source compatibility remains useful for recovery and production E2E debugging, but the preferred new production path stays curated templates plus slots. Template quality work should continue through blueprint/template library improvement rather than making coordinate-drawn slides the default.
- Delivery manifests record Drive Desktop sync and Slack evidence, but public Drive sharing is intentionally not automatic. Sharing permission changes should remain a separate explicit human request.

## Audit Checklist

- Does the deck intent live in intake/spec files rather than chat memory?
- Does every production slide use a curated template slot path or an explicitly documented compatibility path?
- Are generated references captured as raw review inputs, not runtime templates?
- Are rationale, slot-map, quality, visual-smoke, and delivery reports present?
- Did `scripts/run_regression_gate.py` pass after meaningful changes?
- If Slack delivery was requested, is there a bridge or connector evidence path?

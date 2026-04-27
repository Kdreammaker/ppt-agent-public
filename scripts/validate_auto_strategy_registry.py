from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def difference_dimensions(a: dict, b: dict) -> list[str]:
    dimensions = [
        "density",
        "title_hierarchy",
        "slide_rhythm",
        "visual_placement",
        "evidence_style",
        "palette_emphasis",
        "typography_role_bias",
        "chart_or_table_style",
    ]
    return [key for key in dimensions if a.get(key) != b.get(key)]


def main() -> int:
    registry = json.loads((BASE_DIR / "config" / "variant_strategy_registry.json").read_text(encoding="utf-8"))
    canonical = registry["canonical_strategy_ids"]
    expected = [
        "investor_open",
        "operator_dense",
        "board_brief",
        "analytical_dashboard",
        "metric_review_report",
        "strategic_options",
        "formal_memo",
        "citizen_story",
        "b2b_value_proof",
        "feature_and_spec_matrix",
        "portfolio_gallery",
        "case_study_proof",
        "demo_story",
        "screen_product_tour",
        "sensory_showcase",
        "luxury_editorial",
        "itinerary_experience",
        "story_world_pitch",
        "launch_campaign",
        "learning_path",
        "workbook_dense",
        "strategic_blueprint",
        "ecosystem_map",
    ]
    assert_true(canonical == expected, "canonical strategy ids must match PLAN.md order")
    strategies = {item["strategy_id"]: item for item in registry["strategies"]}
    assert_true(set(canonical) == set(strategies), "registry strategies do not match canonical ids")
    required_aliases = {
        "policy_memo": "formal_memo",
        "enterprise_value_map": "b2b_value_proof",
        "feature_matrix": "feature_and_spec_matrix",
        "spec_comparison": "feature_and_spec_matrix",
        "financial_close_report": "metric_review_report",
        "performance_review": "metric_review_report",
        "new_business_blueprint": "strategic_blueprint",
        "service_blueprint": "strategic_blueprint",
        "event_production_plan": "strategic_blueprint",
        "market_landscape": "ecosystem_map",
    }
    assert_true(registry.get("aliases") == required_aliases, "strategy aliases drifted from PLAN.md")
    assert_true(len(registry.get("recommended_ab_mappings", [])) >= 23, "expected at least 23 A/B mappings")
    for mapping in registry["recommended_ab_mappings"]:
        a = strategies[mapping["variant_a"]]
        b = strategies[mapping["variant_b"]]
        changed = difference_dimensions(a, b)
        assert_true(len(changed) >= 4, f"mapping {mapping['mapping_id']} differs in too few dimensions: {changed}")
    fallback = registry["fallbacks"]["general_unknown_intent"]
    assert_true(fallback["variant_a"] == "board_brief" and fallback["variant_b"] == "demo_story", "fallback pair drifted")
    print(json.dumps({"status": "pass", "strategies": len(strategies), "mappings": len(registry["recommended_ab_mappings"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

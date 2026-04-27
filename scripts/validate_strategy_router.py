from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.guide_packet import (
    GuidePacket,
    build_auto_variants,
    compose_guide_packet_from_intent,
    generate_deck_plan,
    generate_renderer_contract,
    load_strategy_registry,
)
from system.strategy_router import run_sparse_request_pipeline


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_public_safe(path: Path) -> None:
    raw = path.read_text(encoding="utf-8")
    raw_lower = raw.lower()
    markers = ["c:\\", "/users/", "/home/", "drive_id", "api_key", "secret"]
    assert_true(not any(marker in raw_lower for marker in markers), f"private marker leaked in {path.name}")


AUTO_BUILD_FIXTURE_IDS = {
    "public_agency_sparse_ko",
    "ir_pitch_en",
    "b2b_saas_ko",
    "b2c_it_service_ko",
    "market_research_en",
    "event_operations_ko",
    "technical_training_en",
    "consumer_electronics_en",
    "luxury_goods_en",
    "creative_portfolio_en",
    "enterprise_sales_en",
    "food_product_ko",
}


def layout_recipes(plan: dict) -> list[str]:
    return [
        str(slide.get("renderer_metadata", {}).get("layout_strategy", {}).get("layout_recipe") or slide.get("layout_recipe"))
        for slide in plan.get("slides", [])
    ]


def layout_recipe_diff(plan_a: dict, plan_b: dict) -> int:
    return sum(1 for a, b in zip(layout_recipes(plan_a), layout_recipes(plan_b), strict=False) if a != b)


def assert_layout_recipe_diff(plan_a: dict, plan_b: dict, context: str) -> int:
    slide_count = min(len(plan_a.get("slides", [])), len(plan_b.get("slides", [])))
    diff = layout_recipe_diff(plan_a, plan_b)
    required = max(1, slide_count // 2)
    assert_true(diff >= required, f"{context} layout_recipe diff too small: diff={diff}, required={required}")
    return diff


def assert_preview_visual_diff(auto_root: Path, fixture: dict, expected_slides: int) -> dict[str, float | int]:
    a_paths = sorted((auto_root / "variant-a" / "previews").glob("slide_*.png"))
    b_paths = sorted((auto_root / "variant-b" / "previews").glob("slide_*.png"))
    assert_true(a_paths and len(a_paths) == len(b_paths), f"{fixture['id']} auto preview sets are incomplete")
    assert_true(len(a_paths) == expected_slides, f"{fixture['id']} auto preview slide count mismatch")
    mean_diffs: list[float] = []
    changed_slides = 0
    for a_path, b_path in zip(a_paths, b_paths, strict=True):
        a_img = Image.open(a_path).convert("RGB").resize((320, 180))
        b_img = Image.open(b_path).convert("RGB").resize((320, 180))
        diff = ImageChops.difference(a_img, b_img)
        mean = sum(ImageStat.Stat(diff).mean) / 3.0
        mean_diffs.append(mean)
        if mean >= 5.0:
            changed_slides += 1
    average_mean_diff = sum(mean_diffs) / len(mean_diffs)
    required_changed = max(1, expected_slides // 2)
    assert_true(
        average_mean_diff >= 5.0 and changed_slides >= required_changed,
        (
            f"{fixture['id']} rendered previews are not visually distinct enough: "
            f"average_mean_diff={average_mean_diff:.2f}, changed_slides={changed_slides}, "
            f"required_changed={required_changed}"
        ),
    )
    return {
        "average_mean_diff": round(average_mean_diff, 3),
        "slides_over_visual_threshold": changed_slides,
        "visual_slide_count": len(mean_diffs),
    }


def validate_auto_build_output(auto_root: Path, fixture: dict, expected_slides: int) -> dict:
    comparison_path = auto_root / "variant-comparison-report.json"
    assert_true(comparison_path.exists(), f"{fixture['id']} missing variant-comparison-report.json")
    summary = json.loads(comparison_path.read_text(encoding="utf-8"))
    assert_true(summary.get("status") == "pass", f"{fixture['id']} auto comparison did not pass: {summary.get('status')}")
    assert_true(
        summary.get("strategy_pair", {}).get("variant_a") == fixture["expected_a"]
        and summary.get("strategy_pair", {}).get("variant_b") == fixture["expected_b"],
        f"{fixture['id']} comparison strategy pair does not match routing",
    )
    assert_true(summary.get("routing_source"), f"{fixture['id']} did not record routing source")
    result = {"id": fixture["id"], "slides": expected_slides}
    plans = {}
    for variant_name, expected_strategy in {"variant-a": fixture["expected_a"], "variant-b": fixture["expected_b"]}.items():
        variant_dir = auto_root / variant_name
        plan = json.loads((variant_dir / "deck-plan.json").read_text(encoding="utf-8"))
        plans[variant_name] = plan
        strategy = plan.get("variant_strategy", {}).get("id")
        assert_true(strategy == expected_strategy, f"{fixture['id']} {variant_name} used {strategy}, expected {expected_strategy}")
        pptx_path = variant_dir / "generated.pptx"
        assert_true(pptx_path.exists(), f"{fixture['id']} {variant_name} missing generated.pptx")
        previews = sorted((variant_dir / "previews").glob("slide_*.png"))
        assert_true(len(previews) == expected_slides, f"{fixture['id']} {variant_name} preview count mismatch")
        assert_public_safe(variant_dir / "deck-plan.json")
        assert_public_safe(variant_dir / "renderer-contract.json")
    result["layout_recipe_diff"] = assert_layout_recipe_diff(
        plans["variant-a"],
        plans["variant-b"],
        f"{fixture['id']} auto build",
    )
    result["visual_diff"] = assert_preview_visual_diff(auto_root, fixture, expected_slides)
    return result


def validate_registry_mapping_plan_diffs(output_root: Path) -> list[dict]:
    registry = load_strategy_registry()
    results = []
    for mapping in registry.get("recommended_ab_mappings", []):
        subtype = (mapping.get("subtypes") or ["general"])[0]
        intent = {
            "topic": mapping["mapping_id"],
            "deck_family": mapping["family"],
            "sector_subtype": subtype,
            "audience": "general validation audience",
            "objective": "validate",
            "tone": ["clear", "credible"],
        }
        source_summary = {
            "contract": "ppt-maker.source-summary.v1",
            "sources": [],
            "assumptions": ["Registry mapping diff validation uses synthetic intent only."],
            "unresolved_blockers": [],
        }
        routing = {
            "selected": {
                "variant_a": {"strategy_id": mapping["variant_a"]},
                "variant_b": {"strategy_id": mapping["variant_b"]},
                "mapping_id": mapping["mapping_id"],
            }
        }
        packet_data = compose_guide_packet_from_intent(intent, source_summary, routing)
        packet = GuidePacket.model_validate(packet_data)
        plan_a = generate_deck_plan(packet, "registry-mapping-validation", mapping["variant_a"])
        plan_b = generate_deck_plan(packet, "registry-mapping-validation", mapping["variant_b"])
        diff = assert_layout_recipe_diff(plan_a, plan_b, f"registry mapping {mapping['mapping_id']}")
        assert_true(diff > 0, f"registry mapping {mapping['mapping_id']} has recipe_diff 0")
        results.append({"mapping_id": mapping["mapping_id"], "layout_recipe_diff": diff, "slides": packet.guide_identity.slide_count})
    path = output_root / "registry-layout-recipe-diff-report.json"
    path.write_text(json.dumps({"mappings": results}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return results


def main() -> int:
    fixtures = json.loads((BASE_DIR / "data" / "fixtures" / "strategy_router" / "fixtures.json").read_text(encoding="utf-8"))
    output_root = BASE_DIR / "outputs" / "projects" / "strategy-router-validation"
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    passed = []
    auto_builds = []
    registry_mapping_diffs = validate_registry_mapping_plan_diffs(output_root)
    for fixture in fixtures:
        project_dir = output_root / fixture["id"]
        artifacts = run_sparse_request_pipeline(fixture["prompt"], project_dir, mode=fixture.get("mode", "assistant"))
        intent = artifacts["intent_profile"]
        routing = artifacts["routing_report"]
        assert_true(intent["deck_family"] == fixture["expected_family"], f"{fixture['id']} family mismatch: {intent}")
        assert_true(intent["sector_subtype"] == fixture["expected_subtype"], f"{fixture['id']} subtype mismatch: {intent}")
        selected = routing["selected"]
        assert_true(selected["variant_a"]["strategy_id"] == fixture["expected_a"], f"{fixture['id']} variant A mismatch")
        assert_true(selected["variant_b"]["strategy_id"] == fixture["expected_b"], f"{fixture['id']} variant B mismatch")
        assert_true(selected["variant_a"]["strategy_id"] != selected["variant_b"]["strategy_id"], f"{fixture['id']} variants match")
        packet_data = compose_guide_packet_from_intent(
            intent,
            artifacts["source_summary"],
            routing,
            request_intake=artifacts["request_intake"],
        )
        packet = GuidePacket.model_validate(packet_data)
        plan_a = generate_deck_plan(packet, "fixture-routing", selected["variant_a"]["strategy_id"])
        plan_b = generate_deck_plan(packet, "fixture-routing", selected["variant_b"]["strategy_id"])
        contract_a = generate_renderer_contract(packet, "fixture-routing", plan_a)
        contract_b = generate_renderer_contract(packet, "fixture-routing", plan_b)
        changed = sum(
            1
            for slide_a, slide_b in zip(plan_a["slides"], plan_b["slides"], strict=False)
            if (
                slide_a["strategy_id"],
                slide_a["layout_recipe"],
                slide_a["content_emphasis"],
                slide_a["evidence_treatment"],
                slide_a["palette_emphasis"],
            )
            != (
                slide_b["strategy_id"],
                slide_b["layout_recipe"],
                slide_b["content_emphasis"],
                slide_b["evidence_treatment"],
                slide_b["palette_emphasis"],
            )
        )
        recipe_diff = assert_layout_recipe_diff(plan_a, plan_b, f"{fixture['id']} fixture plan")
        assert_true(changed >= max(1, len(plan_a["slides"]) // 2), f"{fixture['id']} machine plans are too similar")
        assert_true(contract_a["strategy_contract"] != contract_b["strategy_contract"], f"{fixture['id']} renderer contracts match")
        for name in ["request-intake.json", "source-summary.json", "intent-profile.json", "routing-report.json"]:
            assert_public_safe(project_dir / name)
        if fixture["id"] in AUTO_BUILD_FIXTURE_IDS:
            guide_path = project_dir / "intake" / "guide-data.public.json"
            guide_path.parent.mkdir(parents=True, exist_ok=True)
            guide_path.write_text(json.dumps(packet_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            auto_root = output_root / "auto-builds" / fixture["id"]
            result = build_auto_variants(
                guide_path,
                output_root=output_root / "auto-builds",
                project_id=fixture["id"],
            )
            assert_true(result["status"] == "pass", f"{fixture['id']} auto build did not pass: {result}")
            auto_builds.append(validate_auto_build_output(auto_root, fixture, packet.guide_identity.slide_count))
        passed.append(fixture["id"])
    assert_true(len(auto_builds) >= 12, f"expected at least 12 Auto fixture builds, got {len(auto_builds)}")
    print(
        json.dumps(
            {
                "status": "pass",
                "fixtures": len(passed),
                "auto_builds": len(auto_builds),
                "registry_mappings_checked": len(registry_mapping_diffs),
                "auto_visual_diff_checked": len(auto_builds),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

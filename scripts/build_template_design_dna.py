from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.blueprint_loader import load_blueprints

REFERENCE_CATALOG_PATH = BASE_DIR / "config" / "reference_catalog.json"
BLUEPRINT_PATH = BASE_DIR / "config" / "template_blueprints.json"
OVERRIDES_PATH = BASE_DIR / "config" / "template_design_dna_overrides.json"
OUTPUT_PATH = BASE_DIR / "config" / "template_design_dna.json"

OVERRIDABLE_FIELDS = {
    "density",
    "tone",
    "structure",
    "visual_weight",
    "content_capacity",
    "footer_supported",
    "best_for",
    "avoid_for",
    "review_notes",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_json_optional(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def tags(slide: dict[str, Any]) -> set[str]:
    return {str(tag).lower() for tag in slide.get("style_tags", [])}


def tone(slide: dict[str, Any]) -> list[str]:
    result: list[str] = []
    slide_tags = tags(slide)
    scope = slide.get("scope")
    purpose = slide.get("purpose")
    if scope == "sales" or "sales" in slide_tags:
        result.append("sales")
    if scope == "portfolio" or "portfolio" in slide_tags:
        result.append("portfolio")
    if purpose in {"analysis", "chart", "market"} or {"data", "finance"} & slide_tags:
        result.append("analytical")
    if purpose in {"process", "strategy"} or {"method", "system"} & slide_tags:
        result.append("technical")
    if purpose in {"cover", "summary", "closing"}:
        result.append("executive")
    if not result:
        result.append("executive")
    return list(dict.fromkeys(result))


def structure(slide: dict[str, Any]) -> str:
    variant = str(slide.get("variant", "")).lower()
    purpose = slide.get("purpose")
    slide_tags = tags(slide)
    if purpose == "timeline" or "timeline" in variant:
        return "timeline"
    if purpose == "process" or "process" in variant or "method" in slide_tags:
        return "process"
    if purpose in {"chart", "market"} or "metric" in variant:
        return "metric"
    if "comparison" in variant or "compare" in slide_tags:
        return "comparison"
    if purpose in {"toc", "team", "issue"} or "grid" in variant or "cards" in slide_tags:
        return "grid"
    if purpose in {"analysis", "strategy"}:
        return "comparison"
    return "story"


def visual_weight(slide: dict[str, Any]) -> str:
    text_count = int(slide.get("text_shape_count", 0))
    image_count = int(slide.get("image_count", 0))
    density = str(slide.get("density", "medium")).lower()
    if density == "dense" or text_count >= 12:
        return "text_heavy"
    if image_count >= 1 and text_count <= 5:
        return "visual_first"
    return "balanced"


def text_budget(slot: dict[str, Any]) -> int | None:
    max_chars_per_line = slot.get("max_chars_per_line")
    max_lines = slot.get("max_lines")
    if not max_chars_per_line or not max_lines:
        return None
    return max(1, int(max_chars_per_line) * int(max_lines))


def content_capacity(blueprint: dict[str, Any] | None) -> dict[str, Any]:
    if not blueprint:
        return {
            "text_slots": 0,
            "image_slots": 0,
            "chart_slots": 0,
            "table_slots": 0,
            "estimated_text_budget": 0,
        }
    budgets = [
        budget
        for budget in (text_budget(slot) for slot in blueprint.get("editable_text_slots", []))
        if budget is not None
    ]
    return {
        "text_slots": len(blueprint.get("editable_text_slots", [])),
        "image_slots": len(blueprint.get("editable_image_slots", [])),
        "chart_slots": len(blueprint.get("editable_chart_slots", [])),
        "table_slots": len(blueprint.get("editable_table_slots", [])),
        "estimated_text_budget": sum(budgets),
    }


def footer_supported(blueprint: dict[str, Any] | None) -> bool:
    if not blueprint:
        return False
    return any(slot.get("slot") == "footer_note" for slot in blueprint.get("editable_text_slots", []))


def best_for(slide: dict[str, Any], dna_tone: list[str], dna_structure: str) -> list[str]:
    items = [
        f"{slide.get('purpose')} slides",
        f"{slide.get('scope')} scope",
        f"{dna_structure} structure",
    ]
    if "sales" in dna_tone:
        items.append("buyer-facing narrative")
    if "portfolio" in dna_tone:
        items.append("project storytelling")
    if "analytical" in dna_tone:
        items.append("evidence-backed analysis")
    return [item for item in items if item and not item.startswith("None")]


def avoid_for(slide: dict[str, Any], dna_visual_weight: str, capacity: dict[str, Any]) -> list[str]:
    items: list[str] = []
    if dna_visual_weight == "text_heavy":
        items.append("minimal-text visual moments")
    if dna_visual_weight == "visual_first":
        items.append("dense technical explanation")
    if capacity.get("text_slots", 0) <= 2:
        items.append("multi-point body copy")
    if slide.get("usage_policy") != "production_ready":
        items.append("unreviewed production use without operator check")
    return items


def validate_design_dna_overrides(overrides: dict[str, Any], slide_ids: set[str]) -> None:
    if overrides.get("version") != "1.0":
        raise ValueError("Design DNA overrides must use version '1.0'.")
    slides = overrides.get("slides")
    if not isinstance(slides, dict):
        raise ValueError("Design DNA overrides must contain a 'slides' object.")
    for slide_id, fields in slides.items():
        if slide_id not in slide_ids:
            raise ValueError(f"Design DNA override references unknown slide_id: {slide_id}")
        if not isinstance(fields, dict):
            raise ValueError(f"Design DNA override for {slide_id} must be an object.")
        unsupported = sorted(set(fields) - OVERRIDABLE_FIELDS)
        if unsupported:
            raise ValueError(
                f"Design DNA override for {slide_id} contains unsupported fields: {unsupported}"
            )


def apply_design_dna_overrides(
    slides: dict[str, dict[str, Any]],
    overrides: dict[str, Any] | None,
) -> None:
    if not overrides:
        return
    validate_design_dna_overrides(overrides, set(slides))
    for slide_id, fields in overrides.get("slides", {}).items():
        slides[slide_id].update(fields)
        slides[slide_id]["override_applied"] = True


def build_design_dna() -> dict[str, Any]:
    reference_catalog = load_json(REFERENCE_CATALOG_PATH)
    blueprints = load_blueprints(BLUEPRINT_PATH).get("slides", {})
    overrides = load_json_optional(OVERRIDES_PATH)
    slides: dict[str, Any] = {}
    for slide in reference_catalog.get("slides", []):
        slide_id = slide["slide_id"]
        blueprint = blueprints.get(slide_id)
        dna_tone = tone(slide)
        dna_structure = structure(slide)
        dna_visual_weight = visual_weight(slide)
        capacity = content_capacity(blueprint)
        slides[slide_id] = {
            "template_key": slide.get("template_key"),
            "library_id": slide.get("library_id"),
            "purpose": slide.get("purpose"),
            "scope": slide.get("scope"),
            "density": slide.get("density", "medium"),
            "tone": dna_tone,
            "structure": dna_structure,
            "visual_weight": dna_visual_weight,
            "content_capacity": capacity,
            "footer_supported": footer_supported(blueprint),
            "best_for": best_for(slide, dna_tone, dna_structure),
            "avoid_for": avoid_for(slide, dna_visual_weight, capacity),
            "override_applied": False,
        }
    apply_design_dna_overrides(slides, overrides)
    return {
        "version": "1.0",
        "generated_from": {
            "reference_catalog_path": "config/reference_catalog.json",
            "blueprint_path": "config/template_blueprints.json",
            "overrides_path": "config/template_design_dna_overrides.json" if overrides else None,
        },
        "slides": dict(sorted(slides.items())),
    }


def main() -> int:
    payload = build_design_dna()
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(OUTPUT_PATH)
    print(f"design_dna_slides={len(payload['slides'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

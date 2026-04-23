from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.reference_pipeline import LIBRARY_ROOT, load_json, write_json

OUTPUT = BASE_DIR / "config" / "template_pattern_catalog.json"


def pattern_from_record(record: dict[str, Any]) -> dict[str, Any]:
    identity = record.get("identity", {})
    slide_id = identity.get("slide_id")
    semantic = record.get("semantic_seed", {})
    category = semantic.get("initial_category_guess", {}).get("value", "general")
    story_role = semantic.get("initial_story_role_guess", {}).get("value", "content")
    visual = record.get("visual_structure", {})
    style = record.get("style_system", {})
    counts = record.get("deterministic_counts", {})
    return {
        "pattern_id": f"pattern_{slide_id}",
        "pattern_name": f"{category} / {story_role}",
        "based_on_slide_ids": [slide_id],
        "category": category,
        "layout_type": visual.get("layout_type", "unknown"),
        "story_role": story_role,
        "recommended_audience": [],
        "recommended_deck_type": [record.get("deck_context", {}).get("deck_type_primary", "unknown")],
        "placeholder_roles": [],
        "text_budget": {
            "text_shape_count": counts.get("text_shape_count", 0)
        },
        "image_budget": {
            "picture_count": counts.get("picture_count", 0)
        },
        "chart_budget": {
            "chart_count": counts.get("chart_count", 0),
            "table_count": counts.get("table_count", 0)
        },
        "style_rules": {
            "font_families": style.get("font_families", []),
            "visual_density": visual.get("visual_density", "unknown"),
        },
        "best_for": record.get("reuse_and_graph_hints", {}).get("best_for", []),
        "avoid_for": record.get("reuse_and_graph_hints", {}).get("avoid_for", []),
        "promotion_status": "analysis_only",
    }


def build_catalog() -> dict[str, Any]:
    patterns: list[dict[str, Any]] = []
    for path in sorted((LIBRARY_ROOT / "good" / "metadata").glob("*.json")):
        metadata = load_json(path)
        for record in metadata.get("slides", []):
            patterns.append(pattern_from_record(record))
    return {
        "schema_version": "1.0",
        "generated_from": ["assets/slides/library/good/metadata/*.json"],
        "patterns": sorted(patterns, key=lambda item: item["pattern_id"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build template pattern catalog from reviewed good reference metadata.")
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args(argv)
    output = Path(args.output)
    if not output.is_absolute():
        output = (BASE_DIR / output).resolve()
    catalog = build_catalog()
    write_json(output, catalog)
    print(f"patterns={len(catalog['patterns'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

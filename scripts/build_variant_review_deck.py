from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.build_deck import build_deck_from_spec, resolve_path

DEFAULT_INPUT = BASE_DIR / "data" / "specs" / "variant_review_sample.json"
EXPANDED_SPEC_PATH = BASE_DIR / "outputs" / "reports" / "variant_review_expanded_spec.json"
RATIONALE_MD_PATH = BASE_DIR / "outputs" / "reports" / "variant_review_rationale.md"
RATIONALE_JSON_PATH = BASE_DIR / "outputs" / "reports" / "variant_review_rationale.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def config_path(config_dir: Path, value: str) -> str:
    return str(resolve_path(config_dir, value))


def expand_variant_spec(config: dict[str, Any], config_dir: Path) -> dict[str, Any]:
    shared_content = dict(config.get("shared_content", {}))
    slides = []
    for variant in config.get("variants", []):
        text_slots = dict(shared_content)
        text_slots.update(variant.get("text_slots", {}))
        slides.append(
            {
                "layout": "template_slide",
                "slide_selector": variant["slide_selector"],
                "text_slots": text_slots,
                "clear_unfilled_slots": True,
            }
        )
    return {
        "$schema": "../../config/deck_spec.schema.json",
        "name": config.get("name", "Variant Review Deck"),
        "theme_path": config_path(config_dir, config["theme_path"]),
        "reference_catalog_path": config_path(config_dir, config.get("reference_catalog_path", "../../config/reference_catalog.json")),
        "blueprint_path": config_path(config_dir, config.get("blueprint_path", "../../config/template_blueprints.json")),
        "output_path": config_path(config_dir, config["output_path"]),
        "slides": slides,
    }


def write_expanded_spec(spec: dict[str, Any]) -> None:
    EXPANDED_SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPANDED_SPEC_PATH.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_deck_rationale(output_path: Path) -> dict[str, Any]:
    report_path = BASE_DIR / "outputs" / "reports" / f"{output_path.stem}_slide_selection_rationale.json"
    return load_json(report_path)


def write_variant_rationale(config: dict[str, Any], deck_rationale: dict[str, Any], output_path: Path) -> None:
    variants = config.get("variants", [])
    slides = deck_rationale.get("slides", [])
    recommended = config.get("recommended_variant")
    rows = []
    for variant, slide in zip(variants, slides, strict=False):
        rows.append(
            {
                "variant_id": variant.get("variant_id"),
                "label": variant.get("label"),
                "strategy": variant.get("strategy"),
                "selected_template_key": slide.get("selected_template_key"),
                "selected_library": slide.get("selected_library"),
                "selected_variant": slide.get("selected_variant"),
                "confidence": slide.get("confidence"),
                "recommended": variant.get("variant_id") == recommended,
                "selection_factors": slide.get("selection_factors", {}),
            }
        )

    payload = {
        "deck": output_path.as_posix(),
        "recommended_variant": recommended,
        "variants": rows,
    }
    RATIONALE_JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Variant Review Rationale",
        "",
        f"- Deck: `{output_path.name}`",
        f"- Recommended variant: `{recommended}`",
        "",
        "| Variant | Label | Selected template | Library | Template variant | Confidence | Recommendation |",
        "| --- | --- | --- | --- | --- | ---: | --- |",
    ]
    for row in rows:
        confidence = "" if row.get("confidence") is None else f"{float(row['confidence']):.2f}"
        recommendation = "default" if row.get("recommended") else "alternative"
        lines.append(
            f"| {row.get('variant_id')} | {row.get('label')} | {row.get('selected_template_key')} | "
            f"{row.get('selected_library')} | {row.get('selected_variant')} | {confidence} | {recommendation} |"
        )

    lines.extend(["", "## Strategy Notes", ""])
    for row in rows:
        lines.append(f"- `{row.get('variant_id')}`: {row.get('strategy')}")
    RATIONALE_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    input_path = Path(argv[0]).resolve() if argv else DEFAULT_INPUT
    config = load_json(input_path)
    expanded_spec = expand_variant_spec(config, input_path.parent)
    write_expanded_spec(expanded_spec)
    output_path = build_deck_from_spec(EXPANDED_SPEC_PATH)
    original_dir = input_path.parent
    configured_output = resolve_path(original_dir, config["output_path"])
    if output_path != configured_output:
        raise RuntimeError(f"Unexpected variant output path: {output_path} != {configured_output}")
    deck_rationale = load_deck_rationale(output_path)
    write_variant_rationale(config, deck_rationale, output_path)
    print(output_path)
    print(RATIONALE_MD_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

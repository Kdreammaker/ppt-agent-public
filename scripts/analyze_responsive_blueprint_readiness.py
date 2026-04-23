from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pptx import Presentation

BASE_DIR = Path(__file__).resolve().parents[1]
EMU_PER_INCH = 914400

SOURCE_CANVAS = {
    "aspect_ratio": "16:9",
    "width_in": 13.333,
    "height_in": 7.5,
}

TARGET_CANVASES = {
    "4:3": {"width_in": 10.0, "height_in": 7.5},
    "9:16": {"width_in": 4.219, "height_in": 7.5},
}

BOUNDS_FIELDS = (
    "editable_text_slots",
    "editable_image_slots",
    "editable_chart_slots",
    "editable_table_slots",
    "overlay_safe_zones",
)

ZONE_FIELDS = ("header_zone", "footer_zone", "page_zone")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def inches(value: int) -> float:
    return round(value / EMU_PER_INCH, 3)


def rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return resolved.as_posix()


def normalize_bounds(bounds: dict[str, Any], canvas: dict[str, float]) -> dict[str, float]:
    width = float(canvas["width_in"])
    height = float(canvas["height_in"])
    return {
        "left_pct": round(float(bounds["left"]) / width, 6),
        "top_pct": round(float(bounds["top"]) / height, 6),
        "width_pct": round(float(bounds["width"]) / width, 6),
        "height_pct": round(float(bounds["height"]) / height, 6),
    }


def project_bounds(normalized: dict[str, float], target: dict[str, float]) -> dict[str, float]:
    return {
        "left": round(normalized["left_pct"] * float(target["width_in"]), 3),
        "top": round(normalized["top_pct"] * float(target["height_in"]), 3),
        "width": round(normalized["width_pct"] * float(target["width_in"]), 3),
        "height": round(normalized["height_pct"] * float(target["height_in"]), 3),
    }


def risk_flags(bounds: dict[str, float], target: dict[str, float]) -> list[str]:
    flags: list[str] = []
    right = bounds["left"] + bounds["width"]
    bottom = bounds["top"] + bounds["height"]
    if right > float(target["width_in"]):
        flags.append("exceeds_target_width")
    if bottom > float(target["height_in"]):
        flags.append("exceeds_target_height")
    if bounds["width"] < 0.55:
        flags.append("too_narrow_for_text_or_image")
    if bounds["height"] < 0.18:
        flags.append("too_short_for_text")
    return flags


def iter_bound_records(blueprint: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for field in BOUNDS_FIELDS:
        for index, item in enumerate(blueprint.get(field, []), start=1):
            bounds = item.get("bounds")
            if isinstance(bounds, dict):
                records.append(
                    {
                        "source": field,
                        "index": index,
                        "slot": item.get("slot"),
                        "bounds": bounds,
                    }
                )
    for field in ZONE_FIELDS:
        bounds = blueprint.get(field)
        if isinstance(bounds, dict):
            records.append(
                {
                    "source": field,
                    "index": 1,
                    "slot": field,
                    "bounds": bounds,
                }
            )
    return records


def source_canvas_for_blueprint(blueprint: dict[str, Any]) -> dict[str, Any]:
    library_path = blueprint.get("library_path")
    if not library_path:
        return SOURCE_CANVAS
    path = (BASE_DIR / str(library_path)).resolve()
    if not path.exists():
        return SOURCE_CANVAS
    prs = Presentation(str(path))
    width = inches(prs.slide_width)
    height = inches(prs.slide_height)
    return {
        "aspect_ratio": "16:9",
        "width_in": width,
        "height_in": height,
        "library_path": rel(path),
    }


def summarize_blueprints(blueprints: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for slide_id, blueprint in sorted(blueprints.get("slides", {}).items()):
        records = iter_bound_records(blueprint)
        rows.append(
            {
                "slide_id": slide_id,
                "template_key": blueprint.get("template_key"),
                "scope": blueprint.get("scope"),
                "purpose": blueprint.get("purpose"),
                "absolute_bounds_records": len(records),
                "slot_records": sum(1 for record in records if str(record["source"]).startswith("editable_")),
                "zone_records": sum(1 for record in records if str(record["source"]).endswith("_zone")),
                "image_slot_records": len(blueprint.get("editable_image_slots", [])),
            }
        )
    return rows


def prototype_conversion(blueprints: dict[str, Any], template_key: str) -> dict[str, Any]:
    matches = [
        blueprint
        for blueprint in blueprints.get("slides", {}).values()
        if blueprint.get("template_key") == template_key or blueprint.get("slide_id") == template_key
    ]
    if not matches:
        raise ValueError(f"Template key or slide id not found: {template_key}")
    blueprint = matches[0]
    source_canvas = source_canvas_for_blueprint(blueprint)
    records = iter_bound_records(blueprint)
    previews: list[dict[str, Any]] = []
    for record in records[:20]:
        normalized = normalize_bounds(record["bounds"], source_canvas)
        targets = {}
        for target_name, target_canvas in TARGET_CANVASES.items():
            projected = project_bounds(normalized, target_canvas)
            targets[target_name] = {
                "bounds": projected,
                "risk_flags": risk_flags(projected, target_canvas),
            }
        previews.append(
            {
                "source": record["source"],
                "slot": record.get("slot"),
                "source_bounds_in": record["bounds"],
                "normalized": normalized,
                "target_previews": targets,
            }
        )
    return {
        "template_key": blueprint.get("template_key"),
        "slide_id": blueprint.get("slide_id"),
        "source_canvas": source_canvas,
        "target_canvases": TARGET_CANVASES,
        "policy": "diagnostic_only_no_production_aspect_enablement",
        "records_previewed": len(previews),
        "records_total": len(records),
        "previews": previews,
    }


def build_report(blueprint_path: Path, template_key: str) -> dict[str, Any]:
    blueprints = load_json(blueprint_path)
    rows = summarize_blueprints(blueprints)
    total_absolute = sum(row["absolute_bounds_records"] for row in rows)
    by_scope: dict[str, int] = {}
    for row in rows:
        key = str(row.get("scope") or "unknown")
        by_scope[key] = by_scope.get(key, 0) + row["absolute_bounds_records"]
    return {
        "schema_version": "1.0",
        "blueprint_path": rel(blueprint_path),
        "summary": {
            "slide_count": len(rows),
            "absolute_bounds_records": total_absolute,
            "bounds_by_scope": dict(sorted(by_scope.items())),
            "current_production_policy": "16:9_only",
            "production_enablement": "blocked_until_dedicated_aspect_templates_and_blueprints_exist",
        },
        "prototype_conversion": prototype_conversion(blueprints, template_key),
        "slides": rows,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    proto = report["prototype_conversion"]
    lines = [
        "# Responsive Blueprint Readiness",
        "",
        "## Summary",
        "",
        f"- Blueprint file: `{report['blueprint_path']}`",
        f"- Slides inspected: `{summary['slide_count']}`",
        f"- Absolute bounds records: `{summary['absolute_bounds_records']}`",
        f"- Bounds by scope: `{summary['bounds_by_scope']}`",
        f"- Production policy: `{summary['current_production_policy']}`",
        f"- Enablement: `{summary['production_enablement']}`",
        "",
        "## Prototype Conversion",
        "",
        f"- Template: `{proto['template_key']}`",
        f"- Slide id: `{proto['slide_id']}`",
        f"- Source canvas: `{proto['source_canvas']['width_in']} x {proto['source_canvas']['height_in']} in`",
        f"- Policy: `{proto['policy']}`",
        f"- Previewed records: `{proto['records_previewed']}` of `{proto['records_total']}`",
        "",
        "| Source | Slot | 4:3 risks | 9:16 risks |",
        "| --- | --- | --- | --- |",
    ]
    for item in proto["previews"]:
        risks_4_3 = ", ".join(item["target_previews"]["4:3"]["risk_flags"]) or "none"
        risks_9_16 = ", ".join(item["target_previews"]["9:16"]["risk_flags"]) or "none"
        lines.append(f"| `{item['source']}` | `{item.get('slot')}` | {risks_4_3} | {risks_9_16} |")
    lines.extend(
        [
            "",
            "## Required Migration Work",
            "",
            "- Create dedicated 4:3 and 9:16 template libraries instead of stretching current 16:9 layouts.",
            "- Store normalized and aspect-specific bounds side by side, with explicit safe zones per aspect.",
            "- Add aspect-aware selector constraints before any non-16:9 production build is allowed.",
            "- Add visual smoke and drift baselines for each newly supported aspect.",
            "- Keep current 4:3 fail-fast behavior until those assets and validators exist.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze readiness for responsive/aspect-aware template blueprints.")
    parser.add_argument("--blueprint-path", default="config/template_blueprints.json")
    parser.add_argument("--template-key", default="channel_cover_v1")
    parser.add_argument("--output-json", default="outputs/reports/responsive_blueprint_readiness.json")
    parser.add_argument("--output-md", default="outputs/reports/responsive_blueprint_readiness.md")
    args = parser.parse_args(argv)

    blueprint_path = (BASE_DIR / args.blueprint_path).resolve()
    report = build_report(blueprint_path, args.template_key)
    output_json = (BASE_DIR / args.output_json).resolve()
    output_md = (BASE_DIR / args.output_md).resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(output_md, report)
    print(output_json)
    print(output_md)
    print(
        "responsive_blueprint_readiness="
        f"slides={report['summary']['slide_count']} "
        f"absolute_bounds={report['summary']['absolute_bounds_records']} "
        f"prototype={report['prototype_conversion']['template_key']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pptx import Presentation

BASE_DIR = Path(__file__).resolve().parents[1]

EMU_PER_INCH = 914400
RATIO_16_9 = 16 / 9
RATIO_4_3 = 4 / 3
RATIO_TOLERANCE = 0.02


def inches(value: int) -> float:
    return round(value / EMU_PER_INCH, 3)


def classify_ratio(width_in: float, height_in: float) -> str:
    if height_in == 0:
        return "unknown"
    ratio = width_in / height_in
    if abs(ratio - RATIO_16_9) <= RATIO_TOLERANCE:
        return "16:9"
    if abs(ratio - RATIO_4_3) <= RATIO_TOLERANCE:
        return "4:3"
    return "custom"


def inspect_pptx(path: Path) -> dict[str, Any]:
    prs = Presentation(str(path))
    width_in = inches(prs.slide_width)
    height_in = inches(prs.slide_height)
    return {
        "path": path.relative_to(BASE_DIR).as_posix() if path.is_relative_to(BASE_DIR) else path.as_posix(),
        "slide_width_in": width_in,
        "slide_height_in": height_in,
        "ratio": round(width_in / height_in, 4) if height_in else None,
        "aspect_class": classify_ratio(width_in, height_in),
        "slide_count": len(prs.slides),
    }


def inspect_many(paths: list[Path]) -> list[dict[str, Any]]:
    return [inspect_pptx(path) for path in sorted(paths)]


def count_by_aspect(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("aspect_class") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def detect_fixed_canvas() -> dict[str, Any]:
    build_path = BASE_DIR / "scripts" / "build_deck.py"
    text = build_path.read_text(encoding="utf-8")
    return {
        "script": "scripts/build_deck.py",
        "sets_slide_width_13_33": "prs.slide_width = Inches(13.33)" in text,
        "sets_slide_height_7_5": "prs.slide_height = Inches(7.5)" in text,
        "current_policy": "fixed_16_9_canvas"
        if "prs.slide_width = Inches(13.33)" in text and "prs.slide_height = Inches(7.5)" in text
        else "inspect_manually",
    }


def support_summary(template_rows: list[dict[str, Any]], generated_rows: list[dict[str, Any]]) -> dict[str, Any]:
    template_counts = count_by_aspect(template_rows)
    generated_counts = count_by_aspect(generated_rows)
    all_templates_16_9 = bool(template_rows) and template_counts == {"16:9": len(template_rows)}
    generated_include_16_9 = generated_counts.get("16:9", 0) > 0
    templates_include_4_3 = template_counts.get("4:3", 0) > 0
    return {
        "template_aspects": template_counts,
        "generated_deck_aspects": generated_counts,
        "build_canvas": detect_fixed_canvas(),
        "support_16_9": "verified" if all_templates_16_9 and generated_include_16_9 else "needs_review",
        "support_4_3": "requires_dedicated_templates" if not templates_include_4_3 else "template_library_present",
        "policy": (
            "Current production support is 16:9. 4:3 output should fail fast or use dedicated 4:3 "
            "template libraries with aspect-specific blueprints; automatic stretching or cropping is not "
            "accepted as production-quality compatibility."
        ),
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# Template Aspect Ratio Audit",
        "",
        "## Summary",
        "",
        f"- Template aspects: `{summary['template_aspects']}`",
        f"- Generated deck aspects: `{summary['generated_deck_aspects']}`",
        f"- 16:9 support: `{summary['support_16_9']}`",
        f"- 4:3 support: `{summary['support_4_3']}`",
        f"- Build canvas policy: `{summary['build_canvas']['current_policy']}`",
        "",
        "## Policy",
        "",
        summary["policy"],
        "",
        "## Curated Template Libraries",
        "",
        "| File | Slides | Size | Aspect |",
        "| --- | ---: | --- | --- |",
    ]
    for row in payload["template_libraries"]:
        lines.append(
            f"| `{row['path']}` | {row['slide_count']} | "
            f"{row['slide_width_in']} x {row['slide_height_in']} in | {row['aspect_class']} |"
        )
    lines.extend(
        [
            "",
            "## Generated Decks",
            "",
            "| File | Slides | Size | Aspect |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for row in payload["generated_decks"]:
        lines.append(
            f"| `{row['path']}` | {row['slide_count']} | "
            f"{row['slide_width_in']} x {row['slide_height_in']} in | {row['aspect_class']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template-root", default="assets/slides/templates/decks")
    parser.add_argument("--generated-root", default="outputs/decks")
    parser.add_argument("--output-json", default="outputs/reports/template_aspect_ratio_audit.json")
    parser.add_argument("--output-md", default="outputs/reports/template_aspect_ratio_audit.md")
    args = parser.parse_args(argv)

    template_root = (BASE_DIR / args.template_root).resolve()
    generated_root = (BASE_DIR / args.generated_root).resolve()
    template_paths = list(template_root.rglob("*.pptx"))
    generated_paths = list(generated_root.rglob("*.pptx")) if generated_root.exists() else []

    template_rows = inspect_many(template_paths)
    generated_rows = inspect_many(generated_paths)
    payload = {
        "summary": support_summary(template_rows, generated_rows),
        "template_libraries": template_rows,
        "generated_decks": generated_rows,
    }

    output_json = (BASE_DIR / args.output_json).resolve()
    output_md = (BASE_DIR / args.output_md).resolve()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(output_md, payload)
    print(output_json)
    print(output_md)
    print(f"template_aspects={payload['summary']['template_aspects']}")
    print(f"generated_deck_aspects={payload['summary']['generated_deck_aspects']}")
    print(f"support_16_9={payload['summary']['support_16_9']}")
    print(f"support_4_3={payload['summary']['support_4_3']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

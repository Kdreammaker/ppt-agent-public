from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Literal

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.compose_deck_spec_from_intake import compose_spec, load_json as load_composer_json, slugify
from system.blueprint_loader import load_blueprints
from system.deck_models import validate_deck_spec
from system.intake_models import validate_deck_intake

InputKind = Literal["auto", "spec", "intake"]
ApprovalMode = Literal["assistant", "auto"]
DEFAULT_REPORT_ROOT = BASE_DIR / "outputs" / "reports"
BLUEPRINT_MODE_POLICY = BASE_DIR / "config" / "blueprint_mode_policy.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_blueprint_mode_policy() -> dict[str, Any]:
    if BLUEPRINT_MODE_POLICY.exists():
        data = load_json(BLUEPRINT_MODE_POLICY)
        if isinstance(data, dict):
            return data
    return {
        "schema_version": "1.0",
        "policy_id": "assistant_auto_blueprint_policy",
        "modes": {
            "assistant": {
                "default_visible": True,
                "default_action": "show_blueprint",
                "blocking": True,
                "skip_allowed": True,
                "requires_explicit_continue_for_build": True,
            },
            "auto": {
                "default_visible": False,
                "default_action": "skip_blueprint",
                "blocking": False,
                "skip_allowed": True,
            },
        },
    }


def resolve_path(base_dir: Path, value: str | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    return path if path.is_absolute() else (base_dir / path).resolve()


def base_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return Path(os.path.relpath(resolved, BASE_DIR)).as_posix()


def detect_input_kind(data: dict[str, Any], requested: InputKind) -> Literal["spec", "intake"]:
    if requested in {"spec", "intake"}:
        return requested
    if "slides" in data and "theme_path" in data:
        return "spec"
    if "output_preferences" in data and "slides" not in data:
        return "intake"
    raise ValueError("Could not detect input kind. Use --kind spec or --kind intake.")


def load_spec(input_path: Path, requested_kind: InputKind) -> tuple[dict[str, Any], Path, str]:
    input_path = input_path.resolve()
    data = load_json(input_path)
    kind = detect_input_kind(data, requested_kind)
    if kind == "spec":
        validate_deck_spec(data)
        return data, input_path.parent, kind
    intake = validate_deck_intake(data)
    draft_output = BASE_DIR / "outputs" / "ascii_blueprints" / f"{slugify(intake.name)}_draft_spec.json"
    spec = compose_spec(intake, input_path, draft_output)
    validate_deck_spec(spec)
    return spec, draft_output.parent, kind


def blueprint_lookup(spec: dict[str, Any], spec_dir: Path) -> dict[str, dict[str, Any]]:
    blueprint_path = resolve_path(spec_dir, spec.get("blueprint_path")) or BASE_DIR / "config" / "template_blueprints.json"
    if not blueprint_path.exists() and blueprint_path.name != "template_blueprints":
        blueprint_path = BASE_DIR / "config" / "template_blueprints.json"
    blueprints = load_blueprints(blueprint_path)
    lookup: dict[str, dict[str, Any]] = {}
    for blueprint in blueprints.get("slides", {}).values():
        if isinstance(blueprint, dict) and blueprint.get("template_key"):
            lookup[str(blueprint["template_key"])] = blueprint
    return lookup


def load_theme(spec: dict[str, Any], spec_dir: Path) -> tuple[dict[str, Any], str | None]:
    theme_path = resolve_path(spec_dir, spec.get("theme_path"))
    if theme_path is None:
        theme_path = BASE_DIR / "config" / "pptx_theme.neutral_modern.json"
    if not theme_path.exists():
        return {}, base_relative(theme_path)
    theme = load_json(theme_path)
    return theme, base_relative(theme_path)


def asset_ids_by_role(spec: dict[str, Any]) -> dict[str, str]:
    ids: dict[str, str] = {}
    intents = spec.get("asset_intents", [])
    if not isinstance(intents, list):
        return ids
    for intent in intents:
        if not isinstance(intent, dict):
            continue
        role = str(intent.get("role") or intent.get("asset_class") or "").strip()
        asset_id = str(intent.get("asset_id") or "").strip()
        if role and asset_id and role not in ids:
            ids[role] = asset_id
    return ids


def type_scale_from_theme(theme: dict[str, Any]) -> dict[str, float | int | None]:
    sizes = theme.get("sizes", {})
    if not isinstance(sizes, dict):
        sizes = {}
    return {
        "title": sizes.get("cover_title"),
        "h1": sizes.get("hero_title") or sizes.get("cover_title"),
        "h2": sizes.get("card_title"),
        "h3": sizes.get("section_header"),
        "body": sizes.get("body"),
    }


def build_style_contract(
    spec: dict[str, Any],
    *,
    spec_dir: Path,
    slides: list[dict[str, Any]],
) -> dict[str, Any]:
    theme, theme_path = load_theme(spec, spec_dir)
    colors = theme.get("colors", {}) if isinstance(theme.get("colors"), dict) else {}
    asset_ids = asset_ids_by_role(spec)
    purposes = sorted({str(slide.get("purpose") or "content") for slide in slides})
    template_keys = [str(slide.get("template_key")) for slide in slides if slide.get("template_key")]
    recipe = str(spec.get("recipe") or "unspecified")
    mode_policy = str(spec.get("mode_policy") or "unspecified")
    font_family = str(theme.get("font_family") or "Malgun Gothic")
    return {
        "schema_version": "1.0",
        "source": {
            "theme_path": theme_path,
            "asset_intent_ids": asset_ids,
            "recipe": recipe,
            "mode_policy": mode_policy,
            "template_keys": template_keys,
        },
        "color_system": {
            "primary": colors.get("primary"),
            "accent": colors.get("accent_1") or colors.get("accent"),
            "secondary": colors.get("accent_2"),
            "neutral_dark": colors.get("dark"),
            "neutral_muted": colors.get("gray"),
            "surface": colors.get("white") or colors.get("light"),
            "panel": colors.get("panel"),
            "border": colors.get("border"),
            "rationale": "Use the theme palette as the deck-wide color system so slide choices stay consistent across structure approval and final rendering.",
        },
        "typography": {
            "title_font": font_family,
            "heading_font": font_family,
            "body_font": font_family,
            "fallback": "PowerPoint default sans-serif if the named font is unavailable.",
            "rationale": "Use one CJK-safe family for title, heading, and body text to reduce font substitution risk across Windows and shared PPTX handoff.",
        },
        "type_scale": type_scale_from_theme(theme),
        "template_style_rationale": (
            f"Selected for {recipe} in {mode_policy} mode with slide purposes "
            f"{', '.join(purposes) if purposes else 'content'}; use this contract as deck-level style guidance, not as a rendered preview."
        ),
        "preview_boundary": "This style contract is generated from spec, theme, asset-intent, and template metadata. It is not a thumbnail, screenshot, rendered HTML preview, or final visual QA report.",
    }


def text_slots(slide: dict[str, Any]) -> dict[str, str]:
    raw = slide.get("text_slots", {})
    if isinstance(raw, dict):
        return {str(key): str(value) for key, value in raw.items() if str(value).strip()}
    return {}


def selector(slide: dict[str, Any]) -> dict[str, Any]:
    raw = slide.get("slide_selector", {})
    return raw if isinstance(raw, dict) else {}


def slide_purpose(slide: dict[str, Any], blueprint: dict[str, Any] | None) -> str:
    return str(selector(slide).get("purpose") or slide.get("purpose") or (blueprint or {}).get("purpose") or "content")


def slide_title(slide: dict[str, Any], index: int) -> str:
    slots = text_slots(slide)
    for key in ("title", "headline", "hero_title", "cover_title", "section_title"):
        if slots.get(key):
            return slots[key]
    values = [str(item) for item in slide.get("text_values", []) if str(item).strip()]
    return values[0] if values else f"Slide {index}"


def slide_subtitle(slide: dict[str, Any]) -> str:
    slots = text_slots(slide)
    for key in ("subtitle", "kicker", "section_header", "summary", "body"):
        if slots.get(key):
            return slots[key]
    return ""


def slot_names(slide: dict[str, Any], blueprint: dict[str, Any] | None, key: str, blueprint_key: str) -> list[str]:
    names: set[str] = set()
    raw = slide.get(key, {})
    if isinstance(raw, dict):
        names.update(str(item) for item in raw.keys())
    if blueprint:
        for item in blueprint.get(blueprint_key, []):
            if isinstance(item, dict) and item.get("slot"):
                names.add(str(item["slot"]))
    return sorted(names)


def region_summary(slide: dict[str, Any], blueprint: dict[str, Any] | None) -> dict[str, list[str]]:
    text = sorted(text_slots(slide))
    values = slide.get("text_values", [])
    if isinstance(values, list) and values:
        text.extend(f"text_value_{index}" for index, _ in enumerate(values, start=1))
    return {
        "title": [name for name in text if name in {"title", "headline", "hero_title", "cover_title", "section_title", "subtitle"}],
        "content": [name for name in text if name not in {"title", "headline", "hero_title", "cover_title", "section_title", "subtitle"}],
        "image": slot_names(slide, blueprint, "image_slots", "editable_image_slots"),
        "chart": slot_names(slide, blueprint, "chart_slots", "editable_chart_slots"),
        "table": slot_names(slide, blueprint, "table_slots", "editable_table_slots"),
    }


def truncate(value: str, width: int) -> str:
    clean = re.sub(r"\s+", " ", value).strip()
    if len(clean) <= width:
        return clean
    return clean[: max(0, width - 3)] + "..."


def render_row(columns: list[str], widths: list[int]) -> str:
    cells = [truncate(value, width).ljust(width) for value, width in zip(columns, widths)]
    return "| " + " | ".join(cells) + " |"


def render_rule(widths: list[int]) -> str:
    return "+-" + "-+-".join("-" * width for width in widths) + "-+"


def region_line(label: str, values: list[str]) -> str:
    return f"  {label.ljust(7)}: {', '.join(values) if values else '-'}"


def build_blueprint_payload(
    spec: dict[str, Any],
    *,
    spec_dir: Path,
    input_path: Path,
    input_kind: str,
    approval_mode: ApprovalMode,
) -> dict[str, Any]:
    blueprints = blueprint_lookup(spec, spec_dir)
    slides = []
    for index, slide in enumerate(spec.get("slides", []), start=1):
        template_key = str(slide.get("template_key") or "")
        blueprint = blueprints.get(template_key)
        regions = region_summary(slide, blueprint)
        slides.append(
            {
                "slide_number": index,
                "purpose": slide_purpose(slide, blueprint),
                "template_key": template_key or None,
                "layout": slide.get("layout"),
                "title": slide_title(slide, index),
                "subtitle": slide_subtitle(slide),
                "regions": regions,
            }
        )
    mode_policy = load_blueprint_mode_policy()
    return {
        "schema_version": "1.0",
        "blueprint_role": "pre_build_structure_approval",
        "input_path": base_relative(input_path),
        "input_kind": input_kind,
        "deck_name": spec.get("name"),
        "approval_mode": approval_mode,
        "final_file_generation_required": False,
        "final_outputs_generated": [],
        "preview_kind": "structure_only_ascii",
        "visual_preview_available": False,
        "visual_preview_note": "This blueprint lists slide order, template keys, and editable regions only. It is not a rendered visual preview, thumbnail, or final design review.",
        "style_contract": build_style_contract(spec, spec_dir=spec_dir, slides=slides),
        "checkpoint_policy": mode_policy,
        "slides": slides,
        "summary": {
            "slide_count": len(slides),
            "image_placeholders": sum(len(slide["regions"]["image"]) for slide in slides),
            "chart_placeholders": sum(len(slide["regions"]["chart"]) for slide in slides),
            "table_placeholders": sum(len(slide["regions"]["table"]) for slide in slides),
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    widths = [4, 12, 34, 36]
    style = payload.get("style_contract", {}) if isinstance(payload.get("style_contract"), dict) else {}
    color_system = style.get("color_system", {}) if isinstance(style.get("color_system"), dict) else {}
    typography = style.get("typography", {}) if isinstance(style.get("typography"), dict) else {}
    type_scale = style.get("type_scale", {}) if isinstance(style.get("type_scale"), dict) else {}
    lines = [
        f"# ASCII Blueprint: {payload.get('deck_name') or 'Untitled Deck'}",
        "",
        f"- Role: `{payload['blueprint_role']}`",
        f"- Input: `{payload['input_path']}` ({payload['input_kind']})",
        f"- Approval mode: `{payload['approval_mode']}`",
        "- No PPTX/HTML files generated by this command.",
        "- Preview kind: `structure_only_ascii`",
        "- Visual preview: not generated by this command.",
        "",
        "## What This Blueprint Is",
        "",
        "This file is a pre-build structure checkpoint. It shows slide order, selected templates, titles, and editable text/image/chart/table regions so an operator can approve the story structure before final files are built.",
        "",
        "## What This Blueprint Is Not",
        "",
        "This file is not a visual preview, screenshot, thumbnail, rendered HTML view, or final design QA report. It does not show exact slide appearance, image crops, typography, spacing, or element geometry. Use a later HTML/PPTX preview or rendered thumbnail pass for visual approval.",
        "",
        "## Style Contract",
        "",
        "This deck-level style contract is generated from the spec, theme, asset-intent, and template metadata. Treat it like a slide `global.css` for human-AI coordination, not as a rendered preview.",
        "",
        "### Color System",
        "",
        f"- Primary: `{color_system.get('primary') or 'unspecified'}`",
        f"- Accent: `{color_system.get('accent') or 'unspecified'}`",
        f"- Secondary: `{color_system.get('secondary') or 'unspecified'}`",
        f"- Neutral dark: `{color_system.get('neutral_dark') or 'unspecified'}`",
        f"- Neutral muted: `{color_system.get('neutral_muted') or 'unspecified'}`",
        f"- Surface: `{color_system.get('surface') or 'unspecified'}`",
        f"- Panel: `{color_system.get('panel') or 'unspecified'}`",
        f"- Border: `{color_system.get('border') or 'unspecified'}`",
        f"- Rationale: {color_system.get('rationale') or 'Use theme defaults consistently across the deck.'}",
        "",
        "### Typography",
        "",
        f"- Title font: `{typography.get('title_font') or 'unspecified'}`",
        f"- Heading font: `{typography.get('heading_font') or 'unspecified'}`",
        f"- Body font: `{typography.get('body_font') or 'unspecified'}`",
        f"- Fallback: {typography.get('fallback') or 'Use PowerPoint default sans-serif if unavailable.'}",
        f"- Rationale: {typography.get('rationale') or 'Use consistent typography across slides.'}",
        "",
        "### Type Scale",
        "",
        f"- Title: `{type_scale.get('title') or 'unspecified'}` pt",
        f"- H1: `{type_scale.get('h1') or 'unspecified'}` pt",
        f"- H2: `{type_scale.get('h2') or 'unspecified'}` pt",
        f"- H3: `{type_scale.get('h3') or 'unspecified'}` pt",
        f"- Body: `{type_scale.get('body') or 'unspecified'}` pt",
        "",
        "### Style Rationale And Preview Boundary",
        "",
        f"- Template/style rationale: {style.get('template_style_rationale') or 'Use selected templates and theme defaults.'}",
        f"- Preview boundary: {style.get('preview_boundary') or payload.get('visual_preview_note')}",
        "",
        "## Slide Order",
        "",
        render_rule(widths),
        render_row(["No", "Purpose", "Title", "Regions"], widths),
        render_rule(widths),
    ]
    for slide in payload["slides"]:
        regions = slide["regions"]
        active = [
            label
            for label, values in (
                ("title", regions["title"]),
                ("content", regions["content"]),
                ("image", regions["image"]),
                ("chart", regions["chart"]),
                ("table", regions["table"]),
            )
            if values
        ]
        lines.append(
            render_row(
                [
                    f"{slide['slide_number']:02d}",
                    slide["purpose"],
                    slide["title"],
                    ", ".join(active) or "structure",
                ],
                widths,
            )
        )
    lines.extend([render_rule(widths), "", "## Slide Details", ""])
    for slide in payload["slides"]:
        regions = slide["regions"]
        lines.extend(
            [
                f"### Slide {slide['slide_number']:02d}: {slide['purpose']}",
                "",
                f"- Template: `{slide.get('template_key') or 'selector-driven'}`",
                f"- Layout: `{slide.get('layout')}`",
                f"- Title: {slide['title']}",
            ]
        )
        if slide.get("subtitle"):
            lines.append(f"- Subtitle: {slide['subtitle']}")
        lines.extend(
            [
                "",
                "```text",
                "+---------------- SLIDE STRUCTURE ----------------+",
                region_line("TITLE", regions["title"]),
                region_line("CONTENT", regions["content"]),
                region_line("IMAGE", regions["image"]),
                region_line("CHART", regions["chart"]),
                region_line("TABLE", regions["table"]),
                "+-------------------------------------------------+",
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Approval Checkpoint",
            "",
            "- Assistant Mode: show this structure blueprint before final file generation. Build PPTX/HTML only after the user or operator explicitly approves, revises, continues, or skips the checkpoint.",
            "- Auto Mode: skip this checkpoint by default unless a workflow explicitly requests a blueprint report.",
            "- This command itself never creates PPTX/HTML. Build commands may create final files only after the structure checkpoint is accepted, intentionally skipped, or bypassed by Auto policy.",
            "",
        ]
    )
    return "\n".join(lines)


def render_ascii_blueprint(
    input_path: Path,
    *,
    kind: InputKind = "auto",
    approval_mode: ApprovalMode = "assistant",
    output_md: Path | None = None,
    output_json: Path | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    input_path = input_path.resolve()
    spec, spec_dir, input_kind = load_spec(input_path, kind)
    deck_id = slugify(str(spec.get("project_id") or spec.get("name") or input_path.stem))
    output_md = (output_md or DEFAULT_REPORT_ROOT / f"{deck_id}_ascii_blueprint.md").resolve()
    output_json = (output_json or DEFAULT_REPORT_ROOT / f"{deck_id}_ascii_blueprint.json").resolve()
    payload = build_blueprint_payload(
        spec,
        spec_dir=spec_dir,
        input_path=input_path,
        input_kind=input_kind,
        approval_mode=approval_mode,
    )
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(payload), encoding="utf-8")
    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_md, output_json, payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render an ASCII pre-build slide blueprint from an intake or deck spec.")
    parser.add_argument("input_path")
    parser.add_argument("--kind", choices=["auto", "spec", "intake"], default="auto")
    parser.add_argument("--approval-mode", choices=["assistant", "auto"], default="assistant")
    parser.add_argument("--output-md", default=None)
    parser.add_argument("--output-json", default=None)
    args = parser.parse_args(argv)

    md_path, json_path, payload = render_ascii_blueprint(
        Path(args.input_path),
        kind=args.kind,
        approval_mode=args.approval_mode,
        output_md=Path(args.output_md) if args.output_md else None,
        output_json=Path(args.output_json) if args.output_json else None,
    )
    print(md_path)
    print(json_path)
    print(
        "ascii_blueprint="
        f"slides={payload['summary']['slide_count']} "
        f"images={payload['summary']['image_placeholders']} "
        f"charts={payload['summary']['chart_placeholders']} "
        f"tables={payload['summary']['table_placeholders']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

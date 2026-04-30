from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.intake_models import validate_deck_intake
from scripts.compose_deck_spec_from_intake import (
    desired_slide_count,
    include_items,
    mode_policy_for_intake,
    purpose_sequence,
    slugify,
)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def base_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except ValueError:
        return os.path.relpath(path.resolve(), BASE_DIR.resolve()).replace("\\", "/")


def sentence(value: str, fallback: str) -> str:
    compact = " ".join(str(value or "").split())
    return compact.rstrip(".") + "." if compact else fallback


def title_for(index: int, purpose: str, item_titles: list[str], intake_name: str, *, is_korean: bool = False) -> str:
    if index == 0:
        return intake_name
    if index == 1 and purpose == "toc":
        return "목차" if is_korean else "Agenda"
    item_index = max(0, min(index - 2, len(item_titles) - 1))
    if item_titles and index >= 2:
        return item_titles[item_index]
    return purpose.replace("_", " ").title()


def asset_intents_for_slide(slide_number: int, purpose: str) -> list[dict[str, Any]]:
    if slide_number == 1:
        return [{"role": "theme", "asset_class": "theme", "source_type": "metadata_only"}]
    if purpose in {"chart", "analysis", "market", "summary"}:
        return [{"role": "chart_preset", "asset_class": "chart_preset", "source_type": "metadata_only"}]
    return [{"role": "image_placeholder", "asset_class": "image", "source_type": "user_supplied_or_generated"}]


def approval_state_for(mode: str) -> dict[str, Any]:
    if mode == "assistant":
        return {
            "status": "pending",
            "required_before_final_build": True,
            "approved_checkpoints": [],
            "notes": "Assistant final build waits for configured review checkpoints.",
        }
    return {
        "status": "not_required",
        "required_before_final_build": False,
        "approved_checkpoints": [],
        "notes": "Auto Mode records assumptions and proceeds unless a blocking gate is hit.",
    }


def compose_plan(intake_path: Path, output_path: Path, mode_override: str | None = None) -> dict[str, Any]:
    raw = load_json(intake_path)
    intake = validate_deck_intake(raw)
    project_id = slugify(intake.name)
    count = desired_slide_count(intake)
    purposes = purpose_sequence(intake, count)
    items = include_items(intake)
    item_titles = [item.title for item in items]
    mode = mode_override or mode_policy_for_intake(intake)
    if mode not in {"auto", "assistant"}:
        raise ValueError(f"unsupported operating mode: {mode}")
    is_korean = (intake.presentation_context.locale or "").lower().startswith("ko")
    toc = [title_for(index, purpose, item_titles, intake.name, is_korean=is_korean) for index, purpose in enumerate(purposes)]
    slide_plans = []
    for index, purpose in enumerate(purposes):
        slide_number = index + 1
        title = toc[index]
        include_detail = items[index - 2].detail if index >= 2 and index - 2 < len(items) else None
        slide_plans.append(
            {
                "plan_slide_id": f"{project_id}-s{slide_number:02d}",
                "slide_number": slide_number,
                "working_title": title,
                "message": sentence(include_detail or intake.primary_goal, "State the slide message."),
                "supporting_points": item_titles[:3] if index == 1 else ([include_detail] if include_detail else item_titles[index - 2 : index + 1]),
                "visual_intent": "Use public-safe template metadata and editable slide elements; do not depend on raw private assets.",
                "layout_intent": purpose,
                "asset_intents": asset_intents_for_slide(slide_number, purpose),
                "content_budget": {
                    "max_title_chars": 72,
                    "max_body_points": 4 if str(intake.content_density.value) != "high" else 6,
                    "density": str(intake.content_density.value),
                },
            }
        )
    plan = {
        "schema_version": "1.0",
        "plan_id": f"plan.{project_id}",
        "request_id": project_id,
        "source_intake_path": base_relative(intake_path),
        "operating_mode": mode,
        "audience": intake.audience.primary,
        "goal": intake.primary_goal,
        "narrative_arc": " -> ".join(toc),
        "toc": toc,
        "slide_plans": slide_plans,
        "brand_style_intent": {
            "tone": [item.value for item in intake.tone],
            "theme_path": intake.brand_or_template_scope.theme_path,
            "preferred_scope": intake.brand_or_template_scope.preferred_scope,
            "notes": "Public-safe style intent only; private prompt packs and ranking remain outside the plan.",
        },
        "assumptions": [
            "Use the validated intake as source of truth.",
            "Keep connector and asset evidence metadata-only until explicit materialization is approved.",
            "Preserve plan IDs in generated specs and reports.",
        ],
        "approval_state": approval_state_for(mode),
    }
    write_json(output_path, plan)
    write_markdown(output_path.with_suffix(".md"), plan)
    return plan


def write_markdown(path: Path, plan: dict[str, Any]) -> None:
    lines = [
        f"# Deck Plan: {plan['request_id']}",
        "",
        f"- mode: `{plan['operating_mode']}`",
        f"- goal: {plan['goal']}",
        f"- audience: {plan['audience']}",
        f"- approval: `{plan['approval_state']['status']}`",
        "",
        "## Table Of Contents",
    ]
    for title in plan.get("toc", []):
        lines.append(f"- {title}")
    lines.append("")
    lines.append("## Slide Plans")
    for slide in plan.get("slide_plans", []):
        lines.extend(
            [
                f"### {slide['slide_number']}. {slide['working_title']}",
                "",
                f"- id: `{slide['plan_slide_id']}`",
                f"- message: {slide['message']}",
                f"- layout intent: {slide['layout_intent']}",
                f"- visual intent: {slide['visual_intent']}",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compose a deck plan before spec/rendering.")
    parser.add_argument("intake_path")
    parser.add_argument("--output", default=None)
    parser.add_argument("--operating-mode", choices=["auto", "assistant"], default=None)
    args = parser.parse_args(argv)

    intake_path = Path(args.intake_path)
    if not intake_path.is_absolute():
        intake_path = (BASE_DIR / intake_path).resolve()
    intake_data = load_json(intake_path)
    project_id = slugify(str(intake_data.get("name") or intake_path.stem))
    output = Path(args.output or f"outputs/projects/{project_id}/plans/deck_plan.json")
    if not output.is_absolute():
        output = (BASE_DIR / output).resolve()
    compose_plan(intake_path, output, args.operating_mode)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

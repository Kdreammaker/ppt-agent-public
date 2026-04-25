from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.deck_models import validate_deck_spec
from system.intake_models import validate_deck_intake
from scripts.compose_deck_spec_from_intake import append_workspace_asset_intents, compose_spec, slugify


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def base_relative(path: Path, base: Path = BASE_DIR) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return os.path.relpath(path.resolve(), base.resolve()).replace("\\", "/")


def resolve_base_relative(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (BASE_DIR / path).resolve()


def apply_plan_to_spec(spec: dict[str, Any], plan: dict[str, Any], plan_path: Path, output_path: Path) -> dict[str, Any]:
    spec_dir = output_path.parent.resolve()
    spec["deck_plan_ref"] = base_relative(plan_path, spec_dir)
    mode = plan.get("operating_mode")
    if mode in {"auto", "assistant"}:
        spec["mode_policy"] = mode
    project_id = spec.get("project_id") or plan.get("request_id") or slugify(str(spec.get("name") or "deck"))
    trace_report = BASE_DIR / "outputs" / "reports" / f"{project_id}_plan_traceability.json"
    spec["plan_traceability_report_path"] = base_relative(trace_report, spec_dir)
    slide_plans = plan.get("slide_plans", [])
    trace_slides: list[dict[str, Any]] = []
    for index, slide in enumerate(spec.get("slides", [])):
        if index >= len(slide_plans) or not isinstance(slide, dict):
            continue
        plan_slide = slide_plans[index]
        plan_slide_id = str(plan_slide.get("plan_slide_id"))
        slide["plan_slide_id"] = plan_slide_id
        slide["plan_decision_refs"] = [
            f"{plan.get('plan_id')}:toc",
            f"{plan.get('plan_id')}:{plan_slide_id}:message",
            f"{plan.get('plan_id')}:{plan_slide_id}:layout_intent",
        ]
        text_slots = slide.setdefault("text_slots", {})
        if isinstance(text_slots, dict) and plan_slide.get("working_title"):
            text_slots["title"] = str(plan_slide["working_title"])
        if plan_slide.get("message"):
            notes = slide.setdefault("report_notes", [])
            if isinstance(notes, list):
                notes.append(f"Plan message: {plan_slide['message']}")
        trace_slides.append(
            {
                "slide_number": index + 1,
                "plan_slide_id": plan_slide_id,
                "working_title": plan_slide.get("working_title"),
                "decision_refs": slide["plan_decision_refs"],
            }
        )
    write_traceability_report(trace_report, plan, output_path, trace_slides)
    return spec


def write_traceability_report(path: Path, plan: dict[str, Any], spec_path: Path, slides: list[dict[str, Any]]) -> None:
    payload = {
        "schema_version": "1.0",
        "status": "valid",
        "plan_id": plan.get("plan_id"),
        "request_id": plan.get("request_id"),
        "spec_path": base_relative(spec_path),
        "deck_plan_ref": base_relative(resolve_base_relative(str(plan.get("source_intake_path", "")))) if plan.get("source_intake_path") else None,
        "summary": {
            "slides": len(slides),
            "operating_mode": plan.get("operating_mode"),
            "approval_state": plan.get("approval_state", {}).get("status"),
        },
        "slides": slides,
    }
    write_json(path, payload)
    md = path.with_suffix(".md")
    lines = [
        f"# Plan Traceability: {payload['request_id']}",
        "",
        f"- plan: `{payload['plan_id']}`",
        f"- spec: `{payload['spec_path']}`",
        f"- mode: `{payload['summary']['operating_mode']}`",
        "",
        "| Slide | Plan slide ID | Working title |",
        "| --- | --- | --- |",
    ]
    for slide in slides:
        lines.append(f"| {slide['slide_number']} | `{slide['plan_slide_id']}` | {slide['working_title']} |")
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compose a deck spec from a deck plan.")
    parser.add_argument("plan_path")
    parser.add_argument("--output", default=None)
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--preferred-user-asset", action="append", default=[])
    args = parser.parse_args(argv)

    plan_path = Path(args.plan_path)
    if not plan_path.is_absolute():
        plan_path = (BASE_DIR / plan_path).resolve()
    plan = load_json(plan_path)
    intake_path = resolve_base_relative(str(plan.get("source_intake_path", "")))
    intake = validate_deck_intake(load_json(intake_path))
    default_output = intake.output_preferences.output_spec_path or f"data/specs/{slugify(intake.name)}_spec.json"
    output_path = Path(args.output or default_output)
    if not output_path.is_absolute():
        output_path = (BASE_DIR / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    spec = compose_spec(intake, intake_path, output_path)
    spec = apply_plan_to_spec(spec, plan, plan_path, output_path)
    workspace = Path(args.workspace).resolve() if args.workspace else None
    append_workspace_asset_intents(
        spec,
        workspace=workspace,
        preferred_asset_ids=list(args.preferred_user_asset),
        operating_mode=spec.get("mode_policy", "auto"),
    )
    validate_deck_spec(spec)
    write_json(output_path, spec)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

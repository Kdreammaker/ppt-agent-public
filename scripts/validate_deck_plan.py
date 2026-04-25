from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
WORK_DIR = BASE_DIR / "outputs" / "deck_plan_validation"
REPORT = BASE_DIR / "outputs" / "reports" / "deck_plan_validation.json"
SCHEMA = BASE_DIR / "config" / "deck_plan.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True, check=False)


def validate_plan_shape(path: Path) -> list[str]:
    plan = load_json(path)
    errors: list[str] = []
    for field in ("schema_version", "plan_id", "request_id", "source_intake_path", "operating_mode", "audience", "goal", "toc", "slide_plans", "brand_style_intent", "assumptions", "approval_state"):
        if field not in plan:
            errors.append(f"{path.name} missing {field}")
    if plan.get("schema_version") != "1.0":
        errors.append(f"{path.name} schema_version must be 1.0")
    if plan.get("operating_mode") not in {"auto", "assistant"}:
        errors.append(f"{path.name} operating_mode invalid")
    slides = plan.get("slide_plans", [])
    if not isinstance(slides, list) or not slides:
        errors.append(f"{path.name} must include slide_plans")
    for index, slide in enumerate(slides, start=1):
        if int(slide.get("slide_number", 0)) != index:
            errors.append(f"{path.name} slide {index} has wrong slide_number")
        for field in ("plan_slide_id", "working_title", "message", "visual_intent", "layout_intent", "asset_intents", "content_budget"):
            if field not in slide:
                errors.append(f"{path.name} slide {index} missing {field}")
    approval = plan.get("approval_state", {})
    if plan.get("operating_mode") == "assistant" and approval.get("required_before_final_build") is not True:
        errors.append("assistant plan must require final-build approval")
    if plan.get("operating_mode") == "auto" and approval.get("required_before_final_build") is not False:
        errors.append("auto plan must not require nonblocking final-build approval")
    serialized = json.dumps(plan, ensure_ascii=False)
    if re.search(r"C:\\Users\\|C:/Users/|external_asset_registry", serialized, re.IGNORECASE):
        errors.append(f"{path.name} leaked local/private path")
    return errors


def main() -> int:
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    checks: dict[str, Any] = {"schema": SCHEMA.relative_to(BASE_DIR).as_posix()}
    try:
        load_json(SCHEMA)
    except Exception as exc:
        errors.append(f"deck plan schema invalid: {exc}")

    auto_intake = WORK_DIR / "auto_intake.json"
    source = load_json(BASE_DIR / "data" / "intake" / "business_growth_review.json")
    source["name"] = "Growth Review Auto Plan Smoke"
    source["review_requirements"]["approval_mode"] = "none"
    source["variation_level"] = "single_path"
    source["output_preferences"]["output_spec_path"] = "outputs/deck_plan_validation/auto_plan_spec.json"
    source["output_preferences"]["output_deck_path"] = "outputs/decks/auto_plan_smoke.pptx"
    write_json(auto_intake, source)

    plans = {
        "auto": WORK_DIR / "auto_deck_plan.json",
        "assistant": WORK_DIR / "assistant_deck_plan.json",
    }
    commands = [
        [sys.executable, "scripts/compose_deck_plan_from_intake.py", auto_intake.as_posix(), "--output", plans["auto"].as_posix(), "--operating-mode", "auto"],
        [sys.executable, "scripts/compose_deck_plan_from_intake.py", "data/intake/business_growth_review.json", "--output", plans["assistant"].as_posix(), "--operating-mode", "assistant"],
    ]
    for command in commands:
        result = run(command)
        if result.returncode != 0:
            errors.append(result.stderr.strip() or result.stdout.strip())
    for mode, path in plans.items():
        if path.exists():
            errors.extend(validate_plan_shape(path))
            if path.with_suffix(".md").exists():
                checks[f"{mode}_markdown"] = path.with_suffix(".md").relative_to(BASE_DIR).as_posix()
            checks[f"{mode}_plan"] = path.relative_to(BASE_DIR).as_posix()
        else:
            errors.append(f"missing {mode} deck plan")

    patch = run(
        [
            sys.executable,
            "scripts/patch_deck_plan.py",
            plans["assistant"].as_posix(),
            "--slide",
            "1",
            "--title",
            "Reviewed Executive Growth Review",
            "--approve-checkpoint",
            "deck_plan_review",
        ]
    )
    if patch.returncode != 0:
        errors.append(f"plan patch failed: {patch.stderr.strip() or patch.stdout.strip()}")
    else:
        patched = load_json(plans["assistant"])
        if patched.get("slide_plans", [{}])[0].get("working_title") != "Reviewed Executive Growth Review":
            errors.append("plan patch did not update slide title")
        if "deck_plan_review" not in patched.get("approval_state", {}).get("approved_checkpoints", []):
            errors.append("plan patch did not record approved checkpoint")
        checks["patch_flow"] = "passed"

    report = {
        "schema_version": "1.0",
        "status": "valid" if not errors else "invalid",
        "summary": {"errors": len(errors), "checks": checks},
        "errors": errors,
    }
    write_json(REPORT, report)
    if errors:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1
    print("deck_plan=valid plans=2 patch_flow=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

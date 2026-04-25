from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
REPORT_DIR = BASE_DIR / "outputs" / "reports"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def utc_stamp() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def base_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def slide_by_number(plan: dict[str, Any], slide_number: int) -> dict[str, Any]:
    for slide in plan.get("slide_plans", []):
        if isinstance(slide, dict) and int(slide.get("slide_number", 0)) == slide_number:
            return slide
    raise ValueError(f"slide not found in deck plan: {slide_number}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Patch a deck plan without regenerating the full plan.")
    parser.add_argument("plan_path")
    parser.add_argument("--slide", type=int, default=None)
    parser.add_argument("--title", default=None)
    parser.add_argument("--message", default=None)
    parser.add_argument("--supporting-point", action="append", default=[])
    parser.add_argument("--approval-status", choices=["pending", "approved", "revise_requested", "skipped", "blocked"], default=None)
    parser.add_argument("--approve-checkpoint", action="append", default=[])
    args = parser.parse_args(argv)

    plan_path = Path(args.plan_path)
    if not plan_path.is_absolute():
        plan_path = (BASE_DIR / plan_path).resolve()
    plan = load_json(plan_path)
    changed: list[str] = []
    backup = plan_path.with_suffix(plan_path.suffix + f".bak-{utc_stamp()}")
    shutil.copy2(plan_path, backup)

    if args.slide is not None:
        slide = slide_by_number(plan, args.slide)
        if args.title is not None:
            slide["working_title"] = args.title
            changed.append(f"slide_{args.slide}.working_title")
        if args.message is not None:
            slide["message"] = args.message
            changed.append(f"slide_{args.slide}.message")
        if args.supporting_point:
            points = list(slide.get("supporting_points", []))
            points.extend(args.supporting_point)
            slide["supporting_points"] = points
            changed.append(f"slide_{args.slide}.supporting_points")
    approval = plan.setdefault("approval_state", {})
    if args.approval_status is not None:
        approval["status"] = args.approval_status
        changed.append("approval_state.status")
    if args.approve_checkpoint:
        checkpoints = list(approval.get("approved_checkpoints", []))
        for checkpoint in args.approve_checkpoint:
            if checkpoint not in checkpoints:
                checkpoints.append(checkpoint)
        approval["approved_checkpoints"] = checkpoints
        changed.append("approval_state.approved_checkpoints")
    if not changed:
        raise SystemExit("No patch arguments were provided.")

    write_json(plan_path, plan)
    report = {
        "schema_version": "1.0",
        "status": "patched",
        "plan_path": base_relative(plan_path),
        "backup_path": base_relative(backup),
        "summary": {
            "changed_fields": changed,
            "full_plan_echoed": False,
        },
    }
    report_path = REPORT_DIR / f"{plan_path.stem}_plan_patch_summary.json"
    write_json(report_path, report)
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

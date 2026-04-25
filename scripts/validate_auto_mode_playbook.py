from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
PLAYBOOK = BASE_DIR / "config" / "mode_playbooks" / "auto_mode_playbook.json"
REPORT = BASE_DIR / "outputs" / "reports" / "auto_mode_playbook_validation.json"
REQUIRED_STAGE_IDS = [
    "intake_normalization",
    "plan_creation",
    "assumption_recording",
    "template_family_selection",
    "brand_style_contract_selection",
    "asset_metadata_search_plan",
    "render",
    "review",
    "revise_rerender",
    "delivery_decision",
]


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    playbook = load_json(PLAYBOOK)
    errors: list[str] = []
    if playbook.get("playbook_id") != "auto_mode_playbook":
        errors.append("playbook_id must be auto_mode_playbook")
    if playbook.get("deck_plan_required") is not True:
        errors.append("Auto playbook must require deck plans")
    if playbook.get("approval_model") != "nonblocking_policy_record":
        errors.append("Auto playbook approval model must be nonblocking_policy_record")
    stage_ids = [str(stage.get("id")) for stage in playbook.get("stages", []) if isinstance(stage, dict)]
    if stage_ids != REQUIRED_STAGE_IDS:
        errors.append(f"Auto stages mismatch: {stage_ids}")
    for stage in playbook.get("stages", []):
        template = BASE_DIR / str(stage.get("template", ""))
        if not template.exists():
            errors.append(f"missing Auto stage template: {stage.get('template')}")
        if "outputs" not in stage or not stage.get("outputs"):
            errors.append(f"stage {stage.get('id')} missing outputs")
    fields = set(playbook.get("required_runtime_report_fields", []))
    for field in ("deck_plan_ref", "assumptions_ref", "stage_artifacts", "revision_decision"):
        if field not in fields:
            errors.append(f"Auto runtime report field missing {field}")
    for skeleton in playbook.get("prompt_skeleton_refs", []):
        if not (BASE_DIR / skeleton).exists():
            errors.append(f"missing prompt skeleton: {skeleton}")
    serialized = json.dumps(playbook, ensure_ascii=False)
    if re.search(r"C:\\Users\\|C:/Users/|external_asset_registry", serialized, re.IGNORECASE):
        errors.append("Auto playbook leaked local/private path")

    report = {
        "schema_version": "1.0",
        "status": "valid" if not errors else "invalid",
        "summary": {"errors": len(errors), "stages": len(stage_ids), "runtime_fields": len(fields)},
        "errors": errors,
    }
    write_json(REPORT, report)
    if errors:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1
    print(f"auto_mode_playbook=valid stages={len(stage_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

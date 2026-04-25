from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
PLAYBOOK = BASE_DIR / "config" / "mode_playbooks" / "assistant_mode_playbook.json"
REPORT = BASE_DIR / "outputs" / "reports" / "assistant_mode_playbook_validation.json"
REQUIRED_CHECKPOINTS = [
    "intake_clarification",
    "deck_plan_review",
    "table_of_contents_review",
    "slide_by_slide_content_plan_review",
    "font_palette_layout_style_review",
    "asset_metadata_candidate_review",
    "final_build_continue_revise_skip_decision",
    "delivery_review",
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
    if playbook.get("playbook_id") != "assistant_mode_playbook":
        errors.append("playbook_id must be assistant_mode_playbook")
    if playbook.get("deck_plan_required") is not True:
        errors.append("Assistant playbook must require deck plans")
    if playbook.get("approval_model") != "explicit_approval_before_final_build_when_review_is_requested":
        errors.append("Assistant approval model mismatch")
    checkpoints = list(playbook.get("checkpoints", []))
    if checkpoints != REQUIRED_CHECKPOINTS:
        errors.append(f"Assistant checkpoints mismatch: {checkpoints}")
    stage_ids = [str(stage.get("id")) for stage in playbook.get("stages", []) if isinstance(stage, dict)]
    if stage_ids != REQUIRED_CHECKPOINTS:
        errors.append(f"Assistant stages mismatch: {stage_ids}")
    for stage in playbook.get("stages", []):
        template = BASE_DIR / str(stage.get("template", ""))
        if not template.exists():
            errors.append(f"missing Assistant stage template: {stage.get('template')}")
        if stage.get("approval_required") is not True:
            errors.append(f"stage {stage.get('id')} must require approval")
    summary_template = BASE_DIR / str(playbook.get("review_summary_template", ""))
    if not summary_template.exists():
        errors.append("Assistant review summary template missing")
    for skeleton in playbook.get("prompt_skeleton_refs", []):
        if not (BASE_DIR / skeleton).exists():
            errors.append(f"missing prompt skeleton: {skeleton}")
    serialized = json.dumps(playbook, ensure_ascii=False)
    if re.search(r"C:\\Users\\|C:/Users/|external_asset_registry", serialized, re.IGNORECASE):
        errors.append("Assistant playbook leaked local/private path")

    report = {
        "schema_version": "1.0",
        "status": "valid" if not errors else "invalid",
        "summary": {"errors": len(errors), "checkpoints": len(checkpoints), "stages": len(stage_ids)},
        "errors": errors,
    }
    write_json(REPORT, report)
    if errors:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1
    print(f"assistant_mode_playbook=valid checkpoints={len(checkpoints)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
POLICY = BASE_DIR / "config" / "prompt_pack_boundary_policy.json"
REPORT = BASE_DIR / "outputs" / "reports" / "prompt_pack_boundary_validation.json"
FORBIDDEN_TEXT_PATTERNS = [
    re.compile(r"private prompt wording", re.IGNORECASE),
    re.compile(r"proprietary example", re.IGNORECASE),
    re.compile(r"raw connector payload", re.IGNORECASE),
    re.compile(r"C:\\Users\\|C:/Users/", re.IGNORECASE),
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
    policy = load_json(POLICY)
    errors: list[str] = []
    if policy.get("policy_id") != "prompt_pack_boundary":
        errors.append("policy_id must be prompt_pack_boundary")
    public = policy.get("public_layer", {})
    private = policy.get("private_layer", {})
    if public.get("skeleton_root") != "docs/mode_playbooks/prompt_skeletons":
        errors.append("public skeleton root mismatch")
    if private.get("manifest_env") != "PPT_AGENT_PRIVATE_PROMPT_PACK_MANIFEST":
        errors.append("private manifest env mismatch")
    for field in ("prompt_pack_id", "version", "compatible_public_skeleton_ids", "checksum", "private_storage_ref"):
        if field not in private.get("required_fields", []):
            errors.append(f"private manifest field missing {field}")
    report_rules = policy.get("public_report_rules", {})
    if report_rules.get("cite_prompt_version_ids_only") is not True:
        errors.append("public reports must cite prompt version IDs only")
    if report_rules.get("never_echo_private_prompt_text") is not True:
        errors.append("public reports must never echo private prompt text")
    skeletons = policy.get("skeletons", [])
    if len(skeletons) < 3:
        errors.append("expected at least three public prompt skeletons")
    for skeleton in skeletons:
        path = BASE_DIR / str(skeleton.get("path", ""))
        if not path.exists():
            errors.append(f"missing prompt skeleton: {skeleton.get('path')}")
            continue
        text = path.read_text(encoding="utf-8")
        if str(skeleton.get("skeleton_id")) not in text:
            errors.append(f"skeleton ID not present in {skeleton.get('path')}")
        for pattern in FORBIDDEN_TEXT_PATTERNS:
            if "do not include" in text.lower() and pattern.pattern.lower().startswith("private"):
                continue
            if pattern.search(text) and "Safety:" not in text:
                errors.append(f"unexpected forbidden phrase in {skeleton.get('path')}: {pattern.pattern}")
        if "{deck_" not in text and "{approval_" not in text and "{checkpoint_" not in text:
            errors.append(f"skeleton lacks placeholders: {skeleton.get('path')}")
    serialized = json.dumps(policy, ensure_ascii=False)
    if re.search(r"C:\\Users\\|C:/Users/|external_asset_registry", serialized, re.IGNORECASE):
        errors.append("prompt pack policy leaked local/private path")

    report = {
        "schema_version": "1.0",
        "status": "valid" if not errors else "invalid",
        "summary": {"errors": len(errors), "skeletons": len(skeletons)},
        "errors": errors,
    }
    write_json(REPORT, report)
    if errors:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1
    print(f"prompt_pack_boundary=valid skeletons={len(skeletons)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

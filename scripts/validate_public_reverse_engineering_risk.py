from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
POLICY = BASE_DIR / "config" / "public_reverse_engineering_risk_policy.json"
REPORT = BASE_DIR / "outputs" / "reports" / "public_reverse_engineering_risk_validation.json"


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
    if policy.get("policy_id") != "public_reverse_engineering_risk":
        errors.append("policy_id must be public_reverse_engineering_risk")
    surfaces = set(policy.get("threat_model", {}).get("abuse_surfaces", []))
    for surface in (
        "public_source_inspection",
        "repeated_local_smoke_execution",
        "public_cli_output_scraping",
        "connector_metadata_search_enumeration",
        "asset_type_fan_out_abuse",
        "prompt_or_playbook_leakage",
        "clean_export_operational_intelligence_leakage",
    ):
        if surface not in surfaces:
            errors.append(f"missing abuse surface: {surface}")
    classifications = policy.get("classifications", {})
    for bucket in ("public", "public_safe_but_sensitive", "private_only", "never_logged"):
        if not isinstance(classifications.get(bucket), list) or not classifications[bucket]:
            errors.append(f"classification bucket missing or empty: {bucket}")
    private_only = set(classifications.get("private_only", []))
    never_logged = set(classifications.get("never_logged", []))
    for item in ("private prompt wording", "private ranking weights", "raw connector payloads"):
        if item not in private_only:
            errors.append(f"private_only missing {item}")
    for item in ("tokens", "workspace codes", "Drive IDs", "approval records", "local absolute private paths"):
        if item not in never_logged:
            errors.append(f"never_logged missing {item}")
    report_rules = policy.get("public_report_rules", {})
    if report_rules.get("forbid_raw_rank_scores") is not True:
        errors.append("public reports must forbid raw rank scores")
    if int(report_rules.get("max_connector_results_per_report", 0)) > 8:
        errors.append("public connector reports must cap visible results at 8")
    clean = policy.get("clean_export_rules", {})
    for key in ("exclude_work_logs", "exclude_handoff_prompts", "exclude_private_prompt_packs", "include_public_safe_playbooks"):
        if clean.get(key) is not True:
            errors.append(f"clean_export_rules.{key} must be true")
    serialized = json.dumps(policy, ensure_ascii=False)
    if re.search(r"C:\\Users\\|C:/Users/", serialized):
        errors.append("policy leaked a local absolute path")

    report = {
        "schema_version": "1.0",
        "status": "valid" if not errors else "invalid",
        "summary": {
            "errors": len(errors),
            "abuse_surfaces": len(surfaces),
            "classification_buckets": len(classifications),
        },
        "errors": errors,
    }
    write_json(REPORT, report)
    if errors:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1
    print(f"public_reverse_engineering_risk=valid surfaces={len(surfaces)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

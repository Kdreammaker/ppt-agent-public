from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
POLICY = BASE_DIR / "config" / "asset_connector_query_governance_policy.json"
MAPPING_CONTRACT = BASE_DIR / "config" / "asset_connector_mapping_contract.json"
USAGE_CONTRACT = BASE_DIR / "config" / "asset_usage_summary_contract.json"
REPORT = BASE_DIR / "outputs" / "reports" / "asset_connector_query_governance_validation.json"


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
    mapping = load_json(MAPPING_CONTRACT)
    usage = load_json(USAGE_CONTRACT)
    errors: list[str] = []
    if policy.get("policy_id") != "asset_connector_query_governance":
        errors.append("policy_id must be asset_connector_query_governance")
    limits = policy.get("limits", {})
    if int(limits.get("max_results_per_asset_type", 999)) > 8:
        errors.append("max_results_per_asset_type must be <= 8")
    if int(limits.get("max_asset_types_per_request", 999)) > 5:
        errors.append("max_asset_types_per_request must be <= 5")
    if int(limits.get("max_similar_queries_per_session", 999)) > 4:
        errors.append("max_similar_queries_per_session must be <= 4")
    supported = set(policy.get("supported_asset_types", []))
    for asset_type in ("palette", "icon", "illustration", "font", "deck_component"):
        if asset_type not in supported:
            errors.append(f"supported_asset_types missing {asset_type}")
    dimensions = set(policy.get("required_request_dimensions", []))
    for dimension in ("intent", "domain", "audience", "medium", "output_surface", "asset_type", "limit"):
        if dimension not in dimensions:
            errors.append(f"required request dimension missing {dimension}")
    summary_fields = set(policy.get("public_summary_fields", []))
    for field in ("quota_status", "scope_status", "redaction_summary", "abuse_state"):
        if field not in summary_fields:
            errors.append(f"public summary field missing {field}")
    safe_fields = set(policy.get("minimum_safe_metadata_fields", []))
    mapping_fields = set(mapping.get("expected_metadata_fields", []))
    usage_fields = set(usage.get("public_summary_fields", []))
    for field in ("semantic_context", "template_media_policy", "license_action", "risk_level"):
        if field not in safe_fields:
            errors.append(f"minimum safe metadata missing {field}")
        if field not in mapping_fields and field not in usage_fields:
            errors.append(f"field {field} not represented by mapping or usage contracts")
    private_audit = set(policy.get("private_audit_fields", []))
    for field in ("raw_rank_scores", "private_registry_refs", "tenant_id", "actor_id"):
        if field not in private_audit:
            errors.append(f"private audit field missing {field}")
    redaction = policy.get("redaction_rules", {})
    for key in ("omit_raw_private_payloads", "omit_raw_rank_scores", "omit_registry_paths", "hash_repeated_query_keys"):
        if redaction.get(key) is not True:
            errors.append(f"redaction_rules.{key} must be true")
    for state in ("rate_limited", "scope_limited", "manual_review_required", "blocked"):
        if state not in policy.get("abuse_states", []):
            errors.append(f"abuse state missing {state}")
    serialized = json.dumps(policy, ensure_ascii=False)
    if re.search(r"C:\\Users\\|C:/Users/|external_asset_registry", serialized, re.IGNORECASE):
        errors.append("query governance policy leaked local/private paths")

    report = {
        "schema_version": "1.0",
        "status": "valid" if not errors else "invalid",
        "summary": {
            "errors": len(errors),
            "asset_types": len(supported),
            "public_summary_fields": len(summary_fields),
            "private_audit_fields": len(private_audit),
        },
        "errors": errors,
    }
    write_json(REPORT, report)
    if errors:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1
    print(f"asset_connector_query_governance=valid asset_types={len(supported)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
